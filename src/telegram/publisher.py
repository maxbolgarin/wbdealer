from aiogram import Bot
from aiogram.types import BufferedInputFile

# Default Unicode emoji, used when custom emoji IDs are not configured
DEFAULT_EMOJI = {
    "top": "💰",
    "good": "👍",
    "bad": "👎",
    "expensive": "😱",
}


def _emoji(unicode_fallback: str, custom_id: str) -> str:
    """Return custom tg-emoji tag if ID is set, otherwise Unicode fallback."""
    if custom_id:
        return f'<tg-emoji emoji-id="{custom_id}">{unicode_fallback}</tg-emoji>'
    return unicode_fallback


class TelegramPublisher:
    def __init__(self, bot: Bot, chat_id: str, emoji_ids: dict[str, str] | None = None) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.emoji_ids = emoji_ids or {}

    async def publish_post(self, photo_bytes: bytes, caption: str) -> int:
        photo = BufferedInputFile(file=photo_bytes, filename="collage.jpg")
        message = await self.bot.send_photo(
            chat_id=self.chat_id,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
        )
        return message.message_id

    def format_post(
        self,
        title: str,
        products: list[dict],
        channel_name: str = "Мужской Wildberries",
        channel_url: str = "",
    ) -> str:
        e_top = _emoji(DEFAULT_EMOJI["top"], self.emoji_ids.get("top", ""))
        e_good = _emoji(DEFAULT_EMOJI["good"], self.emoji_ids.get("good", ""))
        e_bad = _emoji(DEFAULT_EMOJI["bad"], self.emoji_ids.get("bad", ""))
        e_expensive = _emoji(DEFAULT_EMOJI["expensive"], self.emoji_ids.get("expensive", ""))

        # Map AI emoji ratings to configured emoji
        emoji_map = {"💰": e_top, "👍": e_good, "👎": e_bad, "😱": e_expensive}

        lines = [f"<b>{title}</b>", ""]

        for p in products:
            nm_id = p["nm_id"]
            name = p["display_name"]
            raw_emoji = p["emoji_rating"]
            emoji = emoji_map.get(raw_emoji, raw_emoji)
            price = p["price_rub"]
            url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
            lines.append(f'»  {name}: <a href="{url}">{nm_id}</a> {emoji} {price}₽')

        lines.append("")
        lines.append("— — — — — — —")
        lines.append("")
        lines.append(f"<blockquote>{e_good} - Топ")
        lines.append(f"{e_bad} - Не очень")
        lines.append(f"{e_expensive} - Дорого</blockquote>")
        lines.append("")
        lines.append("— — — — — — — — —")
        lines.append("")
        if channel_url:
            lines.append(f'✏️ <a href="{channel_url}">{channel_name}</a>')
        else:
            lines.append(f"✏️ {channel_name}")

        return "\n".join(lines)
