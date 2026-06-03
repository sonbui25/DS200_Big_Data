"""
Migrate comment_embeddings -> partitioned table with FK per partition.

Flow:
  1. Rename comment_embeddings -> comment_embeddings_old
  2. Create new comment_embeddings (PARTITION BY LIST dim_table)
  3. Create 8 partitions, each with FK to its dim table
  4. Copy data from old -> new (chunk_id preserved)
  5. Reset sequence to continue from max(chunk_id) + 1
  6. Verify row counts match
  7. Drop old table

Usage:
  python -m src.scripts.database.migrate_partition_embeddings
  python -m src.scripts.database.migrate_partition_embeddings --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.append(str(PROJECT_ROOT))

from src.app.config.settings import settings
from src.app.database.connection import get_engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# dim_table value -> referenced table name
PARTITIONS = {
	"dim_display":      "dim_display",
	"dim_camera":       "dim_camera",
	"dim_performance":  "dim_performance",
	"dim_storage":      "dim_storage",
	"dim_design":       "dim_design",
	"dim_battery":      "dim_battery",
	"dim_connectivity": "dim_connectivity",
	"dim_utilities":    "dim_utilities",
}


def connect() -> Any:
	engine = get_engine()
	return engine.raw_connection()


def run_migration(conn: Any, dry_run: bool = False) -> None:
	cur = conn.cursor()

	# ── 0. Detect state: fresh or resume ──────────────────────────────────
	cur.execute("""
		SELECT EXISTS (
			SELECT 1 FROM information_schema.tables
			WHERE table_name = 'comment_embeddings_old'
		)
	""")
	old_table_exists = cur.fetchone()[0]

	if old_table_exists:
		# Resume mode: Step 1-3 already done, just need to copy remaining data
		logger.info("RESUME MODE: comment_embeddings_old found. Skipping Step 1-3.")
		source_table = "comment_embeddings_old"
	else:
		source_table = "comment_embeddings"

	cur.execute(f"SELECT COUNT(*) FROM {source_table}")
	old_count = cur.fetchone()[0]
	logger.info("Source rows in %s: %s", source_table, f"{old_count:,}")

	cur.execute(f"SELECT MAX(chunk_id) FROM {source_table}")
	max_chunk_id = cur.fetchone()[0] or 0
	logger.info("Max chunk_id: %s", max_chunk_id)

	# Show per-table counts in source
	cur.execute(f"""
		SELECT dim_table, COUNT(*) FROM {source_table}
		GROUP BY dim_table ORDER BY dim_table
	""")
	for dim_table, cnt in cur.fetchall():
		logger.info("  %-25s %s rows", dim_table, f"{cnt:,}")

	if dry_run:
		logger.info("[DRY RUN] Would migrate %s rows into 8 partitions. Stopping.", f"{old_count:,}")
		return

	if not old_table_exists:
		# ── 1. Rename old table ───────────────────────────────────────────
		logger.info("Step 1: Rename comment_embeddings -> comment_embeddings_old")
		cur.execute("ALTER TABLE comment_embeddings RENAME TO comment_embeddings_old")
		conn.commit()

		# ── 2. Create partitioned parent table ────────────────────────────
		logger.info("Step 2: Create partitioned comment_embeddings")
		cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
		cur.execute("""
			CREATE TABLE comment_embeddings (
				chunk_id    INTEGER      NOT NULL,
				dim_id      INTEGER      NOT NULL,
				dim_table   VARCHAR(30)  NOT NULL,
				list_index  INTEGER      NOT NULL,
				chunk_index INTEGER      NOT NULL DEFAULT 0,
				chunk_text  TEXT         NOT NULL,
				embedding   vector(768),
				created_at  TIMESTAMP    DEFAULT NOW(),
				PRIMARY KEY (chunk_id, dim_table)
			) PARTITION BY LIST (dim_table)
		""")
		conn.commit()

		# ── 3. Create partitions with FK ──────────────────────────────────
		logger.info("Step 3: Create 8 partitions with foreign keys")
		for dim_table_value, ref_table in PARTITIONS.items():
			short_name = dim_table_value.replace("dim_", "")
			partition_name = f"comment_embeddings_{short_name}"

			cur.execute(f"""
				CREATE TABLE {partition_name}
				PARTITION OF comment_embeddings
				FOR VALUES IN ('{dim_table_value}')
			""")

			cur.execute(f"""
				ALTER TABLE {partition_name}
				ADD CONSTRAINT fk_{short_name}_dim_id
				FOREIGN KEY (dim_id) REFERENCES {ref_table} (dim_id)
			""")

			logger.info("  Created %s -> FK to %s.dim_id", partition_name, ref_table)

		conn.commit()
	else:
		logger.info("Step 1-3: SKIPPED (already done)")

	# ── 4. Copy data (per partition to avoid timeout) ────────────────────
	logger.info("Step 4: Copy data from old table to partitioned table (per partition)")
	copied_total = 0

	for dim_table_value in PARTITIONS:
		batch_size = 10000
		copied_table = 0

		# Resume: check if this partition already has data (from previous failed run)
		cur.execute("""
			SELECT MAX(chunk_id) FROM comment_embeddings
			WHERE dim_table = %s
		""", (dim_table_value,))
		last_id = cur.fetchone()[0] or 0
		if last_id > 0:
			cur.execute("""
				SELECT COUNT(*) FROM comment_embeddings
				WHERE dim_table = %s
			""", (dim_table_value,))
			already = cur.fetchone()[0]
			logger.info("  %s: resuming from chunk_id=%s (%s rows already copied)", dim_table_value, last_id, f"{already:,}")

		while True:
			cur.execute(f"""
				INSERT INTO comment_embeddings
					(chunk_id, dim_id, dim_table, list_index, chunk_index, chunk_text, embedding, created_at)
				SELECT
					chunk_id, dim_id, dim_table, list_index, chunk_index, chunk_text, embedding, created_at
				FROM comment_embeddings_old
				WHERE dim_table = %s
				  AND chunk_id > %s
				ORDER BY chunk_id
				LIMIT %s
			""", (dim_table_value, last_id, batch_size))

			rows = cur.rowcount
			if rows == 0:
				break

			conn.commit()
			copied_table += rows
			copied_total += rows

			# Get last chunk_id inserted in this batch
			cur.execute("""
				SELECT MAX(chunk_id) FROM comment_embeddings
				WHERE dim_table = %s
			""", (dim_table_value,))
			last_id = cur.fetchone()[0] or 0

			sys.stdout.write(
				f"\r  {dim_table_value}: {copied_table:,} rows copied"
			)
			sys.stdout.flush()

		if copied_table > 0:
			sys.stdout.write("\n")
			sys.stdout.flush()
		logger.info("  %-25s %s rows copied", dim_table_value, f"{copied_table:,}")

	logger.info("  Total copied: %s", f"{copied_total:,}")

	# ── 5. Create sequence + indexes ──────────────────────────────────────
	logger.info("Step 5: Create sequence and indexes")

	# Sequence for chunk_id (continue from max)
	cur.execute("DROP SEQUENCE IF EXISTS comment_embeddings_chunk_id_seq CASCADE")
	cur.execute(f"""
		CREATE SEQUENCE comment_embeddings_chunk_id_seq
		START WITH {max_chunk_id + 1}
		OWNED BY comment_embeddings.chunk_id
	""")
	cur.execute("""
		ALTER TABLE comment_embeddings
		ALTER COLUMN chunk_id SET DEFAULT nextval('comment_embeddings_chunk_id_seq')
	""")

	# Unique index (same as original)
	cur.execute("""
		CREATE UNIQUE INDEX ux_comment_embeddings_source
		ON comment_embeddings (dim_id, dim_table, list_index, chunk_index)
	""")

	conn.commit()

	# ── 6. Verify ────────────────────────────────────────────────────────
	logger.info("Step 6: Verify migration")
	cur.execute("SELECT COUNT(*) FROM comment_embeddings")
	new_count = cur.fetchone()[0]

	cur.execute("SELECT COUNT(*) FROM comment_embeddings_old")
	old_verify = cur.fetchone()[0]

	if new_count != old_verify:
		raise RuntimeError(
			f"Row count mismatch! old={old_verify:,} new={new_count:,}. "
			f"Old table kept as comment_embeddings_old for recovery."
		)

	logger.info("  old=%s, new=%s — MATCH", f"{old_verify:,}", f"{new_count:,}")

	# Verify per-partition
	cur.execute("""
		SELECT dim_table, COUNT(*) FROM comment_embeddings
		GROUP BY dim_table ORDER BY dim_table
	""")
	for dim_table, cnt in cur.fetchall():
		logger.info("  partition %-25s %s rows", dim_table, f"{cnt:,}")

	# Verify FKs exist
	cur.execute("""
		SELECT conname, conrelid::regclass, confrelid::regclass
		FROM pg_constraint
		WHERE contype = 'f'
		  AND conrelid::regclass::text LIKE 'comment_embeddings_%'
		ORDER BY conname
	""")
	fk_rows = cur.fetchall()
	logger.info("  Foreign keys created: %s", len(fk_rows))
	for fk_name, src, ref in fk_rows:
		logger.info("    %s: %s -> %s", fk_name, src, ref)

	# ── 7. Drop old table ────────────────────────────────────────────────
	logger.info("Step 7: Drop comment_embeddings_old")
	cur.execute("DROP TABLE comment_embeddings_old")
	conn.commit()

	logger.info("=" * 60)
	logger.info("Migration complete!")
	logger.info("  Total rows: %s", f"{new_count:,}")
	logger.info("  Partitions: %s", len(PARTITIONS))
	logger.info("  Foreign keys: %s", len(fk_rows))
	logger.info("  Next chunk_id: %s", max_chunk_id + 1)
	logger.info("=" * 60)

	cur.close()


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Migrate comment_embeddings to partitioned table with FK per partition."
	)
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="Only show what would happen, don't execute.",
	)
	args = parser.parse_args()

	logger.info("Connecting to DB %s:%s/%s ...", settings.db_host, settings.db_port, settings.db_name)
	conn = connect()

	try:
		run_migration(conn, dry_run=args.dry_run)
	except Exception as exc:
		conn.rollback()
		logger.error("Migration FAILED: %s", exc, exc_info=True)
		logger.error("If partial, check if comment_embeddings_old exists for recovery.")
		raise SystemExit(1) from exc
	finally:
		conn.close()
		logger.info("DB connection closed.")


if __name__ == "__main__":
	main()
