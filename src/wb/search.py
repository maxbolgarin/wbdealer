import asyncio
import logging
import random

import httpx

from src.wb.product import Product

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

BASE_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.wildberries.ru",
    "Referer": "https://www.wildberries.ru/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

# (upper_bound, basket_suffix) — updated March 2026
_BASKET_RANGES: list[tuple[int, str]] = [
    (143, "01"),
    (287, "02"),
    (431, "03"),
    (719, "04"),
    (1007, "05"),
    (1061, "06"),
    (1115, "07"),
    (1169, "08"),
    (1313, "09"),
    (1601, "10"),
    (1655, "11"),
    (1919, "12"),
    (2045, "13"),
    (2189, "14"),
    (2405, "15"),
    (2621, "16"),
    (2837, "17"),
    (3053, "18"),
    (3269, "19"),
    (3485, "20"),
    (3693, "21"),
    (3855, "22"),
    (4059, "23"),
    (4143, "24"),
    (4389, "25"),
    (4600, "26"),
]


class WBSearchClient:
    """Клиент для поиска товаров через WB Search API."""

    async def search(
        self,
        query: str,
        limit: int = 100,
        sort: str = "popular",
        min_rating: int = 4,
        price_range: tuple[int, int] | None = None,
    ) -> list[Product]:
        """Ищет товары на WB и возвращает список Product."""
        params: dict[str, str | int] = {
            "appType": 1,
            "curr": "rub",
            "dest": -1257786,
            "lang": "ru",
            "page": 1,
            "query": query,
            "resultset": "catalog",
            "sort": sort,
            "spp": 30,
            "suppressSpellcheck": "false",
        }

        if min_rating:
            params["frating"] = min_rating

        if price_range is not None:
            min_price, max_price = price_range
            params["priceU"] = f"{min_price * 100};{max_price * 100}"

        data = {}
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            for attempt in range(MAX_RETRIES):
                response = await client.get(BASE_URL, params=params)
                if response.status_code == 429:
                    delay = 2 ** (attempt + 1) + random.uniform(1, 3)
                    logger.warning(f"WB 429, retry {attempt + 1}/{MAX_RETRIES} after {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                response.raise_for_status()
                data = response.json()
                break
            else:
                logger.error(f"WB search failed after {MAX_RETRIES} retries for '{query}'")
                return []

        # v18: products are at top level, not under "data"
        items = data.get("products", []) or data.get("data", {}).get("products", [])

        products: list[Product] = []
        for item in items:
            # v18: prices are in sizes[].price; fall back to top-level fields
            sale_price = item.get("salePriceU", 0)
            orig_price = item.get("priceU", 0)
            sizes = item.get("sizes", [])
            if sizes and "price" in sizes[0]:
                price_info = sizes[0]["price"]
                sale_price = price_info.get("product", sale_price)
                orig_price = price_info.get("basic", orig_price)

            product = Product(
                nm_id=item["id"],
                name=item.get("name", ""),
                brand=item.get("brand", ""),
                price_rub=sale_price // 100,
                original_price_rub=orig_price // 100,
                discount_pct=item.get("sale", 0),
                rating=item.get("rating", 0),
                feedbacks=item.get("feedbacks", 0),
                category=query,
                image_urls=self._build_image_urls(
                    item["id"], item.get("pics", 1)
                ),
            )
            products.append(product)

        await asyncio.sleep(random.uniform(1, 3))

        return products

    @staticmethod
    def _build_image_urls(nm_id: int, pics_count: int) -> list[str]:
        """Формирует URL-ы изображений товара на CDN WB."""
        vol = nm_id // 100000
        part = nm_id // 1000

        basket = "27"
        for upper_bound, suffix in _BASKET_RANGES:
            if vol <= upper_bound:
                basket = suffix
                break

        urls: list[str] = []
        for i in range(1, min(pics_count, 4) + 1):
            url = (
                f"https://basket-{basket}.wbbasket.ru/"
                f"vol{vol}/part{part}/{nm_id}/images/big/{i}.webp"
            )
            urls.append(url)

        return urls
