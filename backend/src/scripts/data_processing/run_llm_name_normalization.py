"""
Bước 4: Chuẩn hóa tên sản phẩm bằng LLM (LLM Name Normalization)

Mục tiêu của bước này là sử dụng một mô hình ngôn ngữ lớn (LLM) để chuẩn hóa tên sản phẩm điện thoại, 
loại bỏ các râu ria (marketing, tình trạng,...) không cần thiết và giữ lại phần cốt lõi giúp phân biệt các mẫu máy khác nhau.

Kỹ thuật áp dụng:
- Sử dụng mô hình ChatGPT (gpt-5.4-mini) qua Langchain.
- Đọc dữ liệu từ `unique_smartphone_specs.json`, gọi LLM để chuẩn hóa tên sản phẩm, và ghi kết quả vào `ready_to_load_specs.json` để chuẩn bị cho bước 5 (Final Deduplication).
- Tự động lưu mỗi 100 sample đã xử lý, đồng thời nghỉ ngơi 30 giây sau mỗi 100 sample để tránh sập Rate Limit tuỳ Provider.

Input: `unique_smartphone_specs.json` (1,547 records) — đầu vào là các bản ghi đã được loại bỏ trùng lặp dựa trên phần cứng, nhưng tên sản phẩm vẫn còn thô và chứa nhiều râu ria.
Output: `ready_to_load_specs.json` — toàn bộ record gốc được bổ sung thêm trường `search_query_name` chứa tên đã được chuẩn hóa, sẵn sàng để nạp vào database và phục vụ cho việc tìm kiếm sau này.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Đọc API key từ .env
load_dotenv(override=True)

# Thiết lập đường dẫn thư mục gốc
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base_dir)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.app.services.llm.llm_client import LLMNameNormalizer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    api_key = os.getenv("LLM_PROVIDER_FOR_NAME_NORMALIZATION_API_KEY")
    # try getting the NER key if the specific one fails
    if not api_key:
        api_key = os.getenv("LLM_PROVIDER_FOR_NER_API_KEY")
        
    provider = os.getenv("LLM_PROVIDER_FOR_NAME_NORMALIZATION", "openai")

    if not api_key:
        logging.error("Thiếu LLM_PROVIDER_FOR_NAME_NORMALIZATION_API_KEY trong file .env")
        sys.exit(1)

    import time
    
    input_file = os.path.join(base_dir, "data", "processed", "unique_smartphone_specs.json")
    output_file = os.path.join(base_dir, "data", "processed", "ready_to_load_specs.json")

    # Kiểm tra file input
    if not os.path.exists(input_file):
        logging.error(f"Không tìm thấy file nguồn (unique specs): {input_file}")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logging.info(f"Đã quét {len(data)} sản phẩm từ {input_file} chuẩn bị Normalize tên...")

    # Khởi tạo class bóc tách
    llm_normalizer = LLMNameNormalizer(api_key=api_key, provider=provider)

    processed_data = []
    
    # Tiến hành xử lý LLM
    for i, item in enumerate(data):
        fact = item.get("fact_product", {})
        dim_perf = item.get("dim_performance", {})
        dim_stor = item.get("dim_storage", {})

        raw_name = fact.get("product_name", "Unknown")
        chipset = dim_perf.get("chipset", "")
        ram = dim_perf.get("ram_capacity", "")
        storage = dim_stor.get("internal_storage", "")

        logging.info(f"Processing ({i+1}/{len(data)}): {raw_name}")

        # Gọi LLM prompt (dừng và delay nếu cần để tránh sập Rate Limit tuỳ Provider)
        search_query_name = llm_normalizer.normalize_name(
            product_name=raw_name, 
            chipset=chipset, 
            ram=ram, 
            storage=storage
        )

        item["search_query_name"] = search_query_name
        processed_data.append(item)

        logging.info(f"  -> Normalized: {search_query_name}")

        # Tự động lưu mỗi 100 sample và nghỉ 30 giây
        if (i + 1) % 100 == 0:
            logging.info(f"Đã xử lý {i + 1} sample. Đang lưu file tạm...")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            logging.info("Đã lưu. Nghỉ ngơi 30 giây để tránh rate limit...")
            time.sleep(30)

    # Ghi file chuẩn bị để load RDS
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)

    logging.info(f"Hoàn thành! Đã ghi gộp {len(processed_data)} bản ghi ra file: {output_file}")

if __name__ == "__main__":
    main()
