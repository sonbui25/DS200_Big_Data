from pathlib import Path

import boto3

from src.app.config.settings import settings


def build_transcript_key(product_id: int, video_id: int) -> str:
    return f"transcripts/{product_id}/{video_id}_transcript.txt"


def build_comments_key(product_id: int, video_id: int) -> str:
    return f"comments/{product_id}/{video_id}_comments.csv"


def upload_transcript_file(local_path: str, product_id: int, video_id: int) -> str:
    if not settings.aws_s3_transcripts_bucket:
        raise ValueError("Missing AWS_S3_TRANSCRIPTS_BUCKET in environment.")

    key = build_transcript_key(product_id=product_id, video_id=video_id)
    s3_client = boto3.client("s3", region_name=settings.aws_region)
    s3_client.upload_file(local_path, settings.aws_s3_transcripts_bucket, key)
    return f"s3://{settings.aws_s3_transcripts_bucket}/{key}"


def upload_comments_file(local_path: str, product_id: int, video_id: int) -> str:
    if not settings.aws_s3_comments_bucket:
        raise ValueError("Missing AWS_S3_COMMENTS_BUCKET in environment.")

    key = build_comments_key(product_id=product_id, video_id=video_id)
    s3_client = boto3.client("s3", region_name=settings.aws_region)
    s3_client.upload_file(local_path, settings.aws_s3_comments_bucket, key)
    return f"s3://{settings.aws_s3_comments_bucket}/{key}"


def ensure_local_file_exists(local_path: str) -> None:
    file_path = Path(local_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {local_path}")
