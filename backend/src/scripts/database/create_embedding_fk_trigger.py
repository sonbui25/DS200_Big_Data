"""
Create a trigger on comment_embeddings that validates dim_id exists
in the correct dim table (based on dim_table column).

This acts as a "polymorphic foreign key" without changing the table schema.

What it does:
  - On INSERT or UPDATE: checks that dim_id exists in the table named by dim_table
  - If dim_id is invalid -> raises exception, row is rejected
  - If dim_table is not one of the 8 allowed tables -> raises exception

Does NOT:
  - Change any table schema
  - Add columns or indexes
  - Affect existing data or queries

Usage:
  python -m src.scripts.database.create_embedding_fk_trigger
  python -m src.scripts.database.create_embedding_fk_trigger --drop   (remove trigger)
  python -m src.scripts.database.create_embedding_fk_trigger --verify (test with sample data)
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

ALLOWED_DIM_TABLES = [
	"dim_display",
	"dim_camera",
	"dim_performance",
	"dim_storage",
	"dim_design",
	"dim_battery",
	"dim_connectivity",
	"dim_utilities",
]

TRIGGER_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION check_comment_embedding_dim_fk()
RETURNS TRIGGER AS $$
DECLARE
	allowed_tables TEXT[] := ARRAY[
		'dim_display', 'dim_camera', 'dim_performance', 'dim_storage',
		'dim_design', 'dim_battery', 'dim_connectivity', 'dim_utilities'
	];
	dim_exists BOOLEAN;
BEGIN
	-- Validate dim_table is one of the allowed tables
	IF NOT (NEW.dim_table = ANY(allowed_tables)) THEN
		RAISE EXCEPTION
			'Invalid dim_table="%". Must be one of: %',
			NEW.dim_table, array_to_string(allowed_tables, ', ');
	END IF;

	-- Check dim_id exists in the referenced dim table
	EXECUTE format(
		'SELECT EXISTS (SELECT 1 FROM %I WHERE dim_id = $1)',
		NEW.dim_table
	) INTO dim_exists USING NEW.dim_id;

	IF NOT dim_exists THEN
		RAISE EXCEPTION
			'FK violation: dim_id=% does not exist in table "%"',
			NEW.dim_id, NEW.dim_table;
	END IF;

	RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGER_SQL = """
DROP TRIGGER IF EXISTS trg_check_dim_fk ON comment_embeddings;
CREATE TRIGGER trg_check_dim_fk
	BEFORE INSERT OR UPDATE ON comment_embeddings
	FOR EACH ROW
	EXECUTE FUNCTION check_comment_embedding_dim_fk();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS trg_check_dim_fk ON comment_embeddings;
DROP FUNCTION IF EXISTS check_comment_embedding_dim_fk();
"""


def connect() -> Any:
	engine = get_engine()
	return engine.raw_connection()


def create_trigger(conn: Any) -> None:
	cur = conn.cursor()

	logger.info("Creating trigger function: check_comment_embedding_dim_fk()")
	cur.execute(TRIGGER_FUNCTION_SQL)

	logger.info("Creating trigger: trg_check_dim_fk on comment_embeddings")
	cur.execute(TRIGGER_SQL)

	conn.commit()
	logger.info("Trigger created successfully.")
	cur.close()


def drop_trigger(conn: Any) -> None:
	cur = conn.cursor()

	logger.info("Dropping trigger and function...")
	cur.execute(DROP_SQL)

	conn.commit()
	logger.info("Trigger removed.")
	cur.close()


def verify_trigger(conn: Any) -> None:
	"""Test the trigger with fake data to confirm it works."""
	cur = conn.cursor()

	# 1. Verify trigger exists
	cur.execute("""
		SELECT tgname FROM pg_trigger
		WHERE tgrelid = 'comment_embeddings'::regclass
		  AND tgname = 'trg_check_dim_fk'
	""")
	row = cur.fetchone()
	if not row:
		logger.error("Trigger trg_check_dim_fk NOT FOUND on comment_embeddings!")
		return
	logger.info("Trigger exists: %s", row[0])

	# 2. Test: invalid dim_table should be rejected
	logger.info("Test 1: INSERT with invalid dim_table='fake_table' ...")
	try:
		cur.execute("""
			INSERT INTO comment_embeddings
				(dim_id, dim_table, list_index, chunk_index, chunk_text)
			VALUES (1, 'fake_table', 0, 0, 'test')
		""")
		conn.rollback()
		logger.error("  FAIL: should have raised exception but didn't!")
	except Exception as exc:
		conn.rollback()
		logger.info("  PASS: rejected with: %s", str(exc).strip().split('\n')[0])

	# 3. Test: invalid dim_id should be rejected
	logger.info("Test 2: INSERT with valid dim_table but non-existent dim_id=999999 ...")
	try:
		cur.execute("""
			INSERT INTO comment_embeddings
				(dim_id, dim_table, list_index, chunk_index, chunk_text)
			VALUES (999999, 'dim_battery', 0, 0, 'test')
		""")
		conn.rollback()
		logger.error("  FAIL: should have raised exception but didn't!")
	except Exception as exc:
		conn.rollback()
		logger.info("  PASS: rejected with: %s", str(exc).strip().split('\n')[0])

	# 4. Test: valid dim_id should be accepted (then rollback)
	logger.info("Test 3: INSERT with valid dim_table and real dim_id=1 ...")
	try:
		cur.execute("""
			INSERT INTO comment_embeddings
				(dim_id, dim_table, list_index, chunk_index, chunk_text)
			VALUES (1, 'dim_battery', 99999, 99999, 'trigger_test_row')
		""")
		conn.rollback()  # rollback so we don't leave test data
		logger.info("  PASS: accepted (rolled back test row)")
	except Exception as exc:
		conn.rollback()
		logger.error("  FAIL: rejected valid data: %s", str(exc).strip().split('\n')[0])

	logger.info("Verification complete.")
	cur.close()


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Create/drop trigger for polymorphic FK on comment_embeddings."
	)
	parser.add_argument("--drop", action="store_true", help="Remove trigger instead of creating.")
	parser.add_argument("--verify", action="store_true", help="Test trigger with sample data.")
	args = parser.parse_args()

	logger.info("Connecting to DB %s:%s/%s ...", settings.db_host, settings.db_port, settings.db_name)
	conn = connect()

	try:
		if args.drop:
			drop_trigger(conn)
		else:
			create_trigger(conn)
			if args.verify:
				verify_trigger(conn)
	except Exception as exc:
		conn.rollback()
		logger.error("Failed: %s", exc, exc_info=True)
		raise SystemExit(1) from exc
	finally:
		conn.close()
		logger.info("DB connection closed.")


if __name__ == "__main__":
	main()
