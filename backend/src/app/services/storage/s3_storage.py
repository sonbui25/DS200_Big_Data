from pathlib import Path
import re
import logging

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


def _build_s3_key(prefix: str, product_name: str, filename: str) -> str:
    normalized_prefix = prefix.strip("/").strip()
    safe_product_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_name).strip("_").lower()
    if normalized_prefix:
        return f"{normalized_prefix}/{safe_product_name}/{filename}"
    return f"{safe_product_name}/{filename}"


def _storage_file_stem(storage_id: int | str) -> str:
    return str(storage_id).strip() or "asset"


def build_transcript_key(product_name: str, storage_id: int | str) -> str:
    stem = _storage_file_stem(storage_id)
    return _build_s3_key(
        prefix=settings.aws_s3_transcripts_prefix,
        product_name=product_name,
        filename=f"{stem}_transcript.json",
    )


def build_comments_key(product_name: str, storage_id: int | str) -> str:
    stem = _storage_file_stem(storage_id)
    return _build_s3_key(
        prefix=settings.aws_s3_comments_prefix,
        product_name=product_name,
        filename=f"{stem}_comments.csv",
    )


def build_audio_key(product_name: str, storage_id: int | str, extension: str) -> str:
    safe_extension = extension.lstrip(".") or "mp3"
    stem = _storage_file_stem(storage_id)
    return _build_s3_key(
        prefix=settings.aws_s3_audio_prefix,
        product_name=product_name,
        filename=f"{stem}_audio.{safe_extension}",
    )


def upload_audio_file(file_path: str, product_name: str, storage_id: int | str) -> str:
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
    s3_key = build_audio_key(product_name, storage_id, path_obj.suffix)
    _build_s3_client().upload_file(str(path_obj), settings.aws_s3_bucket, s3_key)
    return f"s3://{settings.aws_s3_bucket}/{s3_key}"


def upload_comments_file(file_path: str, product_name: str, storage_id: int | str) -> str:
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
    s3_key = build_comments_key(product_name, storage_id)
    _build_s3_client().upload_file(str(path_obj), settings.aws_s3_bucket, s3_key)
    return f"s3://{settings.aws_s3_bucket}/{s3_key}"


def upload_transcript_file(file_path: str, product_name: str, storage_id: int | str) -> str:
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
    s3_key = build_transcript_key(product_name, storage_id)
    _build_s3_client().upload_file(str(path_obj), settings.aws_s3_bucket, s3_key)
    return f"s3://{settings.aws_s3_bucket}/{s3_key}"

def delete_product_files_from_s3(product_name: str, logger: logging.Logger | None = None) -> int:
    import logging
    log = logger or logging.getLogger("media_pipeline.s3")

    safe_product_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", product_name).strip("_").lower()
    s3_client = _build_s3_client()

    prefixes = [
        f"{settings.aws_s3_audio_prefix}/{safe_product_name}/",
        f"{settings.aws_s3_comments_prefix}/{safe_product_name}/",
        f"{settings.aws_s3_transcripts_prefix}/{safe_product_name}/",
    ]

    deleted = 0
    for prefix in prefixes:
        paginator = s3_client.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=settings.aws_s3_bucket, Prefix=prefix):
            objects_to_delete = [
                {"Key": v["Key"], "VersionId": v["VersionId"]}
                for v in page.get("Versions", [])
            ] + [
                {"Key": m["Key"], "VersionId": m["VersionId"]}
                for m in page.get("DeleteMarkers", [])
            ]

            if not objects_to_delete:
                continue

            log.debug(f"Deleting {len(objects_to_delete)} objects under prefix={prefix}")

            response = s3_client.delete_objects(
                Bucket=settings.aws_s3_bucket,
                Delete={"Objects": objects_to_delete},
            )

            for err in response.get("Errors", []):
                log.warning(
                    f"S3 delete failed: Key={err.get('Key')} "
                    f"Code={err.get('Code')} Message={err.get('Message')}"
                )

            actually_deleted = len(response.get("Deleted", []))
            deleted += actually_deleted
            log.debug(f"Deleted {actually_deleted}/{len(objects_to_delete)} objects")

    return deleted