import json

import openai

from src.ai.prompts import CURATION_PROMPT
from src.wb.product import Product


class AICurator:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def curate_post(
        self, products: list[Product], category: dict
    ) -> dict:
        products_data = [
            {
                "nm_id": p.nm_id,
                "name": p.name,
                "brand": p.brand,
                "price": p.price_rub,
                "original_price": p.original_price_rub,
                "discount": p.discount_pct,
                "rating": p.rating,
                "feedbacks": p.feedbacks,
            }
            for p in products
        ]

        prompt = CURATION_PROMPT.format(
            category_emoji=category["emoji"],
            category_name=category["name"],
            products_json=json.dumps(products_data, ensure_ascii=False, indent=2),
            count=6,
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.choices[0].message.content

        # Handle ```json ... ``` blocks
        if "```json" in text:
            text = text.split("```json", 1)[1]
            text = text.split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1]
            text = text.split("```", 1)[0]

        return json.loads(text.strip())
