# Media Collection Scripts

> Thư mục này chứa các script chuyên xử lý việc thu thập Media (Audio, Comments, Transcripts) từ YouTube cho từng sản phẩm điện thoại. Toàn bộ dữ liệu được tự động tải xuống, tổ chức theo cấu trúc thư mục chuẩn, đẩy lên **Amazon S3**, đồng thời ghi nhận siêu dữ liệu vào **PostgreSQL (RDS)**.

---

## Mục lục

- [1. Cấu trúc Module](#1-cấu-trúc-module)
- [2. Tổ chức dữ liệu](#2-tổ-chức-dữ-liệu)
- [3. Quản lý dữ liệu trên RDS](#3-quản-lý-dữ-liệu-trên-rds)
- [4. Quy trình thu thập](#4-quy-trình-thu-thập)
- [5. Cơ chế Rollback & Đồng bộ](#5-cơ-chế-rollback--đồng-bộ)
- [6. Hệ thống Logging](#6-hệ-thống-logging)
- [7. Hướng dẫn cấu hình](#7-hướng-dẫn-cấu-hình)
- [8. Hướng dẫn chạy Script](#8-hướng-dẫn-chạy-script)

---

## 1. Cấu trúc Module

Script được tách thành các module nhỏ để dễ bảo trì:

```
src/scripts/media/
├── run_unique_smartphone_media_flow.py  # Entry point: CLI + Pipeline chính
├── _media_db.py                         # Toàn bộ thao tác CSDL (CRUD)
├── _media_cleaner.py                    # Xóa đồng bộ DB + S3 + Local
├── _media_logger.py                     # Hệ thống logging tích hợp S3
└── MEDIA_COLLECTION_README.md
```

**Thư viện bên ngoài chính:**

| Thư viện | Mục đích |
|---|---|
| `yt-dlp` | Tải audio (.mp3) và comments (.csv) từ YouTube |
| `youtube-transcript-api` (v1.2.4+) | Lấy transcript/phụ đề video |
| `boto3` | Tương tác Amazon S3 |
| `sqlalchemy` + `psycopg2` | Ghi nhận metadata vào PostgreSQL RDS |
| `unidecode` | Chuyển tiếng Việt có dấu → không dấu cho tên file |

---

## 2. Tổ chức dữ liệu

### Cấu trúc Local

Dữ liệu local được tổ chức **mirror** hoàn toàn với cấu trúc S3, nhóm theo loại Media và `product_name` (đã chuẩn hóa):

```
data/processed/youtube_media/
├── audio/
│   └── {product_name}/
│       ├── 01_{tieu_de_video}_audio.mp3
│       └── 02_{tieu_de_video}_audio.mp3
├── comments/
│   └── {product_name}/
│       ├── 01_{tieu_de_video}_comments.csv
│       └── 01_{tieu_de_video}.info.json
├── transcripts/
│   └── {product_name}/
│       ├── 01_{tieu_de_video}_transcript.json
│       └── ...
└── media_log/
    └── {YYYY-MM-DD}/
        ├── pipeline_{HHMMSS}.log
        └── {product_name}.log
```

### Cấu trúc Amazon S3

```
s3://smartphone-data-s3/
├── audio/{product_name}/{indexed_title}_audio.mp3
├── comments/{product_name}/{indexed_title}_comments.csv
├── transcripts/{product_name}/{indexed_title}_transcript.json
└── media_log/{YYYY-MM-DD}/{product_name}.log
```

**Quy tắc đặt tên file:**

- `product_name` được chuẩn hóa: chữ thường, bỏ dấu (dùng `unidecode`), thay ký tự đặc biệt bằng `_`.
- Tên file video theo định dạng `{số_thứ_tự:02d}_{tiêu_đề_video}` (ví dụ: `01_Mo_Hop_Danh_Gia_iPhone_12`), giới hạn 50 ký tự.
- Tiêu đề video cũng được xử lý `unidecode` để tránh lỗi encoding trên các hệ điều hành khác nhau.

---

## 3. Quản lý dữ liệu trên RDS

Sau khi upload S3 thành công, metadata được ghi ngay vào 2 bảng:

**Bảng `dim_video_transcripts`** — Siêu dữ liệu của mỗi video:

| Cột | Mô tả |
|---|---|
| `product_id` | Tham chiếu đến sản phẩm trong `fact_product` |
| `youtube_url` | Đường dẫn video YouTube (dùng làm unique key) |
| `s3_audio_path` | Đường dẫn S3 đầy đủ (`s3://...`) |
| `s3_comments_path` | Đường dẫn S3 đầy đủ |
| `s3_transcript_path` | Đường dẫn S3 đầy đủ (có thể `NULL` nếu video không có transcript) |

**Bảng `dim_video_comments`** — Nội dung bình luận (phục vụ NLP, Sentiment Analysis):

| Cột | Mô tả |
|---|---|
| `video_id` | Khóa ngoại tới `dim_video_transcripts` |
| `user_name` | Tên người bình luận |
| `comment_text` | Nội dung văn bản bình luận |

---

## 4. Quy trình thu thập

Với mỗi sản phẩm hợp lệ, pipeline thực hiện tuần tự:

**Bước 1 — Tìm kiếm video (YouTube Data API):**
- Query: `review {product_name}`, `regionCode="VN"` để ưu tiên kết quả tiếng Việt.
- Số video tối đa mỗi sản phẩm cấu hình qua `YOUTUBE_MAX_RESULTS_PER_PRODUCT` trong `.env` (giới hạn tối đa 50 theo YouTube API).

**Bước 2 — Tải nội dung từng video:**
- **Audio** (.mp3): Dùng `yt-dlp` với flag `-x --audio-format mp3`.
- **Comments** (.csv): Dùng `yt-dlp` với `--write-info-json --write-comments`, parse từ `.info.json`.
- **Transcript** (.json): Dùng `youtube-transcript-api` v1.2.4+, ưu tiên ngôn ngữ `['vi', 'en']`. Nếu không có vi/en, tự động **fallback** sang bất kỳ ngôn ngữ nào available (kể cả auto-generated). Transcript được lưu dạng JSON với `ensure_ascii=False` để giữ nguyên tiếng Việt.

**Bước 3 — Upload lên S3:**
- 3 file được upload tuần tự: audio → comments → transcript.
- Nếu upload thất bại, video đó bị bỏ qua (`continue`), không làm gián đoạn các video tiếp theo.

**Bước 4 — Ghi nhận vào DB:**
- Kiểm tra `youtube_url` đã tồn tại chưa trước khi insert (idempotent).
- Insert `dim_video_transcripts` trước, lấy `video_id`, sau đó insert `dim_video_comments`.

**Bước 5 — Đánh dấu hoàn thành:**
- Tên sản phẩm được lưu vào `data/processed/media_completed_products.json`.

---

## 5. Cơ chế Rollback & Đồng bộ

### Tracking file

File `media_completed_products.json` đánh dấu các sản phẩm đã thu thập đủ. Khi script khởi động, các sản phẩm có trong file này sẽ bị **bỏ qua hoàn toàn**.

Nếu file tracking bị mất hoặc rỗng trong khi DB/S3 vẫn còn data, chạy lệnh sau để rebuild lại từ DB:

```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --rebuild-tracking
```

### Rollback tự động (3 tầng đồng bộ)

Với mỗi sản phẩm **chưa có trong tracking file**, hệ thống tự động rollback trước khi ingest lại, đảm bảo không có rác dữ liệu:

```
Rollback đồng bộ:
  1. DB  → Xóa dim_video_comments (child) trước
         → Xóa dim_video_transcripts (parent) sau
            (đúng thứ tự để tránh Foreign Key Violation)
  2. S3  → Xóa tất cả Versions + Delete Markers
            (hỗ trợ bucket bật Versioning)
  3. Local → Xóa toàn bộ subfolder audio/, comments/, transcripts/
              của product đó
```

> **Lưu ý S3 Versioning:** Bucket `smartphone-data-s3` đang bật Versioning. IAM user cần có đủ các quyền: `s3:ListBucketVersions`, `s3:DeleteObjectVersion`, `s3:DeleteObject`.

### Checkpoint & Resume (khi hết Quota API)

Khi YouTube Data API hết quota (lỗi 403 `quotaExceeded`), script tự động dừng và lưu tiến độ vào checkpoint file. Chạy lại với `--resume` để tiếp tục từ điểm dừng:

```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --resume
```

---

## 6. Hệ thống Logging

Mỗi lần chạy sinh ra **2 loại log file** được lưu đồng thời local và S3:

| Log file | Nội dung |
|---|---|
| `pipeline_{HHMMSS}.log` | Toàn bộ tiến trình pipeline (start/stop, skip, tổng kết) |
| `{product_name}.log` | Chi tiết xử lý từng video của 1 sản phẩm |

**Cơ chế flush lên S3 — không cần đợi pipeline kết thúc:**

- Tự động flush sau mỗi **10 dòng log** (cấu hình được qua `flush_every`).
- Flush **ngay lập tức** khi gặp log level `ERROR` hoặc `CRITICAL`.
- Flush **trước khi thoát** khi bị `Ctrl+C` (bắt `SIGINT`).
- Force flush khi xử lý xong mỗi sản phẩm.

```
2026-05-02 14:30:22 [INFO]  Pipeline started: specs=... max_products=None
2026-05-02 14:30:25 [INFO]  [1/1447] >>> Processing: 'iPhone 12 Apple A14' (ID=1)
2026-05-02 14:30:26 [DEBUG] Deleting 9 objects under prefix=audio/iphone_12_apple_a14/
2026-05-02 14:30:27 [INFO]  Cleared product_id=1: s3_files=9 local_folders=3
2026-05-02 14:30:31 [INFO]  transcript fetch done lang=preferred count=426
2026-05-02 14:30:35 [WARNING] Transcript fetch failed id=rD_uJwsxkjk: No transcripts found
2026-05-02 14:31:02 [INFO]  Done: hits=30 upl=30 comms=1842
```

---

## 7. Hướng dẫn cấu hình

Các biến cấu hình trong file `.env`:

```env
# YouTube
YOUTUBE_DATA_API_KEY=AIza...
YOUTUBE_MAX_RESULTS_PER_PRODUCT=30   # Tối đa 50 theo giới hạn YouTube API

# AWS
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=smartphone-data-s3
AWS_S3_AUDIO_PREFIX=audio
AWS_S3_COMMENTS_PREFIX=comments
AWS_S3_TRANSCRIPTS_PREFIX=transcripts
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# DB
DB_HOST=...
DB_PORT=5432
DB_NAME=ds200
DB_USER=postgres
DB_PASSWORD=...
```

**IAM Permissions tối thiểu cho S3:**

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:DeleteObject",
    "s3:DeleteObjectVersion",
    "s3:ListBucket",
    "s3:ListBucketVersions",
    "s3:GetBucketVersioning"
  ],
  "Resource": [
    "arn:aws:s3:::smartphone-data-s3",
    "arn:aws:s3:::smartphone-data-s3/*"
  ]
}
```

---

## 8. Hướng dẫn chạy Script

**Chạy toàn bộ pipeline:**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow
```

**Chạy thử 1 sản phẩm đầu tiên (test mode):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --test
```

**Tiếp tục từ checkpoint sau khi hết quota:**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --resume
```

**Rebuild tracking file từ DB (khi file bị mất/rỗng):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --rebuild-tracking
```

**Giới hạn số sản phẩm xử lý (debug):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --max-products 10
```

**Tắt verbose log của YouTube/yt-dlp:**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --quiet-youtube
```

> **Lưu ý:** Mọi cơ chế kiểm tra (Check), tiếp tục (Resume) và phục hồi (Rollback) đều được tự động hóa hoàn toàn. Nếu pipeline bị gián đoạn do mất mạng hoặc hết API Quota, chỉ cần chạy lại lệnh `--resume` — hệ thống tự đọc checkpoint và tracking file, tiếp tục đúng chỗ đứt mà không bị trùng lặp dữ liệu.