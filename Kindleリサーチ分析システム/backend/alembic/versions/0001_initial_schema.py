"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-06 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector / timescaledb 拡張は init.sql で作成済みのため不要

    # kindle_books
    op.create_table(
        "kindle_books",
        sa.Column("asin", sa.String(10), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("subtitle", sa.Text),
        sa.Column("author", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("publisher", sa.Text),
        sa.Column("published_date", sa.Date),
        sa.Column("genre", sa.String(100)),
        sa.Column("sub_genre", sa.String(100)),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("kindle_unlimited", sa.Boolean, server_default="false"),
        sa.Column("cover_image_url", sa.Text),
        sa.Column("review_count", sa.Integer, server_default="0"),
        sa.Column("average_rating", sa.Numeric(3, 2)),
        sa.Column("page_count", sa.Integer),
        sa.Column("description", sa.Text),
        sa.Column("keywords", ARRAY(sa.Text)),
        # pgvector 型は生SQL で追加
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    # pgvector カラムを生SQL で追加（Alembicは Vector 型未対応）
    op.execute("ALTER TABLE kindle_books ADD COLUMN IF NOT EXISTS title_embedding vector(1536)")
    op.execute("ALTER TABLE kindle_books ADD COLUMN IF NOT EXISTS desc_embedding vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_kindle_books_title_embedding "
        "ON kindle_books USING ivfflat (title_embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # bsr_history
    op.create_table(
        "bsr_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("asin", sa.String(10), sa.ForeignKey("kindle_books.asin"), nullable=False),
        sa.Column("bsr", sa.Integer, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("estimated_daily_sales", sa.Integer),
        sa.Column("data_source", sa.String(20), server_default="'keepa'"),
    )
    op.create_index("idx_bsr_history_asin_recorded", "bsr_history", ["asin", "recorded_at"])
    # TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('bsr_history', 'recorded_at', if_not_exists => TRUE)"
    )

    # keyword_analyses
    op.create_table(
        "keyword_analyses",
        sa.Column("keyword", sa.Text, primary_key=True),
        sa.Column("sv_merchant_words", sa.Integer),
        sa.Column("sv_autocomplete_score", sa.Numeric(4, 2)),
        sa.Column("sv_helium10", sa.Integer),
        sa.Column("sv_estimated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sv_confidence", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("sv_note", sa.Text),
        sa.Column("competition", sa.String(10)),
        sa.Column("book_count", sa.Integer),
        sa.Column("avg_bsr", sa.Integer),
        sa.Column("trend", sa.String(10)),
        sa.Column("related_keywords", ARRAY(sa.Text)),
        sa.Column("top_asins", ARRAY(sa.String(10))),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("sv_updated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        "ALTER TABLE keyword_analyses ADD CONSTRAINT ck_sv_confidence "
        "CHECK (sv_confidence IN (1,2,3))"
    )
    op.execute(
        "ALTER TABLE keyword_analyses ADD CONSTRAINT ck_competition "
        "CHECK (competition IS NULL OR competition IN ('low','medium','high'))"
    )
    op.execute(
        "ALTER TABLE keyword_analyses ADD CONSTRAINT ck_trend "
        "CHECK (trend IS NULL OR trend IN ('rising','stable','declining'))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_keyword_analyses_keyword_trgm "
        "ON keyword_analyses USING gin (keyword gin_trgm_ops)"
    )

    # genre_trends
    op.create_table(
        "genre_trends",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("genre", sa.String(100), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("avg_bsr", sa.Integer),
        sa.Column("median_bsr", sa.Integer),
        sa.Column("book_count", sa.Integer),
        sa.Column("top_keywords", ARRAY(sa.Text)),
        sa.Column("target_demo", sa.Text),
        sa.Column("trend_score", sa.Numeric(4, 3)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "ALTER TABLE genre_trends ADD CONSTRAINT ck_period "
        "CHECK (period IN ('daily','weekly','monthly','halfyear'))"
    )
    op.execute(
        "ALTER TABLE genre_trends ADD CONSTRAINT ck_trend_score "
        "CHECK (trend_score IS NULL OR trend_score BETWEEN 0 AND 1)"
    )
    op.create_index("idx_genre_trends_genre_period", "genre_trends", ["genre", "period"])

    # book_covers
    op.create_table(
        "book_covers",
        sa.Column("asin", sa.String(10), sa.ForeignKey("kindle_books.asin"), primary_key=True),
        sa.Column("image_url", sa.Text, nullable=False),
        sa.Column("primary_colors", ARRAY(sa.Text)),
        sa.Column("font_style", sa.String(50)),
        sa.Column("layout", sa.String(50)),
        sa.Column("mood", sa.String(50)),
        sa.Column("analysis_json", JSONB),
        sa.Column("ctr_score", sa.SmallInteger),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # book_reviews
    op.create_table(
        "book_reviews",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("asin", sa.String(10), sa.ForeignKey("kindle_books.asin"), nullable=False),
        sa.Column("rating", sa.SmallInteger, nullable=False),
        sa.Column("review_text", sa.Text),
        sa.Column("helpful_votes", sa.Integer, server_default="0"),
        sa.Column("verified_purchase", sa.Boolean, server_default="false"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_book_reviews_asin", "book_reviews", ["asin"])

    # collection_jobs
    op.create_table(
        "collection_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("target_count", sa.Integer),
        sa.Column("processed_count", sa.Integer, server_default="0"),
        sa.Column("error_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("collection_jobs")
    op.drop_table("book_reviews")
    op.drop_table("book_covers")
    op.drop_table("genre_trends")
    op.drop_table("keyword_analyses")
    op.drop_table("bsr_history")
    op.drop_table("kindle_books")
