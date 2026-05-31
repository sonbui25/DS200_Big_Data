import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from unidecode import unidecode

from src.app.config.settings import settings


def _build_s3_client():
    client_kwargs: dict = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            client_kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client("s3", **client_kwargs)


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", unidecode(name)).strip("_").lower()


class S3FlushHandler(logging.Handler):
    """
    Flush log file lên S3 sau mỗi `flush_every` records.
    Luôn flush khi gặp ERROR/CRITICAL.
    Gọi .flush_now() để force upload bất cứ lúc nào.
    """

    def __init__(self, log_path: Path, s3_key: str, flush_every: int = 10):
        super().__init__()
        self.log_path = log_path
        self.s3_key = s3_key
        self.flush_every = flush_every
        self._count = 0

    def emit(self, record: logging.LogRecord) -> None:
        self._count += 1
        force = record.levelno >= logging.ERROR
        if force or self._count >= self.flush_every:
            self.flush_now()
            self._count = 0

    def flush_now(self) -> None:
        if not self.log_path.exists():
            return
        try:
            _build_s3_client().upload_file(
                str(self.log_path),
                settings.aws_s3_bucket,
                self.s3_key,
            )
        except Exception as exc:
            # Không để lỗi S3 crash pipeline
            print(f"[WARN] S3 log flush failed: {exc}", flush=True)

def upload_log_to_s3(log_path: Path, product_name: str | None = None) -> str | None:
    """Upload log file lên S3 sau khi pipeline xong. Trả về s3 path hoặc None nếu lỗi."""
    try:
        import re
        import boto3
        from unidecode import unidecode

        client_kwargs: dict = {"region_name": settings.aws_region}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            if settings.aws_session_token:
                client_kwargs["aws_session_token"] = settings.aws_session_token
        s3_client = boto3.client("s3", **client_kwargs)

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if product_name:
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", unidecode(product_name)).strip("_").lower()
            s3_key = f"media_log/{date_str}/{safe}.log"
        else:
            s3_key = f"media_log/{date_str}/{log_path.name}"

        s3_client.upload_file(str(log_path), settings.aws_s3_bucket, s3_key)
        return f"s3://{settings.aws_s3_bucket}/{s3_key}"

    except Exception as exc:
        # Không để lỗi log làm crash pipeline
        print(f"[WARN] Failed to upload log to S3: {exc}", flush=True)
        return None
    
def setup_pipeline_logger(
    media_dir: Path,
    product_name: str | None = None,
    flush_every: int = 10,
) -> tuple[logging.Logger, Path, S3FlushHandler]:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    parent_log_dir = media_dir / "media_log"
    parent_log_dir.mkdir(parents=True, exist_ok=True)

    if not product_name: 
        # Khởi tạo pipeline: Luôn tạo thư mục mới nếu thư mục mặc định đã tồn tại
        log_dir = parent_log_dir / date_str
        idx = 1
        while log_dir.exists():
            log_dir = parent_log_dir / f"{date_str}_{idx}"
            idx += 1
    else:
        # Logging cho product: Lấy thư mục mới nhất của ngày hôm nay để ghi vào
        log_dir = parent_log_dir / date_str
        idx = 1
        while (parent_log_dir / f"{date_str}_{idx}").exists():
            log_dir = parent_log_dir / f"{date_str}_{idx}"
            idx += 1

    log_dir.mkdir(parents=True, exist_ok=True)
    real_date_str = log_dir.name # Lấy tên thực tế để đẩy lên s3: ví dụ: 2026-05-05_1

    if product_name:
        log_filename = f"{_safe_name(product_name)}.log"
    else:
        log_filename = f"pipeline_{datetime.now(timezone.utc).strftime('%H%M%S')}.log"

    log_path = log_dir / log_filename
    s3_key = f"media_log/{real_date_str}/{log_filename}"

    logger = logging.getLogger(f"media_pipeline.{log_filename}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler 1: console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler 2: local file
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler 3: S3 periodic flush
    s3_handler = S3FlushHandler(log_path, s3_key, flush_every=flush_every)
    s3_handler.setFormatter(formatter)
    logger.addHandler(s3_handler)

    logger.info(f"Logger initialized → local={log_path} s3={s3_key} flush_every={flush_every}")
    return logger, log_path, s3_handler