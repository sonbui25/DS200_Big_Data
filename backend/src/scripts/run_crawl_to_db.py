import argparse
import json
import re
from pathlib import Path

from src.app.services.crawlers.product_link_crawler import crawl_product_links
from src.app.services.crawlers.product_spec_crawler import crawl_product_specs
from src.scripts.load_products_to_db import load_products_to_db


def _write_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list in file: {path}")
    return payload


def classify_phone(product_name: str) -> str:
    if re.search(r"\bcũ\b", product_name, re.IGNORECASE):
        return "OLD"

    percentages = re.findall(r"(\d+)\s*%", product_name)
    for percentage in percentages:
        if int(percentage) < 100:
            return "OLD"

    if re.search(r"chính hãng", product_name, re.IGNORECASE):
        return "NEW"
    return "OLD"


def deduplicate_records(records: list[dict]) -> list[dict]:
    unique_records: list[dict] = []
    seen_names: set[str] = set()
    for record in records:
        product_name = (record.get("fact_product") or {}).get("product_name")
        if not product_name or product_name in seen_names:
            continue
        seen_names.add(product_name)
        unique_records.append(record)
    return unique_records


def filter_records(records: list[dict], target_group: str) -> list[dict]:
    if target_group == "ALL":
        return records
    return [
        record
        for record in records
        if classify_phone((record.get("fact_product") or {}).get("product_name", "")) == target_group
    ]


def deduplicate_link_records(records: list[dict]) -> list[dict]:
    unique_records: list[dict] = []
    seen_urls: set[str] = set()
    for record in records:
        url = (record.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique_records.append(record)
    return unique_records


def filter_link_records(records: list[dict], target_group: str) -> list[dict]:
    if target_group == "ALL":
        return records
    return [
        record
        for record in records
        if classify_phone((record.get("product_name") or "").strip()) == target_group
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full crawl and load data into database.")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete YouTube tables, then fact+dims, before loading.",
    )
    parser.add_argument(
        "--truncate-youtube",
        action="store_true",
        help="Delete only dim_video_comments and dim_video_transcripts before loading.",
    )
    parser.add_argument(
        "--target-group",
        choices=["ALL", "NEW", "OLD"],
        default="ALL",
        help="Filter product group right after link stage (ALL/NEW/OLD).",
    )
    parser.add_argument(
        "--links-file",
        default="data/raw/product_links.json",
        help="Input/output path for product links JSON.",
    )
    parser.add_argument(
        "--skip-link-crawl",
        action="store_true",
        help="Reuse existing links-file instead of crawling links again.",
    )
    parser.add_argument(
        "--db-batch-size",
        type=int,
        default=1,
        help="Insert mapped specs to DB in batches during crawl (default 1 = near real-time).",
    )
    args = parser.parse_args()

    links_path = Path(args.links_file)
    if args.skip_link_crawl:
        print("[INFO] Step 1/4 - Loading existing product links...", flush=True)
        product_links = _read_json(links_path)
        print(f"[INFO] Loaded {len(product_links)} links from {links_path}.", flush=True)
    else:
        print("[INFO] Step 1/4 - Crawling product links...", flush=True)
        product_links = list(crawl_product_links())
        print(f"[INFO] Crawled {len(product_links)} product links.", flush=True)

    unique_links = deduplicate_link_records(product_links)
    filtered_links = filter_link_records(unique_links, target_group=args.target_group)
    filtered_links_path = Path(f"data/processed/product_links_filtered_{args.target_group.lower()}.json")
    _write_json(links_path, product_links)
    _write_json(filtered_links_path, filtered_links)
    print(
        f"[INFO] Step 2/4 - Link filtering done raw={len(product_links)} "
        f"unique={len(unique_links)} filtered={len(filtered_links)} target_group={args.target_group}",
        flush=True,
    )

    batch_size = max(1, args.db_batch_size)
    if args.truncate or args.truncate_youtube:
        print("[INFO] Step 3/5 - Truncating DB before streaming inserts...", flush=True)
        load_products_to_db(
            spec_records=[],
            raw_links=filtered_links,
            truncate=args.truncate,
            truncate_youtube=args.truncate_youtube,
        )

    print(
        f"[INFO] Step 4/5 - Crawling product specs and streaming to DB (batch_size={batch_size})...",
        flush=True,
    )
    product_specs: list[dict] = []
    unique_specs: list[dict] = []
    seen_product_names: set[str] = set()
    insert_batch: list[dict] = []
    inserted_count = 0
    skipped_malformed_count = 0
    skipped_existing_count = 0

    def _flush_insert_batch(current_index: int, total_links: int) -> None:
        nonlocal inserted_count, skipped_malformed_count, skipped_existing_count, insert_batch
        if not insert_batch:
            return
        batch_inserted, batch_malformed, batch_existing = load_products_to_db(
            spec_records=insert_batch,
            raw_links=filtered_links,
            truncate=False,
            truncate_youtube=False,
        )
        inserted_count += batch_inserted
        skipped_malformed_count += batch_malformed
        skipped_existing_count += batch_existing
        print(
            f"[INFO] [DB] [{current_index}/{total_links}] batch={len(insert_batch)} "
            f"inserted={batch_inserted} skipped_existing={batch_existing} skipped_malformed={batch_malformed} "
            f"totals inserted={inserted_count} skipped_existing={skipped_existing_count} skipped_malformed={skipped_malformed_count}",
            flush=True,
        )
        insert_batch = []

    def _on_mapped_record(mapped_record: dict, index: int, total_links: int) -> None:
        product_specs.append(mapped_record)
        product_name = (mapped_record.get("fact_product") or {}).get("product_name")
        if not product_name or product_name in seen_product_names:
            return
        seen_product_names.add(product_name)
        unique_specs.append(mapped_record)
        insert_batch.append(mapped_record)
        if len(insert_batch) >= batch_size:
            _flush_insert_batch(current_index=index, total_links=total_links)

    crawl_product_specs(filtered_links, on_mapped_record=_on_mapped_record)
    _flush_insert_batch(current_index=len(filtered_links), total_links=len(filtered_links))

    _write_json(Path("data/processed/product_specs.json"), product_specs)
    filtered_specs_path = Path(
        f"data/processed/product_specs_filtered_{args.target_group.lower()}.json"
    )
    _write_json(filtered_specs_path, unique_specs)
    print(
        f"[INFO] Saved JSON files. crawled_specs={len(product_specs)} "
        f"unique_specs={len(unique_specs)} target_group={args.target_group}",
        flush=True,
    )
    print("[INFO] Step 5/5 - Streaming load completed.", flush=True)
    print(
        "[INFO] Done. "
        f"inserted={inserted_count} "
        f"skipped_malformed={skipped_malformed_count} "
        f"skipped_existing={skipped_existing_count}",
        flush=True,
    )


if __name__ == "__main__":
    main()
