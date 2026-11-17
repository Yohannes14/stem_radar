"""Abstract base provider for internal and external search adapters."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from app.services.search.models import SearchResultItem


class BaseSearchProvider(ABC):
    """Abstract search provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier name."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider dependencies, network, and credentials are configured."""
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[SearchResultItem], int]:
        """Execute query and return normalized results and total estimated match count."""
        ...

