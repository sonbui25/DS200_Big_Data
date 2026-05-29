"""
5 tool cho RAG Agent, định nghĩa bằng LangChain @tool decorator.
Docstring của mỗi tool = description mà LLM dùng để quyết định gọi tool nào.
"""

import logging
from functools import lru_cache

import psycopg2
import psycopg2.extras
from langchain_core.tools import tool

from src.app.config.settings import settings

logger = logging.getLogger(__name__)

ASPECT_TO_DIM: dict[str, tuple[str, list[str]]] = {
    "display":      ("dim_display",      ["display_type", "color_depth", "display_standard", "resolution", "screen_size", "touch_technology"]),
    "camera":       ("dim_camera",       ["rear_camera", "front_camera", "flash_light", "camera_features", "video_recording", "video_call"]),
    "performance":  ("dim_performance",  ["cpu_speed", "core_count", "chipset", "ram_capacity", "gpu_chip"]),
    "storage":      ("dim_storage",      ["phonebook_storage", "internal_storage", "external_memory", "max_external_support"]),
    "design":       ("dim_design",       ["design_style", "dimensions", "weight"]),
    "battery":      ("dim_battery",      ["battery_type", "battery_capacity", "removable_battery"]),
    "connectivity": ("dim_connectivity", ["network_3g", "network_4g", "sim_type", "sim_slots", "wifi", "gps", "bluetooth", "gprs_edge", "headphone_jack", "nfc", "usb_connection", "other_connections", "charging_port"]),
    "utilities":    ("dim_utilities",    ["movie_playback", "music_playback", "charging_port_alt", "voice_recorder", "fm_radio", "other_features"]),
}

_ASPECT_LIST = " | ".join(ASPECT_TO_DIM.keys())


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        connect_timeout=10,
    )


# Phải khớp chính xác với embedding_comment.py: cùng model, cùng max_seq_length,
# cùng bước pyvi tokenize — nếu không query vector sẽ lệch không gian với comment vector.
_EMBEDDING_MODEL_NAME = "dangvantuan/vietnamese-embedding"
_MODEL_MAX_TOKENS = 254


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    model.max_seq_length = _MODEL_MAX_TOKENS
    return model


def _embed(text: str) -> list[float]:
    from pyvi.ViTokenizer import tokenize
    processed = tokenize(text).strip() or text
    return _get_embedding_model().encode(processed, normalize_embeddings=True).tolist()


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
    conn = _connect()
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
    conn = _connect()
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

    conn = _connect()
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
aspect hợp lệ: {_ASPECT_LIST}.
"""
get_product_specs = tool(get_product_specs)


# ─────────────────────────────────────────────
# Tool 4
# ─────────────────────────────────────────────

def get_comments(product_id: int, aspect: str, query: str, top_k: int = 20) -> list[str]:
    if aspect not in ASPECT_TO_DIM:
        return [f"aspect không hợp lệ: {aspect}"]

    table, _ = ASPECT_TO_DIM[aspect]  # ví dụ "dim_camera" — vừa là tên bảng dim, vừa là giá trị cột dim_table
    query_vec = _embed(query)
    query_vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    conn = _connect()
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
                """, (table, product_id, query_vec_str, top_k))
                rows = cur.fetchall()
                if rows:
                    return [r[0] for r in rows]
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
query là nội dung cụ thể muốn tìm, ví dụ: 'chụp đêm bị nhiễu', 'pin tụt nhanh', 'lag khi chơi game'.
aspect hợp lệ: {_ASPECT_LIST}.
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

    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT product_id, product_name, price FROM fact_product {where} ORDER BY price LIMIT 50",
                params,
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
