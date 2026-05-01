# Smartphone Deduplication Pipeline

> Lọc trùng dữ liệu smartphone dựa trên cấu hình phần cứng, kết hợp chuẩn hóa tên sản phẩm bằng LLM để phục vụ tìm kiếm YouTube.

---

## Mục lục

1. [Vấn đề](#1-vấn-đề)
2. [Thiết kế Giải pháp](#2-thiết-kế-giải-pháp)
3. [Tiêu chuẩn Gom nhóm](#3-tiêu-chuẩn-gom-nhóm)
4. [Tổng quan Pipeline](#4-tổng-quan-pipeline)
5. [Chi tiết Kỹ thuật](#5-chi-tiết-kỹ-thuật)
6. [Kế hoạch File & Script](#6-kế-hoạch-file--script)

---

## 1. Vấn đề

Khi cào dữ liệu từ các trang thương mại điện tử (ví dụ: MobileCity), tên sản phẩm thường bị pha tạp bởi các tiền tố và hậu tố mang tính Marketing. Một mẫu máy duy nhất có thể bị phân mảnh thành hàng chục record riêng biệt:

| Loại nhiễu | Ví dụ |
|---|---|
| Tình trạng | `99%`, `Cũ keng`, `Mới fullbox`, `Trầy xước nhẹ` |
| Khuyến mãi | `Flash sale`, `Giảm giá 30%`, `Mừng khai trương` |
| Biến thể | `128GB`, `8/256GB`, `Mặt lưng da`, `Fan edition` |
| Nguồn gốc | `Bản Mỹ`, `Bản Hàn`, `Chính hãng VN/A`, `Nội địa` |

Sự phân mảnh này dẫn đến hai vấn đề nghiêm trọng:

- **Redundancy:** Database bị phình to bởi các record rác mô tả cùng một thiết bị vật lý.
- **YouTube API Quota Exhaustion:** Tìm kiếm YouTube với tên sản phẩm rườm rà, trùng lặp làm cạn kiệt API quota và trả về kết quả nhiễu.

---

## 2. Thiết kế Giải pháp

Thay vì dùng Regex hoặc LLM để parse chuỗi tên phức tạp, chiến lược được chọn là **Attribute-based Hardware Deduplication**.

> **Tiền đề cốt lõi:** Tên sản phẩm có thể khác nhau do Marketing, nhưng bộ thông số kỹ thuật (Chipset, RAM, Dung lượng, Màn hình, Camera) của cùng một biến thể máy là **tuyệt đối cố định và giống hệt nhau** trên mọi listing. Nếu hai record chia sẻ toàn bộ các hardware attribute cốt lõi, xác suất cực cao chúng là cùng một thiết bị.

**Vai trò của LLM:**

LLM chỉ tham gia ở **bước cuối cùng**, sau khi danh sách đã được deduplicate. Nhiệm vụ duy nhất là đọc hardware spec và cụm tên Marketing để sinh ra `normalized_name` sạch (ví dụ: `"iPhone 14 Pro Max 256GB"`) phục vụ tìm kiếm YouTube.

---

## 3. Tiêu chuẩn Gom nhóm

Các record được gom thành **Duplicate** hoặc **Unique** bằng cách hash tổ hợp 7 hardware field cốt lõi sau. Đây là các định danh phần cứng mạnh nhất, không có lý do để làm giả hay thay đổi bằng ngôn ngữ Marketing.

| Field | Path | Mô tả |
|---|---|---|
| Chipset | `dim_performance.chipset` | Tên vi xử lý / CPU |
| Core Count | `dim_performance.core_count` | Số nhân CPU |
| RAM | `dim_performance.ram_capacity` | Dung lượng RAM |
| GPU | `dim_performance.gpu_chip` | Chip đồ họa |
| Dimensions | `dim_design.dimensions` | Kích thước vật lý |
| Weight | `dim_design.weight` | Trọng lượng |
| Battery | `dim_battery.battery_capacity` | Dung lượng pin |

**Xử lý Regional Variants:**

Việc xét trùng lặp dựa hoàn toàn vào hardware spec. Nếu bản Mỹ và bản Hàn có phần cứng giống hệt nhau, chúng được gộp thành một record. Ngược lại, nếu một hãng dùng chip khác nhau theo mã vùng (ví dụ: Samsung bản Mỹ dùng Snapdragon, bản Hàn/Việt dùng Exynos), sự khác biệt ở hardware field sẽ tự động tạo ra hai hash khác nhau — kết quả là hai thiết bị riêng biệt.

---

## 4. Tổng quan Pipeline

```
[1] Crawl Links
       │
       ▼
[2] Crawl Specs → all_product_specs_raw.json
       │
       ▼
[3] Attribute-based Deduplication
       │
       ├──► unique_smartphone_specs.json   (1 record / hardware profile)
       └──► suspected_duplicates.json      (duplicates kèm reference_id)
       │
       ▼
[4] LLM Name Normalization
       │
       └──► [5] ready_to_load_specs.json 
       │
       ▼
[5] run_final_deduplication.py
       │
       ▼
[6] final_ready_to_load_specs.json→ Load to PostgreSQL RDS
```

**Bước 1 — Crawl Links:**
Chạy crawler thu thập danh sách URL sản phẩm → lưu vào `data/raw/product_links.json`.

**Bước 2 — Crawl Specs to Local JSON:**
Chạy `run_crawl_all_specs_only.py` để lấy toàn bộ bảng thông số kỹ thuật → lưu thành file vật lý `backend/data/raw/all_product_specs_raw.json`.

**Bước 3 — Attribute-based Deduplication:**
Chạy `run_deduplicate_specs.py` để thực hiện thuật toán deduplication dựa trên 7 hardware field cốt lõi.
Duyệt qua `all_product_specs_raw.json`, tính MD5 hash từ 7 core field, gom nhóm, bầu chọn Master record, và tách ra 2 file output:

- `backend/data/processed/unique_smartphone_specs.json` — 1 record đại diện mỗi hardware profile, mỗi record có `id` duy nhất.
- `backend/data/processed/suspected_duplicates.json` — Các record trùng lặp, mỗi record có `reference_id` trỏ về `id` của Master.

**Bước 4 — LLM Name Normalization:**
Chạy `run_llm_name_normalization.py` để prompt LLM duyệt qua danh sách unique và sinh ra trường `search_query_name` cho mỗi thiết bị. Output: `ready_to_load_specs.json`.

**Bước 5 — Lọc trùng vòng 2:**
Chạy `run_final_deduplication.py` xóa các bản ghi trùng search query, để lọc bỏ các bản ghi trùng lặp còn sót lại. Output: `final_ready_to_load_specs.json`.

**Bước 6 — Load to RDS:**
Nạp `final_ready_to_load_specs.json` vào các bảng Fact và Dimension trên PostgreSQL.

---

## 5. Chi tiết Kỹ thuật

### 5.1 Các kỹ thuật áp dụng trong Deduplication (Bước 3)

**Text & HTML Normalization:**

Dữ liệu cào về thường bị lẫn khoảng trắng thừa và ký tự xuống dòng (`\r\n`). Thuật toán lowercase toàn bộ chuỗi và strip các khoảng trắng dư thừa trước khi hash.

**MD5 Hashing:**

7 core field được ghép thành một chuỗi phân tách bằng ` | `, sau đó băm bằng `MD5`. Cách này cho phép group-by-hash hàng nghìn record chỉ trong vài mili-giây.

**Tiêu chuẩn bầu chọn Master Record:**

Khi một nhóm chứa nhiều record chung hash, thuật toán sắp xếp theo **độ dài `product_name` tăng dần** và chọn record có tên ngắn nhất làm Master — nhằm loại bỏ các tiền tố Marketing rườm rà.

> ⚠️ **Edge Case — Bản "Cũ" có tên ngắn hơn bản "Mới":**
>
> Trong một số trường hợp, listing "cũ 99%" lại có chuỗi tên ngắn hơn listing mới nguyên seal, vì bản mới thường bị nhồi thêm thông tin quà tặng và khuyến mãi. Kết quả là Master record được bầu chọn có thể mang tên dính chữ `"cũ 99%"`.
>
> **Điều này không có vấn đề.** Mục tiêu duy nhất của Bước 3 là Hardware Deduplication — gom đúng phần cứng. Tên "xỉn" sẽ được xử lý triệt để ở Bước 4: LLM đọc tên Master cùng với hardware spec rồi sinh ra `search_query_name` chuẩn (loại bỏ mọi từ "cũ, mới, khuyến mãi") để tìm kiếm YouTube.

**ID Management:**

- **Master record** → được cấp `id` duy nhất, format rút trích từ MD5 (ví dụ: `DEV-CF746AC17A`).
- **Duplicate records** → đẩy vào `suspected_duplicates.json` kèm `reference_id` là foreign key trỏ về `id` của Master, phục vụ truy vết và audit ngược.

---

### 5.2 Lệnh chạy

Từ thư mục gốc `backend/`:

```bash
python -m src.scripts.run_deduplicate_specs
```

**Kết quả log mẫu:**

```
INFO: Đã load 1666 bản ghi từ D:\Git\DS200_Big_Data\backend\data\raw\all_product_specs_raw.json
INFO: Phân tích hoàn tất: Phát hiện 1547 hồ sơ phần cứng (mẫu điện thoại) độc nhất.
INFO: Đã ghi 1547 bản ghi độc nhất -> D:\Git\DS200_Big_Data\backend\data\processed\unique_smartphone_specs.json
INFO: Đã ghi 119 bản ghi trùng lặp -> D:\Git\DS200_Big_Data\backend\data\processed\suspected_duplicates.json
```

| Metric | Giá trị |
|---|---|
| Raw records đầu vào | 1,666 |
| Unique hardware profiles | 1,547 |
| Suspected duplicates | 119 |

---

### 5.3 Mẫu dữ liệu: Suspected Duplicate Record

Record dưới đây nằm trong file trùng lặp. Nó bị đánh giá là hardware duplicate của thiết bị khác — chú ý trường `reference_id` được tự động thêm vào cuối. Record này sẽ **không** được nạp vào database.

```json
{
  "_source_url": "https://mobilecity.vn/dien-thoai/iphone-16e-cu-99-dep.html",
  "fact_product": {
    "product_name": "iPhone 16e cũ (99% Đẹp như mới)",
    "os_version": "iOS 18.4",
    "language_support": "Tiếng Việt, Đa ngôn ngữ"
  },
  "dim_display": {
    "display_type": "Super Retina XDR OLED",
    "color_depth": "16 triệu màu",
    "display_standard": "Super Retina XDR OLED, HDR10, 800 nits (HBM), 1200 nits (peak)\r\n6.1 inches, 1.5K (1170 x 2532 pixels)\r\nTỷ lệ 19.5:9, mật độ điểm ảnh ~457 ppi",
    "resolution": "1170 x 2532 pixels",
    "screen_size": "6.1 inches",
    "touch_technology": "Cảm ứng điện dung đa điểm"
  },
  "dim_camera": {
    "rear_camera": "48 MP, f/1.6, 26mm (góc rộng), PDAF, OIS\r\nQuay phim: 4K@24/25/30/60fps, 1080p@25/30/60/120/240fps, HDR, OIS, stereo sound rec.",
    "front_camera": "12 MP, f/1.9 (góc rộng)\r\nSL 3D, (độ sâu/sinh trắc học)\r\nQuay phim: 4K@24/25/30/60fps, 1080p@25/30/60/120fps, HDR",
    "flash_light": "Có",
    "camera_features": "Dual-LED dual-tone flash, HDR, panorama, 3D (spatial) audio (camera sau)\r\nHDR, Dolby Vision HDR, 3D (spatial) audio, stereo sound rec. (camera trước)",
    "video_recording": "4K@24/25/30/60fps, 1080p@25/30/60/120/240fps, HDR, OIS, stereo sound rec.",
    "video_call": "Có"
  },
  "dim_performance": {
    "cpu_speed": "2x4.04 GHz + 4x2.20 GHz",
    "core_count": "6 nhân",
    "chipset": "Apple A18 (3 nm)\r\n6 nhân (2x4.04 GHz + 4x2.20 GHz)\r\nGPU: Apple GPU (4 lõi đồ họa)",
    "ram_capacity": "8GB",
    "gpu_chip": "Apple GPU (4 lõi đồ họa)"
  },
  "dim_storage": {
    "phonebook_storage": "Không giới hạn",
    "internal_storage": "128-512GB",
    "external_memory": "Không",
    "max_external_support": "Không"
  },
  "dim_design": {
    "design_style": "Khung nhôm phẳng\r\n2 mặt kính cường lực phẳng (Ceramic Shield)\r\nKháng nước, bụi IP68 (dưới 6m trong 30 phút)",
    "dimensions": "146.7 x 71.5 x 7.8 mm",
    "weight": "167 g"
  },
  "dim_battery": {
    "battery_type": "Li-Ion",
    "battery_capacity": "Li-Ion 4005 mAh\r\nSạc nhanh (dây) >20W\r\nSạc không dây (Qi) 7.5W",
    "removable_battery": "Không"
  },
  "dim_connectivity": {
    "network_3g": "HSDPA 850 / 900 / 1700(AWS) / 1900 / 2100",
    "network_4g": "HSPA, LTE (CA), 5G",
    "sim_type": "Nano SIM + eSIM",
    "sim_slots": "Nano SIM + eSIM",
    "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6, 2 băng tần, hotspot",
    "gps": "GPS, GLONASS, GALILEO, BDS, QZSS, NavIC",
    "bluetooth": "5.3, A2DP, LE",
    "gprs_edge": "Có",
    "headphone_jack": "Không\r\nLoa kép stereo",
    "nfc": "Có",
    "usb_connection": "USB Type-C 2.0",
    "other_connections": "NFC",
    "charging_port": "Type-C"
  },
  "dim_utilities": {
    "movie_playback": null,
    "music_playback": null,
    "charging_port_alt": "Type-C",
    "voice_recorder": "Có",
    "fm_radio": "Có",
    "other_features": null
  },
  "reference_id": "DEV-CF746AC17A"
}
```

---

### 5.4 Mẫu dữ liệu: Unique Smartphone Record

Record dưới đây nằm trong file đã lọc sạch. Nó được đánh giá là không có hardware duplicate và sẽ được nạp vào database. Đây chính là Master record mà `DEV-CF746AC17A` ở trên tham chiếu đến.

```json
{
  "_source_url": "https://mobilecity.vn/dien-thoai/iphone-16e-apple-a18.html",
  "fact_product": {
    "product_name": "iPhone 16e Chính hãng VN/A",
    "os_version": "iOS 18.4",
    "language_support": "Tiếng Việt, Đa ngôn ngữ"
  },
  "dim_display": {
    "display_type": "Super Retina XDR OLED",
    "color_depth": "16 triệu màu",
    "display_standard": "Super Retina XDR OLED, HDR10, 800 nits (HBM), 1200 nits (peak)\r\n6.1 inches, 1.5K (1170 x 2532 pixels)\r\nTỷ lệ 19.5:9, mật độ điểm ảnh ~457 ppi",
    "resolution": "1170 x 2532 pixels",
    "screen_size": "6.1 inches",
    "touch_technology": "Cảm ứng điện dung đa điểm"
  },
  "dim_camera": {
    "rear_camera": "48 MP, f/1.6, 26mm (góc rộng), PDAF, OIS\r\nQuay phim: 4K@24/25/30/60fps, 1080p@25/30/60/120/240fps, HDR, OIS, stereo sound rec.",
    "front_camera": "12 MP, f/1.9 (góc rộng)\r\nSL 3D, (độ sâu/sinh trắc học)\r\nQuay phim: 4K@24/25/30/60fps, 1080p@25/30/60/120fps, HDR",
    "flash_light": "Có",
    "camera_features": "Dual-LED dual-tone flash, HDR, panorama, 3D (spatial) audio (camera sau)\r\nHDR, Dolby Vision HDR, 3D (spatial) audio, stereo sound rec. (camera trước)",
    "video_recording": "4K@24/25/30/60fps, 1080p@25/30/60/120/240fps, HDR, OIS, stereo sound rec.",
    "video_call": "Có"
  },
  "dim_performance": {
    "cpu_speed": "2x4.04 GHz + 4x2.20 GHz",
    "core_count": "6 nhân",
    "chipset": "Apple A18 (3 nm)\r\n6 nhân (2x4.04 GHz + 4x2.20 GHz)\r\nGPU: Apple GPU (4 lõi đồ họa)",
    "ram_capacity": "8GB",
    "gpu_chip": "Apple GPU (4 lõi đồ họa)"
  },
  "dim_storage": {
    "phonebook_storage": "Không giới hạn",
    "internal_storage": "128-512GB",
    "external_memory": "Không",
    "max_external_support": "Không"
  },
  "dim_design": {
    "design_style": "Khung nhôm phẳng\r\n2 mặt kính cường lực phẳng (Ceramic Shield)\r\nKháng nước, bụi IP68 (dưới 6m trong 30 phút)",
    "dimensions": "146.7 x 71.5 x 7.8 mm",
    "weight": "167 g"
  },
  "dim_battery": {
    "battery_type": "Li-Ion",
    "battery_capacity": "Li-Ion 4005 mAh\r\nSạc nhanh (dây) >20W\r\nSạc không dây (Qi) 7.5W",
    "removable_battery": "Không"
  },
  "dim_connectivity": {
    "network_3g": "HSDPA 850 / 900 / 1700(AWS) / 1900 / 2100",
    "network_4g": "HSPA, LTE (CA), 5G",
    "sim_type": "Nano SIM + eSIM",
    "sim_slots": "Nano SIM + eSIM",
    "wifi": "Wi-Fi 802.11 a/b/g/n/ac/6, 2 băng tần, hotspot",
    "gps": "GPS, GLONASS, GALILEO, BDS, QZSS, NavIC",
    "bluetooth": "5.3, A2DP, LE",
    "gprs_edge": "Có",
    "headphone_jack": "Không\r\nLoa kép stereo",
    "nfc": "Có",
    "usb_connection": "USB Type-C 2.0",
    "other_connections": "NFC",
    "charging_port": "Type-C"
  },
  "dim_utilities": {
    "movie_playback": null,
    "music_playback": null,
    "charging_port_alt": "Type-C",
    "voice_recorder": "Có",
    "fm_radio": "Có",
    "other_features": null
  },
  "id": "DEV-CF746AC17A"
}
```

---

### 5.5 Các kỹ thuật áp dụng trong LLM Name Normalization (Bước 4)
Dựa vào prompt và code bạn cung cấp, đây là phần bổ sung cho README:

#### Mục tiêu

Sau khi deduplication, mỗi Master record vẫn mang tên Marketing thô từ crawler. Bước này dùng LLM để đọc hardware spec và sinh ra trường `search_query_name` — tên sạch, chuẩn hóa — phục vụ tìm kiếm YouTube/Google review chính xác nhất.

#### Input / Output

| | Mô tả |
|---|---|
| **Input** | `unique_smartphone_specs.json` (1,547 records) |
| **Output** | `ready_to_load_specs.json` — toàn bộ record gốc được bổ sung thêm trường `search_query_name` |

#### Model & Cấu hình

```python
self.llm = ChatOpenAI(
    model="gpt-5.4-mini",
    api_key=api_key,
    temperature=0.1        # Gần như deterministic — tránh LLM "sáng tạo" tên máy
)
```

Temperature thấp (`0.1`) là bắt buộc: tên điện thoại không có chỗ cho sự ngẫu nhiên.

#### Schema đầu ra (Structured Output)

```python
class NormalizedPhoneName(BaseModel):
    search_query_name: str = Field(
        description="Tên chuẩn của điện thoại kèm theo tên loại chipset "
                    "(không lấy phần thông số xung nhịp/nhân)."
    )
```

LLM được ràng buộc trả về JSON theo Pydantic schema — loại bỏ hoàn toàn rủi ro parse lỗi.

#### Chiến lược Prompt

Script truyền vào 3 trường từ mỗi record:

| Trường truyền vào | Field nguồn | Vai trò |
|---|---|---|
| `product_name` | `fact_product.product_name` | Tên thô chứa nhiễu Marketing |
| `chipset` | `dim_performance.chipset` | Chuỗi dài gồm tên chip + xung nhịp + GPU |
| `internal_storage` | `dim_storage.internal_storage` | Dung lượng (dùng để LLM tránh nhầm, không đưa vào output) |

**Quy tắc sinh `search_query_name`:**

- Format: `[Brand + Model]` + `[Tên chip rút gọn]`
- **Giữ lại:** tên brand, model chính xác
- **Bỏ hoàn toàn:** RAM, ROM/Storage, màu sắc, tình trạng (`cũ`, `99%`), mã vùng (`VN/A`, `bản Mỹ`), khuyến mãi
- **Chipset:** Chỉ giữ tên dòng chip, cắt bỏ số nhân, xung nhịp GHz, kiến trúc nm, GPU
- **Dual-chip** (Samsung S10 series): Giữ cả hai tên chip chuẩn

#### Ví dụ minh họa

| `product_name` (thô) | `chipset` (thô) | `search_query_name` (output) |
|---|---|---|
| `iPhone 16e cũ (99% Đẹp như mới)` | `Apple A18 (3 nm)\r\n6 nhân...` | `iPhone 16e` |
| `Samsung Galaxy S23 Ultra Chính hãng VN/A 8GB/256GB Giảm 30%` | `Qualcomm SM8550... Snapdragon 8 Gen 2 (4 nm)\r\n8 nhân...` | `Samsung Galaxy S23 Ultra Snapdragon 8 Gen 2` |
| `Samsung Galaxy S10 Plus` | `Exynos 9820: 8 nhân...\r\nSnapdragon 855: 8 nhân...` | `Samsung Galaxy S10 Plus Exynos 9820 Snapdragon 855` |
| `Tecno CAMON 30 Pro 5G (màn AMOLED 144Hz)` | `Dimensity 8200 Ultimate...` | `Tecno CAMON 30 Pro 5G Dimensity 8200 Ultimate` |

> **Lý do giữ chipset trong search query:** Các mẫu máy bán ở nhiều thị trường khác nhau (Samsung S-series, OnePlus...) dùng chip khác nhau theo khu vực. Query `"Samsung Galaxy S23 Snapdragon 8 Gen 2"` sẽ trả về video review đúng variant, thay vì trộn lẫn kết quả của cả hai phiên bản Exynos và Snapdragon.

#### Lệnh chạy

```bash
python -m src.scripts.run_llm_name_normalization
```

**Kết quả log mẫu:**

```
INFO: Processing (1546/1547): Tecno Spark 7
INFO:   -> Normalized: Tecno Spark 7 Helio A25
INFO: Processing (1547/1547): Tecno CAMON 30 Pro 5G (màn AMOLED 144Hz)
INFO:   -> Normalized: Tecno CAMON 30 Pro 5G Dimensity 8200 Ultimate
INFO: Hoàn thành! Đã ghi gộp 1547 bản ghi ra file: .../ready_to_load_specs.json
```

### 5.6 Các kỹ thuật áp dụng trong Final Deduplication (Bước 5)

Bước này sẽ duyệt qua `ready_to_load_specs.json` và loại bỏ các record có `search_query_name` trùng lặp, để đảm bảo mỗi thiết bị vật lý chỉ còn một record duy nhất trước khi nạp vào database. 

