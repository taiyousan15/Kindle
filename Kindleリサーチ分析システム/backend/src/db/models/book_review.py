from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class BookReview(Base):
    __tablename__ = "book_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asin: Mapped[str] = mapped_column(
        String(10), ForeignKey("kindle_books.asin"), nullable=False
    )
    review_id: Mapped[str | None] = mapped_column(Text, unique=True)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    body: Mapped[str | None] = mapped_column(Text)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0)
    reviewer_type: Mapped[str | None] = mapped_column(String(20))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sentiment: Mapped[str | None] = mapped_column(String(10))
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    book = relationship("KindleBook", back_populates="reviews")
