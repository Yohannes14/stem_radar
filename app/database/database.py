"""Database initialization and async session management."""

import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.core.taxonomy import DEFAULT_CATEGORIES
from app.database.models import (  # noqa: F401
    AcademicResource,
    Article,
    ArticleCategory,
    Base,
    Category,
    NotificationLog,
    Opportunity,
    OpportunityReport,
    SavedArticle,
    Source,
    UniversityProfile,
    User,
    UserFeedback,
    UserLearningProgress,
    UserPreference,
    UserWatchlist,
)

logger = logging.getLogger(__name__)

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
    ("Shega Media", "shega", "https://shega.co/feed/", "rss"),
    ("Addis Standard", "addis-standard", "https://addisstandard.com/feed/", "rss"),
    ("The Reporter Ethiopia", "reporter-ethiopia", "https://www.thereporterethiopia.com/feed/", "rss"),
    ("BBC Africa", "bbc-africa", "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "rss"),
    ("Al Jazeera World", "aljazeera-world", "https://www.aljazeera.com/xml/rss/all.xml", "rss"),
]

# Baseline articles populated on launch for immediate discoverability
BASELINE_ARTICLES = [
    (
        "Telebirr Reaches 45 Million Users and Integrates with National ID Fayda",
        "https://shega.co/post/telebirr-expands-digital-payments-and-national-id-integration",
        "shega",
        (
            "Ethio telecom's Telebirr platform expands digital financial inclusion across Ethiopia "
            "with instant Fayda verification."
        ),
        ["ethiopia-tech", "software-engineering"],
    ),
    (
        "Ethiopian AI Institute (EAII) Unveils Multilingual Healthcare Diagnostics Model",
        "https://shega.co/post/eaii-unveils-healthcare-nlp-diagnostics",
        "shega",
        (
            "The Ethiopian Artificial Intelligence Institute has launched a specialized diagnostic "
            "assistant supporting local languages."
        ),
        ["ethiopia-tech", "ai"],
    ),
    (
        "Chapa Payment Gateway Expands Cross-Border Remittances Across East Africa",
        "https://shega.co/post/chapa-cross-border-fintech-remittance-expansion",
        "shega",
        (
            "Ethiopian fintech startup Chapa launches multi-currency settlement and developer APIs "
            "for regional Horn of Africa trade."
        ),
        ["ethiopia-tech", "software-engineering"],
    ),
    (
        "National Bank of Ethiopia Accelerates Financial Market Reforms and Securities Exchange",
        "https://addisstandard.com/national-bank-of-ethiopia-accelerates-financial-market-reforms",
        "addis-standard",
        (
            "NBE announces updated foreign exchange directives and preliminary listing frameworks "
            "for the Ethiopian Securities Exchange."
        ),
        ["ethiopia-affairs", "tech-policy"],
    ),
    (
        "African Union Convenes Continental Summit on Renewable Energy Grid Integration and GERD",
        "https://addisstandard.com/african-union-renewable-energy-grid-integration",
        "addis-standard",
        (
            "Continental delegates in Addis Ababa discuss cross-border transmission of clean hydropower "
            "from the Grand Ethiopian Renaissance Dam."
        ),
        ["ethiopia-affairs", "renewable-energy", "global-politics"],
    ),
    (
        "United Nations Security Council Adopts Landmark Framework on Global AI Safety Treaties",
        "https://www.aljazeera.com/news/un-security-council-ai-safety-framework",
        "aljazeera-world",
        (
            "Member states pass multilateral resolution establishing verifiable safety benchmarks "
            "and non-proliferation protocols for frontier autonomous systems."
        ),
        ["global-politics", "tech-policy"],
    ),
]

# Baseline verified academic opportunities for Student Hub
BASELINE_OPPORTUNITIES = [
    {
        "title": "DAAD Helmut-Schmidt Master's Scholarships for Public Policy and STEM Governance",
        "slug": "daad-helmut-schmidt-masters-scholarship",
        "opportunity_type": "scholarship",
        "provider_name": "German Academic Exchange Service (DAAD)",
        "provider_type": "government",
        "official_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/daad-scholarships/",
        "application_url": "https://www.daad.de/go/en/stipa50026397",
        "country": "Germany",
        "eligible_nationalities": "Developing and Emerging Countries (including Ethiopia & Sub-Saharan Africa)",
        "study_level": "masters",
        "stem_fields": "Technology Policy, Computer Science, Engineering Management, Sustainable Development",
        "funding_type": "fully_funded",
        "benefits": (
            "Full tuition waiver, €934 monthly living allowance, health insurance, "
            "roundtrip travel allowance, German language course."
        ),
        "eligibility_criteria": (
            "First academic degree (Bachelor's or equivalent) with above-average results, "
            "English proficiency (IELTS 6.5+ or TOEFL 80+)."
        ),
        "required_documents": (
            "Curriculum Vitae (Europass), Letter of Motivation, Degree Certificates, "
            "Academic Transcripts, Language Certificate."
        ),
        "application_deadline": datetime(2027, 7, 31, 23, 59, tzinfo=timezone.utc),
        "is_rolling": False,
        "verification_tier": "officially_verified",
        "source_attribution": "DAAD Official Portal",
    },
    {
        "title": "Fulbright Foreign Student Program for Graduate STEM Studies",
        "slug": "fulbright-foreign-student-program-stem",
        "opportunity_type": "scholarship",
        "provider_name": "U.S. Department of State",
        "provider_type": "government",
        "official_url": "https://foreign.fulbrightonline.org/",
        "application_url": "https://apply.iie.org/ffsp",
        "country": "United States",
        "eligible_nationalities": "International (Over 160 eligible countries including Ethiopia)",
        "study_level": "masters",
        "stem_fields": (
            "Computer Science, Artificial Intelligence, Robotics, Biotechnology, Physics, Electrical Engineering"
        ),
        "funding_type": "fully_funded",
        "benefits": (
            "Full graduate tuition, living stipend, comprehensive sickness and accident insurance, "
            "roundtrip airfare, J-1 visa sponsorship."
        ),
        "eligibility_criteria": (
            "Undergraduate degree equivalent to a U.S. bachelor's degree, outstanding academic record, "
            "English proficiency, demonstrated leadership."
        ),
        "required_documents": (
            "Statement of Purpose, Personal Statement, 3 Letters of Recommendation, "
            "Official Transcripts, GRE/TOEFL if required by host department."
        ),
        "application_deadline": datetime(2027, 5, 15, 23, 59, tzinfo=timezone.utc),
        "is_rolling": False,
        "verification_tier": "officially_verified",
        "source_attribution": "U.S. Embassy & IIE Portal",
    },
    {
        "title": "Mastercard Foundation Scholars Program at Addis Ababa University",
        "slug": "mastercard-foundation-scholars-aau",
        "opportunity_type": "scholarship",
        "provider_name": "Mastercard Foundation & Addis Ababa University",
        "provider_type": "foundation",
        "official_url": "http://www.aau.edu.et/mcfsp/",
        "application_url": "http://www.aau.edu.et/mcfsp/how-to-apply/",
        "country": "Ethiopia",
        "eligible_nationalities": "African Nations (Priority to Ethiopian qualified youth, women, and refugees)",
        "study_level": "masters",
        "stem_fields": "Engineering, Computer Science, Health Sciences, Agricultural Technology, Environmental Science",
        "funding_type": "fully_funded",
        "benefits": (
            "Comprehensive scholarship covering tuition fees, laptop, accommodation, "
            "monthly living stipend, books, mentoring, and career support."
        ),
        "eligibility_criteria": (
            "Academic excellence, demonstrated financial need, commitment to give back to the "
            "African continent, under 35 years of age."
        ),
        "required_documents": (
            "Completed MCFSP application form, Bachelor's degree and student copy transcript, "
            "proof of financial need, recommendation letters."
        ),
        "application_deadline": datetime(2027, 4, 30, 23, 59, tzinfo=timezone.utc),
        "is_rolling": False,
        "verification_tier": "officially_verified",
        "source_attribution": "Addis Ababa University Official Portal",
    },
    {
        "title": "Erasmus Mundus Joint Master Degree in Artificial Intelligence & Robotics",
        "slug": "erasmus-mundus-master-ai-robotics",
        "opportunity_type": "scholarship",
        "provider_name": "European Commission",
        "provider_type": "government",
        "official_url": "https://erasmus-plus.ec.europa.eu/opportunities/opportunities-for-individuals/students/erasmus-mundus-joint-masters",
        "application_url": "https://erasmus-plus.ec.europa.eu/catalogue",
        "country": "European Union",
        "eligible_nationalities": "Worldwide (All Nationalities)",
        "study_level": "masters",
        "stem_fields": "Artificial Intelligence, Robotics, Autonomous Vehicles, Computer Vision, Machine Learning",
        "funding_type": "fully_funded",
        "benefits": (
            "100% tuition coverage, €1,400 monthly living allowance across 2-year multi-country "
            "mobility, travel and installation allowance."
        ),
        "eligibility_criteria": (
            "Bachelor's degree in Computer Science, Mathematics, Electrical Engineering, or related "
            "STEM discipline; English C1 level."
        ),
        "required_documents": (
            "Academic Transcripts, Degree Certificate, CV, 2 Academic References, Proof of Residence, "
            "Motivation Letter."
        ),
        "application_deadline": datetime(2027, 2, 15, 23, 59, tzinfo=timezone.utc),
        "is_rolling": False,
        "verification_tier": "officially_verified",
        "source_attribution": "European Commission Erasmus+ Catalogue",
    },
    {
        "title": "CERN Summer Student Fellowship & Research Programme",
        "slug": "cern-summer-student-programme",
        "opportunity_type": "internship",
        "provider_name": "European Organization for Nuclear Research (CERN)",
        "provider_type": "research_institute",
        "official_url": "https://careers.cern/summer",
        "application_url": "https://jobs.smartrecruiters.com/CERN/summer-student-programme",
        "country": "Switzerland",
        "eligible_nationalities": "Global (All Nationalities)",
        "study_level": "undergraduate",
        "stem_fields": (
            "High-Energy Physics, Computing, Distributed Systems, Electronics, Mechanical Engineering, Data Science"
        ),
        "funding_type": "fully_funded",
        "benefits": (
            "Daily living allowance of 92 CHF, travel reimbursement, comprehensive health insurance, "
            "hands-on particle accelerator projects, world-class lecture series."
        ),
        "eligibility_criteria": (
            "Must have completed at least 3 years of full-time undergraduate STEM studies, "
            "good knowledge of English or French."
        ),
        "required_documents": "CV, most recent official academic transcript, at least one letter of recommendation.",
        "application_deadline": datetime(2027, 1, 31, 23, 59, tzinfo=timezone.utc),
        "is_rolling": False,
        "verification_tier": "officially_verified",
        "source_attribution": "CERN Careers Official Portal",
    },
]

# Baseline verified university admission profiles
BASELINE_UNIVERSITIES = [
    {
        "name": "Addis Ababa University",
        "slug": "addis-ababa-university",
        "country": "Ethiopia",
        "city": "Addis Ababa",
        "official_portal_url": "http://www.aau.edu.et",
        "admissions_portal_url": "https://portal.aau.edu.et",
        "admission_requirements": (
            "National University Entrance Examination scores for undergraduates; recognized bachelor degree "
            "+ University GAT (Graduate Admission Test) for postgraduate programs."
        ),
        "application_procedures": (
            "1. Register on AAU portal. 2. Take Graduate Admission Test (GAT). 3. Submit department entrance "
            "examination. 4. Upload verified credentials."
        ),
        "tuition_and_funding": (
            "Subsidized government tuition for Ethiopian nationals; competitive self-sponsored rates and "
            "donor scholarships (Mastercard Foundation, Sida) for graduate researchers."
        ),
        "international_guidelines_url": "http://www.aau.edu.et/international-students/",
        "academic_regulations_url": "http://www.aau.edu.et/academics/academic-rules-and-regulations/",
        "research_opportunities_url": "http://www.aau.edu.et/research/",
    },
    {
        "name": "Massachusetts Institute of Technology (MIT)",
        "slug": "mit",
        "country": "United States",
        "city": "Cambridge, MA",
        "official_portal_url": "https://www.mit.edu",
        "admissions_portal_url": "https://mitadmissions.org",
        "admission_requirements": (
            "Rigorous high school/undergraduate STEM coursework (Calculus, Physics, Chemistry, Biology); "
            "competitive standardized tests or research portfolio."
        ),
        "application_procedures": (
            "Undergraduate via MIT application portal; Graduate applications directly to individual departments "
            "(EECS, MechE, AeroAstro, Physics)."
        ),
        "tuition_and_funding": (
            "Need-blind admissions for all undergraduate students (including international); 100% demonstrated "
            "financial need met without loans. Most graduate STEM students receive full Research Assistantship (RA) "
            "funding."
        ),
        "international_guidelines_url": "https://iso.mit.edu",
        "academic_regulations_url": "https://web.mit.edu/faculty/rules/",
        "research_opportunities_url": "https://urop.mit.edu",
    },
    {
        "name": "University of Oxford",
        "slug": "university-of-oxford",
        "country": "United Kingdom",
        "city": "Oxford",
        "official_portal_url": "https://www.ox.ac.uk",
        "admissions_portal_url": "https://www.ox.ac.uk/admissions",
        "admission_requirements": (
            "Undergraduate: AAA to A*A*A at A-level or equivalent International Baccalaureate / national "
            "qualification. Graduate: First-class or strong upper second-class undergraduate degree."
        ),
        "application_procedures": (
            "Undergraduate via UCAS by October 15. Graduate applications via Oxford online portal by December "
            "or January deadline for funding consideration."
        ),
        "tuition_and_funding": (
            "Over 1,000 fully funded graduate scholarships available annually, including Clarendon Fund, "
            "Rhodes Scholarships, and Oxford-Weidenfeld and Hoffmann Scholarships."
        ),
        "international_guidelines_url": "https://www.ox.ac.uk/admissions/graduate/international-applicants",
        "academic_regulations_url": "https://governance.admin.ox.ac.uk/legislation/statutes",
        "research_opportunities_url": "https://www.ox.ac.uk/research",
    },
]

# Baseline legal, copyright-verified open educational resources
BASELINE_ACADEMIC_RESOURCES = [
    {
        "title": "MIT 6.006: Introduction to Algorithms",
        "slug": "mit-6006-intro-to-algorithms",
        "resource_type": "lecture_materials",
        "stem_discipline": "Computer Science",
        "provider_institution": "MIT OpenCourseWare",
        "official_access_url": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/",
        "license_type": "Creative Commons BY-NC-SA",
        "is_copyright_verified": True,
        "description": (
            "Foundational university course on mathematical analysis of algorithms, asymptotic notation, "
            "sorting, binary search trees, hashing, dynamic programming, and shortest path graph algorithms."
        ),
    },
    {
        "title": "Harvard CS50: Introduction to Computer Science",
        "slug": "harvard-cs50-intro-computer-science",
        "resource_type": "free_course",
        "stem_discipline": "Computer Science & Programming",
        "provider_institution": "Harvard University",
        "official_access_url": "https://cs50.harvard.edu/x/",
        "license_type": "Creative Commons Open Access",
        "is_copyright_verified": True,
        "description": (
            "Flagship introductory course teaching algorithmic thinking, computational problem solving, "
            "memory management, and modern software development with C, Python, SQL, and HTML/CSS."
        ),
    },
    {
        "title": "DeepLearning.AI: Machine Learning Specialization",
        "slug": "deeplearning-ai-machine-learning",
        "resource_type": "free_course",
        "stem_discipline": "Artificial Intelligence & ML",
        "provider_institution": "Stanford Online & DeepLearning.AI",
        "official_access_url": "https://www.deeplearning.ai/courses/machine-learning-specialization/",
        "license_type": "Open Educational Resource",
        "is_copyright_verified": True,
        "description": (
            "Comprehensive 3-course curriculum by Andrew Ng covering supervised learning, linear regression, "
            "neural networks, decision trees, unsupervised learning, recommender systems, and reinforcement learning."
        ),
    },
    {
        "title": "The Rust Programming Language (Official Open Textbook)",
        "slug": "rust-programming-language-book",
        "resource_type": "open_textbook",
        "stem_discipline": "Systems Programming",
        "provider_institution": "The Rust Foundation & Community",
        "official_access_url": "https://doc.rust-lang.org/book/",
        "license_type": "MIT / Apache 2.0",
        "is_copyright_verified": True,
        "description": (
            "The definitive open-access guide to Rust, covering ownership, borrowing, lifetimes, fearless "
            "concurrency, pattern matching, macros, and low-level system design without garbage collection overhead."
        ),
    },
    {
        "title": "arXiv Open Scientific Research Repository",
        "slug": "arxiv-open-scientific-repository",
        "resource_type": "research_repository",
        "stem_discipline": "STEM Research & Mathematics",
        "provider_institution": "Cornell University & arXiv Community",
        "official_access_url": "https://arxiv.org/",
        "license_type": "Open Access",
        "is_copyright_verified": True,
        "description": (
            "Free, open-access electronic distribution archive of over 2.4 million scholarly articles in physics, "
            "mathematics, computer science, quantitative biology, electrical engineering, and systems science."
        ),
    },
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
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA synchronous=NORMAL")
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
            if "search_history_enabled" not in pref_cols:
                conn.exec_driver_sql("ALTER TABLE user_preferences ADD COLUMN search_history_enabled BOOLEAN DEFAULT 1")
                logger.info("Migrated schema: added user_preferences.search_history_enabled")
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

        # Seed baseline articles for immediate discoverability
        from app.database.repository import Repository

        repo = Repository(session)
        sources_list = await repo.get_sources(active_only=False)
        source_map = {s.slug: s.id for s in sources_list}
        cats_list = await repo.get_categories()
        cat_map = {c.slug: c.id for c in cats_list}

        seeded_articles = 0
        for title, url, src_slug, desc, cat_slugs in BASELINE_ARTICLES:
            src_id = source_map.get(src_slug)
            if src_id and not (await repo.article_exists(url)):
                c_ids = [cat_map[cs] for cs in cat_slugs if cs in cat_map]
                await repo.save_article(
                    title=title,
                    url=url,
                    source_id=src_id,
                    description=desc,
                    category_ids=c_ids,
                    commit=False,
                )
                seeded_articles += 1

        if seeded_articles:
            await session.commit()
            logger.info("Seeded %d baseline articles for new domains", seeded_articles)

        # Seed baseline academic opportunities for Student Hub
        seeded_opps = 0
        for opp_data in BASELINE_OPPORTUNITIES:
            existing = await repo.get_opportunity_by_slug(opp_data["slug"])
            if not existing:
                await repo.save_opportunity(**opp_data, commit=False)
                seeded_opps += 1
        if seeded_opps:
            await session.commit()
            logger.info("Seeded %d baseline academic opportunities", seeded_opps)

        # Seed baseline university profiles
        seeded_unis = 0
        for uni_data in BASELINE_UNIVERSITIES:
            existing = await repo.get_university_by_slug(uni_data["slug"])
            if not existing:
                await repo.save_university_profile(**uni_data, commit=False)
                seeded_unis += 1
        if seeded_unis:
            await session.commit()
            logger.info("Seeded %d baseline university profiles", seeded_unis)

        # Seed baseline open educational resources
        seeded_res = 0
        for res_data in BASELINE_ACADEMIC_RESOURCES:
            existing = await repo.get_academic_resource_by_slug(res_data["slug"])
            if not existing:
                await repo.save_academic_resource(**res_data, commit=False)
                seeded_res += 1
        if seeded_res:
            await session.commit()
            logger.info("Seeded %d baseline academic resources", seeded_res)

    logger.info("Database initialized successfully.")
