# Quản lý Database PostgreSQL RDS (Smartphone Specs)

> Hướng dẫn về tổ chức, kết nối, tải và quản lý dữ liệu trên cơ sở dữ liệu PostgreSQL RDS thông qua các Scripts chuyên dụng trực thuộc thư mục `backend/src/scripts/database`.

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Thiết kế DB Schema (Star Schema)](#2-thiết-kế-db-schema-star-schema)
3. [Cấu hình Kết nối](#3-cấu-hình-kết-nối)
4. [Các Script Quản lý](#4-các-script-quản-lý)
5. [Quy trình Load Dữ liệu (Load Pipeline)](#5-quy-trình-load-dữ-liệu-load-pipeline)
6. [Lưu ý khi vận hành](#6-lưu-ý-khi-vận-hành)

---

## 1. Tổng quan

Sau khi đã cào và làm sạch dữ liệu thành công qua quy trình Deduplication & Normalization (sản sinh ra `final_ready_to_load_specs.json`), bước tiếp theo là đẩy dữ liệu lưu trữ bền vững vào **PostgreSQL RDS**. 
Nền tảng sử dụng kiến trúc phân tích dạng **Star Schema** để tối ưu cho việc truy vấn chuyên sâu về các khía cạnh thông số .

---

## 2. Thiết kế DB Schema (Star Schema)

Cấu trúc cơ sở dữ liệu dựa trên mô hình bảng Fact-Dimension, trong đó mọi thông số của một chiếc điện thoại được chia nhỏ ra thành các Table theo nhóm thông số cấu hình.

**Bảng trung tâm:**
- `fact_product`: Chứa các thông tin định danh và kinh doanh của sản phẩm (`product_name`, giá, os). Đóng vai trò là HUB chính, kết nối với tất cả các bảng Dimension qua khóa ngoại `product_id`.

**Các bảng phân tích (Dimension Tables):** 
Mỗi Dimension table phân rã chi tiết về một hệ thống nhất định của điện thoại. Cấu trúc chung của một bảng Dimension phần cứng luôn bao gồm `product_id` (Khóa ngoại) và các cột metadata (`youtuber_review`, `user_review`).
- `dim_display`: Màn hình (loại màn hình, độ phân giải, kích thước, chuẩn màn hình, công nghệ cảm ứng...)
- `dim_camera`: Máy ảnh (camera trước/sau, quay phim, tính năng camera, flash...)
- `dim_performance`: Hiệu năng (tốc độ CPU, số nhân, chipset, dung lượng RAM, chip đồ họa GPU)
- `dim_storage`: Lưu trữ (bộ nhớ trong, danh bạ, thẻ nhớ ngoài...)
- `dim_design`: Thiết kế (phong cách thiết kế, kích thước, trọng lượng)
- `dim_battery`: Pin & sạc (loại pin, dung lượng, pin có thể tháo rời...)
- `dim_connectivity`: Kết nối (mạng 3G/4G, loại SIM, Wifi, GPS, Bluetooth, NFC, cổng sạc, jack tai nghe...)
- `dim_utilities`: Tiện ích (chơi nhạc, xem phim, ghi âm, radio FM, các tính năng khác...)

**Các bảng phân tích nội dung Media (YouTube):**
Bổ sung các bảng lưu trữ dữ liệu từ YouTube để phục vụ cho phân tích Text và AI/RAG:
- `dim_video_transcripts`: Lưu trữ đường dẫn tới S3 chứa video/audio/transcript và nội dung text thô của Transcript video Youtube liên quan đến sản phẩm. (Tham chiếu `product_id` từ `fact_product`)
- `dim_video_comments`: Lưu trữ nội dung bình luận của người dùng bên dưới các video Youtube. (Tham chiếu qua `video_id` từ bảng `dim_video_transcripts`)

---

## 3. Cấu hình Kết nối

Hệ thống sử dụng thư viện **SQLAlchemy** để quản trị ORM và quản lý connection pool. 

Tất cả cấu hình bảo mật kết nối tới RDS được thiết lập quản lý bới `backend/src/app/config/settings.py` đọc từ file `.env`. 

```env
DATABASE_URL=postgresql://<username>:<password>@<rds_endpoint>:<port>/<db_name>
```

> **Ghi chú**: Đảm bảo security group của RDS Instance cho phép địa chỉ IP (hoặc server ứng dụng) truy cập vào cổng 5432 (Cổng mặc định của PostgreSQL).

---

## 4. Các Script Quản lý

Thư mục này `backend/src/scripts/database/` chứa các kịch bản thực thi trực tiếp việc tác động dữ liệu lên PostgreSQL RDS:

- **`bootstrap_db.py`**:
  - *Chức năng*: Khởi tạo Database Schema lần đầu. Lệnh này sẽ tạo tự động tất cả các Table Fact và Dimension dựa theo mô hình trong `backend/src/app/database/models.py`.
  - *Sử dụng*: Chạy 1 lần duy nhất trên Data Warehouse hoặc khi muốn reset toàn bộ Schema.
  - *Câu lệnh*: `python -m src.scripts.database.bootstrap_db`

- **`load_products_to_db.py`**:
  - *Chức năng*: Xử lý file JSON sạch đã được lọc trùng (`final_ready_to_load_specs.json`) để thực hiện thao tác **INSERT** hàng loạt vào Database một cách an toàn. Đảm bảo toàn vẹn dữ liệu (Bấm `product_id` từ Fact vào các bảng Dim).
  - *Câu lệnh*: `python -m src.scripts.database.load_products_to_db`

---

## 5. Quy trình Load Dữ liệu (Load Pipeline)

Để chạy luồng đẩy dữ liệu vào db, hãy thực hiện theo tuần tự sau:

### Bước 1: Khởi tạo/Kiểm tra Schema
Nếu là lần đầu hoặc bạn vừa xóa Database đi làm lại, hãy định nghĩa Schema:
```bash
python -m src.scripts.database.bootstrap_db
```

### Bước 2: Nạp cục dữ liệu Final
Data đã được thiết kế sẵn để nằm ở `backend/data/processed/final_ready_to_load_specs.json`. Script load này đã cover cả việc bóc tách data JSON đưa map vào Dimension hợp lý:
```bash
python -m src.scripts.database.load_products_to_db
```

**Hoạt động kỹ thuật của `load_products_to_db`**:
- **Transaction Safe**: Cơ chế Bulk Insert/Transaction. Nếu một lỗi parse xảy ra giữa chừng, thao tác sẽ được rollback thay vì gặp trạng thái dữ liệu rác.
- **Relational Integrity**: Script insert `fact_product` trước tiên để lấy `product_id` tự tăng dội ngược trở lại. Sau đó insert đồng thời mảnh dữ liệu đó vào các bảng `dim` cùng với FOREIGN KEY đó. 

---

## 6. Lưu ý khi vận hành

1. **Idempotent Load**: Việc nạp lại một lượt dữ liệu `final_ready_to_load_specs.json` có thể dẫn đến việc trùng lặp (duplicate PK hoặc thông tin) nếu không cẩn trọng trong code Load_Script. (Hiện tại RDS cần được cấu hình UPSERT tùy thuộc vào logic của project).
2. **PostgreSQL Size**: File JSON 1,500 records dung lượng nhỏ, nhưng phần Text Dimension có nội dung cực kì lớn, nên hãy để ý Indexing phù hợp phục vụ AI tra cứu về sau. Tương lai ta có thể thêm Extension `pgvector` vào RDS nếu làm RAG.
3. **Sao lưu**: Hãy config AWS RDS tự động backup hằng ngày để không bị mất dữ liệu quý giá này nếu thao tác nhầm!
