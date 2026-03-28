import asyncio
import random
import logging
from src.wb.search import WBSearchClient
from src.wb.categories import CATEGORIES
from src.ai.curator import AICurator
from src.media.collage import CollageBuilder
from src.telegram.publisher import TelegramPublisher
from src.storage.db import Storage
from src.config import Settings

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, config: Settings, search_client: WBSearchClient, curator: AICurator,
                 collage_builder: CollageBuilder, publisher: TelegramPublisher, storage: Storage):
        self.config = config
        self.search = search_client
        self.curator = curator
        self.collage = collage_builder
        self.publisher = publisher
        self.storage = storage
        self._lock = asyncio.Lock()

    async def run(self) -> str:
        """Full pipeline cycle. Returns status message. Uses lock to prevent concurrent runs."""
        if self._lock.locked():
            return "Pipeline already running, skipping"
        async with self._lock:
            return await self._execute()

    async def _execute(self) -> str:
        """The actual pipeline logic."""
        try:
            # 1. Select category (avoid recent ones)
            category = await self._select_category()
            logger.info(f"Selected category: {category['name']}")

            # 2. Search products across all queries in category
            all_products = []
            for query in category["queries"]:
                products = await self.search.search(
                    query=query, limit=50, sort="popular",
                    min_rating=int(self.config.min_rating),
                    price_range=category.get("price_range"),
                )
                all_products.extend(products)
            logger.info(f"Found {len(all_products)} candidates")

            # 3. Filter: dedup + basic filters + check published
            filtered = []
            seen_ids = set()
            for p in all_products:
                if p.nm_id in seen_ids:
                    continue
                if await self.storage.is_published(p.nm_id):
                    continue
                if p.rating < self.config.min_rating:
                    continue
                if p.feedbacks < self.config.min_feedbacks:
                    continue
                seen_ids.add(p.nm_id)
                filtered.append(p)
            logger.info(f"After filtering: {len(filtered)}")

            if len(filtered) < self.config.products_per_post:
                return f"Not enough products ({len(filtered)}) for category {category['name']}"

            # 4. AI curation: select best 6
            curated = await self.curator.curate_post(filtered[:30], category)

            # 5. Build collage
            product_map = {p.nm_id: p for p in filtered}
            image_urls = []
            curated_full = []
            for item in curated["products"]:
                nm_id = item["nm_id"]
                if nm_id in product_map:
                    product = product_map[nm_id]
                    # Use image #2 (index 1) — first image is usually infographic
                    img_idx = 1 if len(product.image_urls) > 1 else 0
                    image_urls.append(product.image_urls[img_idx])
                    curated_full.append({**item, "price_rub": product.price_rub})

            collage_bytes = await self.collage.build(image_urls)

            # 6. Format and publish
            caption = self.publisher.format_post(title=curated["title"], products=curated_full)
            message_id = await self.publisher.publish_post(collage_bytes, caption)

            # 7. Record in history
            published_ids = [p["nm_id"] for p in curated_full]
            await self.storage.mark_published(published_ids, category["name"], message_id)

            return f"Published: {curated['title']} ({len(curated_full)} products)"

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            return f"Error: {e}"

    async def _select_category(self) -> dict:
        recent = await self.storage.get_recent_categories(n=len(CATEGORIES) // 2)
        available = [c for c in CATEGORIES if c["name"] not in recent]
        if not available:
            available = CATEGORIES
        return random.choice(available)
