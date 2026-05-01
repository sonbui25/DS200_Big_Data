# Media Collection Scripts

> Thư mục này chứa các script chuyên xử lý việc tải và thu thập thông tin Media (Youtube, Hình ảnh) từ các nguồn ngoại vi dồn về hệ thống nội bộ.

---

## Tổng quan các Scripts

### `run_unique_smartphone_media_flow.py`
- **Mục đích**: Bước chạy riêng biệt để thu thập Media (Hình ảnh tải về hoặc link Review từ YouTube). Thường được chạy sau khi dữ liệu điện thoại đã trải qua các bước lọc trùng và chuẩn hóa tên (để không gọi YouTube API cho các truy vấn trùng lặp gây lãng phí dung lượng).
- **Cách chạy**:
  ```bash
  python -m src.scripts.media.run_unique_smartphone_media_flow
  ```
