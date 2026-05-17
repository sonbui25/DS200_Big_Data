"""
Pipeline phân loại aspect cho comment YouTube review điện thoại.

Bước 1 — Classify: dùng keyword matching để gán aspect vào từng comment
          Kết quả lưu vào cột aspects JSONB trong dim_video_comments.

Bước 2 — Aggregate: tổng hợp comment theo (product_id, aspect)
          Kết quả lưu vào cột user_review trong 8 bảng dim_*.

Chạy:
    python -m src.scripts.data_processing.run_classify_comment_aspect
    python -m src.scripts.data_processing.run_classify_comment_aspect --step 1
    python -m src.scripts.data_processing.run_classify_comment_aspect --step 2
    python -m src.scripts.data_processing.run_classify_comment_aspect --test
"""

import argparse
import json
import logging
import sys

import psycopg2
import psycopg2.extras

from src.app.config.settings import settings
from src.scripts.data_processing._aspect_keywords import keyword_match

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ASPECT_TO_TABLE = {
    "display":      "dim_display",
    "camera":       "dim_camera",
    "battery":      "dim_battery",
    "performance":  "dim_performance",
    "design":       "dim_design",
    "storage":      "dim_storage",
    "connectivity": "dim_connectivity",
    "utilities":    "dim_utilities",
}


def connect() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        connect_timeout=10,
        options="-c statement_timeout=120000",
    )
    conn.autocommit = False
    return conn


def step1_classify(conn: psycopg2.extensions.connection, fetch_size: int, commit_every: int, test: bool) -> None:
    """
    Đọc từng batch comment chưa classify (aspects IS NULL),
    gán aspect bằng keyword matching, ghi kết quả vào DB.
    Resume tự động: comment đã có aspects != NULL sẽ bị bỏ qua.
    """
    # withhold=True → DECLARE ... WITH HOLD → cursor tồn tại sau mỗi commit
    read_cur  = conn.cursor("classify_read", withhold=True)
    write_cur = conn.cursor()

    logger.info("Đang fetch comments chưa classify...")
    read_cur.execute("""
        SELECT comment_id, comment_text
        FROM dim_video_comments
        WHERE aspects IS NULL
          AND LENGTH(TRIM(comment_text)) >= 3
    """)
    logger.info("Query OK — bắt đầu classify.")

    processed     = 0
    fetch_num     = 0
    update_buffer: list[tuple] = []

    while True:
        rows = read_cur.fetchmany(fetch_size)
        if not rows:
            break

        fetch_num    += 1
        matched_count = 0

        for comment_id, comment_text in rows:
            aspects_dict = keyword_match(comment_text)
            if aspects_dict:
                matched_count += 1
            update_buffer.append((json.dumps(aspects_dict, ensure_ascii=False), comment_id))

        logger.info(
            "[Fetch %d] %s comments | match: %s | đã xử lý: %s",
            fetch_num, f"{len(rows):,}", f"{matched_count:,}", f"{processed:,}",
        )

        if len(update_buffer) >= commit_every:
            psycopg2.extras.execute_batch(
                write_cur,
                "UPDATE dim_video_comments SET aspects = %s::jsonb WHERE comment_id = %s",
                update_buffer,
            )
            conn.commit()
            processed    += len(update_buffer)
            update_buffer = []
            logger.info("  ✔ Commit | %s", f"{processed:,}")

        if test:
            logger.info("--test mode: dừng sau 1 fetch.")
            break

    if update_buffer:
        psycopg2.extras.execute_batch(
            write_cur,
            "UPDATE dim_video_comments SET aspects = %s::jsonb WHERE comment_id = %s",
            update_buffer,
        )
        conn.commit()
        processed += len(update_buffer)

    read_cur.close()
    write_cur.close()
    logger.info("Bước 1 hoàn tất. Tổng đã xử lý: %s comment", f"{processed:,}")


def step2_aggregate(conn: psycopg2.extensions.connection) -> None:
    """
    Với mỗi aspect, tổng hợp toàn bộ comment đã classify (aspects ? 'aspect_name')
    theo product_id và ghi vào cột user_review của bảng dim tương ứng.
    Một comment thuộc nhiều aspect sẽ xuất hiện trong tất cả bảng liên quan.
    """
    cursor = conn.cursor()

    for aspect, dim_table in ASPECT_TO_TABLE.items():
        cursor.execute(f"""
            SELECT
                v.product_id,
                json_agg(c.comment_text ORDER BY c.comment_id) AS comments,
                COUNT(*) AS total
            FROM dim_video_comments c
            JOIN dim_video_transcripts v ON c.video_id = v.video_id
            WHERE c.aspects ? %s
            GROUP BY v.product_id
        """, (aspect,))

        rows = cursor.fetchall()

        for product_id, comments_list, total in rows:
            user_review_json = json.dumps(
                {"total": total, "comments": comments_list},
                ensure_ascii=False,
            )
            cursor.execute(f"""
                UPDATE {dim_table}
                SET user_review  = %s,
                    last_updated = NOW()
                WHERE product_id = %s
            """, (user_review_json, product_id))

        conn.commit()
        logger.info("%s: đã cập nhật %s sản phẩm", dim_table, f"{len(rows):,}")

    cursor.close()
    logger.info("Bước 2 hoàn tất.")


def print_stats(conn: psycopg2.extensions.connection) -> None:
    cursor = conn.cursor()

    cursor.execute("""
        SELECT aspect_key, COUNT(*) AS so_luong
        FROM dim_video_comments,
             jsonb_object_keys(aspects) AS aspect_key
        WHERE aspects IS NOT NULL AND aspects != '{}'
        GROUP BY aspect_key
        ORDER BY so_luong DESC
    """)
    logger.info("--- Kết quả classify ---")
    for aspect, count in cursor.fetchall():
        logger.info("  %-15s %s comment", aspect, f"{count:,}")

    cursor.execute("SELECT COUNT(*) FROM dim_video_comments WHERE aspects = '{}'")
    logger.info("Không liên quan (aspects={}): %s", f"{cursor.fetchone()[0]:,}")

    cursor.execute("SELECT COUNT(*) FROM dim_video_comments WHERE aspects IS NULL")
    logger.info("Chưa classify (aspects IS NULL): %s", f"{cursor.fetchone()[0]:,}")

    cursor.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phân loại aspect cho comment YouTube review điện thoại."
    )
    parser.add_argument(
        "--step",
        choices=["1", "2", "both"],
        default="both",
        help="Bước cần chạy: 1=classify, 2=aggregate, both=cả hai (mặc định: both)",
    )
    parser.add_argument(
        "--fetch-size",
        type=int,
        default=5000,
        help="Số comment fetch mỗi lần từ DB (mặc định: 5000)",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=1000,
        help="Commit sau mỗi N comment (mặc định: 1000)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Chạy thử 1 fetch rồi dừng (dùng để kiểm tra keyword list)",
    )
    args = parser.parse_args()

    logger.info("Kết nối DB %s:%s/%s ...", settings.db_host, settings.db_port, settings.db_name)
    try:
        conn = connect()
    except Exception as e:
        logger.error("Không thể kết nối DB: %s", e)
        sys.exit(1)
    logger.info("Kết nối DB thành công.")

    try:
        if args.step in ("1", "both"):
            step1_classify(conn, args.fetch_size, args.commit_every, args.test)
            print_stats(conn)

        if args.step in ("2", "both") and not args.test:
            step2_aggregate(conn)

    except KeyboardInterrupt:
        logger.warning("Bị dừng bởi người dùng (Ctrl+C). Đang rollback...")
        conn.rollback()
    except Exception as e:
        logger.error("Lỗi không mong đợi: %s", e, exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
        logger.info("Đã đóng kết nối DB.")


if __name__ == "__main__":
    main()
