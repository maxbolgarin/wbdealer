from aiogram import Bot
from aiogram.types import BufferedInputFile


class TelegramPublisher:
    def __init__(self, bot: Bot, chat_id: str) -> None:
        self.bot = bot
        self.chat_id = chat_id

    async def publish_post(self, photo_bytes: bytes, caption: str) -> int:
        photo = BufferedInputFile(file=photo_bytes, filename="collage.jpg")
        message = await self.bot.send_photo(
            chat_id=self.chat_id,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
        )
        return message.message_id

    @staticmethod
    def format_post(
        title: str,
        products: list[dict],
        channel_name: str = "Мужской Wildberries",
    ) -> str:
        lines = [f"<b>{title}</b>", ""]

        for p in products:
            nm_id = p["nm_id"]
            name = p["display_name"]
            emoji = p["emoji_rating"]
            price = p["price_rub"]
            url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
            lines.append(f'» {name}: <a href="{url}">{nm_id}</a> {emoji} {price}₽')

        lines.append("")
        lines.append("— — — — — — — — —")
        lines.append("")
        lines.append("👍 - Топ")
        lines.append("👎 - Не очень")
        lines.append("😱 - Дорого")
        lines.append("")
        lines.append("— — — — — — — — — — —")
        lines.append("")
        lines.append(f"✏️ {channel_name}")

        return "\n".join(lines)
