from sqlalchemy import select, text

from src.db.models.keyword_analysis import KeywordAnalysis
from src.db.repositories.base import BaseRepository


class KeywordRepository(BaseRepository[KeywordAnalysis]):
    model = KeywordAnalysis

    async def search(self, q: str, limit: int = 20) -> list[KeywordAnalysis]:
        stmt = (
            select(KeywordAnalysis)
            .where(KeywordAnalysis.keyword.ilike(f"%{q}%"))
            .order_by(KeywordAnalysis.sv_estimated.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def search_trigram(self, q: str, limit: int = 20) -> list[KeywordAnalysis]:
        """pg_trgm を使った類似検索（インデックス活用）。"""
        stmt = (
            select(KeywordAnalysis)
            .where(text("keyword % :q").bindparams(q=q))
            .order_by(text("similarity(keyword, :q) DESC").bindparams(q=q))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, kw: KeywordAnalysis) -> KeywordAnalysis:
        existing = await self.find_by_id(kw.keyword)
        if existing is None:
            self._session.add(kw)
            await self._session.flush()
            return kw
        for field in ("sv_merchant_words", "sv_autocomplete_score", "sv_helium10",
                      "sv_estimated", "sv_confidence", "sv_note", "competition",
                      "book_count", "avg_bsr", "trend", "related_keywords", "top_asins",
                      "sv_updated_at"):
            val = getattr(kw, field, None)
            if val is not None:
                setattr(existing, field, val)
        await self._session.flush()
        return existing
