import argparse
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import Connection, Engine

from src.app.database.connection import get_engine, health_check
from src.app.database.models import (
    dim_battery,
    dim_camera,
    dim_connectivity,
    dim_design,
    dim_display,
    dim_performance,
    dim_storage,
    dim_utilities,
    dim_video_comments,
    dim_video_transcripts,
    fact_product,
)

DIM_TABLES = [
    dim_display,
    dim_camera,
    dim_performance,
    dim_storage,
    dim_design,
    dim_battery,
    dim_connectivity,
    dim_utilities,
]


def _read_json_file(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list JSON in {path}")
    return data


def _build_link_index(raw_links: list[dict]) -> dict[str, dict]:
    link_index: dict[str, dict] = {}
    for item in raw_links:
        url = item.get("url")
        if isinstance(url, str) and url:
            link_index[url] = item
    return link_index


def _truncate_youtube_tables(connection: Connection) -> None:
    connection.execute(
        text("TRUNCATE TABLE dim_video_comments, dim_video_transcripts RESTART IDENTITY CASCADE")
    )


def _truncate_tables(connection: Connection) -> None:
    table_names = [dim_video_comments.name, dim_video_transcripts.name, *(table.name for table in DIM_TABLES), fact_product.name]
    connection.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))


def _sanitize_payload_for_table(table, payload: dict) -> dict:
    sanitized_payload: dict = {}
    for key, value in payload.items():
        if key not in table.c:
            continue
        sanitized_payload[key] = value
    return sanitized_payload

def _build_fact_payload(record: dict) -> dict:
    fact_payload = dict(record.get("fact_product") or {})
    fact_payload["product_name"] = record.get("search_query_name") or fact_payload.get("product_name")
    return fact_payload

def _insert_single_product(
    connection: Connection,
    record: dict,
    link_index: dict[str, dict],
) -> None:
    fact_payload = _build_fact_payload(record)
    source_url = record.get("_source_url")
    extra_link_data = link_index.get(source_url, {})
    fact_payload["price"] = extra_link_data.get("price_vnd")
    fact_payload["picture_url"] = extra_link_data.get("image")

    sanitized_fact_payload = _sanitize_payload_for_table(fact_product, fact_payload)
    insert_result = connection.execute(fact_product.insert().values(**sanitized_fact_payload))
    product_id = insert_result.inserted_primary_key[0]

    for dim_table in DIM_TABLES:
        dim_payload = dict(record.get(dim_table.name) or {})
        dim_payload["product_id"] = product_id
        sanitized_dim_payload = _sanitize_payload_for_table(dim_table, dim_payload)
        connection.execute(dim_table.insert().values(**sanitized_dim_payload))


def _insert_products(
    engine: Engine,
    spec_records: list[dict],
    link_index: dict[str, dict],
) -> tuple[int, int, int]:
    total_records = len(spec_records)
    inserted_products = 0
    skipped_malformed = 0
    skipped_existing = 0
    with engine.connect() as connection:
        existing_names = {
            row[0]
            for row in connection.execute(select(fact_product.c.product_name)).fetchall()
            if row[0]
        }

    for index, record in enumerate(spec_records, start=1):
        fact_payload = _build_fact_payload(record)
        if not fact_payload:
            skipped_malformed += 1
            if index % 100 == 0:
                print(
                    f"[INFO] Loading progress {index}/{total_records} "
                    f"inserted={inserted_products} skipped_existing={skipped_existing} "
                    f"skipped_malformed={skipped_malformed}",
                    flush=True,
                )
            continue

        product_name = fact_payload.get("product_name")
        if not product_name:
            skipped_malformed += 1
            if index % 100 == 0:
                print(
                    f"[INFO] Loading progress {index}/{total_records} "
                    f"inserted={inserted_products} skipped_existing={skipped_existing} "
                    f"skipped_malformed={skipped_malformed}",
                    flush=True,
                )
            continue

        if product_name in existing_names:
            skipped_existing += 1
            if index % 100 == 0:
                print(
                    f"[INFO] Loading progress {index}/{total_records} "
                    f"inserted={inserted_products} skipped_existing={skipped_existing} "
                    f"skipped_malformed={skipped_malformed}",
                    flush=True,
                )
            continue

        with engine.begin() as connection:
            _insert_single_product(
                connection=connection,
                record=record,
                link_index=link_index,
            )

        existing_names.add(product_name)
        inserted_products += 1
        if index % 100 == 0:
            print(
                f"[INFO] Loading progress {index}/{total_records} "
                f"inserted={inserted_products} skipped_existing={skipped_existing} "
                f"skipped_malformed={skipped_malformed}",
                flush=True,
            )

    return inserted_products, skipped_malformed, skipped_existing


def load_products_to_db(
    spec_records: list[dict],
    raw_links: list[dict],
    truncate: bool = False,
    truncate_youtube: bool = False,
) -> tuple[int, int, int]:
    link_index = _build_link_index(raw_links)
    health_check()
    engine = get_engine()
    if truncate:
        with engine.begin() as connection:
            _truncate_tables(connection=connection)
            print("[INFO] Truncated YouTube tables, product dims, and fact_product.")
    elif truncate_youtube:
        with engine.begin() as connection:
            _truncate_youtube_tables(connection=connection)
            print("[INFO] Truncated dim_video_comments and dim_video_transcripts only.")

    inserted_count, skipped_malformed_count, skipped_existing_count = _insert_products(
        engine=engine,
        spec_records=spec_records,
        link_index=link_index,
    )
    return inserted_count, skipped_malformed_count, skipped_existing_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Load crawled products into database.")
    parser.add_argument(
        "--specs",
        default="data/processed/final_ready_to_load_specs.json",
        help="Path to product specs JSON output. Default is final_ready_to_load_specs.json",
    )
    parser.add_argument(
        "--links",
        default="data/raw/product_links.json",
        help="Path to product links JSON output.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append new records without truncating the database. By default, the database is truncated.",
    )
    parser.add_argument(
        "--truncate-youtube",
        action="store_true",
        help="Delete only dim_video_comments and dim_video_transcripts (keep products).",
    )
    args = parser.parse_args()

    specs_path = Path(args.specs)
    links_path = Path(args.links)

    spec_records = _read_json_file(specs_path)
    raw_links = _read_json_file(links_path)

    # By default we truncate. If --append is passed, we don't truncate.
    do_truncate = not args.append

    inserted_count, skipped_malformed_count, skipped_existing_count = load_products_to_db(
        spec_records=spec_records,
        raw_links=raw_links,
        truncate=do_truncate,
        truncate_youtube=args.truncate_youtube,
    )

    print(f"[INFO] Inserted {inserted_count} products into DB.")
    if skipped_malformed_count:
        print(f"[WARN] Skipped {skipped_malformed_count} malformed records.")
    if skipped_existing_count:
        print(f"[INFO] Skipped {skipped_existing_count} existing records.")


if __name__ == "__main__":
    main()
