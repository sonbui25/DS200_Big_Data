import argparse
import json
import re
from pathlib import Path

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

import subprocess
import sys

def run_script(module_name: str, *args) -> None:
    cmd = [sys.executable, "-m", module_name] + list(args)
    print(f"[INFO] Chạy lệnh: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    if result.returncode != 0:
        print(f"[ERROR] Script {module_name} thất bại với mã lỗi {result.returncode}.", file=sys.stderr)
        sys.exit(result.returncode)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run full pipeline and load data into database.")
    parser.add_argument(
        "--db-batch-size",
        type=int,
        default=10,
        help="Insert mapped specs to DB in batches during crawl (default 10).",
    )
    args = parser.parse_args()
    
    # 1. Kiểm tra product_links.json
    links_path = Path("data/raw/product_links.json")
    if not links_path.exists():
        print(f"[INFO] Không tìm thấy '{links_path}'. Đang gọi crawler để thu thập links...", flush=True)
        run_script("src.scripts.collection.run_crawl_product_links")
    else:
        print(f"[INFO] OK - Đã tìm thấy '{links_path}'. Bỏ qua bước thu thập links.", flush=True)
        
    # 2. Kiểm tra all_product_specs_raw.json
    raw_specs_path = Path("data/raw/all_product_specs_raw.json")
    if not raw_specs_path.exists():
        print(f"[INFO] Không tìm thấy '{raw_specs_path}'. Đang gọi crawler để thu thập specs...", flush=True)
        run_script("src.scripts.collection.run_crawl_all_specs")
    else:
        print(f"[INFO] OK - Đã tìm thấy '{raw_specs_path}'. Bỏ qua bước thu thập cấu hình.", flush=True)

    # 3. Kiểm tra unique_smartphone_specs.json (Deduplicate)
    unique_specs_path = Path("data/processed/unique_smartphone_specs.json")
    if not unique_specs_path.exists():
        print(f"[INFO] Không tìm thấy '{unique_specs_path}'. Đang gọi script deduplicate...", flush=True)
        run_script("src.scripts.data_processing.run_deduplicate_specs")
    else:
        print(f"[INFO] OK - Đã tìm thấy '{unique_specs_path}'. Bỏ qua bước deduplicate.", flush=True)
        
    # 4. Kiểm tra ready_to_load_specs.json (LLM Normalization)
    ready_specs_path = Path("data/processed/ready_to_load_specs.json")
    if not ready_specs_path.exists():
        print(f"[INFO] Không tìm thấy '{ready_specs_path}'. Đang gọi script LLM normalization...", flush=True)
        run_script("src.scripts.data_processing.run_llm_name_normalization")
    else:
        print(f"[INFO] OK - Đã tìm thấy '{ready_specs_path}'. Bỏ qua bước chuẩn hóa LLM.", flush=True)

    # 5. Kiểm tra final_ready_to_load_specs.json (Final Deduplication)
    final_specs_path = Path("data/processed/final_ready_to_load_specs.json")
    if not final_specs_path.exists():
        print(f"[INFO] Không tìm thấy '{final_specs_path}'. Đang gọi script lọc trùng vòng cuối...", flush=True)
        run_script("src.scripts.data_processing.run_final_deduplication")
    else:
        print(f"[INFO] OK - Đã tìm thấy '{final_specs_path}'. Bỏ qua bước lọc trùng vòng cuối.", flush=True)

    # 6. Load data to DB
    print(f"[INFO] Bắt đầu push dữ liệu vào database...", flush=True)
    # Lấy thông số từ terminal arguments truyền vào qua load script
    # Nếu muốn truncate data trước khi chạy, hãy dùng flag ở trong load script, hiện tại chỉ chạy luồng Load
    run_script("src.scripts.database.load_products_to_db")

    print("[INFO] ========================================", flush=True)
    print("[INFO] PIPELINE HOÀN TẤT THÀNH CÔNG !!", flush=True)

if __name__ == "__main__":
    main()
