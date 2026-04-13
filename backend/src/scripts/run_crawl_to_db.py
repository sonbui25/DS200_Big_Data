import argparse
import json
from pathlib import Path

from src.app.services.crawlers.product_link_crawler import crawl_product_links
from src.app.services.crawlers.product_spec_crawler import crawl_product_specs
from src.scripts.load_products_to_db import load_products_to_db


def _write_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full crawl and load data into database.")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing fact/dim rows before loading.",
    )
    args = parser.parse_args()

    print("[INFO] Step 1/3 - Crawling product links...", flush=True)
    product_links = list(crawl_product_links())
    print(f"[INFO] Crawled {len(product_links)} product links.", flush=True)

    print("[INFO] Step 2/3 - Crawling product specs...", flush=True)
    product_specs = list(crawl_product_specs(product_links))
    print(f"[INFO] Crawled {len(product_specs)} product specs.", flush=True)

    _write_json(Path("data/raw/product_links.json"), product_links)
    _write_json(Path("data/processed/product_specs.json"), product_specs)
    print("[INFO] Saved intermediate JSON files.", flush=True)

    print("[INFO] Step 3/3 - Loading data to DB...", flush=True)
    inserted_count, skipped_malformed_count, skipped_existing_count = load_products_to_db(
        spec_records=product_specs,
        raw_links=product_links,
        truncate=args.truncate,
    )
    print(
        "[INFO] Done. "
        f"inserted={inserted_count} "
        f"skipped_malformed={skipped_malformed_count} "
        f"skipped_existing={skipped_existing_count}",
        flush=True,
    )


if __name__ == "__main__":
    main()
