"""
Continue creating embeddings for the REMAINING 5 dimension tables
that were NOT processed by the original embedding_comment.py run.

Already done (by embedding_comment.py):
	dim_display, dim_camera, dim_performance

This script processes:
	dim_storage, dim_design, dim_battery, dim_connectivity, dim_utilities

IMPORTANT:
	- Does NOT truncate or delete any existing data in comment_embeddings.
	- chunk_id (SERIAL) continues naturally from the last ID in the table.
	- Uses ON CONFLICT DO NOTHING so re-runs are safe (idempotent).

Usage:
	python -m src.scripts.data_processing.embedding_comment_remaining
	python -m src.scripts.data_processing.embedding_comment_remaining --batch-size 64
	python -m src.scripts.data_processing.embedding_comment_remaining --max-comments 3000
"""

from __future__ import annotations

import argparse
import json
import logging
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
	dim_connectivity,
	dim_design,
	dim_storage,
	dim_utilities,
)


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "dangvantuan/vietnamese-embedding"
EMBEDDING_DIM        = 768

MODEL_MAX_TOKENS     = 254
CHUNK_SIZE_TOKENS    = 160
CHUNK_OVERLAP_TOKENS = 20

# ── CHI XU LY 5 BANG CON LAI ─────────────────────────────────────────────────
REMAINING_TABLES = [
	dim_storage,
	dim_design,
	dim_battery,
	dim_connectivity,
	dim_utilities,
]


def connect() -> Any:
	engine = get_engine()
	return engine.raw_connection()


def preflight_check(conn: Any) -> None:
	"""
	Safety check: log existing data stats so user can verify continuity.
	Does NOT modify any data.
	"""
	with conn.cursor() as cursor:
		cursor.execute("SELECT COUNT(*), MAX(chunk_id) FROM comment_embeddings")
		total_rows, max_id = cursor.fetchone()
		logger.info(
			"Pre-flight: comment_embeddings has %s existing rows, max chunk_id = %s",
			f"{total_rows:,}" if total_rows else 0,
			max_id or 0,
		)

		cursor.execute(
			"""
			SELECT dim_table, COUNT(*) as cnt
			FROM comment_embeddings
			GROUP BY dim_table
			ORDER BY dim_table
			"""
		)
		for dim_table, cnt in cursor.fetchall():
			logger.info("  existing: %-25s  %s rows", dim_table, f"{cnt:,}")

		# Warn if any of the remaining tables already have partial data
		remaining_names = [t.name for t in REMAINING_TABLES]
		cursor.execute(
			"""
			SELECT dim_table, COUNT(*) as cnt
			FROM comment_embeddings
			WHERE dim_table = ANY(%s)
			GROUP BY dim_table
			""",
			(remaining_names,),
		)
		partial = cursor.fetchall()
		if partial:
			for dim_table, cnt in partial:
				logger.warning(
					"  ⚠ %s already has %s rows — ON CONFLICT DO NOTHING will skip duplicates.",
					dim_table,
					f"{cnt:,}",
				)
		else:
			logger.info("  No existing data for the 5 remaining tables — clean append.")


def ensure_table_and_index(conn: Any) -> None:
	"""
	Ensure table and unique index exist. Does NOT truncate or delete anything.
	"""
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
			CREATE UNIQUE INDEX IF NOT EXISTS ux_comment_embeddings_source
			ON comment_embeddings (dim_id, dim_table, list_index, chunk_index)
			"""
		)
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


def to_vector_literal(embedding: Iterable[float]) -> str:
	return "[" + ",".join(f"{float(value):.8f}" for value in embedding) + "]"


def flush_batch(
	conn: Any,
	model: SentenceTransformer,
	batch: list[tuple[int, str, int, int, str]],
) -> int:
	if not batch:
		return 0

	texts = [hard_truncate_for_model(model, item[4]) for item in batch]

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
				max_length=MODEL_MAX_TOKENS - 10,
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
		description=(
			"Embed comments from the 5 REMAINING dimension tables "
			"(storage, design, battery, connectivity, utilities) "
			"into comment_embeddings. Appends only — never truncates."
		),
	)
	parser.add_argument("--batch-size", type=int, default=1024)
	parser.add_argument(
		"--max-comments",
		type=int,
		default=3000,
		help="Max comments to process PER TABLE (default: 3000, 0 = unlimited).",
	)
	args = parser.parse_args()

	remaining_table_names = [t.name for t in REMAINING_TABLES]

	max_comments_per_table = args.max_comments if args.max_comments > 0 else None

	logger.info("=" * 60)
	logger.info("EMBEDDING REMAINING TABLES ONLY")
	logger.info("Tables: %s", ", ".join(remaining_table_names))
	logger.info("Max comments per table: %s", max_comments_per_table or "unlimited")
	logger.info("Mode: APPEND (no truncate, no delete)")
	logger.info("=" * 60)

	logger.info("Connecting to DB %s:%s/%s ...", settings.db_host, settings.db_port, settings.db_name)
	conn = connect()
	logger.info("DB connection ready.")

	try:
		ensure_table_and_index(conn)
		preflight_check(conn)

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

		batch: list[tuple[int, str, int, int, str]] = []
		total_inserted = 0
		total_comments = 0
		total_chunks   = 0

		for table_name in remaining_table_names:
			logger.info("Processing %s ...", table_name)
			table_inserted = 0
			table_comments = 0

			for dim_id, src_table, list_index, comment in iter_comment_rows(conn, table_name):
				if max_comments_per_table and table_comments >= max_comments_per_table:
					logger.info(
						"  ⏭ %s reached --max-comments=%s, skipping rest.",
						table_name,
						max_comments_per_table,
					)
					break

				total_comments += 1
				table_comments += 1
				chunks = chunk_comment_text(splitter, comment)

				for chunk_index, chunk in enumerate(chunks):
					total_chunks += 1
					batch.append((dim_id, src_table, list_index, chunk_index, chunk))

					if len(batch) >= args.batch_size:
						inserted        = flush_batch(conn, model, batch)
						total_inserted += inserted
						table_inserted += inserted
						batch = []
						sys.stdout.write(
							f"\r  {table_name} | comments={table_comments:,}/{max_comments_per_table or '∞'} "
							f"chunks={total_chunks:,} inserted={total_inserted:,}"
						)
						sys.stdout.flush()

			if batch:
				inserted        = flush_batch(conn, model, batch)
				total_inserted += inserted
				table_inserted += inserted
				batch = []

			logger.info(
				"✓ %s done | comments=%s | inserted=%s",
				table_name,
				f"{table_comments:,}",
				f"{table_inserted:,}",
			)

		# Post-flight: verify final state
		with conn.cursor() as cursor:
			cursor.execute("SELECT COUNT(*), MAX(chunk_id) FROM comment_embeddings")
			final_total, final_max_id = cursor.fetchone()

		logger.info("=" * 60)
		logger.info(
			"All done. comments=%s | chunks=%s | inserted=%s",
			f"{total_comments:,}",
			f"{total_chunks:,}",
			f"{total_inserted:,}",
		)
		logger.info(
			"Final state: total rows = %s, max chunk_id = %s",
			f"{final_total:,}" if final_total else 0,
			final_max_id or 0,
		)
		logger.info("=" * 60)

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
