import csv
import json
import shutil
import subprocess
from pathlib import Path

import requests


YOUTUBE_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"


class YouTubeQuotaExceededError(Exception):
    """YouTube Data API trả lỗi hết quota / giới hạn (403)."""

    def __init__(self, message: str, *, api_reasons: list[str] | None = None) -> None:
        super().__init__(message)
        self.api_reasons = api_reasons or []


def _yt_log(verbose: bool, message: str) -> None:
    if verbose:
        print(message, flush=True)


def _get_yt_dlp_js_runtime_args(*, verbose: bool) -> list[str]:
    """
    yt-dlp YouTube extraction increasingly requires a JS runtime (node/deno).
    Prefer node if available, otherwise deno if available; otherwise return empty.
    """
    node_path = shutil.which("node")
    if node_path:
        _yt_log(verbose, "[INFO] yt-dlp JS runtime: node")
        return ["--js-runtimes", "node"]

    deno_path = shutil.which("deno")
    if deno_path:
        _yt_log(verbose, "[INFO] yt-dlp JS runtime: deno")
        return ["--js-runtimes", "deno"]

    _yt_log(
        verbose,
        "[WARN] yt-dlp JS runtime not found (node/deno). YouTube extraction may fail; install Node.js or Deno.",
    )
    return []


def _run_command(command: list[str]) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        error_message = (result.stderr or result.stdout or "Unknown error").strip()
        raise RuntimeError(error_message)


def _ensure_yt_dlp_available() -> None:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("Missing yt-dlp executable. Please install yt-dlp and add it to PATH.")


def search_youtube_videos(
    product_name: str, api_key: str, max_results: int = 1, *, verbose: bool = True
) -> list[dict]:
    if not api_key:
        raise ValueError("Missing YOUTUBE_DATA_API_KEY in environment.")

    # YouTube Data API search.list allows at most 50 results per request.
    effective_max_results = max(1, min(max_results, 50))
    query_preview = f"review {product_name}"
    if len(query_preview) > 120:
        query_preview = query_preview[:117] + "..."
    _yt_log(
        verbose,
        f"[INFO] YouTube Data API search: q={query_preview!r} maxResults={effective_max_results}",
    )

    params = {
        "part": "snippet",
        "q": f"review {product_name}",
        "type": "video",
        "maxResults": effective_max_results,
        "order": "relevance",
        "key": api_key,
    }
    response = requests.get(YOUTUBE_SEARCH_ENDPOINT, params=params, timeout=20)
    if response.status_code == 403:
        api_reasons: list[str] = []
        message = response.text[:800]
        try:
            err_payload = response.json()
            errors = (err_payload.get("error") or {}).get("errors") or []
            for item in errors:
                if isinstance(item, dict) and item.get("reason"):
                    api_reasons.append(str(item["reason"]))
            if err_payload.get("error", {}).get("message"):
                message = str(err_payload["error"]["message"])
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        quota_like = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
        if api_reasons and quota_like.intersection(set(api_reasons)):
            raise YouTubeQuotaExceededError(
                f"YouTube Data API quota/limit: {message}",
                api_reasons=api_reasons,
            )
        raise RuntimeError(f"YouTube Data API 403 Forbidden: {message}")
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items") or []

    videos: list[dict] = []
    for item in items:
        video_id = item.get("id", {}).get("videoId")
        if not video_id:
            continue
        videos.append(
            {
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
                "video_title": item.get("snippet", {}).get("title"),
            }
        )
    _yt_log(verbose, f"[INFO] YouTube search parsed {len(videos)} video URL(s).")
    return videos


def download_audio(video_url: str, output_stem: Path, *, verbose: bool = True) -> Path:
    _ensure_yt_dlp_available()
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    output_template = str(output_stem.with_suffix("")) + ".%(ext)s"
    _yt_log(verbose, f"[INFO] yt-dlp extract audio url={video_url} out={output_stem}.mp3")
    js_runtime_args = _get_yt_dlp_js_runtime_args(verbose=verbose)
    _run_command(
        [
            "yt-dlp",
            *js_runtime_args,
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "-o",
            output_template,
            video_url,
        ]
    )
    audio_path = output_stem.with_suffix(".mp3")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found after yt-dlp run: {audio_path}")
    size_kb = audio_path.stat().st_size // 1024
    _yt_log(verbose, f"[INFO] yt-dlp audio done path={audio_path} size_kb≈{size_kb}")
    return audio_path


def download_comments(video_url: str, output_stem: Path, *, verbose: bool = True) -> tuple[Path, list[dict]]:
    _ensure_yt_dlp_available()
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    output_template = str(output_stem.with_suffix(""))
    _yt_log(verbose, f"[INFO] yt-dlp fetch comments+metadata url={video_url}")
    js_runtime_args = _get_yt_dlp_js_runtime_args(verbose=verbose)
    _run_command(
        [
            "yt-dlp",
            *js_runtime_args,
            "--skip-download",
            "--write-info-json",
            "--write-comments",
            "-o",
            output_template,
            video_url,
        ]
    )

    info_json_path = output_stem.with_suffix(".info.json")
    if not info_json_path.exists():
        raise FileNotFoundError(f"Info JSON file not found after yt-dlp run: {info_json_path}")

    info_payload = json.loads(info_json_path.read_text(encoding="utf-8"))
    raw_comments = info_payload.get("comments") or []
    comments: list[dict] = []
    for comment in raw_comments:
        comment_text = comment.get("text")
        if not comment_text:
            continue
        comments.append(
            {
                "comment_text": comment_text.strip(),
                "user_name": (comment.get("author") or "").strip() or None,
            }
        )

    csv_path = output_stem.with_name(output_stem.name + "_comments.csv")
    with csv_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["user_name", "comment_text"])
        writer.writeheader()
        writer.writerows(comments)

    _yt_log(verbose, f"[INFO] yt-dlp comments done count={len(comments)} csv={csv_path}")
    return csv_path, comments
