import asyncio
import random

import httpx

from src.wb.product import Product

BASE_URL = "https://search.wb.ru/exactmatch/ru/common/v7/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.wildberries.ru",
    "Referer": "https://www.wildberries.ru/",
}

# (upper_bound, basket_suffix)
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
            "query": query,
            "resultset": "catalog",
            "limit": limit,
            "sort": sort,
            "dest": -1257786,
            "curr": "rub",
            "spp": 30,
        }

        if min_rating:
            params["frating"] = min_rating

        if price_range is not None:
            min_price, max_price = price_range
            params["priceU"] = f"{min_price * 100};{max_price * 100}"

        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("data", {}).get("products", [])

        products: list[Product] = []
        for item in items:
            product = Product(
                nm_id=item["id"],
                name=item.get("name", ""),
                brand=item.get("brand", ""),
                price_rub=item.get("salePriceU", 0) // 100,
                original_price_rub=item.get("priceU", 0) // 100,
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

        basket = "18"
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
