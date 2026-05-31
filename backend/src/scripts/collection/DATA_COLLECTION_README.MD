# Data Collection Scripts

> Thư mục này chứa các kịch bản chạy (scripts) chịu trách nhiệm thu thập (crawling) dữ liệu từ các nguồn bên ngoài (như trang Web MobileCity, API hoặc YouTube). Đây là điểm bắt đầu của Pipeline (The Advanced Workflow), cung cấp dữ liệu thô (Raw Data) cho các bước làm sạch tiếp theo.

---

## 1. Tổng quan các Scripts

Dưới đây là các module chạy độc lập chuyên thu thập dữ liệu:

### 1.1 `run_crawl_product_links.py`
- **Mục đích**: Quét trang chủ và các danh mục điện thoại để gom toàn bộ đường link sản phẩm chi tiết lại thành một danh sách (URL).
- **Input**: *Không có (Tự động crawl từ trang chủ)*.
- **Output**: `data/raw/product_links.json` (mặc định).
- **Cách chạy**:
  ```bash
  python -m src.scripts.collection.run_crawl_product_links
  ```
  *(Có thể thêm `--max-products 100` để giới hạn số lượng cào thử).*

### 1.2 `run_crawl_all_specs.py`
- **Mục đích**: Duyệt qua từng URL vừa quét được ở bước 1, truy cập vào giao diện chi tiết để bóc tách mọi thông số cấu hình phần cứng (Hardware Specs) ra thành JSON có quy chuẩn.
- **Input**: Danh sách link (mặc định lấy từ `data/raw/product_links.json`).
- **Output**: `data/raw/all_product_specs_raw.json` (mặc định). Cấu hình có lưu tạm sau mỗi 50 mẫu phòng trường hợp đứt mạng.
- **Cách chạy**:
  ```bash
  python -m src.scripts.collection.run_crawl_all_specs
  ```

---

## 2. Quy trình (Workflow) Thu thập Đặc trưng

Nếu bạn chạy Data thủ công từ đầu (không sử dụng Pipeline 1-chạm), quy trình của thư mục `collection` nên là:

1. **Gom Link**: Gọi bash `...run_crawl_product_links` 
2. **Gom Specs**: Gọi bash `...run_crawl_all_specs`
3. Lúc này hãy chuyển sang folder `data_processing` để tiến hành làm sạch, lọc hardware và gọi AI chuẩn hóa tên với mớ raw data này nhé. Các file chứa deduplicate sẽ lo việc loại bỏ rác thương mại.
