import json
from pathlib import Path
from typing import List, Dict

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from src.app.prompt_templates import SmartphoneEntity, SmartphoneNERPrompt

import os
from dotenv import load_dotenv

# Load môi trường
load_dotenv()
api_key = os.getenv("LLM_PROVIDER_FOR_NER_API_KEY")
if not api_key:
    raise ValueError("Missing LLM_PROVIDER_FOR_NER_API_KEY in .env")

# Khởi tạo OpenAI Model qua Langchain. Dùng gpt-4o-mini tối ưu chi phí và bám sát kiến thức mới
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=api_key
)

parser = JsonOutputParser(pydantic_object=SmartphoneEntity)

# 2. Lấy Prompt từ file cấu trúc
ner_prompt_obj = SmartphoneNERPrompt()
prompt_template = ChatPromptTemplate.from_messages([
    ("system", ner_prompt_obj.system_prompt + "\n\n{format_instructions}"),
    ("user", "Extract the smartphone entities from this product title: '{product_title}'")
])

# 3. Nối chuỗi tạo Chain của LangChain
ner_chain = prompt_template | llm | parser

def extract_phone_entities(names: List[str]) -> Dict[str, dict]:
    """
    Hàm này chạy LLM để bóc tách 1 list các name.
    Lưu ý: Nếu gọi API nhiều, nên thêm cơ chế Cache hoặc Batching để không bị Rate Limit.
    """
    results = {}
    for name in names:
        try:
            print(f"Đang bóc tách: {name}")
            out = ner_chain.invoke({
                "product_title": name,
                "format_instructions": parser.get_format_instructions()
            })
            results[name] = out
        except Exception as e:
            print(f"Lỗi khi parse {name}: {e}")
    return results

if __name__ == "__main__":
    # Test thử 1 vài case cực khó
    test_cases = [
        "iPhone 14 Pro Max 256GB Bản Mỹ Cũ đẹp 99%",
        "Samsung Galaxy S23 Ultra 12GB/512GB Chính hãng Nguyên Seal",
        "Xiaomi Redmi Note 12 Turbo (Bản Nội địa)",
        "Oppo Find X6 Pro 16GB 512GB (Lưng Da Trầy Xước 98%)"
    ]
    
    print("\n--- TEST NER WITH GPT-4o-MINI ---")
    out_dict = extract_phone_entities(test_cases)
    
    for raw, parsed in out_dict.items():
        print(f"\n[RAW]   {raw}")
        print(f"[PARSE] {json.dumps(parsed, ensure_ascii=False, indent=2)}")
