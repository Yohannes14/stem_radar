"""Unified Search Service coordinating providers, ranking, deduplication, and presentation."""

import logging
import math
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.navigation import nav_back_home_row
from app.database.database import get_session_factory
from app.database.models import SearchQueryLog
from app.database.repository import Repository
from app.processors.deduplicator import normalize_url
from app.services.search.models import SearchResultItem, UnifiedSearchResponse
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.external import ExternalSearchProvider
from app.services.search.providers.internal import InternalSearchProvider

logger = logging.getLogger(__name__)


class SearchService:
    """Core search coordinator unifying internal database discovery and external search adapters."""

    def __init__(self, session_factory=None) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.internal_provider = InternalSearchProvider(session_factory=self.session_factory)
        self.external_provider = ExternalSearchProvider()
        self.providers: List[BaseSearchProvider] = [self.internal_provider, self.external_provider]

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 10,
        user_id: Optional[int] = None,
        news_service=None,
        repo: Optional[Repository] = None,
    ) -> UnifiedSearchResponse:
        """Execute unified multi-domain search with cross-provider normalization and pagination."""
        clean_query = query.strip()
        cat = (category or "all").lower()
        sort_mode = "date" if sort_by == "date" else "relevance"
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 50))
        offset = (safe_page - 1) * safe_page_size

        all_items: List[SearchResultItem] = []
        total_estimated = 0

        # 1. Query Internal Provider (Primary)
        internal_items, internal_count = await self.internal_provider.search(
            query=clean_query,
            category=cat,
            sort_by=sort_mode,
            limit=safe_page_size * 2,
            offset=offset,
            news_service=news_service,
            repo=repo,
        )
        all_items.extend(internal_items)
        total_estimated += internal_count

        # 2. Query External Provider if configured (Stage B integration)
        if self.external_provider.is_available():
            ext_items, ext_count = await self.external_provider.search(
                query=clean_query,
                category=cat,
                sort_by=sort_mode,
                limit=safe_page_size,
                offset=offset,
            )
            # Deduplicate against internal results by normalized URL
            seen_urls = {normalize_url(item.url) for item in all_items}
            for ext_item in ext_items:
                if normalize_url(ext_item.url) not in seen_urls:
                    all_items.append(ext_item)
                    total_estimated += 1

        # 3. Final ranking and sorting
        if sort_mode == "date":
            all_items.sort(
                key=lambda x: (
                    x.published_at.timestamp() if x.published_at else 0.0,
                    x.score,
                ),
                reverse=True,
            )
        else:
            all_items.sort(key=lambda x: x.score, reverse=True)

        # Slice to requested page size
        final_items = all_items[:safe_page_size]
        total_pages = max(1, math.ceil(total_estimated / safe_page_size))

        # 4. Optional consented search history logging
        if user_id and clean_query:
            await self._record_history_if_consented(user_id, clean_query, cat, total_estimated)

        return UnifiedSearchResponse(
            items=final_items,
            total_items=total_estimated,
            page=safe_page,
            page_size=safe_page_size,
            total_pages=total_pages,
            query=clean_query,
            category=cat,
            sort_by=sort_mode,
        )

    async def _record_history_if_consented(self, user_id: int, query: str, category: str, results_count: int) -> None:
        """Check user preference and record search query to history log if consent is enabled."""
        try:
            async with self.session_factory() as session:
                repo = Repository(session)
                pref = await repo.get_or_create_preference(user_id)
                if pref.search_history_enabled:
                    await repo.save_search_query_log(
                        query=query,
                        user_id=user_id,
                        category=category,
                        results_count=results_count,
                    )
        except Exception as exc:
            logger.warning("Failed to record search history log for user %s: %s", user_id, exc)

    async def get_user_search_history(self, user_id: int, limit: int = 10) -> List[SearchQueryLog]:
        """Retrieve recent consented searches for a user."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.get_user_search_history(user_id=user_id, limit=limit)

    async def clear_user_search_history(self, user_id: int) -> int:
        """Clear all search history for a user."""
        async with self.session_factory() as session:
            repo = Repository(session)
            return await repo.clear_user_search_history(user_id=user_id)

    # ------------------ Telegram UI & Markdown Presentation ------------------

    def format_search_results_page(self, response: UnifiedSearchResponse) -> str:
        """Render markdown search response with badges, snippets, and action links."""
        clean_query = response.query
        if not response.items:
            return (
                f"🔍 *STEM RADAR Unified Search*\n\n"
                f'No results found matching *"{clean_query}"* in category `{response.category.upper()}`.\n\n'
                "💡 *Tips:*\n"
                "• Check your spelling or try broader keywords (e.g., `ai`, `scholarship`, `python`, `quantum`)\n"
                "• Switch category to *🌐 All Domains* using the chips below\n"
                "• Run `/collect` to ingest fresh intelligence from external sources"
            )

        cat_badge = response.category.upper()
        sort_badge = "RELEVANCE" if response.sort_by == "relevance" else "RECENT DATE"
        lines = [
            f'🔍 *Search Results for "{clean_query}"*',
            f"📄 Page `{response.page}` of `{response.total_pages}` | Category: `{cat_badge}` | Sort: `{sort_badge}`\n",
        ]

        start_num = (response.page - 1) * response.page_size + 1
        for idx, item in enumerate(response.items, start=start_num):
            cat_emoji = {
                "STEM News": "📰",
                "Research Papers": "📄",
                "Scholarships": "🎓",
                "Universities": "🏛️",
                "Courses & Materials": "📚",
            }.get(item.category, "🏷️")

            verified_tag = " | 🟢 Verified" if item.is_verified else ""
            date_str = item.published_at.strftime("%b %d, %Y") if item.published_at else "Recently"

            # Quick action command hint
            action_hint = ""
            if item.item_type == "scholarship" and item.original_id:
                action_hint = f"👉 /scholarship_{item.original_id}"
            elif item.item_type == "university" and item.slug:
                action_hint = f"👉 /university_{item.slug}"
            elif item.item_type == "course" and item.slug:
                action_hint = f"👉 /resource_{item.slug}"
            elif item.item_type in ("news", "paper") and item.original_id:
                action_hint = f"👉 /ai_sum_{item.original_id} (or tap link)"

            snippet_txt = f"\n_{item.snippet}_" if item.snippet else ""

            lines.append(
                f"*{idx}. [{item.title}]({item.url})*\n"
                f"{cat_emoji} `{item.category}`{verified_tag} • _{item.source_name}_ ({date_str})"
                f"{snippet_txt}\n"
                f"{action_hint}\n"
            )

        lines.append("💡 *Actions:* Use the filter chips and sort toggles below to refine results.")
        return "\n".join(lines)

    def get_search_results_keyboard(
        self,
        query: str,
        page: int,
        total_pages: int,
        category: str = "all",
        sort_by: str = "relevance",
    ) -> InlineKeyboardMarkup:
        """Build interactive keyboard with category chips, sort toggle, and pagination."""
        buttons: List[List[InlineKeyboardButton]] = []
        clean_q = query[:25]

        # Row 1: Primary Category Filter Chips
        c_all = "● " if category == "all" else ""
        c_news = "● " if category == "news" else ""
        c_paper = "● " if category == "research" else ""
        buttons.append(
            [
                InlineKeyboardButton(f"{c_all}🌐 All", callback_data=f"search:cat:all:{sort_by}:{clean_q}"),
                InlineKeyboardButton(f"{c_news}📰 News", callback_data=f"search:cat:news:{sort_by}:{clean_q}"),
                InlineKeyboardButton(f"{c_paper}📄 Papers", callback_data=f"search:cat:research:{sort_by}:{clean_q}"),
            ]
        )

        # Row 2: Secondary Category Filter Chips
        c_sch = "● " if category == "scholarships" else ""
        c_uni = "● " if category == "universities" else ""
        c_crs = "● " if category in ("courses", "study_materials") else ""
        buttons.append(
            [
                InlineKeyboardButton(f"{c_sch}🎓 Awards", callback_data=f"search:cat:scholarships:{sort_by}:{clean_q}"),
                InlineKeyboardButton(f"{c_uni}🏛️ Unis", callback_data=f"search:cat:universities:{sort_by}:{clean_q}"),
                InlineKeyboardButton(f"{c_crs}📚 Courses", callback_data=f"search:cat:courses:{sort_by}:{clean_q}"),
            ]
        )

        # Row 3: Sort Toggle
        rel_label = "🎯 Rank: Relevance" if sort_by == "relevance" else "🎯 Sort by Relevance"
        date_label = "📅 Rank: Newest" if sort_by == "date" else "📅 Sort by Date"
        buttons.append(
            [
                InlineKeyboardButton(rel_label, callback_data=f"search:sort:{category}:relevance:{clean_q}"),
                InlineKeyboardButton(date_label, callback_data=f"search:sort:{category}:date:{clean_q}"),
            ]
        )

        # Row 4: Pagination Navigation
        pag_row: List[InlineKeyboardButton] = []
        if page > 1:
            prev_p = page - 1
            pag_row.append(
                InlineKeyboardButton("⬅️ Prev", callback_data=f"search:page:{prev_p}:{category}:{sort_by}:{clean_q}")
            )
        pag_row.append(InlineKeyboardButton(f"📄 {page}/{max(1, total_pages)}", callback_data="search:noop"))
        if page < total_pages:
            next_p = page + 1
            pag_row.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"search:page:{next_p}:{category}:{sort_by}:{clean_q}")
            )
        buttons.append(pag_row)

        # Row 5: Navigation Back / Home
        buttons.append(nav_back_home_row(back_target="menu:search", home_target="menu:home"))
        return InlineKeyboardMarkup(buttons)


search_service = SearchService()
