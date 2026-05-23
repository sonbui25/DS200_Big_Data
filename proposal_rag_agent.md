# Proposal: RAG Agent System cho tư vấn điện thoại

## 1. Tổng quan

Xây dựng hệ thống Agent sử dụng RAG để trả lời câu hỏi về điện thoại dựa trên ý kiến thực tế của người dùng YouTube — thứ mà các hệ thống deep research (Gemini, Perplexity...) không có vì chúng chủ yếu tham chiếu bài viết được sponsor.

---

## 2. Schema database hiện tại

### Bảng trung tâm

**`fact_product`**
| Cột | Kiểu | Mô tả |
|---|---|---|
| product_id | Integer PK | ID sản phẩm |
| product_name | String | Tên điện thoại |
| os_version | Text | Phiên bản OS |
| language_support | Text | Ngôn ngữ hỗ trợ |
| price | Integer | Giá (VND) |
| picture_url | String | Ảnh sản phẩm |

### 8 bảng dim (specs từ mobilecity + user review từ YouTube)

Mỗi bảng dim có cấu trúc chung:
- `dim_id`, `product_id` (FK → fact_product)
- Các cột spec riêng theo aspect (từ mobilecity)
- `youtuber_review` (Text) — chưa dùng
- `user_review` (Text/JSON) — JSON `{"total": N, "comments": [...]}` đã aggregate từ step 2
- `last_updated`

| Bảng | Cột spec đặc trưng |
|---|---|
| `dim_display` | display_type, resolution, screen_size, color_depth, touch_technology |
| `dim_camera` | rear_camera, front_camera, flash_light, camera_features, video_recording |
| `dim_performance` | chipset, cpu_speed, core_count, ram_capacity, gpu_chip |
| `dim_storage` | internal_storage, external_memory, max_external_support |
| `dim_design` | design_style, dimensions, weight |
| `dim_battery` | battery_type, battery_capacity, removable_battery |
| `dim_connectivity` | wifi, bluetooth, nfc, sim_slots, usb_connection, charging_port |
| `dim_utilities` | movie_playback, music_playback, fm_radio, other_features |

### Bảng YouTube

**`dim_video_transcripts`**
| Cột | Mô tả |
|---|---|
| video_id | PK |
| product_id | FK → fact_product |
| youtube_url | URL video |
| raw_transcript | Transcript thô |

**`dim_video_comments`**
| Cột | Mô tả |
|---|---|
| comment_id | PK |
| video_id | FK → dim_video_transcripts |
| comment_text | Nội dung comment |
| user_name | Tên user |
| aspects | JSONB — `{"camera": 1, "battery": 1, ...}` (đã classify) |
| embedding | vector(384) — **sẽ thêm cho RAG** |

### Quan hệ chính

```
fact_product
  ├── dim_camera, dim_battery, dim_display, ...  (specs + user_review)
  └── dim_video_transcripts
        └── dim_video_comments (aspects, embedding)
```

---

## 3. Kiến trúc RAG Agent

```
User question
     ↓
LLM Agent (Gemini Function Calling)
     ↓
Gọi các Tool phù hợp
     ↓
Tool: structured filter (product_id + aspect) + semantic search (pgvector)
     ↓
Top-K comments relevant → LLM tổng hợp → trả lời
```

---

## 4. Embedding

### Phạm vi
Chỉ embed comment đã được phân loại aspect: `aspects IS NOT NULL AND aspects != '{}'`

Không embed toàn bộ 12.8M comment — chỉ những comment có thông tin hữu ích.

### Đặc thù ngôn ngữ
Comment có 3 ngôn ngữ: **tiếng Việt** (chủ yếu), **tiếng Anh**, **tiếng Indonesia**.
→ Bắt buộc dùng **multilingual embedding model**.

### Model đề xuất: `paraphrase-multilingual-MiniLM-L12-v2`
- Hỗ trợ 50+ ngôn ngữ, bao gồm cả 3 ngôn ngữ trên
- Dimension: **384** — nhỏ gọn, phù hợp số lượng lớn
- Chạy được trên CPU, không cần GPU
- Miễn phí, không phụ thuộc API

### Lưu trữ: pgvector (PostgreSQL extension)
Tận dụng DB sẵn có, không cần infrastructure mới.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE dim_video_comments ADD COLUMN embedding vector(384);

-- Index chỉ trên comment đã classify
CREATE INDEX idx_comments_embedding
ON dim_video_comments
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
WHERE aspects IS NOT NULL AND aspects != '{}';
```

---

## 5. Bộ Tool cho Agent

### Tool 1: `search_product`
```
Input:  name (str) — tên điện thoại user nhập (có thể viết tắt, sai chính tả)
Output: list[{product_id, product_name, price, picture_url}]
Source: fact_product
```
Dùng `pg_trgm` fuzzy search trên `product_name`.
Agent gọi tool này trước tiên để resolve tên → product_id chính xác.

---

### Tool 2: `get_product_specs`
```
Input:  product_id (int), aspect (str) — "camera" | "battery" | "display" | ...
Output: dict — các cột spec của bảng dim tương ứng
Source: dim_camera / dim_battery / dim_display / ...
```
Trả về thông số kỹ thuật cứng từ mobilecity.
Ví dụ: `get_product_specs(123, "camera")` → `{rear_camera: "50MP", front_camera: "12MP", ...}`

---

### Tool 3: `get_comments`
```
Input:  product_id (int), aspect (str), query (str), top_k (int = 20)
Output: list[comment_text]
Source: dim_video_comments JOIN dim_video_transcripts
```
- **Filter**: `product_id` + `aspects ? aspect`
- **Semantic search**: embed `query` → cosine similarity với `embedding`
- Trả về top-K comment liên quan nhất trong tập đã filter

**Đây là tool core nhất** — kết hợp structured filter + semantic retrieval.
Ví dụ: `get_comments(123, "camera", "chụp đêm bị nhiễu không", top_k=20)`

---

### Tool 4: `list_products`
```
Input:  brand (str, optional), max_price (int, optional)
Output: list[{product_id, product_name, price}]
Source: fact_product
```
Liệt kê sản phẩm với filter theo thương hiệu và budget.
Dùng chủ yếu cho use case tư vấn mua điện thoại.

---

## 6. Use cases và flow

### 6.1 Chatbot hỏi đáp
> "Samsung S24 chụp đêm có tốt không?"

```
search_product("Samsung S24") → product_id=123
get_comments(123, "camera", "chụp đêm", top_k=20)
→ LLM tổng hợp từ 20 comment thực tế của người dùng
```

### 6.2 So sánh điện thoại
> "So sánh pin iPhone 15 và Samsung S24"

```
search_product("iPhone 15")   → product_id=456
search_product("Samsung S24") → product_id=123
get_product_specs(456, "battery") + get_product_specs(123, "battery")
get_comments(456, "battery", "pin", top_k=20)
get_comments(123, "battery", "pin", top_k=20)
→ LLM so sánh thông số + ý kiến người dùng song song
```

### 6.3 Tư vấn mua
> "Tôi cần điện thoại pin trâu, camera tốt, dưới 10 triệu"

```
list_products(max_price=10_000_000) → [phone_A, phone_B, phone_C, ...]
với top phones: get_comments(id, "battery", "pin trâu", top_k=10)
               get_comments(id, "camera", "camera chất lượng", top_k=10)
→ LLM gợi ý top 3 kèm lý do từ comment thực tế
```

---

## 7. So sánh với Gemini Deep Research

| Tiêu chí | Gemini Deep Research | Hệ thống này |
|---|---|---|
| Nguồn | Bài viết web, review sponsor | YouTube comment người dùng thực tế |
| Góc nhìn | Quốc tế | Người dùng Việt Nam |
| Số lượng ý kiến | Vài chục nguồn | Hàng nghìn comment/điện thoại |
| Câu hỏi cụ thể | "Camera tốt" | "Chụp đêm bị nhiễu không?" |
| Specs kỹ thuật | Có | Có (mobilecity) |

→ Hai hệ thống **bổ sung cho nhau** — deep research cho cái nhìn tổng quan, hệ thống này cho ý kiến thực tế của người dùng Việt theo từng khía cạnh cụ thể.

---

## 8. Kế hoạch thực hiện (còn ~12 ngày đến 4/6)

| Ngày | Task |
|---|---|
| 1–2 | Thêm pgvector, embed classified comments, lưu vào DB |
| 3–4 | Implement 4 tool + unit test từng tool |
| 5–6 | Kết nối Agent (Gemini Function Calling) + test các use case |
| 7–8 | API endpoint + UI đơn giản (radar chart + chatbox) |
| 9–10 | Chạy so sánh với Gemini Deep Research, ghi nhận insight |
| 11–12 | Viết báo cáo |

---

## 9. Rủi ro và giải pháp

| Rủi ro | Giải pháp |
|---|---|
| Embedding nhiều comment, chậm | Batch processing trên VPS, chạy nohup |
| `search_product` không tìm đúng tên | `pg_trgm` fuzzy search + trả về top 3 để agent chọn |
| Agent gọi sai tool | Viết tool description rõ ràng, thêm ví dụ trong description |
| Comment 3 ngôn ngữ ảnh hưởng embedding | `paraphrase-multilingual-MiniLM` handle được cả 3 |
