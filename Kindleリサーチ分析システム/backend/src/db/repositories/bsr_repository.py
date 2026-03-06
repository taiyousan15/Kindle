from datetime import datetime, timedelta

from sqlalchemy import select

from src.db.models.bsr_history import BSRHistory
from src.db.repositories.base import BaseRepository


class BSRRepository(BaseRepository[BSRHistory]):
    model = BSRHistory

    async def find_by_asin(
        self,
        asin: str,
        days: int = 180,
    ) -> list[BSRHistory]:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(BSRHistory)
            .where(BSRHistory.asin == asin, BSRHistory.recorded_at >= since)
            .order_by(BSRHistory.recorded_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_latest(self, asin: str) -> BSRHistory | None:
        stmt = (
            select(BSRHistory)
            .where(BSRHistory.asin == asin)
            .order_by(BSRHistory.recorded_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_insert(self, records: list[BSRHistory]) -> int:
        for r in records:
            self._session.add(r)
        await self._session.flush()
        return len(records)
