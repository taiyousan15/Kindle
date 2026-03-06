from datetime import datetime

from sqlalchemy import ARRAY, CheckConstraint, DateTime, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class KeywordAnalysis(Base):
    __tablename__ = "keyword_analyses"

    keyword: Mapped[str] = mapped_column(Text, primary_key=True)
    sv_merchant_words: Mapped[int | None] = mapped_column(Integer)
    sv_autocomplete_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    sv_helium10: Mapped[int | None] = mapped_column(Integer)
    sv_estimated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sv_confidence: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
    )
    sv_note: Mapped[str | None] = mapped_column(Text)
    competition: Mapped[str | None] = mapped_column(String(10))
    book_count: Mapped[int | None] = mapped_column(Integer)
    avg_bsr: Mapped[int | None] = mapped_column(Integer)
    trend: Mapped[str | None] = mapped_column(String(10))
    related_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    top_asins: Mapped[list[str] | None] = mapped_column(ARRAY(String(10)))
    last_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sv_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("sv_confidence IN (1,2,3)", name="ck_sv_confidence"),
        CheckConstraint("competition IN ('low','medium','high')", name="ck_competition"),
        CheckConstraint("trend IN ('rising','stable','declining')", name="ck_trend"),
    )
