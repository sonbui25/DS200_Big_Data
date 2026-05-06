# 🚀 Hướng Dẫn Deploy Media Flow Worker Bằng Docker

Tài liệu này hướng dẫn cách đóng gói và chạy tiến trình tải media từ YouTube (`run_unique_smartphone_media_flow.py`) trên VPS Ubuntu (hoặc test trên Local) thông qua Docker và Docker Compose.

## 🏗 Yêu cầu hệ thống
- Đã cài đặt [Docker](https://docs.docker.com/engine/install/).
- Đã cài đặt [Docker Compose](https://docs.docker.com/compose/install/).

## ⚙️ Cấu hình ban đầu
Bạn cần có một file `.env` tại thư mục chứa `docker-compose.yml`. File này chứa các cấu hình quan trọng như API Key, Database URL, AWS Keys:
```env
# Database connection
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# YouTube API Keys
YOUTUBE_DATA_API_KEYS=key1,key2,key3

# AWS S3 Storage
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket_name
```

## 🚚 Khởi chạy dịch vụ

Với kiến trúc Multi-Service Scripts, bạn có thể gọi đích danh pipeline nào muốn chạy bằng cấu trúc `--profile`.

**Ví dụ chạy Media Worker**:
```bash
docker compose --profile media up -d --build media-worker
```
> **Giải thích lệnh**:
> - `--profile media`: Kích hoạt cấu hình (service) được đánh dấu thuộc profile "media" (cụ thể là `media-worker`).
> - `up`: Lệnh khởi tạo và chạy các containers.
> - `-d` (detached): Yêu cầu tiến trình chạy ngầm ở background, để bạn có thể tiếp tục dùng terminal.
> - `--build`: Cưỡng chế Docker build lại Image (cài `ffmpeg`, `nodejs`, `requirements.txt`) để nắm bắt code/thư viện mới nhất trước khi chạy.
> - `media-worker`: Tên đích danh của container cần khởi chạy được định nghĩa trong `docker-compose.yml`.

**Ví dụ chạy Crawl Worker (nếu có)**:
```bash
docker compose --profile crawl up -d crawl-links-worker
```

## 🛠 Quản lý & Theo dõi

- **Xem Logs tiến trình Media**:
  ```bash
  docker compose --profile media logs -f media-worker
  ```
  *(Cờ `-f` hay `--follow` giữ cho terminal liên tục cập nhật dòng log mới mà không bị thoát, để thoát bạn bấm `Ctrl+C`)*

- **Dừng tiến trình khẩn cấp**:
  ```bash
  docker compose --profile media down
  ```
  *(Vì có flag `--profile media`, lệnh mới tìm thấy đúng container media-worker đang chạy để Shutdown)*

- **Sử dụng các Flag khi chạy (ví dụ test Mode)**:
  Nếu bạn cần chạy chế độ `--test` (chỉ 1 sản phẩm) thay vì chạy lệnh mặc định của container, bạn hãy dùng:
  ```bash
  docker compose run --rm media-worker python -m src.scripts.media.run_unique_smartphone_media_flow --test
  ```

## 💾 Lưu ý về Dữ Liệu
Thư mục `backend/data/` ngoài máy host đã được mount vào `/app/data` trong container. Nên bất kỳ quá trình tạo file hay checkpoint ghi vào thư mục này thì tiến độ sẽ được bảo toàn trên máy gốc kể cả khi xoá hay tạo container mới.
