import json
import re

# --- Cấu hình File ---
INPUT_FILE = "data/db_ready_phones.json"    
OLD_PHONES_FILE = "data/db_ready_phones_filtered_old.json"    
NEW_PHONES_FILE = "data/db_ready_phones_filtered_new.json"    

def classify_phone(product_name):
    """
    Hàm phân loại điện thoại dựa trên 3 lớp phễu:
    Trả về "OLD" hoặc "NEW"
    """
    # Lớp lọc 1: Bắt chữ "cũ"
    if re.search(r'\bcũ\b', product_name, re.IGNORECASE):
        return "OLD"
        
    # Lớp lọc 2: Bắt con số trước dấu % (< 100)
    percentages = re.findall(r'(\d+)\s*%', product_name)
    for p in percentages:
        if int(p) < 100:
            return "OLD"

    # Lớp lọc 3: Bắt chữ "chính hãng"
    if re.search(r'chính hãng', product_name, re.IGNORECASE):
        return "NEW"

    # Lớp lọc cuối: Còn lại (không có chữ "chính hãng", cũng không có dấu hiệu cũ)
    return "OLD"

def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            all_records = json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file '{INPUT_FILE}'.")
        return

    old_phones = []
    new_phones = []

    for record in all_records:
        name = record.get("fact_product", {}).get("product_name", "")
        
        # Gọi hàm phân loại
        if classify_phone(name) == "NEW":
            new_phones.append(record)
        else:
            old_phones.append(record)

    # Lưu ra 2 file riêng biệt
    with open(OLD_PHONES_FILE, "w", encoding="utf-8") as f:
        json.dump(old_phones, f, ensure_ascii=False, indent=4)
        
    with open(NEW_PHONES_FILE, "w", encoding="utf-8") as f:
        json.dump(new_phones, f, ensure_ascii=False, indent=4)

    # In báo cáo kết quả
    print(f"{'='*40}")
    print(f"Tổng số máy ban đầu: {len(all_records)}")
    print(f"📦 Phân loại thành công:")
    print(f"  -> File máy CHÍNH HÃNG ({NEW_PHONES_FILE}): {len(new_phones)} sản phẩm")
    print(f"  -> File máy CŨ / CÒN LẠI ({OLD_PHONES_FILE}): {len(old_phones)} sản phẩm")
    print(f"{'='*40}")

if __name__ == "__main__":
    main()