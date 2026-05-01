"""
Bước 5: Final Deduplication

Mục tiêu của bước này là loại bỏ hoàn toàn các bản ghi trùng lặp dựa trên trường `search_query_name` đã được chuẩn hóa từ bước 4.

Kỹ thuật áp dụng:
- Sử dụng một tập hợp (set) để theo dõi các `search_query_name` đã gặp, đảm bảo mỗi tên chuẩn chỉ xuất hiện một lần.

Input: `ready_to_load_specs.json` (1,547 records) — đầu vào là các bản ghi đã được chuẩn hóa tên sản phẩm, nhưng có thể vẫn còn trùng lặp.
Output: `final_ready_to_load_specs.json` — chỉ giữ lại một bản ghi duy nhất
"""
import os
import sys
import json
import logging
from pathlib import Path

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    # Thiết lập đường dẫn
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.append(base_dir)

    input_file = os.path.join(base_dir, "data", "processed", "ready_to_load_specs.json")
    output_file = os.path.join(base_dir, "data", "processed", "final_ready_to_load_specs.json")

    # Kiểm tra file input
    if not os.path.exists(input_file):
        logging.error(f"KhÔng tìm thấy file thiết lập: {input_file}")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logging.info(f"Đã đọc {len(data)} bản ghi từ {input_file}")

    unique_records = []
    seen_names = set()

    for item in data:
        # Lấy tên chuẩn hóa (chuyển sang chữ thường để so sánh chính xác hơn, tránh phân biệt hoa thường)
        search_name_lower = item.get("search_query_name", "").strip().lower()
        
        if not search_name_lower:
            search_name_lower = item.get("fact_product", {}).get("product_name", "unknown").lower()
            
        if search_name_lower not in seen_names:
            seen_names.add(search_name_lower)
            unique_records.append(item)

    duplicates_removed = len(data) - len(unique_records)
    logging.info(f"Đã lọc trùng khớp dựa trên search_query_name.")
    logging.info(f"-> Số bản ghi gốc: {len(data)}")
    logging.info(f"-> Số bản ghi giữ lại: {len(unique_records)}")
    logging.info(f"-> Số bản ghi trùng bị loại: {duplicates_removed}")

    # Output ra file cuối cùng
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_records, f, ensure_ascii=False, indent=2)

    logging.info(f"Hoàn thành! Đã lưu kết quả tại: {output_file}")

if __name__ == "__main__":
    main()
