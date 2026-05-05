# Media Collection Scripts

> Thư mục này chứa các script chuyên xử lý việc thu thập Media (Audio, Comments, Transcripts) từ YouTube cho từng sản phẩm điện thoại. Toàn bộ dữ liệu được tự động tải xuống, tổ chức theo cấu trúc thư mục chuẩn, đẩy lên **Amazon S3**, đồng thời ghi nhận siêu dữ liệu vào **PostgreSQL (RDS)**. Pipeline hỗ trợ **xử lý song song đa luồng** và **xoay vòng API Key** để tối ưu tốc độ thu thập.

---

## Mục lục

- [1. Cấu trúc Module](#1-cấu-trúc-module)
- [2. Tổ chức dữ liệu](#2-tổ-chức-dữ-liệu)
- [3. Quản lý dữ liệu trên RDS](#3-quản-lý-dữ-liệu-trên-rds)
- [4. Quy trình thu thập](#4-quy-trình-thu-thập)
- [5. Xử lý song song & API Key Pool](#5-xử-lý-song-song--api-key-pool)
- [6. Cơ chế Rollback & Đồng bộ](#6-cơ-chế-rollback--đồng-bộ)
- [7. Hệ thống Logging](#7-hệ-thống-logging)
- [8. Hướng dẫn cấu hình](#8-hướng-dẫn-cấu-hình)
- [9. Hướng dẫn chạy Script](#9-hướng-dẫn-chạy-script)

---

## 1. Cấu trúc Module

Script được tách thành các module nhỏ để dễ bảo trì:

```
src/scripts/media/
├── run_unique_smartphone_media_flow.py  # Entry point: CLI + Pipeline chính
├── _media_db.py                         # Toàn bộ thao tác CSDL (CRUD)
├── _media_cleaner.py                    # Xóa đồng bộ DB + S3 + Local
├── _media_logger.py                     # Hệ thống logging tích hợp S3
├── _api_key_pool.py                     # Thread-safe API Key Pool xoay vòng
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

File media chỉ tồn tại **tạm thời** trong quá trình xử lý. Sau khi upload S3 thành công, toàn bộ file media được **xóa tự động**. Local chỉ giữ lại file log:

```
data/processed/youtube_media/
└── media_log/                            ← CHỈ còn lại sau khi pipeline chạy
    └── {YYYY-MM-DD}/
        ├── pipeline_{HHMMSS}.log
        └── {product_name}.log
```

Trong quá trình xử lý (tạm thời, tự xóa sau khi upload S3):
```
data/processed/youtube_media/
├── audio/{product_name}/
│   └── 01_{tieu_de_video}.mp3               ← xóa sau khi upload S3
├── comments/{product_name}/
│   ├── 01_{tieu_de_video}_comments.csv      ← xóa sau khi upload S3
│   └── 01_{tieu_de_video}.info.json         ← xóa sau khi upload S3
└── transcripts/{product_name}/
    └── 01_{tieu_de_video}_transcript.json   ← xóa sau khi upload S3
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

- `product_name` được chuẩn hóa: chữ thường, bỏ dấu (dùng `unidecode`), thay ký tự đặc biệt bằng `_`. Ví dụ: `iphone_12_apple_a14`.
- Tên file video theo định dạng `{số_thứ_tự:02d}_{tiêu_đề_video}`, giới hạn 50 ký tự. Ví dụ: `01_Mo_Hop_Danh_Gia_iPhone_12`.
- Tiêu đề video cũng được xử lý `unidecode` để tránh lỗi encoding trên các hệ điều hành khác nhau.

---

## 3. Quản lý dữ liệu trên RDS

Sau khi upload S3 thành công, metadata được ghi ngay vào 2 bảng:

**Bảng `dim_video_transcripts`** — Siêu dữ liệu của mỗi video:

| Cột | Mô tả |
|---|---|
| `product_id` | Tham chiếu đến sản phẩm trong `fact_product` |
| `youtube_url` | Đường dẫn video YouTube (dùng làm unique key, idempotent) |
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

Với mỗi sản phẩm, pipeline thực hiện tuần tự các bước sau trong thread riêng:

**Bước 1 — Tìm kiếm video (YouTube Data API):**
- Query: `review {product_name}`, `regionCode="VN"` để ưu tiên kết quả tiếng Việt.
- Số video tối đa cấu hình qua `YOUTUBE_MAX_RESULTS_PER_PRODUCT` trong `.env` (giới hạn tối đa 50 theo YouTube API).
- Nếu key hiện tại hết quota → tự động xoay sang key tiếp theo trong pool (xem mục 5).

**Bước 2 — Tải nội dung từng video:**
- **Audio** (.mp3): Dùng `yt-dlp` với flag `-x --audio-format mp3 --remote-components ejs:github`. Flag `--remote-components` cần thiết để giải JS challenge mà YouTube dùng để bảo vệ stream URL.
- **Comments** (.csv): Dùng `yt-dlp` với `--write-info-json --write-comments`, parse từ `.info.json`.
- **Transcript** (.json): Dùng `youtube-transcript-api` v1.2.4+, ưu tiên ngôn ngữ `['vi', 'en']`. Nếu không có vi/en, tự động **fallback** sang bất kỳ ngôn ngữ nào available (kể cả auto-generated). Transcript lưu dạng JSON với `ensure_ascii=False` để giữ nguyên tiếng Việt.

**Bước 3 — Upload lên S3:**
- 3 file được upload tuần tự: audio → comments → transcript.
- Nếu upload thất bại → bỏ qua video đó, **không ghi DB**, không làm gián đoạn các video tiếp theo.

**Bước 4 — Xóa file local:**
- Ngay sau khi upload S3 thành công, toàn bộ file media local được xóa: audio .mp3, comments .csv, .info.json, transcript .json.
- Subfolder rỗng sau khi xử lý xong product cũng được dọn dẹp tự động.

**Bước 5 — Ghi nhận vào DB:**
- Kiểm tra `youtube_url` đã tồn tại chưa trước khi insert (idempotent).
- Insert `dim_video_transcripts` trước → lấy `video_id` → insert `dim_video_comments`.

**Bước 6 — Đánh dấu hoàn thành:**
- Tên sản phẩm được ghi **thread-safe** (dùng `threading.Lock`) vào `data/processed/media_completed_products.json`.

---

## 5. Xử lý song song & API Key Pool

### Đa luồng (ThreadPoolExecutor)

Pipeline xử lý nhiều sản phẩm **đồng thời** thay vì tuần tự, mỗi sản phẩm chạy trong 1 thread độc lập:

```
ThreadPoolExecutor (N workers)
  ├── Worker 1: iPhone 12   ──┐
  ├── Worker 2: Samsung S24   ├── Chạy đồng thời, độc lập nhau
  └── Worker 3: Oppo Reno8   ─┘
```

Số workers cấu hình qua `--workers` (mặc định 3). Khuyến nghị:

| Tình huống | Workers |
|---|---|
| VPS băng thông thấp | 2 |
| VPS bình thường | 3–5 |
| Muốn tiết kiệm quota tối đa | 1 |
| Debug nhanh | `--workers 2 --max-products 4` |

### API Key Pool

Nhiều YouTube Data API keys được xoay vòng tự động, thread-safe, để tránh hết quota giữa chừng:

```
Pool khởi động: [key1, key2, key3, key4]
                     ↑ current

Worker search → key1 → 403 quotaExceeded
                   → mark_exhausted(key1) [acquire lock → rotate → release]
                   → current = key2
                   → retry search → OK

... key2 hết → key3 → key4 → raise YouTubeQuotaExceededError("Hết tất cả keys")
                               → cancel toàn bộ futures còn lại
                               → flush log → pipeline dừng
```

Cấu hình trong `.env` bằng dấu phẩy:
```env
YOUTUBE_DATA_API_KEYS=AIzaS_key1,AIzaS_key2,AIzaS_key3,AIzaS_key4
```

---

## 6. Cơ chế Rollback & Đồng bộ

### Tracking file

File `media_completed_products.json` đánh dấu các sản phẩm đã thu thập đủ. Khi pipeline khởi động, các sản phẩm có trong file này bị **bỏ qua hoàn toàn**. File được ghi thread-safe khi nhiều workers chạy đồng thời.

Nếu file tracking bị mất hoặc rỗng trong khi DB/S3 vẫn còn data, rebuild lại từ DB:

```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --rebuild-tracking
```

### Rollback tự động (3 tầng đồng bộ)

Với mỗi sản phẩm **chưa có trong tracking file**, hệ thống tự động rollback sạch trước khi ingest lại, đảm bảo không có rác dữ liệu:

```
Rollback (theo thứ tự):
  1. DB    → DELETE dim_video_comments (child) trước
           → DELETE dim_video_transcripts (parent) sau
              (đúng thứ tự để tránh Foreign Key Violation)

  2. S3    → list_object_versions() lấy tất cả Versions + Delete Markers
           → delete_objects(VersionId=...) xóa thật sự từng version
              (bucket bật Versioning: delete thường chỉ tạo delete marker,
               phải xóa theo VersionId mới thật sự xóa được)

  3. Local → rmtree(audio/{product_name}/)
           → rmtree(comments/{product_name}/)
           → rmtree(transcripts/{product_name}/)
```

> **Lưu ý S3 Versioning:** Bucket `smartphone-data-s3` đang bật Versioning. IAM user cần đủ quyền: `s3:ListBucketVersions`, `s3:DeleteObjectVersion`, `s3:DeleteObject`.

### Xử lý khi gián đoạn

| Tình huống | Hành vi |
|---|---|
| `Ctrl+C` | SIGINT handler flush log → exit. Lần chạy sau rollback product chưa xong rồi ingest lại |
| Upload S3 thất bại | Skip video đó, không ghi DB → không có record "treo" trong DB |
| Ghi DB thất bại | File đã lên S3 nhưng không có record → rollback lần sau dọn S3 |
| Hết tất cả API keys | Cancel toàn bộ futures, flush log, dừng pipeline |
| Chạy lại sau khi dừng | Tracking file đảm bảo không xử lý lại product đã hoàn thành |
| 2 workers ghi tracking cùng lúc | `threading.Lock` đảm bảo chỉ 1 thread ghi tại 1 thời điểm |

---

## 7. Hệ thống Logging

Mỗi lần chạy sinh ra **2 loại log file** lưu đồng thời local và S3:

| Log file | Nội dung |
|---|---|
| `pipeline_{HHMMSS}.log` | Toàn bộ tiến trình pipeline (start/stop, skip, rollback, pool rotation, tổng kết) |
| `{product_name}.log` | Chi tiết xử lý từng video của 1 sản phẩm |

**Cơ chế flush lên S3 — không cần đợi pipeline kết thúc:**

- Tự động flush sau mỗi **10 dòng log** (cấu hình qua `flush_every`).
- Flush **ngay lập tức** khi gặp log level `ERROR` hoặc `CRITICAL`.
- Flush **trước khi thoát** khi bị `Ctrl+C` (bắt `SIGINT`).
- Force flush khi xử lý xong mỗi sản phẩm.

```
2026-05-03 14:30:22 [INFO]    Pipeline started: specs=... max_products=None workers=3
2026-05-03 14:30:22 [INFO]    API Key Pool: 4 keys — ['...key1', '...key2', '...key3', '...key4']
2026-05-03 14:30:22 [INFO]    Pending: 1447 products to process.
2026-05-03 14:30:25 [INFO]    [1/1447] >>> Processing: 'iPhone 12 Apple A14' (ID=1)
2026-05-03 14:30:26 [DEBUG]   Deleting 9 objects under prefix=audio/iphone_12_apple_a14/
2026-05-03 14:30:27 [INFO]    Cleared product_id=1: s3_files=9 local_folders=3
2026-05-03 14:30:31 [INFO]    transcript fetch done lang=preferred count=426
2026-05-03 14:30:35 [WARNING] Transcript fetch failed id=rD_uJwsxkjk: No transcripts found
2026-05-03 14:30:38 [WARNING] API key ...abc123 exhausted. Rotating to ...def456
2026-05-03 14:31:02 [INFO]    Done: hits=30 upl=30 comms=1842
```

---

## 8. Hướng dẫn cấu hình

Các biến trong file `.env`:

```env
# YouTube — nhiều keys phân cách bằng dấu phẩy
YOUTUBE_DATA_API_KEYS=AIzaS_key1,AIzaS_key2,AIzaS_key3,AIzaS_key4
YOUTUBE_MAX_RESULTS_PER_PRODUCT=30   # Tối đa 50 theo giới hạn YouTube API

# AWS S3
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=smartphone-data-s3
AWS_S3_AUDIO_PREFIX=audio
AWS_S3_COMMENTS_PREFIX=comments
AWS_S3_TRANSCRIPTS_PREFIX=transcripts
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# PostgreSQL RDS
DB_HOST=...
DB_PORT=5432
DB_NAME=ds200
DB_USER=postgres
DB_PASSWORD=...
```

**IAM Permissions tối thiểu cho S3:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
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
  ]
}
```

**Yêu cầu hệ thống:**
- `yt-dlp` cài sẵn trong PATH. Cập nhật thường xuyên vì YouTube thay đổi JS challenge định kỳ:
  ```bash
  yt-dlp -U
  ```
- `node` hoặc `deno` cài sẵn trong PATH (yt-dlp dùng để giải JS challenge).

---

## 9. Hướng dẫn chạy Script

**Chạy toàn bộ pipeline (mặc định 3 workers):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow
```

**Tùy chỉnh số workers theo băng thông VPS:**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --workers 5
```

**Chạy thử 1 sản phẩm (test mode):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --test
```

**Giới hạn số sản phẩm (debug):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --max-products 10 --workers 2
```

**Tắt verbose log của yt-dlp:**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --quiet-youtube
```

**Rebuild tracking file từ DB (khi file bị mất/rỗng):**
```bash
python -m src.scripts.media.run_unique_smartphone_media_flow --rebuild-tracking
```

> **Lưu ý vận hành:** Mọi cơ chế kiểm tra (Check), phục hồi (Rollback) và đánh dấu tiến độ (Tracking) đều được tự động hóa hoàn toàn. Nếu pipeline bị gián đoạn do mất mạng, hết quota, hay `Ctrl+C`, chỉ cần chạy lại lệnh bình thường — hệ thống tự đọc tracking file, rollback product chưa hoàn thành, và tiếp tục từ đúng chỗ mà không bị trùng lặp dữ liệu.