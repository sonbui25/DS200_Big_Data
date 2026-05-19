import logging
import re
import shutil
from pathlib import Path
from unidecode import unidecode

from src.app.services.storage.s3_storage import delete_product_files_from_s3
from ._media_db import get_video_ids_for_product, delete_video_comments, delete_videos_for_product

_fallback_logger = logging.getLogger("media_pipeline.cleaner")


def _safe_product_name(product_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", unidecode(product_name)).strip("_").lower()


def clear_db(product_id: int) -> None:
    video_ids = get_video_ids_for_product(product_id)
    delete_video_comments(video_ids)
    delete_videos_for_product(product_id)


def clear_s3(product_name: str, logger: logging.Logger | None = None) -> int:
    return delete_product_files_from_s3(product_name, logger=logger or _fallback_logger)


def clear_local(product_name: str, media_dir: Path, logger: logging.Logger | None = None) -> int:
    log = logger or _fallback_logger
    safe_name = _safe_product_name(product_name)
    deleted = 0
    for subfolder in ["audio", "comments"]:
        product_dir = media_dir / subfolder / safe_name
        if product_dir.exists():
            shutil.rmtree(product_dir)
            deleted += 1
    return deleted


def clear_all(
    product_id: int,
    product_name: str,
    media_dir: Path,
    logger: logging.Logger | None = None,
) -> None:
    log = logger or _fallback_logger
    clear_db(product_id)
    s3_deleted    = clear_s3(product_name, logger=log)
    local_deleted = clear_local(product_name, media_dir, logger=log)
    log.info(f"Cleared product_id={product_id}: s3_files={s3_deleted} local_folders={local_deleted}")