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
    """User preferences for digest, notifications, quiet hours, and domain subscriptions."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    preferred_categories: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    digest_time: Mapped[str] = mapped_column(String(10), default="08:00", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(10), default="22:00", nullable=False)
    quiet_hours_end: Mapped[str] = mapped_column(String(10), default="07:00", nullable=False)
    high_impact_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    search_history_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UserWatchlist(Base):
    """Keywords and emerging technology watchlists tracked by users."""

    __tablename__ = "user_watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "keyword", name="uq_user_watchlist_keyword"),)

    def __repr__(self) -> str:
        return f"<UserWatchlist(user_id={self.user_id}, keyword='{self.keyword}', matches={self.match_count})>"


class NotificationLog(Base):
    """Delivery log tracking automated notifications to prevent duplicates and monitor telemetry."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    article_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="delivered", nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    article: Mapped[Optional["Article"]] = relationship("Article")

    __table_args__ = (
        UniqueConstraint("user_id", "article_id", "notification_type", name="uq_user_article_notification"),
    )

    def __repr__(self) -> str:
        return f"<NotificationLog(user_id={self.user_id}, type='{self.notification_type}', status='{self.status}')>"


class UserLearningProgress(Base):
    """Tracks educational progress, quizzes completed, and scores per user and topic."""

    __tablename__ = "user_learning_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(30), default="beginner", nullable=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quizzes_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quiz_score_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quiz_score_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_studied_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("user_id", "topic", name="uq_user_learning_topic"),)

    def __repr__(self) -> str:
        return f"<UserLearningProgress(user_id={self.user_id}, topic='{self.topic}', level='{self.level}')>"


class User(Base):
    """Registered platform user record with role-based access and status."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}', admin={self.is_admin})>"
        )


class UserFeedback(Base):
    """User feedback, issue reports, and platform suggestions."""

    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<UserFeedback(user_id={self.user_id}, category='{self.category}')>"


class Opportunity(Base):
    """Verified academic opportunities (scholarships, fellowships, internships, research grants, competitions)."""

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    opportunity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # scholarship, fellowship, internship, research_opp, grant, competition
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(
        String(50), default="university", nullable=False
    )  # university, government, foundation, corporate
    official_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    application_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    eligible_nationalities: Mapped[str] = mapped_column(String(500), default="All", nullable=False)
    study_level: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # undergraduate, masters, phd, postdoctoral, all_levels
    stem_fields: Mapped[str] = mapped_column(String(500), default="All STEM", nullable=False)
    funding_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # fully_funded, partially_funded, tuition_waiver, stipend_only, prize
    benefits: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    eligibility_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    required_documents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_opens_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    is_rolling: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="open", nullable=False, index=True
    )  # open, upcoming, closed, expired
    verification_tier: Mapped[str] = mapped_column(
        String(50), default="officially_verified", nullable=False, index=True
    )  # officially_verified, secondary_verified, unverified_submission
    source_attribution: Mapped[str] = mapped_column(String(255), nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    reports: Mapped[List["OpportunityReport"]] = relationship(
        "OpportunityReport", back_populates="opportunity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_opp_deadline_status", "application_deadline", "status"),
        Index("idx_opp_type_level", "opportunity_type", "study_level"),
    )

    def __repr__(self) -> str:
        return f"<Opportunity(title='{self.title[:25]}...', type='{self.opportunity_type}')>"


class UniversityProfile(Base):
    """Accredited universities, official admission portals, guidelines, and funding."""

    __tablename__ = "university_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    official_portal_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    admissions_portal_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    admission_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_procedures: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tuition_and_funding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    international_guidelines_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    academic_regulations_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    research_opportunities_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UniversityProfile(name='{self.name}', country='{self.country}')>"


class AcademicResource(Base):
    """Open educational resources, official university lecture materials, textbooks, and tutorials."""

    __tablename__ = "academic_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # free_course, lecture_materials, research_repository, programming_tutorial, open_textbook
    stem_discipline: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider_institution: Mapped[str] = mapped_column(String(255), nullable=False)
    official_access_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    license_type: Mapped[str] = mapped_column(
        String(100), default="Open Access", nullable=False
    )  # Creative Commons, MIT, Open Access, Public Domain
    is_copyright_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AcademicResource(title='{self.title[:30]}...', type='{self.resource_type}')>"


class OpportunityReport(Base):
    """Community reports for incorrect, expired, broken, or fraudulent listings and submissions."""

    __tablename__ = "opportunity_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    opportunity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=True
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # expired, broken_link, inaccurate, fraudulent, submission
    details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False, index=True
    )  # pending_review, verified_resolved, dismissed
    reviewed_by_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    opportunity: Mapped[Optional["Opportunity"]] = relationship("Opportunity", back_populates="reports")

    def __repr__(self) -> str:
        return f"<OpportunityReport(id={self.id}, type='{self.report_type}', status='{self.status}')>"


class SearchQueryLog(Base):
    """User search history where users consent to telemetry and repeat retrieval."""

    __tablename__ = "search_query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    query: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    results_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<SearchQueryLog(query='{self.query}', count={self.results_count})>"
