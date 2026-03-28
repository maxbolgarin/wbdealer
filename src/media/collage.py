import asyncio
import io
import logging

import httpx
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class CollageBuilder:
    def __init__(self, settings) -> None:
        self.width = settings.collage_width
        self.height = settings.collage_height
        self.cols = settings.collage_columns
        self.rows = settings.collage_rows
        self.bg_color = settings.collage_bg_color
        self.padding = settings.collage_padding
        self.cell_padding = settings.collage_cell_padding
        self.cell_radius = settings.collage_cell_radius

    async def build(self, image_urls: list[str]) -> bytes:
        images = await self._download_images(image_urls)

        canvas = Image.new("RGBA", (self.width, self.height), self.bg_color)

        cell_w = (
            self.width - self.padding * 2 - self.cell_padding * (self.cols - 1)
        ) // self.cols
        cell_h = (
            self.height - self.padding * 2 - self.cell_padding * (self.rows - 1)
        ) // self.rows

        for idx, img in enumerate(images):
            if idx >= self.cols * self.rows:
                break

            row = idx // self.cols
            col = idx % self.cols

            x = self.padding + col * (cell_w + self.cell_padding)
            y = self.padding + row * (cell_h + self.cell_padding)

            cell = self._create_rounded_cell(img, cell_w, cell_h)
            canvas.paste(cell, (x, y), cell)

        rgb_canvas = canvas.convert("RGB")
        buffer = io.BytesIO()
        rgb_canvas.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()

    def _create_rounded_cell(
        self, image: Image.Image, width: int, height: int
    ) -> Image.Image:
        cell = Image.new("RGBA", (width, height), (255, 255, 255, 255))

        # Crop-to-fill: resize maintaining aspect ratio then center crop
        img_ratio = image.width / image.height
        cell_ratio = width / height

        if img_ratio > cell_ratio:
            # Image is wider — fit by height, crop width
            new_h = height
            new_w = int(height * img_ratio)
        else:
            # Image is taller — fit by width, crop height
            new_w = width
            new_h = int(width / img_ratio)

        resized = image.resize((new_w, new_h), Image.LANCZOS)

        # Center crop
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        cropped = resized.crop((left, top, left + width, top + height))

        cell.paste(cropped, (0, 0))

        # Create rounded rectangle mask
        mask = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            [(0, 0), (width - 1, height - 1)],
            radius=self.cell_radius,
            fill=255,
        )

        result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        result.paste(cell, (0, 0), mask)
        return result

    @staticmethod
    async def _download_images(urls: list[str]) -> list[Image.Image]:
        """Download images sequentially to avoid CDN rate limits."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/avif,image/*,*/*;q=0.8",
            "Referer": "https://www.wildberries.ru/",
        }
        results: list[Image.Image] = []

        async with httpx.AsyncClient(
            headers=headers, timeout=15.0, follow_redirects=True,
        ) as client:
            for idx, url in enumerate(urls):
                img = None
                # Try original URL, then fallback to image 1 (always exists), then others
                attempt_urls = [url]
                base = url.rsplit("/", 1)[0]
                for i in [1, 2, 3, 4]:
                    fallback = base + f"/{i}.webp"
                    if fallback != url and fallback not in attempt_urls:
                        attempt_urls.append(fallback)

                for attempt_url in attempt_urls:
                    for retry in range(3):
                        try:
                            resp = await client.get(attempt_url)
                            if resp.status_code == 200 and len(resp.content) > 500:
                                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                                break
                            elif resp.status_code == 429:
                                await asyncio.sleep(2)
                            else:
                                break
                        except Exception as e:
                            logger.warning(f"Image download error {attempt_url}: {e}")
                            await asyncio.sleep(1)
                    if img:
                        break

                if img:
                    logger.info(f"Image {idx + 1}/{len(urls)}: OK")
                else:
                    logger.warning(f"Image {idx + 1}/{len(urls)}: FAILED, using placeholder")
                    img = Image.new("RGBA", (400, 400), (200, 200, 200, 255))
                results.append(img)

                # Small delay between downloads to avoid rate limits
                if idx < len(urls) - 1:
                    await asyncio.sleep(0.5)

        return results
