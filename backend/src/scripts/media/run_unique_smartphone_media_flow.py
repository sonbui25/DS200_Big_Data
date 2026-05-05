import argparse
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unidecode import unidecode
import signal

from src.app.config.settings import settings
from ._media_logger import setup_pipeline_logger, setup_pipeline_logger, upload_log_to_s3
from src.app.services.external_media.youtube_media_pipeline import (
    YouTubeQuotaExceededError,
    download_audio,
    download_comments,
    download_transcript,
    search_youtube_videos,
)
from src.app.services.storage.s3_storage import (
    upload_audio_file,
    upload_comments_file,
    upload_transcript_file,
)
from ._media_db import (
    fetch_product_id_index,
    insert_video_metadata,
    insert_video_comments,
    get_all_completed_product_names,
)
from ._media_cleaner import clear_all

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ._api_key_pool import YouTubeApiKeyPool

TRACKING_FILE = Path("data/processed/media_completed_products.json")


# ── Helpers ──────────────────────────────────────────────────────────────────

def read_json_records(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list JSON in: {path}")
    return payload


def _parse_youtube_watch_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url)
    host = (parsed.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        return (parsed.path or "").strip("/").split("/")[0]
    query_ids = parse_qs(parsed.query).get("v")
    if query_ids and query_ids[0]:
        return query_ids[0]
    raise ValueError(f"Cannot parse YouTube video id from URL: {youtube_url}")


def load_tracking_file() -> set[str]:
    if not TRACKING_FILE.exists():
        return set()
    try:
        content = TRACKING_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return set()
        data = json.loads(content)
        if isinstance(data, list):
            return set(data)
    except Exception as exc:
        print(f"[WARN] Failed to read {TRACKING_FILE}: {exc}")
    return set()


_tracking_lock = threading.Lock()

def save_completed_product(product_name: str, completed_products: set[str]) -> None:
    """Thread-safe: dùng lock trước khi đọc/ghi file."""
    with _tracking_lock:
        completed_products.add(product_name)
        TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRACKING_FILE.write_text(
            json.dumps(sorted(completed_products), ensure_ascii=False, indent=4),
            encoding="utf-8",
        )


def rebuild_tracking_file_from_db() -> None:
    product_names = get_all_completed_product_names()
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKING_FILE.write_text(
        json.dumps(product_names, ensure_ascii=False, indent=4), encoding="utf-8"
    )
    print(f"[INFO] Rebuilt tracking file: {len(product_names)} products.", flush=True)


# ── Checkpoint ────────────────────────────────────────────────────────────────

def _build_checkpoint_key(specs_path: Path, max_products: int | None) -> dict:
    return {"specs_path": str(specs_path.resolve()), "max_products": max_products}


def _read_checkpoint(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_checkpoint(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps({**payload, "updated_at": datetime.now(timezone.utc).isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(path)


# ── Core processing ───────────────────────────────────────────────────────────

def process_single_product_youtube_media(
    product_id: int,
    product_name: str,
    media_dir: Path,
    youtube_verbose: bool,
    api_key_pool: YouTubeApiKeyPool,      # ← thêm
) -> tuple[int, int, int]:
    logger, log_path, s3_handler = setup_pipeline_logger(media_dir, product_name=product_name)
    logger.info(f"Start processing product_id={product_id} name={product_name!r}")

    # Retry search khi key hết quota
    while True:
        try:
            videos = search_youtube_videos(
                product_name=product_name,
                api_key=api_key_pool.current_key,   # ← dùng pool
                max_results=settings.youtube_max_results_per_product,
                verbose=youtube_verbose,
            )
            break
        except YouTubeQuotaExceededError:
            # Rotate sang key tiếp — nếu hết tất cả keys thì raise lên
            api_key_pool.mark_exhausted(api_key_pool.current_key, logger=logger)

    if not videos:
        logger.info("Done: hits=0 upl=0 comms=0")
        s3_handler.flush_now()
        return 0, 0, 0

    safe_name = (
        re.sub(r"[^a-zA-Z0-9_-]+", "_", unidecode(product_name)).strip("_").lower()
        or f"product_{product_id}"
    )
    audio_dir       = media_dir / "audio"       / safe_name
    comments_dir    = media_dir / "comments"    / safe_name
    transcripts_dir = media_dir / "transcripts" / safe_name
    for d in [audio_dir, comments_dir, transcripts_dir]:
        d.mkdir(parents=True, exist_ok=True)

    hits = upl = comms = 0

    for video_index, video in enumerate(videos, start=1):
        youtube_url = video["youtube_url"]
        video_title = video.get("video_title", "")

        try:
            yt_watch_id = _parse_youtube_watch_video_id(youtube_url)
        except ValueError as exc:
            logger.warning(f"Skip invalid YouTube URL: {exc}")
            continue

        safe_title    = re.sub(r"[^a-zA-Z0-9_-]+", "_", unidecode(video_title)).strip("_")
        safe_title    = safe_title[:50] if safe_title else yt_watch_id
        indexed_title = f"{video_index:02d}_{safe_title}"

        if youtube_verbose:
            title_pv = video_title[:97] + "..." if len(video_title) > 100 else video_title
            logger.info(f"  [{video_index}/{len(videos)}] id={yt_watch_id} title={title_pv!r}")

        try:
            audio_path = download_audio(youtube_url, audio_dir / indexed_title, verbose=youtube_verbose)
            comments_csv_path, comments = download_comments(youtube_url, comments_dir / indexed_title, verbose=youtube_verbose)
        except (RuntimeError, FileNotFoundError) as exc:
            logger.warning(f"  yt-dlp failed id={yt_watch_id}: {exc}")
            continue

        transcript_json_path = None
        try:
            transcript_json_path, _ = download_transcript(yt_watch_id, transcripts_dir / indexed_title, verbose=youtube_verbose)
        except Exception as exc:
            logger.warning(f"  Transcript fetch failed id={yt_watch_id}: {exc}")

        try:
            s3_audio_path    = upload_audio_file(str(audio_path), product_name=product_name, storage_id=indexed_title)
            s3_comments_path = upload_comments_file(str(comments_csv_path), product_name=product_name, storage_id=indexed_title)
            s3_transcript_path = (
                upload_transcript_file(str(transcript_json_path), product_name=product_name, storage_id=indexed_title)
                if transcript_json_path else None
            )
            upl += 1

            # Xóa local ngay sau khi upload S3 thành công
            for local_file in [audio_path, comments_csv_path, transcript_json_path]:
                if local_file and Path(local_file).exists():
                    Path(local_file).unlink()
            # Xóa .info.json của yt-dlp (không upload lên S3)
            info_json = comments_dir / f"{indexed_title}.info.json"
            if info_json.exists():
                info_json.unlink()

        except Exception as exc:
            logger.warning(f"  S3 upload failed id={yt_watch_id}: {exc}")
            continue

        try:
            video_id = insert_video_metadata(product_id, youtube_url, s3_audio_path, s3_comments_path, s3_transcript_path)
            comms   += insert_video_comments(video_id, comments)
            hits    += 1
        except Exception as exc:
            logger.warning(f"  DB insert failed id={yt_watch_id}: {exc}")

    # Xóa các subfolder rỗng sau khi xử lý xong product
    for d in [audio_dir, comments_dir, transcripts_dir]:
        try:
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass

    logger.info(f"Done: hits={hits} upl={upl} comms={comms}")
    s3_handler.flush_now()
    return hits, upl, comms

# ── Pipeline ──────────────────────────────────────────────────────────────────

def _process_one_product(
    index: int,
    total: int,
    product_id: int,
    product_name: str,
    media_dir: Path,
    youtube_verbose: bool,
    completed_products: set[str],
    api_key_pool: YouTubeApiKeyPool,
    pipeline_logger,
) -> tuple[int, int, int]:
    """Wrapper chạy trong thread riêng."""
    pipeline_logger.info(f"[{index}/{total}] >>> Processing: {product_name!r} (ID={product_id})")
    clear_all(product_id, product_name, media_dir, logger=pipeline_logger)

    try:
        hits, upl, comms = process_single_product_youtube_media(
            product_id, product_name, media_dir, youtube_verbose,
            api_key_pool=api_key_pool,
        )
        if hits > 0 or not settings.youtube_api_key_list:
            save_completed_product(product_name, completed_products)
        pipeline_logger.info(
            f"[{index}/{total}] Finished: {product_name!r} "
            f"hits={hits} upl={upl} comms={comms}"
        )
        return hits, upl, comms
    except YouTubeQuotaExceededError:
        raise  # Bubble up để ThreadPoolExecutor bắt
    except Exception as exc:
        pipeline_logger.error(f"[{index}/{total}] Failed {product_name!r}: {exc}")
        traceback.print_exc()
        return 0, 0, 0


def run_pipeline(
    specs_path: Path,
    media_dir: Path,
    max_products: int | None,
    youtube_verbose: bool,
    test_mode: bool = False,
    max_workers: int = 3,           # ← thêm
) -> None:
    pipeline_logger, pipeline_log_path, pipeline_s3 = setup_pipeline_logger(media_dir)

    def _on_interrupt(sig, frame):
        pipeline_logger.warning("Interrupted (SIGINT). Flushing logs...")
        pipeline_s3.flush_now()
        sys.exit(1)
    signal.signal(signal.SIGINT, _on_interrupt)

    pipeline_logger.info(f"Pipeline started: specs={specs_path} max_products={max_products} workers={max_workers}")

    # Khởi tạo API key pool
    api_keys = settings.youtube_api_key_list
    if not api_keys:
        pipeline_logger.error("Không có API key nào. Kiểm tra YOUTUBE_DATA_API_KEYS trong .env")
        return
    api_key_pool = YouTubeApiKeyPool(api_keys)
    pipeline_logger.info(f"API Key Pool: {len(api_keys)} keys — {[f'...{k[-6:]}' for k in api_keys]}")

    specs_records = read_json_records(specs_path)
    if max_products is not None:
        specs_records = specs_records[:max_products]
    if not specs_records:
        pipeline_logger.warning("No records to process.")
        return

    pipeline_logger.info(f"Input={len(specs_records)} records ready.")

    product_names = [
        record.get("search_query_name") or (record.get("fact_product") or {}).get("product_name")
        for record in specs_records
        if record.get("search_query_name") or (record.get("fact_product") or {}).get("product_name")
    ]
    product_id_index = fetch_product_id_index(product_names)
    if not product_id_index:
        pipeline_logger.warning("No products found in DB. Run DB Load script first.")
        return

    # Load tracking vào memory — các thread share qua lock
    completed_products = load_tracking_file()
    pipeline_logger.info(f"Loaded {len(completed_products)} completed products.")

    media_dir.mkdir(parents=True, exist_ok=True)
    total = len(specs_records)

    # Lọc pending — bỏ qua completed
    pending = []
    for index, record in enumerate(specs_records, start=1):
        name = record.get("search_query_name") or (record.get("fact_product") or {}).get("product_name")
        if not name or not product_id_index.get(name) or name in completed_products:
            continue
        pending.append((index, product_id_index[name], name))

    pipeline_logger.info(f"Pending: {len(pending)} products to process.")

    if test_mode:
        pending = pending[:1]
        pipeline_logger.info("TEST MODE: chỉ xử lý 1 product.")

    youtube_hits = media_uploaded = comments_inserted = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _process_one_product,
                index, total, product_id, product_name,
                media_dir, youtube_verbose,
                completed_products, api_key_pool, pipeline_logger,
            ): product_name
            for index, product_id, product_name in pending
        }

        try:
            for future in as_completed(futures):
                product_name = futures[future]
                try:
                    hits, upl, comms = future.result()
                    youtube_hits      += hits
                    media_uploaded    += upl
                    comments_inserted += comms
                except YouTubeQuotaExceededError as exc:
                    pipeline_logger.error(f"Tất cả API keys hết quota: {exc}")
                    pipeline_logger.info("Huỷ các task còn lại. Chạy lại sau.")
                    for f in futures:
                        f.cancel()
                    break
                except Exception as exc:
                    pipeline_logger.error(f"Unexpected error for {product_name!r}: {exc}")
        finally:
            pipeline_s3.flush_now()

    pipeline_logger.info(
        f"Pipeline done: youtube_hits={youtube_hits} "
        f"media_uploaded={media_uploaded} comments_inserted={comments_inserted}"
    )
    pipeline_s3.flush_now()

# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest YouTube media for products → S3 + DB.")
    parser.add_argument("--specs",            default="data/processed/final_ready_to_load_specs.json")
    parser.add_argument("--media-dir",        default="data/processed/youtube_media")
    parser.add_argument("--max-products",     type=int, default=None)
    parser.add_argument("--quiet-youtube",    action="store_true")
    parser.add_argument("--workers",          type=int, default=3, help="Số product xử lý song song.")
    parser.add_argument("--rebuild-tracking", action="store_true")
    parser.add_argument("--test",             action="store_true")
    args = parser.parse_args()

    if args.rebuild_tracking:
        rebuild_tracking_file_from_db()
        return

    try:
        run_pipeline(
            specs_path=Path(args.specs),
            media_dir=Path(args.media_dir),
            max_products=args.max_products,
            youtube_verbose=not args.quiet_youtube,
            test_mode=args.test,
            max_workers=args.workers,
        )
    except YouTubeQuotaExceededError:
        sys.exit(5)


if __name__ == "__main__":
    main()