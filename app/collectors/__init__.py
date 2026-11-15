"""Collector interfaces, models, and concrete collector implementations."""

from app.collectors.arxiv_collector import ArxivCollector
from app.collectors.base import BaseCollector, CollectedArticle
from app.collectors.client import ResilientHTTPClient
from app.collectors.github_collector import GitHubCollector
from app.collectors.registry import CollectorRegistry
from app.collectors.rss_collector import RSSCollector

__all__ = [
    "BaseCollector",
    "CollectedArticle",
    "ResilientHTTPClient",
    "CollectorRegistry",
    "RSSCollector",
    "ArxivCollector",
    "GitHubCollector",
]

