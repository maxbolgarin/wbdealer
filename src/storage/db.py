import json

import asyncpg


class Storage:
    """PostgreSQL хранилище для учёта опубликованных товаров и постов."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def init(self) -> None:
        """Создаёт пул соединений и инициализирует таблицы."""
        self.pool = await asyncpg.create_pool(
            self.dsn, min_size=2, max_size=10
        )

        statements = [
            """
            CREATE TABLE IF NOT EXISTS published_products (
                nm_id BIGINT PRIMARY KEY,
                published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                category TEXT NOT NULL,
                post_id TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS posts (
                id BIGSERIAL PRIMARY KEY,
                published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                category TEXT NOT NULL,
                products_json JSONB NOT NULL,
                telegram_message_id BIGINT
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_published_at
                ON published_products(published_at)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_posts_category
                ON posts(category)
            """,
        ]

        async with self.pool.acquire() as conn:
            for stmt in statements:
                await conn.execute(stmt)

    async def close(self) -> None:
        """Закрывает пул соединений."""
        if self.pool:
            await self.pool.close()

    async def is_published(self, nm_id: int, days: int = 30) -> bool:
        """Проверяет, был ли товар опубликован за последние N дней."""
        row = await self.pool.fetchval(
            "SELECT 1 FROM published_products "
            "WHERE nm_id = $1 AND published_at > NOW() - make_interval(days => $2)",
            nm_id,
            days,
        )
        return row is not None

    async def mark_published(
        self,
        nm_ids: list[int],
        category: str,
        message_id: int | None = None,
    ) -> None:
        """Записывает опубликованные товары и создаёт запись поста."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for nm_id in nm_ids:
                    await conn.execute(
                        "INSERT INTO published_products (nm_id, category, post_id) "
                        "VALUES ($1, $2, $3) "
                        "ON CONFLICT (nm_id) DO UPDATE "
                        "SET published_at = NOW(), category = $2, post_id = $3",
                        nm_id,
                        category,
                        str(message_id) if message_id is not None else None,
                    )

                await conn.execute(
                    "INSERT INTO posts (category, products_json, telegram_message_id) "
                    "VALUES ($1, $2::jsonb, $3)",
                    category,
                    json.dumps(nm_ids),
                    message_id,
                )

    async def get_recent_categories(self, n: int = 5) -> list[str]:
        """Возвращает последние N категорий из постов."""
        rows = await self.pool.fetch(
            "SELECT category FROM posts ORDER BY published_at DESC LIMIT $1",
            n,
        )
        return [row["category"] for row in rows]

    async def get_stats(self) -> dict:
        """Возвращает статистику: кол-во постов, товаров, дата последнего поста."""
        async with self.pool.acquire() as conn:
            total_posts = await conn.fetchval(
                "SELECT COUNT(*) FROM posts"
            )
            total_products = await conn.fetchval(
                "SELECT COUNT(*) FROM published_products"
            )
            last_post_at = await conn.fetchval(
                "SELECT MAX(published_at) FROM posts"
            )

        return {
            "total_posts": total_posts or 0,
            "total_products": total_products or 0,
            "last_post_at": last_post_at.isoformat() if last_post_at else None,
        }
