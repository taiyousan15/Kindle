from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class BSRHistory(Base):
    __tablename__ = "bsr_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asin: Mapped[str] = mapped_column(
        String(10), ForeignKey("kindle_books.asin"), nullable=False
    )
    bsr: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    estimated_daily_sales: Mapped[int | None] = mapped_column(Integer)
    data_source: Mapped[str] = mapped_column(String(20), default="keepa")

    book = relationship("KindleBook", back_populates="bsr_history")
