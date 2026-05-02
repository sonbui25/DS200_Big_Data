"""
Script: run_crawl_product_links.py
Mô tả: Chạy độc lập luồng crawl danh sách link (URL) sản phẩm điện thoại từ MobileCity.

Kỹ thuật: Sử dụng Requests và BeautifulSoup (thông qua hàm crawl_product_links() trong app.services) để lấy dữ liệu trang chủ, bóc tách slugs và gọi API theo từng trang để ghép danh sách.

Input: (Chạy trực tiếp fetching từ website, không cần file input).
Output: Sinh ra file JSON chứa danh sách sản phẩm (mặc định tại data/raw/product_links.json). Mỗi bản ghi gồm: product_name, url, price_vnd, price_str, image, slug.

Cách sử dụng:
1. Chạy mặc định lấy toàn danh sách URL:
   python -m src.scripts.collection.run_crawl_product_links
2. Cào giới hạn với tham số --max-products (ví dụ: test code):
   python -m src.scripts.collection.run_crawl_product_links --max-products 100
3. Chỉ định nơi xuất file:
   python -m src.scripts.collection.run_crawl_product_links --output path/to/backup.json
"""

import argparse
import json
from pathlib import Path

from src.app.services.crawlers.product_link_crawler import crawl_product_links


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy độc lập crawler danh sách URL sản phẩm điện thoại từ MobileCity.")
    parser.add_argument(
        "--output",
        default="data/raw/product_links.json",
        help="Đường dẫn lưu file JSON đầu ra (mặc định: data/raw/product_links.json)."
    )
    parser.add_argument(
        "--max-products",
        type=int,
        default=None,
        help="Giới hạn số lượng sản phẩm tối đa cần crawl. (Mặc định: không giới hạn)"
    )
    args = parser.parse_args()

    print("[INFO] Bắt đầu crawl danh sách link sản phẩm từ MobileCity...", flush=True)
    product_links = list(crawl_product_links(max_total_products=args.max_products))
    
    # Đảm bảo thư mục lưu trữ tồn tại
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ghi dữ liệu ra file JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(product_links, f, ensure_ascii=False, indent=2)
        
    print(f"[INFO] Hoàn thành! Đã thu thập được {len(product_links)} links.", flush=True)
    print(f"[INFO] Kết quả được lưu tại: {output_path.absolute()}", flush=True)


if __name__ == "__main__":
    main()
