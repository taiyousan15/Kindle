from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, Date, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class KindleBook(Base):
    __tablename__ = "kindle_books"

    asin: Mapped[str] = mapped_column(String(10), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str | None] = mapped_column(Text)
    author: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    publisher: Mapped[str | None] = mapped_column(Text)
    published_date: Mapped[datetime | None] = mapped_column(Date)
    genre: Mapped[str | None] = mapped_column(String(100))
    sub_genre: Mapped[str | None] = mapped_column(String(100))
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    kindle_unlimited: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    review_count: Mapped[int] = mapped_column(default=0)
    average_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    page_count: Mapped[int | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    title_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    desc_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bsr_history = relationship("BSRHistory", back_populates="book", lazy="dynamic")
    cover = relationship("BookCover", back_populates="book", uselist=False)
    reviews = relationship("BookReview", back_populates="book", lazy="dynamic")
