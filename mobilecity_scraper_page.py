import json
import time
import random
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# --- CẤU HÌNH ---
INPUT_FILE = "mobilecity_phones_v2.json"          # File chứa danh sách link của
OUTPUT_FILE = "db_ready_phones.json"     # File kết quả xuất ra định dạng chuẩn DB

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
}

# --- HÀM CÀO DỮ LIỆU THÔ ---
def scrape_phone_details(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  [LỖI] HTTP {response.status_code} - {url}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        specs = {}
        
        # Tìm bảng thông số
        spec_box = soup.find('div', class_='product-lightbox-content')
        if spec_box:
            table = spec_box.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) == 2:
                        key = cols[0].text.strip().replace(':', '') 
                        value = cols[1].text.strip()
                        specs[key] = value
                        
        return specs
    except Exception as e:
        print(f"  [LỖI MẠNG] {e} - {url}")
        return None

# --- HÀM LÀM SẠCH VÀ ÁNH XẠ (MAPPING) VÀO SCHEMA DB ---
def clean_val(val):
    """Biến chuỗi rỗng thành None (null trong JSON/SQL)"""
    if not val or val.strip() == "":
        return None
    return val.strip()

def map_to_database_schema(raw_specs, input_data):
    """
    Hàm này lấy dữ liệu thô tiếng Việt và đút vào đúng các "ngăn kéo" 
    tương ứng với Schema PostgreSQL
    """
    if not raw_specs:
        return None

    # Lấy tên sản phẩm từ file đầu vào (chuẩn hơn lấy từ web)
    product_name = input_data.get("name", "Unknown Name")

    db_record = {
        # Metadata (vẫn giữ lại một bản nháp ở ngoài cùng để dễ trace data nếu cần)
        "_source_url": input_data.get("url"),
        
        # 1. Bảng fact_product (ĐÃ THÊM GIÁ VÀ LINK ẢNH)
        "fact_product": {
            "product_name": product_name,
            "price_vnd": input_data.get("price_vnd"),         # Lấy số tiền nguyên bản
            "price_str": input_data.get("price_str"),         # Lấy chuỗi giá tiền hiển thị
            "image_link": input_data.get("image"),            # Lấy link ảnh
            "os_version": clean_val(raw_specs.get("Hệ điều hành")),
            "language_support": clean_val(raw_specs.get("Ngôn ngữ"))
        },
        
        # 2. Bảng dim_display
        "dim_display": {
            "display_type": clean_val(raw_specs.get("Loại màn hình")),
            "color_depth": clean_val(raw_specs.get("Màu màn hình")),
            "display_standard": clean_val(raw_specs.get("Chuẩn màn hình")),
            "resolution": clean_val(raw_specs.get("Độ phân giải")),
            "screen_size": clean_val(raw_specs.get("Màn hình rộng")),
            "touch_technology": clean_val(raw_specs.get("Công nghệ cảm ứng"))
        },
        
        # 3. Bảng dim_camera
        "dim_camera": {
            "rear_camera": clean_val(raw_specs.get("Camera sau")),
            "front_camera": clean_val(raw_specs.get("Camera trước")),
            "flash_light": clean_val(raw_specs.get("Đèn Flash")),
            "camera_features": clean_val(raw_specs.get("Tính năng camera")),
            "video_recording": clean_val(raw_specs.get("Quay phim")),
            "video_call": clean_val(raw_specs.get("Videocall"))
        },
        
        # 4. Bảng dim_performance
        "dim_performance": {
            "cpu_speed": clean_val(raw_specs.get("Tốc độ CPU")),
            "core_count": clean_val(raw_specs.get("Số nhân")),
            "chipset": clean_val(raw_specs.get("Chipset")),
            "ram_capacity": clean_val(raw_specs.get("RAM")),
            "gpu_chip": clean_val(raw_specs.get("Chip đồ họa (GPU)")) or clean_val(raw_specs.get("GPU"))
        },
        
        # 5. Bảng dim_storage
        "dim_storage": {
            "phonebook_storage": clean_val(raw_specs.get("Danh bạ")),
            "internal_storage": clean_val(raw_specs.get("Bộ nhớ trong (ROM)")),
            "external_memory": clean_val(raw_specs.get("Thẻ nhớ ngoài")),
            "max_external_support": clean_val(raw_specs.get("Hỗ trợ thẻ tối đa"))
        },
        
        # 6. Bảng dim_design
        "dim_design": {
            "design_style": clean_val(raw_specs.get("Kiểu dáng")),
            "dimensions": clean_val(raw_specs.get("Kích thước")),
            "weight": clean_val(raw_specs.get("Trọng lượng (g)"))
        },
        
        # 7. Bảng dim_battery
        "dim_battery": {
            "battery_type": clean_val(raw_specs.get("Loại pin")),
            "battery_capacity": clean_val(raw_specs.get("Dung lượng pin")),
            "removable_battery": clean_val(raw_specs.get("Pin có thể tháo rời"))
        },
        
        # 8. Bảng dim_connectivity
        "dim_connectivity": {
            "network_3g": clean_val(raw_specs.get("3G")),
            "network_4g": clean_val(raw_specs.get("4G")),
            "sim_type": clean_val(raw_specs.get("Loại Sim")),
            "sim_slots": clean_val(raw_specs.get("Khe gắn Sim")),
            "wifi": clean_val(raw_specs.get("Wifi")),
            "gps": clean_val(raw_specs.get("GPS")),
            "bluetooth": clean_val(raw_specs.get("Bluetooth")),
            "gprs_edge": clean_val(raw_specs.get("GPRS/EDGE")),
            "headphone_jack": clean_val(raw_specs.get("Jack tai nghe")),
            "nfc": clean_val(raw_specs.get("NFC")),
            "usb_connection": clean_val(raw_specs.get("Kết nối USB")),
            "other_connections": clean_val(raw_specs.get("Kết nối khác")),
            "charging_port": clean_val(raw_specs.get("Cổng sạc"))
        },
        
        # 9. Bảng dim_utilities
        "dim_utilities": {
            "movie_playback": clean_val(raw_specs.get("Xem phim")),
            "music_playback": clean_val(raw_specs.get("Nghe nhạc")),
            "charging_port_alt": clean_val(raw_specs.get("Cổng sạc")),
            "voice_recorder": clean_val(raw_specs.get("Ghi âm")),
            "fm_radio": clean_val(raw_specs.get("FM radio")),
            "other_features": clean_val(raw_specs.get("Chức năng khác"))
        }
    }
    
    return db_record

# --- LUỒNG CHẠY CHÍNH ---
def main():
    # Đọc file đầu vào (danh sách các điện thoại đã cào từ bot trước)
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            phones_list = json.load(f)
    except FileNotFoundError:
        print(f"Không tìm thấy file '{INPUT_FILE}'. Vui lòng tạo file chứa danh sách link.")
        return

    print(f"Bắt đầu xử lý {len(phones_list)} sản phẩm...\n{'='*40}")
    
    final_db_records = []

    # Bọc danh sách bằng tqdm để tạo thanh tiến độ
    pbar = tqdm(phones_list, desc="Đang cào dữ liệu", unit=" máy", ncols=100)

    for idx, phone in enumerate(pbar, 1):
        url = phone.get("url")
        if not url:
            continue
            
        # Cập nhật tên điện thoại đang cào vào đuôi thanh tiến độ cho sinh động
        pbar.set_postfix_str(phone.get('name')[:30] + "...")
        
        raw_specs = scrape_phone_details(url)
        
        if raw_specs:
            mapped_record = map_to_database_schema(raw_specs, phone)
            final_db_records.append(mapped_record)
        
        # --- CƠ CHẾ AUTO-SAVE (CHECKPOINT TỪNG 50 MÁY) ---
        if idx % 50 == 0:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(final_db_records, f, ensure_ascii=False, indent=4)
            # Dùng tqdm.write để in thông báo mà không đè lên thanh progress
            tqdm.write(f"Auto-Save] Đã lưu tạm {len(final_db_records)} sản phẩm vào file!")
        
        # Delay ngẫu nhiên chống block
        time.sleep(random.uniform(0.5, 1.5))

    # Lưu lần cuối cùng (phòng khi tổng số không chia hết cho 50)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_db_records, f, ensure_ascii=False, indent=4)
        
    print(f"\n{'='*50}\n Hoàn thành! Đã lưu tổng cộng {len(final_db_records)} bản ghi chuẩn DB vào '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()