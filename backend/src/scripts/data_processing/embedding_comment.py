"""
Create embeddings for comments stored in the 8 dimension tables and persist them
into comment_embeddings.

Source format:
	each dim table stores user_review as JSON text like:
	{"total": 12, "comments": ["...", "..."]}

Target table:
	comment_embeddings(
		chunk_id SERIAL PRIMARY KEY,
		dim_id INTEGER NOT NULL,
		dim_table VARCHAR(30) NOT NULL,
		list_index INTEGER NOT NULL,
		chunk_index INTEGER NOT NULL DEFAULT 0,
		chunk_text TEXT NOT NULL,
		embedding vector(768),
		created_at TIMESTAMP DEFAULT NOW()
	)

Usage:
	python -m src.scripts.data_processing.embedding_comment
	python -m src.scripts.data_processing.embedding_comment --truncate
	python -m src.scripts.data_processing.embedding_comment --batch-size 64
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

try:
	from sentence_transformers import SentenceTransformer  # pyright: ignore[reportMissingImports]
except ImportError as exc:
	raise SystemExit(
		"Missing dependency 'sentence-transformers'. Install it in backend/requirements.txt and retry."
	) from exc

try:
	from pyvi.ViTokenizer import tokenize  # pyright: ignore[reportMissingImports]
except ImportError as exc:
	raise SystemExit(
		"Missing dependency 'pyvi'. Install it in backend/requirements.txt and retry."
	) from exc

try:
	from langchain_text_splitters import RecursiveCharacterTextSplitter  # pyright: ignore[reportMissingImports]
except ImportError as exc:
	raise SystemExit(
		"Missing dependency 'langchain-text-splitters'. Install it in backend/requirements.txt and retry."
	) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.append(str(PROJECT_ROOT))

from src.app.config.settings import settings
from src.app.database.connection import get_engine
from src.app.database.models import (
	dim_battery,
	dim_camera,
	dim_connectivity,
	dim_design,
	dim_display,
	dim_performance,
	dim_storage,
	dim_utilities,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "dangvantuan/vietnamese-embedding"
EMBEDDING_DIM        = 768

# ── FIX 1 ─────────────────────────────────────────────────────────────────────
# XLM-RoBERTa (base của vietnamese-embedding) có buffer bug khi sequence
# vượt ngưỡng đã tạo buffer lần đầu.
# Safe limit thực tế: 254 tokens (256 - 2 special tokens [CLS][SEP]).
# Đặt MODEL_MAX_TOKENS = 254 và dùng nhất quán ở mọi nơi.
MODEL_MAX_TOKENS = 254   # hard ceiling cho mọi input vào model

# ── FIX 2 ─────────────────────────────────────────────────────────────────────
# Tiếng Việt sau pyvi tokenize: 1 chữ → ~1.5-2 tokens (thêm underscore).
# CHUNK_SIZE phải đủ thấp để sau pyvi vẫn < MODEL_MAX_TOKENS.
# 160 tokens × 1.5 overhead = 240 → vẫn < 254. An toàn.
CHUNK_SIZE_TOKENS    = 160
CHUNK_OVERLAP_TOKENS = 20

SOURCE_TABLES = [
	dim_display,
	dim_camera,
	dim_performance,
	dim_storage,
	dim_design,
	dim_battery,
	dim_connectivity,
	dim_utilities,
]


def connect() -> Any:
	engine = get_engine()
	return engine.raw_connection()


def ensure_target_table(conn: Any) -> None:
	with conn.cursor() as cursor:
		cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS comment_embeddings (
			  chunk_id    SERIAL       PRIMARY KEY,
			  dim_id      INTEGER      NOT NULL,
			  dim_table   VARCHAR(30)  NOT NULL,
			  list_index  INTEGER      NOT NULL,
			  chunk_index INTEGER      NOT NULL DEFAULT 0,
			  chunk_text  TEXT         NOT NULL,
			  embedding   vector(768),
			  created_at  TIMESTAMP    DEFAULT NOW()
			)
			"""
		)
		cursor.execute(
			"""
			ALTER TABLE comment_embeddings
			ADD COLUMN IF NOT EXISTS chunk_index INTEGER NOT NULL DEFAULT 0
			"""
		)
		cursor.execute(
			"""
			DELETE FROM comment_embeddings a
			USING comment_embeddings b
			WHERE a.dim_id      = b.dim_id
			  AND a.dim_table   = b.dim_table
			  AND a.list_index  = b.list_index
			  AND a.chunk_index = b.chunk_index
			  AND a.chunk_id    > b.chunk_id
			"""
		)
		cursor.execute("DROP INDEX IF EXISTS ux_comment_embeddings_source")
		cursor.execute(
			"""
			CREATE UNIQUE INDEX IF NOT EXISTS ux_comment_embeddings_source
			ON comment_embeddings (dim_id, dim_table, list_index, chunk_index)
			"""
		)
	conn.commit()


def truncate_target_table(conn: Any) -> None:
	with conn.cursor() as cursor:
		cursor.execute("TRUNCATE TABLE comment_embeddings RESTART IDENTITY")
	conn.commit()


def normalize_comment_text(value: object) -> str | None:
	if value is None:
		return None
	if isinstance(value, str):
		text_value = value
	elif isinstance(value, dict):
		text_value = value.get("comment_text") or value.get("text") or value.get("comment") or ""
	else:
		text_value = str(value)
	text_value = " ".join(str(text_value).split()).strip()
	return text_value or None


def parse_user_review(raw_value: object) -> dict | None:
	if raw_value is None:
		return None
	if isinstance(raw_value, dict):
		return raw_value
	if isinstance(raw_value, str):
		raw_value = raw_value.strip()
		if not raw_value:
			return None
		try:
			return json.loads(raw_value)
		except json.JSONDecodeError:
			logger.warning("Skip invalid user_review JSON payload.")
			return None
	return None


def preprocess_for_embedding(text: str) -> str:
	"""Tokenize Vietnamese text before encoding to reduce overflow risk."""
	return tokenize(text).strip() or text


def iter_comment_rows(conn: Any, table_name: str) -> Iterator[tuple[int, str, int, str]]:
	with conn.cursor(name=f"read_{table_name}", withhold=True) as cursor:
		cursor.itersize = 1000
		cursor.execute(
			f"""
			SELECT dim_id, user_review
			FROM {table_name}
			WHERE user_review IS NOT NULL
			  AND BTRIM(user_review) <> ''
			ORDER BY dim_id
			"""
		)
		for dim_id, user_review in cursor:
			payload = parse_user_review(user_review)
			if not payload:
				continue
			comments = payload.get("comments") or []
			if not isinstance(comments, list):
				continue
			for list_index, comment in enumerate(comments):
				chunk_text = normalize_comment_text(comment)
				if not chunk_text:
					continue
				yield dim_id, table_name, list_index, chunk_text


def count_model_tokens(model: SentenceTransformer, text: str) -> int:
	return len(
		model.tokenizer(
			text,
			add_special_tokens=False,
			truncation=False,
			verbose=False,
		)["input_ids"]
	)


def build_text_splitter(model: SentenceTransformer) -> RecursiveCharacterTextSplitter:
	def token_length(text: str) -> int:
		return count_model_tokens(model, text)

	return RecursiveCharacterTextSplitter(
		chunk_size=CHUNK_SIZE_TOKENS,
		chunk_overlap=CHUNK_OVERLAP_TOKENS,
		length_function=token_length,
		separators=["\n\n", "\n", ".", "!", "?", ";", ",", " ", ""],
	)


def hard_truncate_for_model(model: SentenceTransformer, text: str) -> str:
	"""
	FIX 3: Hard ceiling = MODEL_MAX_TOKENS (254), bất kể model.max_seq_length.
	Đảm bảo không có input nào vào model vượt ngưỡng buffer an toàn.
	"""
	encoded = model.tokenizer(
		text,
		add_special_tokens=False,
		truncation=True,
		max_length=MODEL_MAX_TOKENS,
		verbose=False,
		return_tensors=None,
	)
	input_ids = (encoded.get("input_ids") or [])[:MODEL_MAX_TOKENS]
	result = model.tokenizer.decode(
		input_ids,
		skip_special_tokens=True,
		clean_up_tokenization_spaces=True,
	).strip()
	if not result:
		return text
	final_token_count = count_model_tokens(model, result)
	if final_token_count > MODEL_MAX_TOKENS:
		logger.warning(
			"hard_truncate still yielded %s tokens after decode — re-truncating.",
			final_token_count,
		)
		input_ids = input_ids[:MODEL_MAX_TOKENS - 10]
		result = model.tokenizer.decode(
			input_ids,
			skip_special_tokens=True,
			clean_up_tokenization_spaces=True,
		).strip() or text
	return result


def chunk_comment_text(splitter: RecursiveCharacterTextSplitter, text: str) -> list[str]:
	processed_text = preprocess_for_embedding(text)
	chunks = [chunk.strip() for chunk in splitter.split_text(processed_text)]
	return [chunk for chunk in chunks if chunk]


def collect_chunk_rows(
	table_names: list[str],
	conn: Any,
	splitter: RecursiveCharacterTextSplitter,
	model: SentenceTransformer,
) -> tuple[list[tuple[int, str, int, int, str]], int, list[int]]:
	chunk_rows: list[tuple[int, str, int, int, str]] = []
	chunk_lengths: list[int] = []
	total_comments = 0

	for table_name in table_names:
		logger.info("Reading source comments from %s ...", table_name)
		for dim_id, source_table, list_index, chunk_text in iter_comment_rows(conn, table_name):
			total_comments += 1
			chunks = chunk_comment_text(splitter, chunk_text)
			for chunk_index, chunk in enumerate(chunks):
				# ── FIX 4 ────────────────────────────────────────────────────
				# Đếm token SAU pyvi tokenize, trước khi đưa vào model.
				# Nếu vẫn > MODEL_MAX_TOKENS thì hard_truncate sẽ xử lý trong flush.
				chunk_token_count = count_model_tokens(model, chunk)
				if chunk_token_count > MODEL_MAX_TOKENS:
					logger.warning(
						"Chunk exceeds MODEL_MAX_TOKENS after split: "
						"%s.dim_id=%s list=%s chunk=%s tokens=%s — will hard-truncate.",
						source_table, dim_id, list_index, chunk_index, chunk_token_count,
					)
				chunk_rows.append((dim_id, source_table, list_index, chunk_index, chunk))
				chunk_lengths.append(chunk_token_count)
		logger.info("Finished scanning %s.", table_name)

	return chunk_rows, total_comments, chunk_lengths


def render_progress(current: int, total: int) -> None:
	if total <= 0:
		return
	ratio = min(max(current / total, 0.0), 1.0)
	bar_width = 28
	filled = int(bar_width * ratio)
	bar = "#" * filled + "-" * (bar_width - filled)
	sys.stdout.write(f"\r[{bar}] {ratio * 100:6.2f}% ({current}/{total})")
	sys.stdout.flush()
	if current >= total:
		sys.stdout.write("\n")
		sys.stdout.flush()


def to_vector_literal(embedding: Iterable[float]) -> str:
	return "[" + ",".join(f"{float(value):.8f}" for value in embedding) + "]"


def flush_batch(
	conn: Any,
	model: SentenceTransformer,
	batch: list[tuple[int, str, int, int, str]],
) -> int:
	if not batch:
		return 0

	# ── FIX 5 ─────────────────────────────────────────────────────────────────
	# Mọi text đều đi qua hard_truncate trước khi vào model.encode().
	# Đây là tuyến phòng thủ cuối — kể cả chunk đã qua splitter vẫn được check.
	texts = [hard_truncate_for_model(model, item[4]) for item in batch]

	# ── FIX 6 ─────────────────────────────────────────────────────────────────
	# Verify toàn bộ batch TRƯỚC khi gọi model.encode().
	# Nếu có bất kỳ text nào vẫn > MODEL_MAX_TOKENS → log và cắt thêm.
	safe_texts = []
	for i, text in enumerate(texts):
		token_count = count_model_tokens(model, text)
		if token_count > MODEL_MAX_TOKENS:
			logger.error(
				"Text still exceeds MODEL_MAX_TOKENS=%s after hard_truncate (tokens=%s). "
				"Force re-truncate at token level.",
				MODEL_MAX_TOKENS,
				token_count,
			)
			encoded = model.tokenizer(
				text,
				add_special_tokens=False,
				truncation=True,
				max_length=MODEL_MAX_TOKENS - 10,  # extra safety margin
				return_tensors=None,
				verbose=False,
			)
			text = model.tokenizer.decode(
				encoded["input_ids"],
				skip_special_tokens=True,
				clean_up_tokenization_spaces=True,
			).strip() or text
		safe_texts.append(text)

	embeddings = model.encode(
		safe_texts,
		batch_size=max(1, min(64, len(safe_texts))),
		normalize_embeddings=True,
		convert_to_numpy=True,
		show_progress_bar=False,
	)

	if len(embeddings) != len(batch):
		raise RuntimeError("Embedding batch size does not match source batch size.")

	rows = []
	for (dim_id, dim_table, list_index, chunk_index, chunk_text), embedding in zip(batch, embeddings):
		if len(embedding) != EMBEDDING_DIM:
			raise RuntimeError(
				f"Unexpected embedding dimension for {dim_table}:{dim_id} -> {len(embedding)}"
			)
		rows.append((dim_id, dim_table, list_index, chunk_index, chunk_text, to_vector_literal(embedding)))

	with conn.cursor() as cursor:
		cursor.executemany(
			"""
			INSERT INTO comment_embeddings (
				dim_id, dim_table, list_index, chunk_index, chunk_text, embedding
			) VALUES (%s, %s, %s, %s, %s, %s::vector)
			ON CONFLICT (dim_id, dim_table, list_index, chunk_index) DO NOTHING
			""",
			rows,
		)
	conn.commit()
	return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed comments from dimension tables into comment_embeddings."
    )
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--truncate", action="store_true")
    parser.add_argument(
        "--tables",
        type=str,
        default=",".join(table.name for table in SOURCE_TABLES),
    )
    args = parser.parse_args()

    table_names = [name.strip() for name in args.tables.split(",") if name.strip()]
    allowed_table_names = {table.name for table in SOURCE_TABLES}
    invalid_table_names = [name for name in table_names if name not in allowed_table_names]
    if invalid_table_names:
        raise SystemExit(
            f"Unsupported table name(s): {', '.join(invalid_table_names)}. "
            f"Use one of: {', '.join(sorted(allowed_table_names))}"
        )

    logger.info("Connecting to DB %s:%s/%s ...", settings.db_host, settings.db_port, settings.db_name)
    conn = connect()
    logger.info("DB connection ready.")

    try:
        ensure_target_table(conn)
        if args.truncate:
            truncate_target_table(conn)
            logger.info("comment_embeddings truncated.")

        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        model.max_seq_length = MODEL_MAX_TOKENS
        logger.info("Model max_seq_length set to %s.", MODEL_MAX_TOKENS)

        splitter = build_text_splitter(model)
        logger.info(
            "LangChain chunking: chunk_size=%s tokens, chunk_overlap=%s tokens.",
            CHUNK_SIZE_TOKENS,
            CHUNK_OVERLAP_TOKENS,
        )

        # ── THAY ĐỔI: stream trực tiếp, không collect all ──────────────────
        batch: list[tuple[int, str, int, int, str]] = []
        total_inserted  = 0
        total_comments  = 0
        total_chunks    = 0

        for table_name in table_names:
            logger.info("Processing %s ...", table_name)
            table_inserted = 0

            for dim_id, src_table, list_index, comment in iter_comment_rows(conn, table_name):
                total_comments += 1
                chunks = chunk_comment_text(splitter, comment)

                for chunk_index, chunk in enumerate(chunks):
                    total_chunks += 1
                    batch.append((dim_id, src_table, list_index, chunk_index, chunk))

                    if len(batch) >= args.batch_size:
                        inserted     = flush_batch(conn, model, batch)
                        total_inserted  += inserted
                        table_inserted  += inserted
                        batch = []
                        sys.stdout.write(
                            f"\r  {table_name} | comments={total_comments:,} "
                            f"chunks={total_chunks:,} inserted={total_inserted:,}"
                        )
                        sys.stdout.flush()

            # Flush phần còn dư của bảng hiện tại
            if batch:
                inserted       = flush_batch(conn, model, batch)
                total_inserted += inserted
                table_inserted += inserted
                batch = []

            logger.info("✓ %s done | inserted=%s", table_name, f"{table_inserted:,}")

        logger.info(
            "All done. comments=%s | chunks=%s | inserted=%s",
            f"{total_comments:,}",
            f"{total_chunks:,}",
            f"{total_inserted:,}",
        )

    except KeyboardInterrupt:
        conn.rollback()
        logger.warning("Interrupted. Transaction rolled back.")
        raise SystemExit(130)
    except Exception as exc:
        conn.rollback()
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        raise SystemExit(1) from exc
    finally:
        conn.close()
        logger.info("DB connection closed.")


if __name__ == "__main__":
	main()