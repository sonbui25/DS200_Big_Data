import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import func, select

from src.app.config.settings import settings
from src.app.database.connection import get_engine, health_check
from src.app.database.models import dim_video_comments, dim_video_transcripts, fact_product
from src.app.services.s3_storage import upload_audio_file, upload_comments_file
from src.app.services.youtube_media_pipeline import (
    YouTubeQuotaExceededError,
    download_audio,
    download_comments,
    search_youtube_videos,
)
from src.scripts.load_products_to_db import load_products_to_db


def classify_phone(product_name: str) -> str:
    if re.search(r"\bcũ\b", product_name, re.IGNORECASE):
        return "OLD"

    percentages = re.findall(r"(\d+)\s*%", product_name)
    for percentage in percentages:
        if int(percentage) < 100:
            return "OLD"

    if re.search(r"chính hãng", product_name, re.IGNORECASE):
        return "NEW"
    return "OLD"


def read_json_records(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list JSON in: {path}")
    return payload


def deduplicate_records(records: list[dict]) -> list[dict]:
    unique_records: list[dict] = []
    seen_names: set[str] = set()
    for record in records:
        product_name = (record.get("fact_product") or {}).get("product_name")
        if not product_name or product_name in seen_names:
            continue
        seen_names.add(product_name)
        unique_records.append(record)
    return unique_records


def _parse_youtube_watch_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        return (parsed.path or "").strip("/").split("/")[0]
    query_ids = parse_qs(parsed.query).get("v")
    if query_ids and query_ids[0]:
        return query_ids[0]
    raise ValueError(f"Cannot parse YouTube video id from URL: {youtube_url}")


def filter_records(records: list[dict], target_group: str) -> list[dict]:
    if target_group == "ALL":
        return records
    return [
        record
        for record in records
        if classify_phone((record.get("fact_product") or {}).get("product_name", "")) == target_group
    ]


def count_videos_for_product(product_id: int) -> int:
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            select(func.count())
            .select_from(dim_video_transcripts)
            .where(dim_video_transcripts.c.product_id == product_id)
        ).scalar_one()
    return int(row or 0)


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


def insert_video_metadata(product_id: int, youtube_url: str, s3_audio_path: str, s3_comments_path: str) -> int:
    engine = get_engine()
    with engine.begin() as connection:
        existing_video_id = connection.execute(
            select(dim_video_transcripts.c.video_id).where(dim_video_transcripts.c.youtube_url == youtube_url)
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


def _build_checkpoint_key(
    specs_path: Path, target_group: str, max_products: int | None
) -> dict[str, str | int | None]:
    return {
        "specs_path": str(specs_path.resolve()),
        "target_group": target_group,
        "max_products": max_products,
    }


def _read_checkpoint(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    merged = {
        **payload,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def run_pipeline(
    specs_path: Path,
    links_path: Path,
    media_dir: Path,
    target_group: str,
    truncate: bool,
    truncate_youtube: bool,
    max_products: int | None,
    youtube_verbose: bool,
    checkpoint_path: Path,
    resume: bool,
    skip_complete_products: bool,
) -> None:
    specs_records = read_json_records(specs_path)
    links_records = read_json_records(links_path) if links_path.exists() else []

    unique_records = deduplicate_records(specs_records)
    filtered_records = filter_records(unique_records, target_group=target_group)
    if max_products is not None:
        filtered_records = filtered_records[:max_products]

    if not filtered_records:
        print("[WARN] No records after unique + filter steps.")
        return

    print(
        f"[INFO] Input={len(specs_records)} unique={len(unique_records)} "
        f"filtered={len(filtered_records)} target_group={target_group}",
        flush=True,
    )

    inserted_count, skipped_malformed_count, skipped_existing_count = load_products_to_db(
        spec_records=filtered_records,
        raw_links=links_records,
        truncate=truncate,
        truncate_youtube=truncate_youtube,
    )
    print(
        f"[INFO] DB load done inserted={inserted_count} "
        f"skipped_malformed={skipped_malformed_count} skipped_existing={skipped_existing_count}",
        flush=True,
    )
    if skipped_existing_count:
        print(
            "[INFO] skipped_existing = product_name already in fact_product (no duplicate insert). "
            "YouTube/S3 steps still run for each filtered product unless URLs already exist in DB.",
            flush=True,
        )

    product_names = [
        (record.get("fact_product") or {}).get("product_name")
        for record in filtered_records
        if (record.get("fact_product") or {}).get("product_name")
    ]
    product_id_index = fetch_product_id_index(product_names=product_names)

    youtube_hits = 0
    media_uploaded = 0
    comments_inserted = 0
    media_dir.mkdir(parents=True, exist_ok=True)
    total_products = len(filtered_records)

    checkpoint_key = _build_checkpoint_key(specs_path, target_group, max_products)
    effective_max_videos = max(1, min(settings.youtube_max_results_per_product, 50))
    last_completed_index = 0
    if resume:
        checkpoint_data = _read_checkpoint(checkpoint_path)
        if checkpoint_data and checkpoint_data.get("checkpoint_key") == checkpoint_key:
            last_completed_index = int(checkpoint_data.get("last_completed_index") or 0)
            print(
                f"[INFO] Resume: bỏ qua các sản phẩm 1..{last_completed_index} (checkpoint).",
                flush=True,
            )
        elif checkpoint_data:
            print(
                "[WARN] Checkpoint không khớp --specs / --target-group / --max-products; bỏ qua --resume.",
                flush=True,
            )

    def persist_progress(last_idx: int, reason: str = "progress") -> None:
        _write_checkpoint(
            checkpoint_path,
            {
                "version": 1,
                "checkpoint_key": checkpoint_key,
                "last_completed_index": last_idx,
                "reason": reason,
            },
        )

    for index, record in enumerate(filtered_records, start=1):
        product_name = (record.get("fact_product") or {}).get("product_name")
        if not product_name:
            continue
        product_id = product_id_index.get(product_name)
        if not product_id:
            continue

        if index <= last_completed_index:
            if youtube_verbose:
                print(
                    f"[INFO] [{index}/{total_products}] Skip (resume) product_id={product_id}",
                    flush=True,
                )
            continue

        if skip_complete_products:
            already = count_videos_for_product(product_id)
            if already >= effective_max_videos:
                print(
                    f"[INFO] [{index}/{total_products}] Skip (đủ video trong DB: {already}/"
                    f"{effective_max_videos}) product_id={product_id}",
                    flush=True,
                )
                persist_progress(index)
                continue

        if youtube_verbose:
            name_preview = product_name if len(product_name) <= 100 else f"{product_name[:97]}..."
            print(
                f"[INFO] [{index}/{total_products}] YouTube: product_id={product_id} "
                f"max_results={settings.youtube_max_results_per_product} name={name_preview!r}",
                flush=True,
            )

        try:
            videos = search_youtube_videos(
                product_name=product_name,
                api_key=settings.youtube_data_api_key,
                max_results=settings.youtube_max_results_per_product,
                verbose=youtube_verbose,
            )
        except YouTubeQuotaExceededError as exc:
            persist_progress(max(index - 1, 0), reason="youtube_quota")
            print(
                f"[WARN] Hết quota / giới hạn YouTube Data API: {exc}. "
                f"Đã lưu checkpoint (last_completed_index={max(index - 1, 0)}). "
                "Chạy lại sau khi quota reset với --resume.",
                flush=True,
            )
            raise

        if not videos:
            print(f"[WARN] [{index}/{total_products}] No YouTube results: {product_name}", flush=True)
            persist_progress(index)
            continue

        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_name).strip("_").lower() or f"product_{product_id}"
        product_videos_done = 0

        for video_index, video in enumerate(videos, start=1):
            youtube_url = video["youtube_url"]
            try:
                yt_watch_id = _parse_youtube_watch_video_id(youtube_url)
            except ValueError as exc:
                print(f"[WARN] Skip invalid YouTube URL ({product_name}): {exc}", flush=True)
                continue

            if youtube_verbose:
                raw_title = video.get("video_title") or ""
                title_preview = raw_title if len(raw_title) <= 100 else f"{raw_title[:97]}..."
                print(
                    f"[INFO]   [{video_index}/{len(videos)}] video_id={yt_watch_id} title={title_preview!r}",
                    flush=True,
                )

            output_stem = media_dir / f"{product_id}_{safe_name}_{yt_watch_id}"

            try:
                audio_path = download_audio(
                    video_url=youtube_url, output_stem=output_stem, verbose=youtube_verbose
                )
                comments_csv_path, comments = download_comments(
                    video_url=youtube_url, output_stem=output_stem, verbose=youtube_verbose
                )
            except (RuntimeError, FileNotFoundError) as exc:
                print(
                    f"[WARN]   yt-dlp failed video_id={yt_watch_id} product_id={product_id}: {exc}",
                    flush=True,
                )
                continue

            if youtube_verbose:
                print(
                    f"[INFO]   S3 upload audio+comments product_id={product_id} storage_id={yt_watch_id}",
                    flush=True,
                )
            try:
                s3_audio_path = upload_audio_file(str(audio_path), product_id=product_id, storage_id=yt_watch_id)
                s3_comments_path = upload_comments_file(
                    str(comments_csv_path), product_id=product_id, storage_id=yt_watch_id
                )
                media_uploaded += 1
            except Exception as exc:
                print(
                    f"[WARN]   S3 upload failed video_id={yt_watch_id} product_id={product_id}: {exc}",
                    flush=True,
                )
                continue

            try:
                video_id = insert_video_metadata(
                    product_id=product_id,
                    youtube_url=youtube_url,
                    s3_audio_path=s3_audio_path,
                    s3_comments_path=s3_comments_path,
                )
                inserted_rows = insert_video_comments(video_id=video_id, comments=comments)
                comments_inserted += inserted_rows
                youtube_hits += 1
                product_videos_done += 1
            except Exception as exc:
                print(
                    f"[WARN]   DB insert failed video_id={yt_watch_id} product_id={product_id}: {exc}",
                    flush=True,
                )
                continue

            if youtube_verbose:
                print(
                    f"[INFO]   DB dim_video_transcripts.video_id={video_id} "
                    f"comments_inserted_batch={inserted_rows}",
                    flush=True,
                )

        print(
            f"[INFO] [{index}/{total_products}] Media done product_id={product_id} "
            f"videos={product_videos_done}/{len(videos)}",
            flush=True,
        )
        persist_progress(index)

    if checkpoint_path.exists():
        tail = _read_checkpoint(checkpoint_path)
        if tail and tail.get("checkpoint_key") == checkpoint_key:
            checkpoint_path.unlink(missing_ok=True)
            print("[INFO] Đã xóa checkpoint (pipeline chạy xong).", flush=True)

    print(
        f"[INFO] Pipeline completed youtube_hits={youtube_hits} "
        f"media_uploaded={media_uploaded} comments_inserted={comments_inserted}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filter unique smartphone records, load DB fact+8 dim, ingest YouTube media/comments, and push to S3."
    )
    parser.add_argument("--specs", default="data/processed/product_specs.json")
    parser.add_argument("--links", default="data/raw/product_links.json")
    parser.add_argument("--media-dir", default="data/processed/youtube_media")
    parser.add_argument("--target-group", choices=["ALL", "NEW", "OLD"], default="NEW")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Full reset: delete YouTube tables, all product dims, then fact_product, then reload JSON.",
    )
    parser.add_argument(
        "--truncate-youtube",
        action="store_true",
        help="Delete only dim_video_comments and dim_video_transcripts (keep products; re-ingest YouTube).",
    )
    parser.add_argument("--max-products", type=int, default=None)
    parser.add_argument(
        "--quiet-youtube",
        action="store_true",
        help="Less verbose logging for YouTube API, yt-dlp, S3, and per-video DB steps.",
    )
    parser.add_argument(
        "--checkpoint-file",
        default="data/processed/youtube_media_checkpoint.json",
        help="File lưu tiến độ khi hết quota; dùng với --resume.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Tiếp tục từ checkpoint (bỏ qua các sản phẩm đã ghi trong file).",
    )
    parser.add_argument(
        "--force-all-products",
        action="store_true",
        help="Không bỏ qua sản phẩm đã đủ video trong DB (mặc định: skip để tiết kiệm quota).",
    )
    args = parser.parse_args()

    health_check()
    try:
        run_pipeline(
            specs_path=Path(args.specs),
            links_path=Path(args.links),
            media_dir=Path(args.media_dir),
            target_group=args.target_group,
            truncate=args.truncate,
            truncate_youtube=args.truncate_youtube,
            max_products=args.max_products,
            youtube_verbose=not args.quiet_youtube,
            checkpoint_path=Path(args.checkpoint_file),
            resume=args.resume,
            skip_complete_products=not args.force_all_products,
        )
    except YouTubeQuotaExceededError:
        sys.exit(5)


if __name__ == "__main__":
    main()
