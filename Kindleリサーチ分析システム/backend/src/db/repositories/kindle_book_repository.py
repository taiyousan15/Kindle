from sqlalchemy import select

from src.db.models.kindle_book import KindleBook
from src.db.repositories.base import BaseRepository


class KindleBookRepository(BaseRepository[KindleBook]):
    model = KindleBook

    async def find_by_genre(self, genre: str, limit: int = 50) -> list[KindleBook]:
        stmt = (
            select(KindleBook)
            .where(KindleBook.genre == genre)
            .order_by(KindleBook.updated_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_asins(self, asins: list[str]) -> list[KindleBook]:
        stmt = select(KindleBook).where(KindleBook.asin.in_(asins))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, book: KindleBook) -> KindleBook:
        existing = await self.find_by_id(book.asin)
        if existing is None:
            self._session.add(book)
            await self._session.flush()
            return book
        # フィールドを更新（immutableパターン: 既存オブジェクトの属性を上書き）
        for field in ("title", "subtitle", "author", "publisher", "published_date",
                      "genre", "sub_genre", "price", "kindle_unlimited", "cover_image_url",
                      "review_count", "average_rating", "page_count", "description", "keywords"):
            val = getattr(book, field, None)
            if val is not None:
                setattr(existing, field, val)
        await self._session.flush()
        return existing
