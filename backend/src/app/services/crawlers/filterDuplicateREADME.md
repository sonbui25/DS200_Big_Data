# Hướng dẫn & Quy trình Lọc Trùng (Duplicate Filtering) Smartphone

## 1. Bối cảnh và Vấn đề (Context & Problem)
Trong quá trình cào dữ liệu từ các trang thương mại điện tử (ví dụ: MobileCity), tên sản phẩm (product title) thu thập về thường chứa rất nhiều tiền tố, hậu tố mang tính chất marketing, sale hoặc phân loại tồn kho. Cùng một mẫu điện thoại cốt lõi nhưng bị phân mảnh thành hàng tá bản ghi khác nhau, ví dụ:
- **Tình trạng độ mới**: "99%", "99.9%", "Cũ keng", "Mới fullbox", "Trầy xước nhẹ".
- **Khuyến mãi / Sự kiện**: "Giảm giá 30%", "Flash sale", "Mừng khai trương".
- **Biến thể bộ nhớ/màu sắc**: "128GB", "8/256GB", "Mặt lưng da".
- **Nguồn gốc / Mã Vùng**: "Bản Mỹ", "Bản Hàn", "Chính hãng VN/A", "Nội địa".

**Hậu quả để lại:**
1. **Dư thừa dữ liệu (Redundancy):** Database bị phình to bởi những thông tin rác.
2. **Kiệt quệ Youtube API Quota:** Khi gọi pipeline cào media YouTube (`youtube_media_pipeline.py`), nếu dùng cả cụm "iPhone 14 Pro Max 256GB Giảm 30% Cũ 99" làm query, YouTube sẽ search không chính xác và văng ra kết quả nhiễu. Hơn nữa, việc tìm kiếm lặp đi lặp lại cho các sản phẩm chung bản chất sẽ ngốn limit API nhanh chóng và làm giảm hiệu suất toàn hệ thống.

## 2. Giải pháp thiết kế: LLM Entity Extraction
Thay vì sử dụng Regex phức tạp, dễ bảo trì kém và thiếu độ linh hoạt với các case mới, bộ lọc trùng sẽ ứng dụng **GenAI / LLM**. Định hướng sắp tới là sử dụng **Google Gemini 3 Flash Lite** (đáp ứng tiêu chí tối ưu hóa chi phí token, tốc độ phản hồi cực nhanh) thông qua **Langchain** + **Pydantic Structured Output**.

## 3. Tiêu chuẩn Bóc tách Thực thể (Entities to Extract)
LLM cần được tuning bằng prompt kỹ lưỡng để parse các tên dài dòng thành chuẩn JSON sau:

- `base_name`: Tên lõi gốc của mẫu điện thoại.
  *Lưu ý then chốt*: Một số hãng (như Xiaomi, Realme) hay đính kèm tên vi xử lý vào tên máy để phân biệt biến thể (VD: *Redmi Note 12 Turbo Snapdragon 7+ Gen 2*, *Realme GT 5 Pro Dimensity*). LLM bắt buộc phải giữ lại hậu tố con chip này trong `base_name` vì nó là yếu tố quyết định phiên bản model. Tuyệt đối bỏ đi các từ khóa rác, km, màu sắc.
- `storage`: Phiên bản RAM / Bộ nhớ trong (VD: "8GB/256GB", "1TB"). Nếu không có thì trả về "unknown".
- `condition`: Tình trạng tổng quát. Cần map tất cả các keyword ("99%", "99.9%", "Nguyên seal", "Like new") về 2 nhóm cơ bản: **"Cũ"** hoặc **"Mới"** để dễ group.
- `region`: Phân loại khu vực / mã (VD: "Chính hãng", "Xách tay", "Bản Mỹ", "VN/A").
- `memory`: Dung lượng RAM (Trích xuất từ cấu hình chi tiết).
- `chipset`: Tên vi xử lý / CPU (Yếu tố cực kỳ quan trọng để định danh chính xác thiết bị, trích xuất từ cấu hình chi tiết).

## 4. Pipeline Mới Phân Tách Crawl & Load (The Advanced Workflow)
Việc chỉ dựa vào chuỗi `product_title` để lọc trùng là rủi ro và thiếu dữ liệu (ví dụ máy không ghi chip trên tên nhưng khác cấu hình). Do đó, chiến lược sẽ thay đổi: thu thập toàn bộ thông tin Dimensions (cấu hình chi tiết) trước khi lọc.

1. **Crawl Links**: Chạy crawler để lấy ~2300 links sản phẩm -> lưu vào `data/raw/product_links.json`.
2. **Crawl Specs to Local JSON**: Cào chi tiết từng sản phẩm (dựa trên link) để lấy thông số kỹ thuật (memory, chipset, camera, battery...) -> **Lưu ra 1 file trung gian (vd: `product_specs_raw.json`) chứ KHÔNG đẩy thẳng vào DB**.
3. **LLM Deduplication & Normalization**: Dùng LLM (Gemini 3 Flash Lite) truyền vào cả *Tên Sản Phẩm* + *Thông Số Kỹ Thuật (Dim)*. LLM sẽ dễ dàng nhận diện và gộp các bản ghi giống nhau về bảng cấu hình nhưng khác râu ria ở tên. Output ra file `product_specs_cleaned.json`.
4. **Generate YouTube Queries**: Lấy các `base_name` đã làm sạch và duy nhất để cào video review.
5. **Load to RDS**: Nạp dữ liệu sạch từ file `cleaned.json` vào các bảng Fact và Dim của PostgreSQL.
