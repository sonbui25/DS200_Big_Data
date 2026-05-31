# Pipeline Orchestration Scripts

> Thư mục này chứa các script tổng hợp, dùng để chạy tự động toàn bộ luồng quy trình (workflow) kết nối giữa các module cào dữ liệu, xử lý dữ liệu và tải dữ liệu lên database thay vì phải chạy từng phần riêng lẻ.

---

## 1. `run_crawl_to_db.py`

**Mục đích**: Đây là script chính để tự động hóa toàn bộ quy trình: từ lúc cào URL sản phẩm, cào nội dung chi tiết (specs), xử lý dữ liệu (lọc trùng, chuẩn hóa bằng LLM) và lưu vào database. Script có khả năng tự phát hiện các bước đã hoàn thành dựa trên việc tồn tại của các file dữ liệu tương ứng.

**Các bước hoạt động**:
1. **Thu thập links**: Gọi script `run_crawl_product_links` nếu file `product_links.json` chưa tồn tại.
2. **Crawl cấu hình**: Gọi script `run_crawl_all_specs` nếu file `all_product_specs_raw.json` chưa tồn tại.
3. **Lọc trùng sơ bộ**: Gọi script `run_deduplicate_specs` nếu file `unique_smartphone_specs.json` chưa tồn tại.
4. **Chuẩn hóa LLM**: Gọi script `run_llm_name_normalization` nếu file `ready_to_load_specs.json` chưa tồn tại.
5. **Lọc trùng cuối**: Gọi script `run_final_deduplication` nếu file `final_ready_to_load_specs.json` chưa tồn tại.
6. **Lưu database**: Cuối cùng gọi script `load_products_to_db` để lưu dữ liệu cuối cùng vào CSDL.

**Cách chạy cơ bản**:
```bash
# Chạy toàn bộ luồng từ thư mục backend
python -m src.scripts.pipeline.run_crawl_to_db

# Có thể tùy chỉnh batch size khi lưu DB
python -m src.scripts.pipeline.run_crawl_to_db --db-batch-size 10
```

---
