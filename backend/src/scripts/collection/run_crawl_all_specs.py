"""
Script: run_crawl_all_specs.py
Mô tả: Chạy độc lập luồng cào chi tiết cấu hình phần cứng (Hardware Specs) cho từng đường link điện thoại. Dữ liệu cào về chưa qua bước lọc trùng hay làm sạch.
Kỹ thuật: Nhận đầu vào là danh sách links, gọi hàm `crawl_product_specs` (thư viện BeautifulSoup) duyệt qua từng trang sản phẩm để bóc tách thông số. Thiết lập cơ chế checkpoint (lưu file json tạm) sau mỗi 50 records để tránh mất dữ liệu nếu gián đoạn mạng.
Input: Danh sách links sản phẩm (mặc định từ: data/raw/product_links.json).
Output: Sinh ra file JSON chứa toàn bộ dữ liệu cấu hình thô, map theo chuẩn Schema (mặc định tại: data/raw/all_product_specs_raw.json).

Cách sử dụng:
1. Chạy mặc định:
   python -m src.scripts.collection.run_crawl_all_specs
2. Chạy với file input/output tùy chỉnh:
   python -m src.scripts.collection.run_crawl_all_specs --links-file custom_links.json --output-file custom_specs.json
"""

import argparse
import json
from pathlib import Path
from src.app.services.crawlers.product_spec_crawler import crawl_product_specs

def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl metadata/specs for all phones into a local JSON file.")
    parser.add_argument(
        "--links-file",
        default="data/raw/product_links.json",
        help="Input path for product links JSON.",
    )
    parser.add_argument(
        "--output-file",
        default="data/raw/all_product_specs_raw.json",
        help="Output path for the fully scraped raw specifications.",
    )
    args = parser.parse_args()

    links_path = Path(args.links_file)
    output_path = Path(args.output_file)

    if not links_path.exists():
        print(f"[ERROR] Missing input file: {links_path}")
        return

    # 1. Đọc list link
    print(f"Reading {links_path}...")
    with open(links_path, "r", encoding="utf-8") as f:
        product_links = json.load(f)

    print(f"[INFO] Loaded {len(product_links)} products to scrape.")

    # List để hứng kết quả
    all_specs_raw = []

    # 2. Định nghĩa hàm callback để lưu lại Data ngay khi bóc xong 1 SP
    def on_mapped(mapped_record: dict, index: int, total: int):
        all_specs_raw.append(mapped_record)
        # Checkpoint: Save mỗi 50 bản ghi phòng hờ đứt mạng
        if index % 50 == 0 or index == total:
            print(f"[CHECKPOINT] Đang ghi tạm {len(all_specs_raw)} records ra {output_path}...")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as out_f:
                json.dump(all_specs_raw, out_f, ensure_ascii=False, indent=2)

    # 3. Chạy crawler (Tận dụng nguyên logic siêu tốt của product_spec_crawler)
    print("Bắt đầu cào Specs cho hệ thống The Advanced Workflow...")
    crawl_product_specs(product_links, on_mapped_record=on_mapped)

    # 4. Chốt hạ
    print(f"Hoàn tất! Đã lưu {len(all_specs_raw)} bản ghi Specs vào {output_path}")

if __name__ == "__main__":
    main()
