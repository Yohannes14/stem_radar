"""SQLAlchemy ORM models for the STEM RADAR platform."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Source(Base):
    """Information sources (RSS feeds, arXiv APIs, GitHub, etc.)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="rss", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    articles: Mapped[List["Article"]] = relationship("Article", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Source(name='{self.name}', slug='{self.slug}', type='{self.source_type}')>"


class Category(Base):
    """STEM categories for classification and filtering."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    articles: Mapped[List["Article"]] = relationship(
        "Article", secondary="article_categories", back_populates="categories"
    )

    def __repr__(self) -> str:
        return f"<Category(name='{self.name}', slug='{self.slug}')>"


class ArticleCategory(Base):
    """Many-to-many relationship linking articles to STEM categories with confidence scores."""

    __tablename__ = "article_categories"

    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class Article(Base):
    """Normalized article / research paper record."""

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False, index=True)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped["Source"] = relationship("Source", back_populates="articles")

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    categories: Mapped[List["Category"]] = relationship(
        "Category", secondary="article_categories", back_populates="articles"
    )
    saved_by: Mapped[List["SavedArticle"]] = relationship(
        "SavedArticle", back_populates="article", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_articles_source_published", "source_id", "published_at"),)

    def __repr__(self) -> str:
        return f"<Article(title='{self.title[:30]}...', source_id={self.source_id})>"


class SavedArticle(Base):
    """User bookmarks / saved articles."""

    __tablename__ = "saved_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    article: Mapped["Article"] = relationship("Article", back_populates="saved_by")

    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article_saved"),)


class UserPreference(Base):
    """User preferences for digest, notifications, and preferred categories."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    preferred_categories: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    digest_time: Mapped[str] = mapped_column(String(10), default="08:00", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
