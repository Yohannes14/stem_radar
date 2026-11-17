"""Internal database search provider querying articles, research, scholarships, and resources."""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from app.database.database import get_session_factory
from app.database.repository import Repository
from app.processors.deduplicator import normalize_url
from app.services.search.models import SearchResultItem
from app.services.search.providers.base import BaseSearchProvider

logger = logging.getLogger(__name__)


def calculate_relevance_score(
    query: str,
    title: str,
    snippet: str,
    is_verified: bool = False,
    published_at: Optional[datetime] = None,
) -> float:
    """Compute text relevance score based on keyword frequencies, title weight, and verified status."""
    clean_query = query.strip().lower()
    terms = [re.escape(t) for t in clean_query.split() if len(t) > 1]
    if not terms:
        terms = [re.escape(clean_query)]

    title_lower = title.lower()
    snippet_lower = snippet.lower()
    score = 0.0

    # 1. Exact phrase match bonus
    if clean_query in title_lower:
        score += 8.0
    elif clean_query in snippet_lower:
        score += 3.0

    # 2. Individual term presence
    for t in terms:
        pattern = rf"\b{t}\b"
        # Title matches are weighted heavily
        title_matches = len(re.findall(pattern, title_lower))
        score += title_matches * 3.0

        # Snippet matches
        snippet_matches = len(re.findall(pattern, snippet_lower))
        score += snippet_matches * 1.0

    # 3. Verified official trust bonus
    if is_verified:
        score += 0.5

    # 4. Slight recency decay/boost (within 30 days gets a modest bump)
    if published_at:
        now = datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            pub_utc = published_at.replace(tzinfo=timezone.utc)
        else:
            pub_utc = published_at
        days_old = max(0, (now - pub_utc).days)
        if days_old <= 30:
            score += 1.0
        elif days_old <= 90:
            score += 0.5

    return round(score, 2)


class InternalSearchProvider(BaseSearchProvider):
    """Database search provider executing cross-table unified queries."""

    def __init__(self, session_factory=None, news_service=None) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.news_service = news_service

    @property
    def name(self) -> str:
        return "internal_database"

    def is_available(self) -> bool:
        return True

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0,
        news_service=None,
        repo: Optional[Repository] = None,
    ) -> Tuple[List[SearchResultItem], int]:
        """Search articles, research papers, scholarships, universities, and courses."""
        clean_query = query.strip()
        cat = (category or "all").lower()
        results: List[SearchResultItem] = []
        seen_urls: Set[str] = set()

        svc = news_service or self.news_service
        # Generous retrieval window per domain to allow cross-table re-ranking
        fetch_limit = max(limit * 3, 50)
        articles_matched_count = 0

        # 1. Search Articles (News, Tech, Programming, Research Papers)
        should_search_articles = cat in ("all", "news", "technology", "programming", "research")
        is_paper_filter = True if cat == "research" else (False if cat in ("news", "technology") else None)
        source_type_filter = "arxiv" if is_paper_filter else None
        cat_slug = None
        if cat in ("technology", "programming"):
            cat_slug = "programming" if cat == "programming" else "software"

        async def _execute_search(active_repo: Repository):
            nonlocal articles_matched_count
            if should_search_articles:
                if svc:
                    articles = await svc.get_recent_news(
                        limit=fetch_limit,
                        offset=0,
                        category_slug=cat_slug,
                        source_type=source_type_filter,
                        query=clean_query,
                    )
                    try:
                        articles_matched_count = await svc.count_news(
                            category_slug=cat_slug,
                            source_type=source_type_filter,
                            query=clean_query,
                        )
                    except Exception:
                        articles_matched_count = len(articles)
                else:
                    articles = await active_repo.search_articles(
                        query=clean_query,
                        limit=fetch_limit,
                        offset=0,
                        category_slug=cat_slug,
                        is_paper=is_paper_filter,
                    )
                    articles_matched_count = len(articles)

                for a in articles:
                    canon_url = normalize_url(a.url)
                    if canon_url in seen_urls:
                        continue
                    seen_urls.add(canon_url)

                    is_paper = bool(a.source and (a.source.source_type == "arxiv" or "arxiv" in a.source.slug.lower()))
                    item_type = "paper" if is_paper else "news"
                    domain_cat = "Research Papers" if is_paper else "STEM News"
                    source_name = a.source.name if a.source else "STEM Radar"
                    snippet = a.description or (a.content[:200] if a.content else "")

                    score = calculate_relevance_score(
                        clean_query,
                        a.title,
                        snippet,
                        is_verified=True,
                        published_at=a.published_at or a.collected_at,
                    )
                    results.append(
                        SearchResultItem(
                            id=f"art:{a.id}",
                            title=a.title,
                            snippet=snippet[:250],
                            source_name=source_name,
                            published_at=a.published_at or a.collected_at,
                            category=domain_cat,
                            is_verified=True,
                            url=a.url,
                            score=score,
                            item_type=item_type,
                            original_id=a.id,
                            metadata={"categories": [c.name for c in (a.categories or [])]},
                        )
                    )

            # 2. Search Scholarships & Academic Opportunities
            if cat in ("all", "scholarships", "projects"):
                opps = await active_repo.search_opportunities(
                    query=clean_query,
                    limit=fetch_limit,
                    offset=0,
                    active_only=True,
                )
                for o in opps:
                    canon_url = normalize_url(o.official_url)
                    if canon_url in seen_urls:
                        continue
                    seen_urls.add(canon_url)

                    snippet = (
                        f"{o.provider_name} • {o.study_level.upper()} • {o.funding_type.replace('_', ' ').title()}"
                    )
                    if o.benefits:
                        snippet += f" • {o.benefits[:100]}"
                    is_verified = o.verification_tier == "officially_verified"
                    score = calculate_relevance_score(
                        clean_query,
                        o.title,
                        f"{snippet} {o.stem_fields} {o.eligibility_criteria}",
                        is_verified=is_verified,
                        published_at=o.published_at,
                    )
                    results.append(
                        SearchResultItem(
                            id=f"opp:{o.id}",
                            title=o.title,
                            snippet=snippet[:250],
                            source_name=o.provider_name,
                            published_at=o.published_at,
                            category="Scholarships",
                            is_verified=is_verified,
                            url=o.application_url or o.official_url,
                            score=score,
                            item_type="scholarship",
                            original_id=o.id,
                            slug=o.slug,
                            metadata={
                                "country": o.country,
                                "study_level": o.study_level,
                                "funding_type": o.funding_type,
                                "deadline": o.application_deadline.isoformat() if o.application_deadline else None,
                            },
                        )
                    )

            # 3. Search University Admissions & Profiles
            if cat in ("all", "universities"):
                unis = await active_repo.search_university_profiles(query=clean_query, limit=fetch_limit, offset=0)
                for u in unis:
                    canon_url = normalize_url(u.admissions_portal_url or u.official_portal_url)
                    if canon_url in seen_urls:
                        continue
                    seen_urls.add(canon_url)

                    snippet = f"{u.name} ({u.country}) • Admissions & Guidelines"
                    if u.admission_requirements:
                        snippet += f" • {u.admission_requirements[:120]}"
                    score = calculate_relevance_score(
                        clean_query,
                        u.name,
                        f"{snippet} {u.country} {u.city or ''}",
                        is_verified=True,
                        published_at=u.last_verified_at,
                    )
                    results.append(
                        SearchResultItem(
                            id=f"uni:{u.id}",
                            title=u.name,
                            snippet=snippet[:250],
                            source_name=u.name,
                            published_at=u.last_verified_at,
                            category="Universities",
                            is_verified=True,
                            url=u.admissions_portal_url,
                            score=score,
                            item_type="university",
                            original_id=u.id,
                            slug=u.slug,
                            metadata={"country": u.country, "city": u.city},
                        )
                    )

            # 4. Search Free Educational Resources & Courses
            if cat in ("all", "courses", "study_materials"):
                resources = await active_repo.search_academic_resources(query=clean_query, limit=fetch_limit, offset=0)
                for r in resources:
                    canon_url = normalize_url(r.official_access_url)
                    if canon_url in seen_urls:
                        continue
                    seen_urls.add(canon_url)

                    snippet = f"{r.provider_institution} • {r.stem_discipline} • {r.license_type}"
                    if r.description:
                        snippet += f" • {r.description[:120]}"
                    score = calculate_relevance_score(
                        clean_query,
                        r.title,
                        f"{snippet} {r.stem_discipline}",
                        is_verified=r.is_copyright_verified,
                        published_at=r.last_verified_at,
                    )
                    results.append(
                        SearchResultItem(
                            id=f"res:{r.id}",
                            title=r.title,
                            snippet=snippet[:250],
                            source_name=r.provider_institution,
                            published_at=r.last_verified_at,
                            category="Courses & Materials",
                            is_verified=r.is_copyright_verified,
                            url=r.official_access_url,
                            score=score,
                            item_type="course",
                            original_id=r.id,
                            slug=r.slug,
                            metadata={"resource_type": r.resource_type, "discipline": r.stem_discipline},
                        )
                    )

        if repo:
            await _execute_search(repo)
        else:
            async with self.session_factory() as session:
                active_repo = Repository(session)
                await _execute_search(active_repo)

        # Total matching pool before pagination
        total_count = max(len(results), articles_matched_count)

        # Sorting logic: relevance vs date
        if sort_by == "date":
            # Primary: published_at descending (nulls last), Secondary: score
            min_dt = datetime.min.replace(tzinfo=timezone.utc)
            results.sort(
                key=lambda x: (
                    (
                        x.published_at.replace(tzinfo=timezone.utc)
                        if x.published_at and x.published_at.tzinfo is None
                        else (x.published_at or min_dt)
                    ),
                    x.score,
                ),
                reverse=True,
            )
        else:
            # Primary: score descending, Secondary: published_at
            results.sort(key=lambda x: x.score, reverse=True)

        # Slice pagination
        paginated_items = results[offset : offset + limit]
        return paginated_items, total_count
