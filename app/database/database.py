"""Database initialization and async session management."""

import logging
from typing import AsyncGenerator

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import (  # noqa: F401
    Article,
    ArticleCategory,
    Base,
    Category,
    NotificationLog,
    SavedArticle,
    Source,
    UserLearningProgress,
    UserPreference,
    UserWatchlist,
)

logger = logging.getLogger(__name__)

# STEM categories registry
DEFAULT_CATEGORIES = [
    ("Artificial Intelligence", "ai", "AI research, models, generative AI, LLMs"),
    ("Machine Learning", "machine-learning", "Algorithms, neural networks, deep learning"),
    ("Robotics", "robotics", "Humanoids, autonomous systems, kinematics, drones"),
    ("Computer Science", "computer-science", "Algorithms, theory, data structures"),
    ("Software Engineering", "software-engineering", "Architecture, systems, DevOps, best practices"),
    ("Cybersecurity", "cybersecurity", "InfoSec, cryptography, privacy, vulnerabilities"),
    ("Electronics", "electronics", "Circuits, microelectronics, semiconductors, chips"),
    ("Embedded Systems", "embedded-systems", "Firmware, microcontrollers, ARM, RISC-V"),
    ("Internet of Things", "iot", "Connected devices, sensors, smart systems"),
    ("Mechanical Engineering", "mechanical-engineering", "CAD, robotics mechanics, dynamics, thermodynamics"),
    ("Electrical Engineering", "electrical-engineering", "Power systems, signal processing, grid"),
    ("Biotechnology", "biotechnology", "CRISPR, bioengineering, synthetic biology, genetics"),
    ("Physics", "physics", "Quantum mechanics, astrophysics, particle physics"),
    ("Chemistry", "chemistry", "Materials science, molecular biology, nano-chemistry"),
    ("Mathematics", "mathematics", "Applied math, statistics, cryptography, topology"),
    ("Space Technology", "space-technology", "Aerospace, rocketry, satellites, exploration"),
    ("Renewable Energy", "renewable-energy", "Solar, wind, battery storage, clean tech"),
    ("STEM Education", "stem-education", "Pedagogy, learning tools, tutorials, student guides"),
    ("Emerging Technologies", "emerging-tech", "Brain-computer interfaces, quantum computing, fusion"),
]

# Initial reliable RSS & API sources verified on real networks
INITIAL_SOURCES = [
    ("TechCrunch", "techcrunch", "https://techcrunch.com/feed/", "rss"),
    ("The Verge", "theverge", "https://www.theverge.com/rss/index.xml", "rss"),
    ("MIT Technology Review", "mit-tech-review", "https://www.technologyreview.com/feed/", "rss"),
    ("IEEE Spectrum", "ieee-spectrum", "https://spectrum.ieee.org/feeds/feed.rss", "rss"),
    (
        "arXiv AI",
        "arxiv-ai",
        "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=15",
        "arxiv",
    ),
    (
        "arXiv Robotics",
        "arxiv-robotics",
        "https://export.arxiv.org/api/query?search_query=cat:cs.RO&sortBy=submittedDate&sortOrder=descending&max_results=15",
        "arxiv",
    ),
    (
        "arXiv Computer Science",
        "arxiv-cs",
        "https://export.arxiv.org/api/query?search_query=cat:cs.SE&sortBy=submittedDate&sortOrder=descending&max_results=15",
        "arxiv",
    ),
    (
        "GitHub Trending",
        "github-trending",
        "https://api.github.com/search/repositories?q=stars:>1000+topic:artificial-intelligence&sort=stars&order=desc&per_page=15",
        "github",
    ),
]

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Retrieve or create the singleton AsyncEngine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
        )

        # Enforce foreign key constraints in SQLite
        if "sqlite" in settings.database_url:

            @event.listens_for(_engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve or create the singleton async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session context."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


def _migrate_sqlite_schema(conn) -> None:
    """Safely apply non-destructive SQLite column additions for backward compatibility."""
    try:
        # 1. Sources migration
        res = conn.exec_driver_sql("PRAGMA table_info(sources)")
        sources_cols = {row[1] for row in res.fetchall()}
        if sources_cols:
            if "last_collected_at" not in sources_cols:
                conn.exec_driver_sql("ALTER TABLE sources ADD COLUMN last_collected_at TIMESTAMP")
                logger.info("Migrated schema: added sources.last_collected_at")
            if "last_error" not in sources_cols:
                conn.exec_driver_sql("ALTER TABLE sources ADD COLUMN last_error TEXT")
                logger.info("Migrated schema: added sources.last_error")
            if "error_count" not in sources_cols:
                conn.exec_driver_sql("ALTER TABLE sources ADD COLUMN error_count INTEGER DEFAULT 0")
                logger.info("Migrated schema: added sources.error_count")

        # 2. User preferences migration
        res = conn.exec_driver_sql("PRAGMA table_info(user_preferences)")
        pref_cols = {row[1] for row in res.fetchall()}
        if pref_cols:
            if "quiet_hours_start" not in pref_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE user_preferences ADD COLUMN quiet_hours_start VARCHAR(10) DEFAULT '22:00'"
                )
                logger.info("Migrated schema: added user_preferences.quiet_hours_start")
            if "quiet_hours_end" not in pref_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE user_preferences ADD COLUMN quiet_hours_end VARCHAR(10) DEFAULT '07:00'"
                )
                logger.info("Migrated schema: added user_preferences.quiet_hours_end")
            if "high_impact_alerts_enabled" not in pref_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE user_preferences ADD COLUMN high_impact_alerts_enabled BOOLEAN DEFAULT 1"
                )
                logger.info("Migrated schema: added user_preferences.high_impact_alerts_enabled")
            if "weekly_report_enabled" not in pref_cols:
                conn.exec_driver_sql("ALTER TABLE user_preferences ADD COLUMN weekly_report_enabled BOOLEAN DEFAULT 1")
                logger.info("Migrated schema: added user_preferences.weekly_report_enabled")
    except Exception as exc:
        logger.warning("Schema migration warning (ignored for non-sqlite or fresh db): %s", exc)


async def init_db() -> None:
    """Initialize database tables and seed baseline categories & sources."""
    engine = get_engine()
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite_schema)

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Seed categories
        existing_cats = await session.execute(select(Category.slug))
        existing_cat_slugs = set(existing_cats.scalars().all())

        new_categories = [
            Category(name=name, slug=slug, description=desc)
            for name, slug, desc in DEFAULT_CATEGORIES
            if slug not in existing_cat_slugs
        ]
        if new_categories:
            session.add_all(new_categories)
            logger.info("Seeded %d STEM categories", len(new_categories))

        # Seed initial sources
        existing_sources = await session.execute(select(Source.slug))
        existing_source_slugs = set(existing_sources.scalars().all())

        new_sources = [
            Source(name=name, slug=slug, url=url, source_type=stype, is_active=True)
            for name, slug, url, stype in INITIAL_SOURCES
            if slug not in existing_source_slugs
        ]
        if new_sources:
            session.add_all(new_sources)
            logger.info("Seeded %d initial sources", len(new_sources))

        await session.commit()
    logger.info("Database initialized successfully.")
