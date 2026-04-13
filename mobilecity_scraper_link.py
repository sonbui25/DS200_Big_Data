"""
Scraper dien thoai tu mobilecity.vn - Phiên Bản V2 (Tối ưu cho Producer)
- Tự động lấy danh sách slug
- Cào vô hạn trang (while True) cho đến khi hết dữ liệu
- Cơ chế delay ngẫu nhiên chống block IP
- Tích hợp Session & Cookie thật để vượt rào bảo mật Laravel
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
import re

# ─── CẤU HÌNH HỆ THỐNG ───────────────────────────────────────────────────────
BASE_URL  = "https://mobilecity.vn/product_view_more"
HOME_URL  = "https://mobilecity.vn/dien-thoai"
COUNT     = 20
CSV_FILE  = "mobilecity_phones_link.csv"
JSON_FILE = "mobilecity_phones_link.json"

# Khởi tạo Session để tự động duy trì kết nối
session = requests.Session()

# Bộ "giấy tờ tùy thân" lấy từ trình duyệt của bạn
HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8,fr;q=0.7",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://mobilecity.vn",
    "referer": "https://mobilecity.vn/dien-thoai",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    
    # 2 vũ khí tối thượng giúp qua mặt tường lửa Laravel:
    "x-csrf-token": "6wMM2672evkjC5235J2u4ZRSYuyb9nXVAa1udl1V",
    "x-requested-with": "XMLHttpRequest",
    
    # Dán toàn bộ chuỗi cookie dài ngoằng của bạn vào đây
    "cookie": '_ga=GA1.1.295552170.1775974631; XSRF-TOKEN=eyJpdiI6InNZb2IxZzF0TXZ2alwvRUw0QXIyME13PT0iLCJ2YWx1ZSI6InNXMG90TklJZk45SVpCUnh4Um9pSDhod21mRk1KTENvSEVnbFN1QzA3dGFrVEdLWGtZOE41d2JGNjR0VUZLdlQiLCJtYWMiOiJlNjRkMjlhYTMwOWQxY2JkMWMwZDhiNTg5MGUxYTFlNmI1ODRiMzA5ZmI1MmVkODk2ZjUwZmFiM2M2MDMwODFjIn0%3D; laravel_session=eyJpdiI6IjVGNnNrUlBPczFOOUlsRzhxQzBqS1E9PSIsInZhbHVlIjoiU3hQNkVmc1wvUCtsRGhMZzFzYlVPOE9Jd3RpTjBac1wvR1wvM0g3VkQwUVhNYlFpY1NORzlwaVg2QmdYVHc5OHgxQVJjdFJKSjZ4TktOTDlRN1JCS1wvdDduY2dkbisyUmd3UUY5SUtIclFPTWRzc2VzancrTEtRQUd5ZUtIOHVQa3BlIiwibWFjIjoiOTU4ZjdlNjViOWIxYTVmMzg0ODQxYTRlYWIxYjIxMjJiM2NkNzBjZjVhNDE0MTkzZWU1MmY5ZjUzNjEyZTA2NSJ9; _ga_K95C6XYT9V=GS2.1.s1775983765$o2$g1$t1775984378$j59$l0$h0; g_state={"i_l":0,"i_ll":1775984378084,"i_b":"lhmwVEF1s2Zg36yDgTinS/6tld2vRZhy/wEdvYUOozo","i_e":{"enable_itp_optimization":0},"i_et":1775984378084}'
}

# Cập nhật Headers vào Session
session.headers.update(HEADERS)

# ─── BƯỚC 0: TỰ ĐỘNG LẤY SLUG ───────────────────────────────────────────────
def discover_slugs() -> list:
    print(f"[Bước 0] Đang quét menu từ {HOME_URL} ...")
    try:
        resp = session.get(HOME_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f" LỖI KHÔNG THỂ TRUY CẬP TRANG CHỦ: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    slugs, seen = [], set()

    for a in soup.select("a[href]"):
        m = re.match(r"https://mobilecity\.vn/dien-thoai-(.+)$", a["href"])
        if m:
            slug = m.group(1).strip("/")
            if slug not in seen and not slug.startswith("may-choi-game"):
                seen.add(slug)
                slugs.append(slug)
    
    print(f" -> Tìm thấy {len(slugs)} hãng/dòng máy.")
    return slugs

# ─── PARSE HTML → LIST SẢN PHẨM ─────────────────────────────────────────────
def parse_products(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.product-list-item")
    result = []
    
    for item in items:
        name_tag = item.select_one("p.name a")
        price_tag = item.select_one("p.price")
        img_tag = item.select_one("img.lazy")
        
        name = name_tag.get_text(strip=True) if name_tag else ""
        url = name_tag["href"] if name_tag else ""
        price_raw = price_tag.get_text(strip=True) if price_tag else ""
        price_clean = re.sub(r"[^\d]", "", price_raw)
        price_num = int(price_clean) if price_clean else 0
        img_url = img_tag.get("data-original", "") if img_tag else ""
        
        if name:
            result.append({
                "name": name,
                "price_vnd": price_num,
                "price_str": price_raw,
                "url": url,
                "image": img_url,
            })
    return result

# ─── LƯU FILE ────────────────────────────────────────────────────────────────
def save_all(products: list):
    if not products: return
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=products[0].keys())
        writer.writeheader()
        writer.writerows(products)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

# ─── FETCH 1 TRANG API ───────────────────────────────────────────────────────
def fetch_api_page(page: int, slug: str) -> list:
    payload = {
        "count": COUNT,
        "slug": slug,
        "page": page,
        "type_category": "phone_categories",
        "get_order": "",
    }
    print(f"  [API Page {page:>2}] Đang cào...", end=" ", flush=True)
    try:
        resp = session.post(BASE_URL, data=payload, timeout=15)
        
        if resp.status_code != 200:
            print(f"Mã lỗi HTTP: {resp.status_code}")
            return []
            
        json_data = resp.json()
        
        # Lấy phone_item ra. Dùng .get() với fallback là rỗng.
        phone_item_data = json_data.get("phone_item")
        
        html_content = ""
        
        # Bắt đầu xử lý tính "bất nhất" của API
        if not phone_item_data:
            # Nếu null hoặc rỗng
            print("Hết dữ liệu (rỗng).")
            return []
        elif isinstance(phone_item_data, list):
            # Nếu server trả về 1 List các đoạn HTML (như lỗi của bạn đang gặp)
            # -> Nối tất cả các phần tử trong list lại thành 1 chuỗi dài
            html_content = "".join(str(item) for item in phone_item_data)
        elif isinstance(phone_item_data, str):
            # Nếu server trả về 1 chuỗi HTML (như dự đoán ban đầu)
            html_content = phone_item_data
        else:
            print(f"Định dạng lạ: {type(phone_item_data)}")
            return []
            
        # Kiểm tra xem có lấy được HTML không, nếu có thì mới bóc tách
        if not html_content.strip():
             print("Dữ liệu rỗng.")
             return []

        products = parse_products(html_content)
        print(f"Lấy được {len(products)} SP.")
        return products
        
    except json.JSONDecodeError:
        print("Lỗi phân tích JSON từ Server. (Có thể bị chặn)")
        return []
    except Exception as e:
        # Nếu vẫn dính lỗi khác, log chi tiết ra để xem
        print(f"LỖI: {e}")
        return []

# ─── CÀO 1 SLUG BẰNG VÒNG LẶP VÔ HẠN ─────────────────────────────────────────
def scrape_slug(slug: str, all_products: list, seen_urls: set) -> int:
    print(f"\n[{slug.upper()}] Bắt đầu cào...")
    total_new = 0
    page = 1 
    
    while True: # VÒNG LẶP VÔ HẠN
        batch = fetch_api_page(page, slug)
        
        if not batch: # Nếu API trả về danh sách rỗng -> Đã cào hết dòng máy này
            break
            
        new_count = 0
        for p in batch:
            if p["url"] not in seen_urls:
                seen_urls.add(p["url"])
                p["slug"] = slug
                all_products.append(p)
                new_count += 1
                
        total_new += new_count
        save_all(all_products)
        
        if new_count == 0:
            print("  -> Dữ liệu bị lặp lại hoàn toàn. Chuyển sang hãng khác.")
            break
            
        page += 1
        
        # DELAY NGẪU NHIÊN: Từ 1.2s đến 3.5s để ngụy trang thành người thật
        sleep_time = random.uniform(1.2, 3.5)
        time.sleep(sleep_time)

    print(f"  => Tổng kết '{slug}': Thu hoạch được {total_new} SP mới.")
    return total_new

# ─── CHẠY HỆ THỐNG ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_products = []
    seen_urls = set()
    
    # Kích hoạt bước 0
    slugs = discover_slugs()

    if slugs:
        for i, slug in enumerate(slugs, 1):
            print(f"\n{'='*50}")
            print(f"--- Tiến độ: {i}/{len(slugs)} ---")
            print(f"{'='*50}")
            scrape_slug(slug, all_products, seen_urls)

        print(f"\n🎉 HOÀN THÀNH TOÀN BỘ! Thu hoạch được {len(all_products)} Link SP duy nhất.")
        print(f"📂 Dữ liệu đã lưu tại: {CSV_FILE} và {JSON_FILE}")