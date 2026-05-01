"""
Định nghĩa schema PROMPT và Pydantic model để chuẩn hóa tên sản phẩm điện thoại.
Schema này sẽ được sử dụng trong LLMNameNormalizer trong file llm_client.py.
"""
from pydantic import BaseModel, Field

class NormalizedPhoneName(BaseModel):
    search_query_name: str = Field(
        description="Tên chuẩn của điện thoại kèm theo tên loại chipset (không lấy phần thông số xung nhịp/nhân)."
    )

NAME_NORMALIZATION_PROMPT = """Bạn là một chuyên gia về các dòng điện thoại trên thị trường. Nhiệm vụ của bạn là chuẩn hoá tên sản phẩm phục vụ cho việc tìm kiếm YouTube/Google review chính xác nhất.

Dữ liệu đầu vào bao gồm:
1. "product_name": Tên được crawl về, thường chứa rất nhiều định dạng rác của marketing như: "cũ 99%", "đẹp như mới", "giảm giá", "hot", "kèm quà tặng", "chính hãng VN/A", "bản Mỹ", "RAM", "ROM", "Màu sắc".
2. "chipset": Thông tin chipset của điện thoại (có thể rất dài, gồm xung nhịp, GPU, số nhân...).
3. "internal_storage": Dung lượng bộ nhớ lưu trữ của điện thoại.

YÊU CẦU ĐẦU RA:
- Trả về chuỗi gồm: [Tên chuẩn của điện thoại] + " " + [Tên Chipset ngắn gọn].
- Tên chuẩn của điện thoại là brand + model. KHÔNG KÈM cấu hình RAM hay ROM/Storage.
- KHÔNG LẤY dung lượng bộ nhớ.
- ĐỐI VỚI CHIPSET: Chỉ giữ lại tên dòng chip (VD: Snapdragon 8 Gen 2, Exynos 9820, Apple A18 Pro). Cắt bỏ và KHÔNG LẤY các phần râu ria liên quan đến số nhân (core), xung nhịp (GHz), kiến trúc (nm), hoặc GPU... Nếu trong chuỗi chipset có 2 loại chip (VD: Exynos 9820 & Snapdragon 855) thì lấy cả 2 tên chip chuẩn. Nếu chipset rỗng thì bỏ qua phần chipset.
- QUYẾT LIỆT LOẠI BỎ khỏi tên điện thoại: tình trạng (cũ, mới, 99%), mã vùng (VN/A, bản Mỹ, Hàn, xách tay), khuyến mãi, quà tặng, màu sắc, từ khóa câu view.

Ví dụ:
  + Tên: "iPhone 16e cũ (99% Đẹp như mới)", Chipset: "Apple A18" -> "iPhone 16e"
  + Tên: "Samsung Galaxy S23 Ultra Chính hãng VN/A 8GB/256GB Giảm 30%", Chipset: "Snapdragon 8 Gen 2 for Galaxy" -> "Samsung Galaxy S23 Ultra Snapdragon 8 Gen 2"
  + Tên: "Samsung Galaxy S23 cũ (Snapdragon 8 Gen 2)", Chipset: "Qualcomm SM8550-AC Snapdragon 8 Gen 2 (4 nm)\\r\\n8 nhân (1x3.36 GHz & 2x2.8 GHz & 2x2.8 GHz & 3x2.0 GHz)\\r\\nGPU: Adreno 740" -> "Samsung Galaxy S23 Snapdragon 8 Gen 2"
  + Tên: "Samsung Galaxy S10 Plus", Chipset: "Exynos 9820: 8 nhân (2x2.73 GHz & 2x2.31 GHz & 4x1.95 GHz)\\r\\nSnapdragon 855: 8 nhân (1x2.84 GHz & 3x2.42 GHz & 4x1.78 GHz)\\r\\nGPU: Mali-G76 MP12 (Exynos) hoặc Adreno 640 (Snapdragon)" -> "Samsung Galaxy S10 Plus Exynos 9820 Snapdragon 855"

### INPUT:
Tên sản phẩm hiện tại: {product_name}
Chipset cung cấp: {chipset}
Bộ nhớ trong (Storage) cung cấp: {internal_storage}
"""
