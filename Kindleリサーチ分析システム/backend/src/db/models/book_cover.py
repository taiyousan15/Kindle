from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class BookCover(Base):
    __tablename__ = "book_covers"

    asin: Mapped[str] = mapped_column(
        String(10), ForeignKey("kindle_books.asin"), primary_key=True
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    primary_colors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    font_style: Mapped[str | None] = mapped_column(String(50))
    layout: Mapped[str | None] = mapped_column(String(50))
    mood: Mapped[str | None] = mapped_column(String(50))
    analysis_json: Mapped[dict | None] = mapped_column(JSONB)
    ctr_score: Mapped[int | None] = mapped_column(SmallInteger)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    book = relationship("KindleBook", back_populates="cover")
