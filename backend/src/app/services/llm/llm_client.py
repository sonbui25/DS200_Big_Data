from openai import OpenAI
import os
import logging
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .name_normalization import NAME_NORMALIZATION_PROMPT, NormalizedPhoneName

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class LLMNameNormalizer:
    def __init__(self, api_key: str, provider: str = "openai"):
        self.provider = provider
        # Khởi tạo mô hình ChatOpenAI từ Langchain
        self.llm = ChatOpenAI(
            model="gpt-5.4-mini", # Vẫn giữ model name này theo cấu hình cũ của bạn
            api_key=api_key,
            temperature=0.1
        )
        
        # Cấu trúc Prompt Template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful phone normalization assistant. Return JSON object with key 'search_query_name'."),
            ("user", NAME_NORMALIZATION_PROMPT)
        ])
        
        # Sử dụng tính năng with_structured_output tự động parse ra Pydantic object
        self.chain = self.prompt | self.llm.with_structured_output(NormalizedPhoneName)
        
    def normalize_name(self, product_name: str, chipset: str, ram: str, storage: str):
        try:
            # Gọi chuỗi (Chain) của Langchain thay vì thuần model API
            response = self.chain.invoke({
                "product_name": product_name,
                "chipset": chipset,
                "internal_storage": storage
            })
            
            return response.search_query_name
            
        except Exception as e:
            logging.error(f"Failed to normalize {product_name}: {e}")
            return product_name
