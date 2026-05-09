from sqlalchemy import func, select
from src.app.database.connection import get_engine
from src.app.database.models import dim_video_comments, dim_video_transcripts, fact_product


def fetch_product_id_index(product_names: list[str]) -> dict[str, int]:
    if not product_names:
        return {}
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            select(fact_product.c.product_id, fact_product.c.product_name).where(
                fact_product.c.product_name.in_(product_names)
            )
        ).fetchall()
    return {row[1]: row[0] for row in rows}


def count_videos_for_product(product_id: int) -> int:
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            select(func.count())
            .select_from(dim_video_transcripts)
            .where(dim_video_transcripts.c.product_id == product_id)
        ).scalar_one()
    return int(row or 0)


def get_existing_youtube_urls_for_product(product_id: int) -> set[str]:
    """Trả về set các YouTube URL đã có trong DB cho product — dùng cho top-up để skip trùng."""
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            select(dim_video_transcripts.c.youtube_url).where(
                dim_video_transcripts.c.product_id == product_id
            )
        ).fetchall()
    return {row[0] for row in rows}


def insert_video_metadata(
    product_id: int,
    youtube_url: str,
    s3_audio_path: str,
    s3_comments_path: str,
) -> int:
    engine = get_engine()
    with engine.begin() as connection:
        existing_video_id = connection.execute(
            select(dim_video_transcripts.c.video_id).where(
                dim_video_transcripts.c.youtube_url == youtube_url
            )
        ).scalar_one_or_none()
        if existing_video_id is not None:
            return existing_video_id
        insert_result = connection.execute(
            dim_video_transcripts.insert().values(
                product_id=product_id,
                youtube_url=youtube_url,
                s3_audio_path=s3_audio_path,
                s3_comments_path=s3_comments_path,
            )
        )
    return insert_result.inserted_primary_key[0]


def insert_video_comments(video_id: int, comments: list[dict]) -> int:
    if not comments:
        return 0
    engine = get_engine()
    inserted_count = 0
    with engine.begin() as connection:
        for comment in comments:
            connection.execute(
                dim_video_comments.insert().values(
                    video_id=video_id,
                    comment_text=comment.get("comment_text"),
                    user_name=comment.get("user_name"),
                )
            )
            inserted_count += 1
    return inserted_count


def get_video_ids_for_product(product_id: int) -> list[int]:
    engine = get_engine()
    with engine.connect() as connection:
        return connection.execute(
            select(dim_video_transcripts.c.video_id).where(
                dim_video_transcripts.c.product_id == product_id
            )
        ).scalars().all()


def delete_video_comments(video_ids: list[int]) -> None:
    if not video_ids:
        return
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            dim_video_comments.delete().where(
                dim_video_comments.c.video_id.in_(video_ids)
            )
        )


def delete_videos_for_product(product_id: int) -> None:
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            dim_video_transcripts.delete().where(
                dim_video_transcripts.c.product_id == product_id
            )
        )


def get_all_completed_product_names() -> list[str]:
    """Lấy tất cả product đã có video trong DB — dùng để rebuild tracking file."""
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            select(fact_product.c.product_name)
            .join(dim_video_transcripts, fact_product.c.product_id == dim_video_transcripts.c.product_id)
            .distinct()
        ).fetchall()
    return [row[0] for row in rows]