"""
Bước 3: Loại bỏ trùng lặp dựa trên phần cứng (Hardware-based Deduplication)

Mục tiêu của bước này là nhóm các bản ghi có thông số phần cứng lõi giống nhau (CPU, RAM, GPU, pin, kích thước, trọng lượng) 
vào cùng một nhóm, bất kể tên sản phẩm có thể khác nhau do râu ria marketing hay lỗi nhập liệu.

Input: `all_product_specs_raw.json` (2,000+ records) — đầu vào là toàn bộ bản ghi thô sau khi crawl, nhưng chưa qua bất kỳ bước loại bỏ trùng lặp nào.
Output:
- `unique_smartphone_specs.json` — chứa một bản ghi "Master" duy nhất cho mỗi nhóm phần cứng, được chọn dựa trên tiêu chí tên sản phẩm ngắn gọn nhất (ít râu ria marketing nhất).
- `suspected_duplicates.json` — chứa các bản ghi còn lại trong mỗi nhóm, được gắn thêm trường `reference_id` tham chiếu tới bản ghi Master tương ứng. Các bản ghi này có thể được xem xét thủ công sau này để quyết định giữ hay loại bỏ hoàn toàn.
"""
import json
import hashlib
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_normalized_value(item, category, field):
    """
    Trích xuất và chuẩn hóa giá trị từ bản ghi JSON.
    Chuyển về chữ thường, xóa khoảng trắng thừa, xóa dấu xuống dòng.
    """
    val = item.get(category, {}).get(field)
    if not val:
        return "unknown"
    return " ".join(str(val).lower().strip().split())

def generate_hardware_hash(item):
    """
    Tạo mã băm (hash) dựa trên 7 thông số phần cứng định danh lõi.
    """
    attributes = [
        get_normalized_value(item, "dim_performance", "chipset"),
        get_normalized_value(item, "dim_performance", "core_count"),
        get_normalized_value(item, "dim_performance", "ram_capacity"),
        get_normalized_value(item, "dim_performance", "gpu_chip"),
        get_normalized_value(item, "dim_design", "dimensions"),
        get_normalized_value(item, "dim_design", "weight"),
        get_normalized_value(item, "dim_battery", "battery_capacity")
    ]
    
    # Gộp tất cả thành một chuỗi duy nhất để băm
    combined_string = " | ".join(attributes)
    
    # Tạo hash (MD5 để ngắn gọn và đủ dùng cho chống trùng lặp dữ liệu)
    return hashlib.md5(combined_string.encode('utf-8')).hexdigest()

def main():
    # Cấu hình đường dẫn (chạy từ thư mục backend/)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    input_file = os.path.join(base_dir, "data", "raw", "all_product_specs_raw.json")
    
    processed_dir = os.path.join(base_dir, "data", "processed")
    unique_file = os.path.join(processed_dir, "unique_smartphone_specs.json")
    duplicates_file = os.path.join(processed_dir, "suspected_duplicates.json")

    # Kiểm tra file input
    if not os.path.exists(input_file):
        logging.error(f"Không tìm thấy file đồ sống (raw data): {input_file}")
        sys.exit(1)

    os.makedirs(processed_dir, exist_ok=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logging.info(f"Đã load {len(data)} bản ghi từ {input_file}")

    # Gom nhóm dữ liệu theo mã băm phần cứng (Hardware Hash)
    grouped_data = {}
    for item in data:
        item_hash = generate_hardware_hash(item)
        if item_hash not in grouped_data:
            grouped_data[item_hash] = []
        grouped_data[item_hash].append(item)

    unique_specs = []
    suspected_duplicates = []

    logging.info(f"Phân tích hoàn tất: Phát hiện {len(grouped_data)} hồ sơ phần cứng (mẫu điện thoại) độc nhất.")

    for item_hash, group in grouped_data.items():
        # Sắp xếp nhóm để chọn bản ghi "Master" tốt nhất.
        # Tiêu chí: Tên ngắn gọn nhất (thường ít bị dính chữ rác QC nhất)
        group_sorted = sorted(
            group,
            key=lambda x: len(x.get("fact_product", {}).get("product_name", ""))
        )
        
        # Chọn Master record
        master = group_sorted[0]
        # Sinh ID định danh duy nhất dựa trên một phần của MD5 Hash
        master_id = f"DEV-{item_hash[:10].upper()}" 
        
        master["id"] = master_id
        unique_specs.append(master)
        
        # Đẩy phần còn lại vào danh sách nghi ngờ trùng lặp (kèm reference_id tham chiếu tới Master)
        for dup in group_sorted[1:]:
            dup["reference_id"] = master_id
            suspected_duplicates.append(dup)

    # Lưu ra files kết quả
    with open(unique_file, 'w', encoding='utf-8') as f:
        json.dump(unique_specs, f, ensure_ascii=False, indent=2)

    with open(duplicates_file, 'w', encoding='utf-8') as f:
        json.dump(suspected_duplicates, f, ensure_ascii=False, indent=2)

    logging.info(f"Đã ghi {len(unique_specs)} bản ghi độc nhất -> {unique_file}")
    logging.info(f"Đã ghi {len(suspected_duplicates)} bản ghi trùng lặp -> {duplicates_file}")

if __name__ == "__main__":
    main()
