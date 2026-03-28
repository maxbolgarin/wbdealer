from dataclasses import dataclass, field


@dataclass
class Product:
    nm_id: int                    # Артикул (nmId) — главный идентификатор
    name: str                     # Название товара
    brand: str                    # Бренд
    price_rub: int                # Текущая цена в рублях (с учётом скидки)
    original_price_rub: int       # Цена без скидки
    discount_pct: int             # Процент скидки
    rating: float                 # Рейтинг товара (0-5)
    feedbacks: int                # Количество отзывов
    category: str                 # Категория/предмет
    image_urls: list[str] = field(default_factory=list)  # URL-ы картинок
    wb_url: str = ""              # Ссылка на страницу товара

    @property
    def short_url(self) -> str:
        """Ссылка формата wildberries.ru/catalog/{nm_id}/detail.aspx"""
        return f"https://www.wildberries.ru/catalog/{self.nm_id}/detail.aspx"

    @property
    def price_quality_label(self) -> str:
        """Эмодзи-рейтинг: 👍 Топ / 👎 Не очень / 😱 Дорого"""
        if self.rating >= 4.5 and self.discount_pct >= 30:
            return "👍"
        elif self.price_rub > 5000:
            return "😱"
        elif self.rating < 4.2:
            return "👎"
        else:
            return "👍"
