import threading
import logging
from collections import deque


class YouTubeApiKeyPool:
    """
    Thread-safe pool xoay vòng API keys.
    Khi 1 key bị quota, tự động chuyển sang key tiếp theo.
    Nếu hết tất cả keys → raise YouTubeQuotaExceededError.
    """

    def __init__(self, api_keys: list[str]) -> None:
        if not api_keys:
            raise ValueError("Cần ít nhất 1 API key.")
        self._keys: deque[str] = deque(api_keys)
        self._exhausted: set[str] = set()
        self._lock = threading.Lock()

    @property
    def current_key(self) -> str:
        with self._lock:
            return self._keys[0]

    def mark_exhausted(self, key: str, logger: logging.Logger | None = None) -> str:
        """
        Đánh dấu key hiện tại đã hết quota, xoay sang key tiếp theo.
        Trả về key mới. Raise nếu hết tất cả.
        """
        from src.app.services.external_media.youtube_media_pipeline import YouTubeQuotaExceededError

        with self._lock:
            self._exhausted.add(key)
            # Xoay cho đến khi tìm được key chưa exhausted
            for _ in range(len(self._keys)):
                self._keys.rotate(-1)
                candidate = self._keys[0]
                if candidate not in self._exhausted:
                    if logger:
                        logger.warning(
                            f"API key ...{key[-6:]} exhausted. "
                            f"Rotating to ...{candidate[-6:]}"
                        )
                    return candidate

            raise YouTubeQuotaExceededError(
                f"Tất cả {len(self._exhausted)} API keys đã hết quota."
            )

    def remaining_keys(self) -> int:
        with self._lock:
            return len(self._keys) - len(self._exhausted)