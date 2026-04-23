from pydantic import BaseModel, Field


class SmartphoneEntity(BaseModel):
    base_name: str = Field(description="The primary name of the smartphone model, e.g., 'iPhone 15 Pro Max', 'Samsung Galaxy S24 Ultra'. If it cannot be determined, return 'unknown'.")
    storage: str = Field(description="The storage capacity, e.g., '128GB', '256GB'. If it cannot be determined, return 'unknown'.")
    condition: str = Field(description="The condition of the phone, e.g., 'Cũ', 'Mới', 'Refurbished'. If it cannot be determined, return 'unknown'.")
    region: str = Field(description="The region or variant, e.g., 'VN/A', 'Mỹ', 'Hàn Quốc', 'Chính hãng', 'Xách tay'. If it cannot be determined, return 'unknown'.")


class SmartphoneNERPrompt(BaseModel):
    @property
    def system_prompt(self) -> str:
        return """You are an expert data extraction assistant. Your task is to extract highly normalized smartphone features from messy e-commerce product titles.

You must extract the following fields:
1. `base_name`: The core make and model (e.g., 'Samsung Galaxy S24 Ultra', 'iPhone 15 Pro Max', 'Xiaomi 14 Pro'). Do not include storage, condition (Mới/Cũ), or regional tags.
2. `storage`: The storage capacity (e.g., '128GB', '8GB/256GB', '1TB'). If not mentioned, return "unknown".
3. `condition`: The condition (e.g., "Mới" (New), "Cũ" (Used), "99%", etc.). Normalise implicitly if possible. If not mentioned, return "unknown".
4. `region`: Origin or variant (e.g., "Chính hãng", "Xách tay", "VN/A", "Bản Mỹ", "Hàn Quốc"). If not mentioned, return "unknown".

RULES:
- Be highly accurate.
- If a field is not present in the text, use exactly the string "unknown".
- Normalize outputs where clear (e.g., "iphone" -> "iPhone", "Ss" -> "Samsung").
"""

    @property
    def user_prompt(self) -> str:
        return "Extract the smartphone entities from this product title: '{product_title}'"

    def get_messages(self, product_title: str) -> list:
        return [
            ("system", self.system_prompt),
            ("user", self.user_prompt.format(product_title=product_title)),
        ]
