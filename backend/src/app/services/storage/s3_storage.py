from pathlib import Path

import boto3

from src.app.config.settings import settings


def _build_s3_client():
    client_kwargs: dict = {"region_name": settings.aws_region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            client_kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client("s3", **client_kwargs)


def _build_s3_key(prefix: str, product_id: int, filename: str) -> str:
    normalized_prefix = prefix.strip("/").strip()
    if normalized_prefix:
        return f"{normalized_prefix}/{product_id}/{filename}"
    return f"{product_id}/{filename}"


def _storage_file_stem(storage_id: int | str) -> str:
    return str(storage_id).strip() or "asset"


def build_transcript_key(product_id: int, storage_id: int | str) -> str:
    stem = _storage_file_stem(storage_id)
    return _build_s3_key(
        prefix=settings.aws_s3_transcripts_prefix,
        product_id=product_id,
        filename=f"{stem}_transcript.txt",
    )


def build_comments_key(product_id: int, storage_id: int | str) -> str:
    stem = _storage_file_stem(storage_id)
    return _build_s3_key(
        prefix=settings.aws_s3_comments_prefix,
        product_id=product_id,
        filename=f"{stem}_comments.csv",
    )


def build_audio_key(product_id: int, storage_id: int | str, extension: str) -> str:
    safe_extension = extension.lstrip(".") or "mp3"
    stem = _storage_file_stem(storage_id)
    return _build_s3_key(
        prefix=settings.aws_s3_audio_prefix,
        product_id=product_id,
        filename=f"{stem}_audio.{safe_extension}",
    )


def upload_transcript_file(local_path: str, product_id: int, storage_id: int | str) -> str:
    if not settings.aws_s3_bucket:
        raise ValueError("Missing AWS_S3_BUCKET in environment.")

    key = build_transcript_key(product_id=product_id, storage_id=storage_id)
    s3_client = _build_s3_client()
    s3_client.upload_file(local_path, settings.aws_s3_bucket, key)
    return f"s3://{settings.aws_s3_bucket}/{key}"


def upload_comments_file(local_path: str, product_id: int, storage_id: int | str) -> str:
    if not settings.aws_s3_bucket:
        raise ValueError("Missing AWS_S3_BUCKET in environment.")

    key = build_comments_key(product_id=product_id, storage_id=storage_id)
    s3_client = _build_s3_client()
    s3_client.upload_file(local_path, settings.aws_s3_bucket, key)
    return f"s3://{settings.aws_s3_bucket}/{key}"


def upload_audio_file(local_path: str, product_id: int, storage_id: int | str) -> str:
    if not settings.aws_s3_bucket:
        raise ValueError("Missing AWS_S3_BUCKET in environment.")

    extension = Path(local_path).suffix
    key = build_audio_key(product_id=product_id, storage_id=storage_id, extension=extension)
    s3_client = _build_s3_client()
    s3_client.upload_file(local_path, settings.aws_s3_bucket, key)
    return f"s3://{settings.aws_s3_bucket}/{key}"


def ensure_local_file_exists(local_path: str) -> None:
    file_path = Path(local_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {local_path}")
