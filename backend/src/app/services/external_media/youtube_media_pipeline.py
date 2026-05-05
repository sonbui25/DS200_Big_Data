import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

import requests
from youtube_transcript_api import YouTubeTranscriptApi

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
    args = []
    
    # Check for cookies file
    cookies_path = Path("cookies.txt")
    if cookies_path.exists():
        _yt_log(verbose, "[INFO] yt-dlp using cookies from cookies.txt")
        args.extend(["--cookies", str(cookies_path)])

    node_path = shutil.which("node")
    if node_path:
        _yt_log(verbose, "[INFO] yt-dlp JS runtime: node")
        args.extend(["--js-runtimes", "node"])
        return args

    deno_path = shutil.which("deno")
    if deno_path:
        _yt_log(verbose, "[INFO] yt-dlp JS runtime: deno")
        args.extend(["--js-runtimes", "deno"])
        return args

    _yt_log(
        verbose,
        "[WARN] yt-dlp JS runtime not found (node/deno). YouTube extraction may fail; install Node.js or Deno.",
    )
    return args


def _run_command(command: list[str]) -> None:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        error_message = (result.stderr or result.stdout or "Unknown error").strip()
        raise RuntimeError(error_message)


def _ensure_yt_dlp_available() -> None:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("Missing yt-dlp executable. Please install yt-dlp and add it to PATH.")


def search_youtube_videos(
    product_name: str,
    api_key: str,
    max_results: int = 5,
    verbose: bool = False,
) -> list[dict]:
    if not api_key:
        raise ValueError("Missing YOUTUBE_DATA_API_KEY in environment.")

    # YouTube Data API search.list allows at most 50 results per request, but we cap it at 30.
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
        "regionCode": "VN",
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
        "--remote-components", "ejs:github",   # ← thêm dòng này
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
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
        "--remote-components", "ejs:github",   # ← thêm dòng này
        "--skip-download",
        "--write-info-json",
        "--write-comments",
        "-o", output_template,
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


def download_transcript(
    video_id: str,
    output_stem: Path,
    *,
    languages: list[str] = ['vi', 'en'],
    verbose: bool = True,
) -> tuple[Path, list[dict]]:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    json_path = output_stem.with_name(output_stem.name + "_transcript.json")

    _yt_log(verbose, f"[INFO] Fetching transcript for video_id={video_id}")
    try:
        api = YouTubeTranscriptApi()

        # Thử lấy ngôn ngữ ưu tiên trước
        try:
            fetched = api.fetch(video_id, languages=languages)
            lang_used = "preferred"
        except Exception:
            # Fallback: lấy danh sách transcript available rồi lấy cái đầu tiên
            transcript_list = api.list(video_id)
            first_transcript = next(iter(transcript_list))
            fetched = first_transcript.fetch()
            lang_used = first_transcript.language_code

        transcript = [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in fetched
        ]
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch transcript: {exc}")

    json_path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _yt_log(verbose, f"[INFO] transcript fetch done lang={lang_used} count={len(transcript)} json={json_path}")

    return json_path, transcript
