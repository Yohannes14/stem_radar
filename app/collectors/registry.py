"""Centralized collector registry for managing and instantiating data collectors."""

import logging
from typing import Dict, List, Type

from app.collectors.arxiv_collector import ArxivCollector
from app.collectors.base import BaseCollector
from app.collectors.github_collector import GitHubCollector
from app.collectors.linkedin_collector import LinkedInCollector
from app.collectors.rss_collector import RSSCollector
from app.collectors.x_collector import XCollector
from app.database.models import Source

logger = logging.getLogger(__name__)


class CollectorRegistry:
    """Registry maintaining mappings from source types to collector classes."""

    _registry: Dict[str, Type[BaseCollector]] = {
        "rss": RSSCollector,
        "arxiv": ArxivCollector,
        "github": GitHubCollector,
        "x": XCollector,
        "linkedin": LinkedInCollector,
    }

    @classmethod
    def register(cls, source_type: str, collector_cls: Type[BaseCollector]) -> None:
        """Register a new collector class for a given source type."""
        cls._registry[source_type.lower()] = collector_cls
        logger.info("Registered collector for type: %s", source_type)

    @classmethod
    def create_collector(cls, source: Source) -> BaseCollector:
        """Instantiate a collector for a specific database Source."""
        source_type = source.source_type.lower()
        collector_cls = cls._registry.get(source_type, RSSCollector)
        return collector_cls(
            source_name=source.name,
            source_slug=source.slug,
            url=source.url,
        )

    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Return all supported source type identifiers."""
        return list(cls._registry.keys())
