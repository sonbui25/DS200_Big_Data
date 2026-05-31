"""DB layer: kết nối Postgres, lookup product name, mapping aspect → dim table."""

import logging
from functools import lru_cache

import psycopg2

from src.app.config.settings import settings

logger = logging.getLogger(__name__)

ASPECT_TO_DIM: dict[str, tuple[str, list[str]]] = {
    "display":      ("dim_display",      ["display_type", "color_depth", "display_standard", "resolution", "screen_size", "touch_technology"]),
    "camera":       ("dim_camera",       ["rear_camera", "front_camera", "flash_light", "camera_features", "video_recording", "video_call"]),
    "performance":  ("dim_performance",  ["cpu_speed", "core_count", "chipset", "ram_capacity", "gpu_chip"]),
    "storage":      ("dim_storage",      ["phonebook_storage", "internal_storage", "external_memory", "max_external_support"]),
    "design":       ("dim_design",       ["design_style", "dimensions", "weight"]),
    "battery":      ("dim_battery",      ["battery_type", "battery_capacity", "removable_battery"]),
    "connectivity": ("dim_connectivity", ["network_3g", "network_4g", "sim_type", "sim_slots", "wifi", "gps", "bluetooth", "gprs_edge", "headphone_jack", "nfc", "usb_connection", "other_connections", "charging_port"]),
    "utilities":    ("dim_utilities",    ["movie_playback", "music_playback", "charging_port_alt", "voice_recorder", "fm_radio", "other_features"]),
}

ASPECT_LIST = " | ".join(ASPECT_TO_DIM.keys())


def connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        connect_timeout=10,
    )


@lru_cache(maxsize=256)
def get_product_name(product_id: int) -> str:
    """Lấy product_name từ fact_product, cache để HyDE khỏi query DB mỗi lần."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT product_name FROM fact_product WHERE product_id = %s", (product_id,))
            row = cur.fetchone()
            return row[0] if row else f"điện thoại (id={product_id})"
    finally:
        conn.close()
