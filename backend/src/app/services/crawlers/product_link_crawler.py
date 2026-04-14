from collections.abc import Sequence
import re
import time

import requests
from bs4 import BeautifulSoup
from src.app.config.settings import settings

BASE_URL = "https://mobilecity.vn/product_view_more"
HOME_URL = "https://mobilecity.vn/dien-thoai"
DEFAULT_COUNT = 20
DEFAULT_TIMEOUT_SECONDS = 20
MAX_API_RETRIES = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _extract_csrf_token(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    token_tag = soup.select_one("meta[name='csrf-token']")
    if not token_tag:
        return ""
    return token_tag.get("content", "").strip()


def _initialize_session(session: requests.Session) -> None:
    session.headers.update(
        {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://mobilecity.vn",
            "referer": HOME_URL,
            "user-agent": USER_AGENT,
            "x-requested-with": "XMLHttpRequest",
        }
    )

    if settings.mobilecity_cookie:
        session.headers["cookie"] = settings.mobilecity_cookie

    if settings.mobilecity_csrf_token:
        session.headers["x-csrf-token"] = settings.mobilecity_csrf_token
        return

    try:
        home_response = session.get(HOME_URL, timeout=DEFAULT_TIMEOUT_SECONDS)
        home_response.raise_for_status()
        csrf_token = _extract_csrf_token(home_response.text)
        if csrf_token:
            session.headers["x-csrf-token"] = csrf_token
    except requests.RequestException as error:
        print(f"[WARN] Failed to initialize session from home page: {error}")


def _discover_slugs(session: requests.Session) -> list[str]:
    response = session.get(HOME_URL, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    slugs: list[str] = []
    seen_slugs: set[str] = set()

    for anchor in soup.select("a[href]"):
        match = re.match(r"https://mobilecity\.vn/dien-thoai-(.+)$", anchor["href"])
        if not match:
            continue
        slug = match.group(1).strip("/")
        if slug and slug not in seen_slugs and not slug.startswith("may-choi-game"):
            seen_slugs.add(slug)
            slugs.append(slug)
    return slugs


def _parse_products(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.product-list-item")
    products: list[dict] = []

    for item in items:
        name_tag = item.select_one("p.name a")
        if not name_tag:
            continue

        price_tag = item.select_one("p.price")
        image_tag = item.select_one("img.lazy")
        raw_price = price_tag.get_text(strip=True) if price_tag else ""
        cleaned_price = re.sub(r"[^\d]", "", raw_price)
        price_vnd = int(cleaned_price) if cleaned_price else 0

        products.append(
            {
                "name": name_tag.get_text(strip=True),
                "url": name_tag.get("href", ""),
                "price_vnd": price_vnd,
                "price_str": raw_price,
                "image": image_tag.get("data-original", "") if image_tag else "",
            }
        )
    return products


def _fetch_api_page(session: requests.Session, slug: str, page: int) -> list[dict]:
    payload = {
        "count": DEFAULT_COUNT,
        "slug": slug,
        "page": page,
        "type_category": "phone_categories",
        "get_order": "",
    }
    response = None
    for attempt in range(MAX_API_RETRIES + 1):
        try:
            response = session.post(BASE_URL, data=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
            response.raise_for_status()
            break
        except requests.RequestException as request_error:
            if attempt >= MAX_API_RETRIES:
                print(f"[WARN] API request failed slug={slug} page={page}: {request_error}")
                return []
            time.sleep(1.0 + attempt)

    if response is None:
        return []

    try:
        body = response.json()
    except requests.exceptions.JSONDecodeError:
        content_type = response.headers.get("content-type", "")
        snippet = response.text[:160].replace("\n", " ")
        print(
            f"[WARN] Non-JSON response slug={slug} page={page} "
            f"content_type={content_type} snippet={snippet}"
        )
        return []

    phone_item = body.get("phone_item")
    if not phone_item:
        return []

    if isinstance(phone_item, list):
        html = "".join(str(chunk) for chunk in phone_item)
    elif isinstance(phone_item, str):
        html = phone_item
    else:
        return []

    if not html.strip():
        return []
    return _parse_products(html)


def crawl_product_links() -> Sequence[dict]:
    """
    Crawl danh sach san pham tu mobilecity.
    Output: list[dict] gom name/url/price_vnd/price_str/image/slug
    """
    session = requests.Session()
    _initialize_session(session=session)

    slugs = _discover_slugs(session=session)
    print(f"[INFO] Discovered {len(slugs)} slugs", flush=True)
    all_products: list[dict] = []
    seen_urls: set[str] = set()
    max_pages_per_slug = max(1, settings.mobilecity_max_pages_per_slug)

    for slug in slugs:
        print(f"[INFO] Crawling slug={slug}", flush=True)
        page = 1
        while True:
            if page > max_pages_per_slug:
                print(
                    f"[WARN] Reached page limit slug={slug} limit={max_pages_per_slug}",
                    flush=True,
                )
                break

            batch = _fetch_api_page(session=session, slug=slug, page=page)
            if not batch:
                print(f"[INFO] Stop slug={slug} at page={page} (empty batch)", flush=True)
                break

            inserted_count = 0
            for product in batch:
                product_url = product.get("url")
                if not product_url or product_url in seen_urls:
                    continue
                seen_urls.add(product_url)
                product["slug"] = slug
                all_products.append(product)
                inserted_count += 1

            print(
                f"[INFO] slug={slug} page={page} fetched={len(batch)} inserted={inserted_count} total={len(all_products)}",
                flush=True,
            )
            if inserted_count == 0:
                print(f"[INFO] Stop slug={slug} at page={page} (no new urls)", flush=True)
                break
            page += 1
            time.sleep(1.2)

    return all_products
