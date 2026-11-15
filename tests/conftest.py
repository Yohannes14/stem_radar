"""Pytest fixtures and test configuration."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.database import DEFAULT_CATEGORIES, INITIAL_SOURCES
from app.database.models import Base, Category, Source

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech News Feed</title>
    <link>https://example.com</link>
    <description>Sample tech news</description>
    <item>
      <title>Breakthrough in Humanoid Robotics Actuators</title>
      <link>https://example.com/robotics-breakthrough?utm_source=twitter</link>
      <description>
        &lt;p&gt;Engineers unveiled a new high-torque electric actuator for humanoids.&lt;/p&gt;
      </description>
      <pubDate>Mon, 10 Nov 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>New Open-Source LLM Architecture Released</title>
      <link>https://example.com/ai-llm-model</link>
      <description>
        Researchers open-source a 10B parameter model with reinforcement learning.
      </description>
      <pubDate>Tue, 11 Nov 2026 15:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv cs.AI query</title>
  <entry>
    <id>http://arxiv.org/abs/2611.12345v1</id>
    <title>Scalable Diffusion Models for Robotics Control</title>
    <summary>
      We propose a novel diffusion policy architecture for robotic manipulation.
    </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <link href="http://arxiv.org/abs/2611.12345v1" rel="alternate" type="text/html"/>
    <published>2026-11-12T10:00:00Z</published>
  </entry>
</feed>
"""


@pytest.fixture
async def test_session_factory():
    """Create an isolated, in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # Seed baseline categories & sources
    async with session_factory() as session:
        for name, slug, desc in DEFAULT_CATEGORIES:
            session.add(Category(name=name, slug=slug, description=desc))
        for name, slug, url, stype in INITIAL_SOURCES:
            session.add(Source(name=name, slug=slug, url=url, source_type=stype, is_active=True))
        await session.commit()

    yield session_factory
    await engine.dispose()
