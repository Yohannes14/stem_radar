"""Official LinkedIn API Integration Collector."""

import logging
import os
from typing import List

from app.collectors.base import BaseCollector, CollectedArticle

logger = logging.getLogger(__name__)


class LinkedInCollector(BaseCollector):
    """Collects permitted technology updates via official authorized LinkedIn APIs."""

    def __init__(
        self,
        source_name: str = "LinkedIn Tech Updates",
        source_slug: str = "linkedin-tech",
        url: str = "https://api.linkedin.com/v2/",
    ) -> None:
        super().__init__(source_name=source_name, source_slug=source_slug, url=url)
        self.client_id = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()

    async def collect(self) -> List[CollectedArticle]:
        if not self.client_id or not self.client_secret:
            logger.info("LinkedIn API integration is disabled: LINKEDIN_CLIENT_ID/SECRET not configured.")
            return []

        # Remains safely inactive until official OAuth permissions are granted.
        logger.info("LinkedIn official API configured. Ready for token authorization.")
        return []
