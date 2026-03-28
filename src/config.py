from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str  # например "@wb_finds" или числовой ID канала/чата
    admin_user_id: int  # Telegram user ID для админ-команд

    # OpenRouter (LLM)
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-sonnet-4"

    # WB Search
    wb_search_base_url: str = "https://search.wb.ru/exactmatch/ru/common/v7/search"

    # Публикация
    posts_per_day: int = 3
    products_per_post: int = 6
    schedule_hours: list[int] = [9, 13, 18]  # MSK

    # Фильтры товаров
    min_rating: float = 4.0
    min_feedbacks: int = 10
    max_price_rub: int = 10000
    min_discount_pct: int = 15

    # Кастомные эмодзи Telegram (ID или пустая строка для дефолтных Unicode)
    emoji_top: str = ""       # 💰 — отличная цена
    emoji_good: str = ""      # 👍 — топ
    emoji_bad: str = ""       # 👎 — не очень
    emoji_expensive: str = "" # 😱 — дорого

    # Коллаж
    collage_width: int = 1080
    collage_height: int = 1080
    collage_columns: int = 3
    collage_rows: int = 2
    collage_bg_color: str = "#E8E8E8"
    collage_padding: int = 20
    collage_cell_padding: int = 10
    collage_cell_radius: int = 12

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "wbdealer"
    postgres_user: str = "wbdealer"
    postgres_password: str = "wbdealer"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
