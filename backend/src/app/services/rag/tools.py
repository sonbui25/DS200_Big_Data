"""5 tool cho RAG Agent, định nghĩa bằng LangChain @tool decorator.
Docstring của mỗi tool = description mà LLM dùng để quyết định gọi tool nào.
"""

import logging

import psycopg2
import psycopg2.extras
from langchain_core.tools import tool

from src.app.services.rag.db import ASPECT_LIST, ASPECT_TO_DIM, connect
from src.app.services.rag.retrieval import hyde_embed

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Tool 1
# ─────────────────────────────────────────────

@tool
def search_product(name: str) -> list[dict]:
    """
    Tìm điện thoại trong database theo tên. Hỗ trợ tên viết tắt hoặc sai chính tả.
    Trả về danh sách tối đa 5 sản phẩm phù hợp nhất.
    Luôn gọi tool này trước để lấy product_id, sau đó đọc kỹ danh sách tên trả về
    để xác định đúng sản phẩm user đang hỏi (ví dụ: phân biệt iPhone 11 vs iPhone 12)
    rồi mới dùng product_id tương ứng để gọi các tool khác.
    """
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            try:
                cur.execute("""
                    SELECT product_id, product_name, price, picture_url
                    FROM fact_product
                    WHERE similarity(product_name, %s) > 0.1
                    ORDER BY similarity(product_name, %s) DESC
                    LIMIT 5
                """, (name, name))
            except Exception:
                conn.rollback()
                cur.execute("""
                    SELECT product_id, product_name, price, picture_url
                    FROM fact_product
                    WHERE product_name ILIKE %s
                    ORDER BY product_name
                    LIMIT 5
                """, (f"%{name}%",))

            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Tool 2
# ─────────────────────────────────────────────

@tool
def get_all_specs(product_id: int) -> dict:
    """
    Lấy toàn bộ thông số kỹ thuật của điện thoại gồm tất cả các khía cạnh (display, camera, battery...).
    Dùng khi cần tư vấn tổng quan hoặc so sánh nhiều máy — thay vì gọi get_product_specs nhiều lần.
    Trả về dict với key là tên aspect, value là các thông số tương ứng (bỏ qua cột null).
    """
    result = {}
    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for aspect, (table, columns) in ASPECT_TO_DIM.items():
                col_list = ", ".join(columns)
                cur.execute(
                    f"SELECT {col_list} FROM {table} WHERE product_id = %s LIMIT 1",
                    (product_id,),
                )
                row = cur.fetchone()
                if row:
                    filtered = {k: v for k, v in dict(row).items() if v is not None}
                    if filtered:
                        result[aspect] = filtered
        return result
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Tool 3
# ─────────────────────────────────────────────

def get_product_specs(product_id: int, aspect: str) -> dict:
    if aspect not in ASPECT_TO_DIM:
        return {"error": f"aspect không hợp lệ: {aspect}. Chọn: {list(ASPECT_TO_DIM)}"}

    table, columns = ASPECT_TO_DIM[aspect]
    col_list = ", ".join(columns)

    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT {col_list} FROM {table} WHERE product_id = %s LIMIT 1",
                (product_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"error": f"Không tìm thấy product_id={product_id} trong {table}"}
            return {k: v for k, v in dict(row).items() if v is not None}
    finally:
        conn.close()


get_product_specs.__doc__ = f"""
Lấy thông số kỹ thuật chính thức của điện thoại theo một khía cạnh cụ thể từ dữ liệu MobileCity.
Dùng khi user hỏi rõ về thông số cứng của một khía cạnh: camera bao nhiêu MP, pin bao nhiêu mAh, chip gì, RAM bao nhiêu...
Nếu cần tổng quan nhiều khía cạnh cùng lúc, dùng get_all_specs thay thế.
aspect hợp lệ: {ASPECT_LIST}.
"""
get_product_specs = tool(get_product_specs)


# ─────────────────────────────────────────────
# Tool 4
# ─────────────────────────────────────────────

def get_comments(product_id: int, aspect: str, query: str, top_k: int = 20) -> list[str]:
    if aspect not in ASPECT_TO_DIM:
        return [f"aspect không hợp lệ: {aspect}"]

    table, _ = ASPECT_TO_DIM[aspect]  # ví dụ "dim_camera" — vừa là tên bảng dim, vừa là giá trị cột dim_table
    query_vec = hyde_embed(query, aspect, product_id)
    query_vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    conn = connect()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(f"""
                    SELECT ce.chunk_text
                    FROM comment_embeddings ce
                    JOIN {table} d ON ce.dim_id = d.dim_id
                    WHERE ce.dim_table = %s
                      AND d.product_id = %s
                      AND ce.embedding IS NOT NULL
                    ORDER BY ce.embedding <=> %s::vector
                    LIMIT %s
                """, (table, product_id, query_vec_str, top_k * 5))
                rows = cur.fetchall()
                if rows:
                    seen: set[str] = set()
                    unique: list[str] = []
                    for (text,) in rows:
                        if text not in seen:
                            seen.add(text)
                            unique.append(text)
                            if len(unique) >= top_k:
                                break
                    return unique
            except Exception:
                conn.rollback()

            # Fallback nếu semantic search lỗi (model query embed không load được...)
            cur.execute(f"""
                SELECT ce.chunk_text
                FROM comment_embeddings ce
                JOIN {table} d ON ce.dim_id = d.dim_id
                WHERE ce.dim_table = %s
                  AND d.product_id = %s
                ORDER BY RANDOM()
                LIMIT %s
            """, (table, product_id, top_k))
            return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


get_comments.__doc__ = f"""
Lấy ý kiến thực tế của người dùng YouTube Việt Nam về điện thoại theo khía cạnh cụ thể.
Đây là nguồn dữ liệu phản ánh trải nghiệm thực tế — không phải thông số kỹ thuật hay bài review sponsor.
Dùng khi user hỏi 'có tốt không', 'người dùng nói gì', 'thực tế thế nào', hoặc so sánh trải nghiệm.

query: phải mô tả CHỦ ĐỀ cụ thể muốn tìm trong comment.
  - Tốt: 'chụp đêm bị nhiễu', 'pin tụt nhanh', 'lag chơi game', 'sạc nhanh'.
  - Tránh: 'người dùng thích', 'có tốt không', 'ý kiến chung' (cụm meta —
    embedding không phân biệt sentiment qua những từ này, retrieval sẽ nhiễu).

aspect hợp lệ: {ASPECT_LIST}.
"""
get_comments = tool(get_comments)


# ─────────────────────────────────────────────
# Tool 5
# ─────────────────────────────────────────────

@tool
def list_products(brand: str | None = None, max_price: int | None = None) -> list[dict]:
    """
    Liệt kê điện thoại trong database, có thể lọc theo thương hiệu và giá tối đa (VND).
    Dùng cho use case tư vấn mua điện thoại khi user đưa ra budget hoặc thương hiệu mong muốn.
    Ví dụ: brand='Samsung', max_price=10000000 để lọc Samsung dưới 10 triệu.
    """
    conditions = []
    params: list = []

    if brand:
        conditions.append("product_name ILIKE %s")
        params.append(f"%{brand}%")

    if max_price is not None:
        conditions.append("price <= %s AND price > 0")
        params.append(max_price)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT product_id, product_name, price FROM fact_product {where} ORDER BY price DESC LIMIT 20",
                params,
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
