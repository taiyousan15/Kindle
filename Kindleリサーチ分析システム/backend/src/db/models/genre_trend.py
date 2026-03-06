from datetime import datetime

from sqlalchemy import ARRAY, CheckConstraint, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class GenreTrend(Base):
    __tablename__ = "genre_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    genre: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    avg_bsr: Mapped[int | None] = mapped_column(Integer)
    median_bsr: Mapped[int | None] = mapped_column(Integer)
    book_count: Mapped[int | None] = mapped_column(Integer)
    top_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    target_demo: Mapped[str | None] = mapped_column(Text)
    trend_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "period IN ('daily','weekly','monthly','halfyear')", name="ck_period"
        ),
        CheckConstraint(
            "trend_score BETWEEN 0 AND 1", name="ck_trend_score"
        ),
    )
