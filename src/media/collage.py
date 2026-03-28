import asyncio
import io

import httpx
from PIL import Image, ImageDraw


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
        async def _download_one(client: httpx.AsyncClient, url: str) -> Image.Image:
            # Try the given URL, then fallback to other image indices
            attempts = [url]
            # If URL ends with /1.webp, also try /2.webp, /3.webp
            for i in range(2, 5):
                attempts.append(url.rsplit("/", 1)[0] + f"/{i}.webp")

            for attempt_url in attempts:
                for retry in range(2):
                    try:
                        response = await client.get(attempt_url)
                        if response.status_code == 200 and len(response.content) > 100:
                            return Image.open(io.BytesIO(response.content)).convert("RGBA")
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)

            return Image.new("RGBA", (400, 400), (200, 200, 200, 255))

        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "Accept": "image/webp,image/avif,image/*,*/*;q=0.8",
                "Referer": "https://www.wildberries.ru/",
            },
            timeout=15.0,
            follow_redirects=True,
        ) as client:
            tasks = [_download_one(client, url) for url in urls]
            return await asyncio.gather(*tasks)
