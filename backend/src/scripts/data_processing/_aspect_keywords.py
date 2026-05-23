"""
Keyword dictionary và unit patterns cho comment aspect classification.
Tách ra file riêng để dễ cập nhật mà không chạm vào logic chính.
"""

import re

KEYWORDS: dict[str, list[str]] = {
    "camera": [
        # VI
        "camera", "chụp", "ảnh", "zoom", "selfie", "quay", "phim",
        "góc rộng", "telephoto", "chụp đêm", "chụp ngày", "xóa phông",
        "chân dung", "ống kính", "siêu rộng", "macro",
        "cam", "chụp hình", "camera trước", "camera sau",
        "cam trước", "cam sau", "quay video", "lấy nét", "thiếu sáng",
        # EN
        "photo", "picture", "shoot", "lens", "portrait", "video",
        "footage", "nightmode", "bokeh", "ultrawide", "snapshot",
    ],
    "battery": [
        # VI
        "pin", "sạc", "hao pin", "nạp điện", "sạc nhanh", "sạc không dây",
        "cạn pin", "trâu pin", "pin trâu", "thời lượng pin",
        "trâu", "tụt", "tuột", "hao", "bin",
        "sạc pin", "hết pin", "pin tụt", "pin khỏe",
        "qua đêm", "nhanh hết", "tụt nhanh", "pin tuột", "mau hết",
        # EN
        "battery", "charge", "charging", "drain", "fast charge",
        "wireless charge", "battery life", "power bank",
    ],
    "display": [
        # VI
        "màn hình", "màn", "độ sáng", "tần số quét", "ám vàng",
        "burn-in", "tấm nền", "độ phân giải", "notch", "đục lỗ",
        "oled", "amoled", "lcd", "hiển thị", "phân giải", "rực rỡ",
        # EN
        "screen", "display", "nit", "refresh rate", "resolution",
        "panel", "brightness", "pwm", "punchhole",
    ],
    "performance": [
        # VI
        "hiệu năng", "lag", "mượt", "chậm", "giật", "nóng máy",
        "đơ", "nhanh", "hiệu suất", "tản nhiệt", "chip",
        "vi xử lý", "xử lý", "ram",
        "game", "chơi game", "cấu hình", "chơi", "liên quân", "pubg",
        "giật lag", "ứng dụng", "đa nhiệm", "phần mềm", "khởi động", "lướt web",
        # EN
        "snapdragon", "dimensity", "cpu", "gpu", "processor",
        "benchmark", "smooth", "heating", "throttle", "performance",
        "helio", "gaming", "freeze",
    ],
    "design": [
        # VI
        "thiết kế", "mỏng", "nhẹ", "nặng", "màu sắc", "vỏ máy",
        "kính", "nhôm", "titan", "nhựa", "sang trọng", "ngoại hình",
        "mặt lưng", "vừa tay", "mẫu mã", "kiểu dáng", "nhỏ gọn",
        "mỏng nhẹ", "bắt mắt", "cầm chắc", "lưng nhựa", "thời trang",
        # EN
        "design", "build quality", "color", "weight", "thin", "premium",
        "glass", "aluminum", "titanium", "finish", "aesthetic",
    ],
    "storage": [
        # VI
        "bộ nhớ", "lưu trữ", "dung lượng", "rom", "thẻ nhớ",
        "bộ nhớ trong", "bộ nhớ ngoài", "đầy bộ nhớ",
        # EN
        "storage", "sd card", "microsd", "internal storage", "capacity",
    ],
    "connectivity": [
        # VI
        "wifi", "sóng", "kết nối", "sim", "mạng", "hotspot", "jack tai nghe",
        "bắt sóng", "bắt wifi", "sóng wifi",
        # EN
        "bluetooth", "nfc", "network", "signal", "lte", "type-c",
        "5g", "4g", "3g",
    ],
    "utilities": [
        # VI
        "tính năng", "vân tay", "chống nước", "nhận diện khuôn mặt",
        "loa ngoài", "âm thanh", "stereo", "always on display",
        "cảm ứng", "nhận diện", "mở khóa", "nghe nhạc", "tai nghe",
        "cảm biến vân tay",
        # EN
        "face id", "fingerprint", "ip68", "ip67", "waterproof",
        "speaker", "audio", "dolby", "haptic", "aod",
    ],
}

# Số + đơn vị kỹ thuật — không dùng \b vì dính liền với chữ số
# Ví dụ: "120Hz", "64MP", "5000mAh", "256GB"
UNIT_PATTERNS: dict[str, list[str]] = {
    "display":     [r"\d+\s*hz"],
    "camera":      [r"\d+\s*mp"],
    "battery":     [r"\d+\s*mah", r"\d+\s*w(?:att)?(?:\s|$)"],
    "storage":     [r"\d+\s*(?:gb|tb)"],
}

# Precompile 1 lần khi import — tránh recompile mỗi lần gọi keyword_match
_KW_COMPILED = {
    aspect: [
        re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in kws
    ]
    for aspect, kws in KEYWORDS.items()
}

_UNIT_COMPILED = {
    aspect: [re.compile(pat, re.IGNORECASE) for pat in pats]
    for aspect, pats in UNIT_PATTERNS.items()
}


def keyword_match(text: str) -> dict[str, int]:
    """
    Trả về dict {aspect: 1} cho mỗi aspect có keyword xuất hiện trong text.
    Dùng word boundary \\b để tránh khớp substring (vd: "ai" không khớp "bhai").
    """
    matched: dict[str, int] = {}

    for aspect, patterns in _KW_COMPILED.items():
        for pat in patterns:
            if pat.search(text):
                matched[aspect] = 1
                break

    for aspect, patterns in _UNIT_COMPILED.items():
        if aspect not in matched:
            for pat in patterns:
                if pat.search(text):
                    matched[aspect] = 1
                    break

    return matched
