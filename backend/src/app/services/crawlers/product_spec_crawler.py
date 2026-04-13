from collections.abc import Sequence
import time

import requests
from bs4 import BeautifulSoup


def crawl_product_specs(product_links: Sequence[dict]) -> Sequence[dict]:
    """
    Crawl thong so chi tiet va map ve schema DB-ready.
    """
    mapped_records: list[dict] = []
    total_links = len(product_links)
    success_count = 0
    failed_count = 0
    skipped_count = 0

    print(f"[INFO] Start spec crawler with {total_links} links", flush=True)
    headers = {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    for index, phone in enumerate(product_links, start=1):
        url = phone.get("url")
        if not url:
            skipped_count += 1
            print(
                f"[WARN] [{index}/{total_links}] Missing URL, skip record",
                flush=True,
            )
            continue

        print(f"[INFO] [{index}/{total_links}] Crawling specs: {url}", flush=True)
        raw_specs = _scrape_phone_details(url=url, headers=headers)
        if not raw_specs:
            failed_count += 1
            print(
                f"[WARN] [{index}/{total_links}] Failed to scrape specs: {url}",
                flush=True,
            )
            continue

        mapped_record = _map_to_database_schema(raw_specs=raw_specs, input_data=phone)
        if mapped_record:
            mapped_records.append(mapped_record)
            success_count += 1
            print(
                f"[INFO] [{index}/{total_links}] Success mapped={success_count} failed={failed_count} skipped={skipped_count}",
                flush=True,
            )
        else:
            failed_count += 1
            print(
                f"[WARN] [{index}/{total_links}] Failed to map schema: {url}",
                flush=True,
            )
        time.sleep(0.8)

    print(
        f"[INFO] Finished spec crawler total={total_links} success={success_count} failed={failed_count} skipped={skipped_count}",
        flush=True,
    )
    return mapped_records


def _scrape_phone_details(url: str, headers: dict) -> dict | None:
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    spec_box = soup.find("div", class_="product-lightbox-content")
    if not spec_box:
        return None

    table = spec_box.find("table")
    if not table:
        return None

    specs: dict = {}
    rows = table.find_all("tr")
    for row in rows:
        columns = row.find_all("td")
        if len(columns) != 2:
            continue
        key = columns[0].text.strip().replace(":", "")
        value = columns[1].text.strip()
        specs[key] = value
    return specs


def _clean_val(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return value.strip()


def _map_to_database_schema(raw_specs: dict, input_data: dict) -> dict | None:
    if not raw_specs:
        return None

    return {
        "_source_url": input_data.get("url"),
        "fact_product": {
            "product_name": input_data.get("name", "Unknown Name"),
            "os_version": _clean_val(raw_specs.get("Hệ điều hành")),
            "language_support": _clean_val(raw_specs.get("Ngôn ngữ")),
        },
        "dim_display": {
            "display_type": _clean_val(raw_specs.get("Loại màn hình")),
            "color_depth": _clean_val(raw_specs.get("Màu màn hình")),
            "display_standard": _clean_val(raw_specs.get("Chuẩn màn hình")),
            "resolution": _clean_val(raw_specs.get("Độ phân giải")),
            "screen_size": _clean_val(raw_specs.get("Màn hình rộng")),
            "touch_technology": _clean_val(raw_specs.get("Công nghệ cảm ứng")),
        },
        "dim_camera": {
            "rear_camera": _clean_val(raw_specs.get("Camera sau")),
            "front_camera": _clean_val(raw_specs.get("Camera trước")),
            "flash_light": _clean_val(raw_specs.get("Đèn Flash")),
            "camera_features": _clean_val(raw_specs.get("Tính năng camera")),
            "video_recording": _clean_val(raw_specs.get("Quay phim")),
            "video_call": _clean_val(raw_specs.get("Videocall")),
        },
        "dim_performance": {
            "cpu_speed": _clean_val(raw_specs.get("Tốc độ CPU")),
            "core_count": _clean_val(raw_specs.get("Số nhân")),
            "chipset": _clean_val(raw_specs.get("Chipset")),
            "ram_capacity": _clean_val(raw_specs.get("RAM")),
            "gpu_chip": _clean_val(raw_specs.get("Chip đồ họa (GPU)"))
            or _clean_val(raw_specs.get("GPU")),
        },
        "dim_storage": {
            "phonebook_storage": _clean_val(raw_specs.get("Danh bạ")),
            "internal_storage": _clean_val(raw_specs.get("Bộ nhớ trong (ROM)")),
            "external_memory": _clean_val(raw_specs.get("Thẻ nhớ ngoài")),
            "max_external_support": _clean_val(raw_specs.get("Hỗ trợ thẻ tối đa")),
        },
        "dim_design": {
            "design_style": _clean_val(raw_specs.get("Kiểu dáng")),
            "dimensions": _clean_val(raw_specs.get("Kích thước")),
            "weight": _clean_val(raw_specs.get("Trọng lượng (g)")),
        },
        "dim_battery": {
            "battery_type": _clean_val(raw_specs.get("Loại pin")),
            "battery_capacity": _clean_val(raw_specs.get("Dung lượng pin")),
            "removable_battery": _clean_val(raw_specs.get("Pin có thể tháo rời")),
        },
        "dim_connectivity": {
            "network_3g": _clean_val(raw_specs.get("3G")),
            "network_4g": _clean_val(raw_specs.get("4G")),
            "sim_type": _clean_val(raw_specs.get("Loại Sim")),
            "sim_slots": _clean_val(raw_specs.get("Khe gắn Sim")),
            "wifi": _clean_val(raw_specs.get("Wifi")),
            "gps": _clean_val(raw_specs.get("GPS")),
            "bluetooth": _clean_val(raw_specs.get("Bluetooth")),
            "gprs_edge": _clean_val(raw_specs.get("GPRS/EDGE")),
            "headphone_jack": _clean_val(raw_specs.get("Jack tai nghe")),
            "nfc": _clean_val(raw_specs.get("NFC")),
            "usb_connection": _clean_val(raw_specs.get("Kết nối USB")),
            "other_connections": _clean_val(raw_specs.get("Kết nối khác")),
            "charging_port": _clean_val(raw_specs.get("Cổng sạc")),
        },
        "dim_utilities": {
            "movie_playback": _clean_val(raw_specs.get("Xem phim")),
            "music_playback": _clean_val(raw_specs.get("Nghe nhạc")),
            "charging_port_alt": _clean_val(raw_specs.get("Cổng sạc")),
            "voice_recorder": _clean_val(raw_specs.get("Ghi âm")),
            "fm_radio": _clean_val(raw_specs.get("FM radio")),
            "other_features": _clean_val(raw_specs.get("Chức năng khác")),
        },
    }
