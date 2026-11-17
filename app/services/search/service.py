"""Unified Search Service coordinating providers, ranking, deduplication, and presentation."""

import logging
import math
import re
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.keyboards.navigation import nav_back_home_row
from app.database.database import get_session_factory
from app.database.models import SearchQueryLog
from app.database.repository import Repository
from app.processors.deduplicator import normalize_url
from app.services.search.ai_assistant import SearchAIAssistant, search_ai_assistant
from app.services.search.models import (
    SearchAISummary,
    SearchResultItem,
    SourceComparison,
    UnifiedSearchResponse,
)
from app.services.search.providers.base import BaseSearchProvider
from app.services.search.providers.internal import InternalSearchProvider
from app.services.search.providers.registry import ExternalSearchRegistry

logger = logging.getLogger(__name__)


class SearchService:
    """Core search coordinator unifying internal database discovery and external search adapters."""

    def __init__(self, session_factory=None, external_registry=None, ai_assistant=None) -> None:
        self.session_factory = session_factory or get_session_factory()
        self.internal_provider = InternalSearchProvider(session_factory=self.session_factory)
        self.external_registry = external_registry or ExternalSearchRegistry()
        self.ai_assistant: SearchAIAssistant = ai_assistant or search_ai_assistant
        self.providers: List[BaseSearchProvider] = [self.internal_provider, *self.external_registry.providers]

    async def search(
        self,
        query: str,
        category: Optional[str] = "all",
        sort_by: str = "relevance",
        page: int = 1,
        page_size: int = 10,
        user_id: Optional[int] = None,
        source: str = "all",
        news_service=None,
        repo: Optional[Repository] = None,
    ) -> UnifiedSearchResponse:
        """Execute unified multi-domain search with cross-provider normalization and pagination."""
        clean_query = query.strip()
        cat = (category or "all").lower()
        sort_mode = "date" if sort_by == "date" else "relevance"
        src_scope = source.lower() if source in ("all", "internal", "external") else "all"
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 50))
        offset = (safe_page - 1) * safe_page_size

        all_items: List[SearchResultItem] = []
        seen_urls = set()
        total_estimated = 0

        # 1. Query Internal Provider (when source is "all" or "internal")
        if src_scope in ("all", "internal"):
            internal_items, internal_count = await self.internal_provider.search(
                query=clean_query,
                category=cat,
                sort_by=sort_mode,
                limit=safe_page_size * 2,
                offset=offset,
                news_service=news_service,
                repo=repo,
            )
            for it in internal_items:
                canon_url = normalize_url(it.url)
                if canon_url not in seen_urls:
                    seen_urls.add(canon_url)
                    all_items.append(it)
            total_estimated += internal_count

        # 2. Query External Discovery Registry (when source is "all" or "external")
        if src_scope in ("all", "external"):
            ext_items, ext_count = await self.external_registry.search_all_external(
                query=clean_query,
                category=cat,
                sort_by=sort_mode,
                limit=safe_page_size * 2 if src_scope == "external" else safe_page_size,
                offset=offset,
            )
            new_ext_count = 0
            for ext_it in ext_items:
                canon_url = normalize_url(ext_it.url)
                if canon_url not in seen_urls:
                    seen_urls.add(canon_url)
                    all_items.append(ext_it)
                    new_ext_count += 1

            if src_scope == "external":
                total_estimated = ext_count if ext_count > 0 else new_ext_count
            elif src_scope == "all":
                if internal_count == 0:
                    total_estimated = ext_count if ext_count > 0 else new_ext_count
                else:
                    total_estimated = internal_count + new_ext_count

        # 3. Final ranking and sorting across merged pool
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

        # 4. Consented search history logging
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
            source=src_scope,
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

    # ------------------ AI Search Assistant (Stage 15) ------------------

    async def ai_summarize_query(
        self,
        query: str,
        category: str = "all",
        source: str = "all",
        limit: int = 5,
        news_service=None,
        repo: Optional[Repository] = None,
    ) -> SearchAISummary:
        """Fetch top search results for query and generate grounded AI synthesis with citations."""
        search_res = await self.search(
            query=query,
            category=category,
            sort_by="relevance",
            page=1,
            page_size=limit,
            source=source,
            news_service=news_service,
            repo=repo,
        )
        return await self.ai_assistant.summarize_search_results(
            query=query,
            items=search_res.items,
            category=category,
        )

    async def compare_search_items(
        self,
        item_a: SearchResultItem,
        item_b: SearchResultItem,
        topic: Optional[str] = None,
    ) -> SourceComparison:
        """Perform cross-source comparative evaluation between two search items."""
        return await self.ai_assistant.compare_sources(item_a, item_b, topic=topic)

    # ------------------ Telegram UI & Markdown Presentation ------------------

    def format_search_results_page(self, response: UnifiedSearchResponse) -> str:
        """Render markdown search response with badges, snippets, and action links."""
        clean_query = response.query
        if not response.items:
            scope_str = "Live Web & Database" if response.source == "all" else response.source.title()
            cat_upper = response.category.upper()
            return (
                f'🔍 *Search Results for "{clean_query}"*\n\n'
                f'No results found matching *"{clean_query}"* in `{scope_str}` (Category: `{cat_upper}`).\n\n'
                "💡 *Tips:*\n"
                "• Check your spelling or try broader keywords (e.g., `ai`, `scholarship`, `python`, `quantum`)\n"
                "• Switch Scope to *🌐 All Sources* or *📡 Live Web* using the source selector below\n"
                "• Run `/collect` to ingest fresh intelligence from external sources"
            )

        cat_badge = response.category.upper()
        sort_badge = "RELEVANCE" if response.sort_by == "relevance" else "RECENT DATE"
        scope_badge = "ALL SOURCES" if response.source == "all" else f"SCOPE: {response.source.upper()}"
        header_stats = (
            f"📄 Page `{response.page}` of `{response.total_pages}` | "
            f"{scope_badge} | Cat: `{cat_badge}` | Sort: `{sort_badge}`\n"
        )
        lines = [
            f'🔍 *Search Results for "{clean_query}"*',
            header_stats,
        ]

        start_num = (response.page - 1) * response.page_size + 1
        for idx, item in enumerate(response.items, start=start_num):
            cat_emoji = {
                "STEM News": "📰",
                "Research Papers": "📄",
                "Scholarships": "🎓",
                "Universities": "🏛️",
                "Courses & Materials": "📚",
                "Web Discovery": "🌐",
                "Reference & Concept": "📖",
            }.get(item.category, "🏷️")

            verified_tag = " | 🟢 Verified" if item.is_verified else ""
            date_str = item.published_at.strftime("%b %d, %Y") if item.published_at else "Recently"

            # Quick action command hint & direct link
            action_hint = ""
            if item.item_type == "scholarship" and item.original_id:
                action_hint = f"👉 /scholarship_{item.original_id} • 🔗 [Official Portal]({item.url})"
            elif item.item_type == "university" and item.slug:
                action_hint = f"👉 /university_{item.slug} • 🔗 [Admissions Portal]({item.url})"
            elif item.item_type == "course" and item.slug:
                action_hint = f"👉 /resource_{item.slug} • 🔗 [Access Materials]({item.url})"
            elif item.item_type in ("news", "paper") and item.original_id:
                action_hint = f"👉 /ai_sum_{item.original_id} • 🔗 [Read Original]({item.url})"
            elif item.item_type == "external":
                display_source = item.source_name if item.source_name and item.source_name != "Web" else "Web Source"
                action_hint = f"🔗 [Open on {display_source}]({item.url})"

            clean_title = re.sub(r"[*_`]", "", item.title or "Untitled").strip()
            clean_snippet = re.sub(r"[*_`]", "", item.snippet or "").strip()
            snippet_txt = f"\n_{clean_snippet}_" if clean_snippet else ""

            lines.append(
                f"*{idx}. [{clean_title}]({item.url})*\n"
                f"{cat_emoji} `{item.category}`{verified_tag} • _{item.source_name}_ ({date_str})"
                f"{snippet_txt}\n"
                f"{action_hint}\n"
            )

        lines.append("💡 *Actions:* Use the source selector, category chips, and sort toggles below to refine.")
        return "\n".join(lines)

    def get_search_results_keyboard(
        self,
        query: str,
        page: int,
        total_pages: int,
        category: str = "all",
        sort_by: str = "relevance",
        source: str = "all",
    ) -> InlineKeyboardMarkup:
        """Build interactive keyboard with source selector, category chips, sort toggle, and pagination."""
        buttons: List[List[InlineKeyboardButton]] = []
        clean_q = query[:25]
        src = source if source in ("all", "internal", "external") else "all"

        # Row 1: Source Selector (Unified / Local DB / Live Web Discovery)
        s_all = "● " if src == "all" else ""
        s_int = "● " if src == "internal" else ""
        s_ext = "● " if src == "external" else ""
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{s_all}🌐 Unified", callback_data=f"search:src:all:{category}:{sort_by}:{clean_q}"
                ),
                InlineKeyboardButton(
                    f"{s_int}🏠 Local DB", callback_data=f"search:src:internal:{category}:{sort_by}:{clean_q}"
                ),
                InlineKeyboardButton(
                    f"{s_ext}📡 Live Web", callback_data=f"search:src:external:{category}:{sort_by}:{clean_q}"
                ),
            ]
        )

        # Row 2: Primary Category Filter Chips
        c_all = "● " if category == "all" else ""
        c_news = "● " if category == "news" else ""
        c_paper = "● " if category == "research" else ""
        buttons.append(
            [
                InlineKeyboardButton(f"{c_all}🌐 All", callback_data=f"search:cat:all:{sort_by}:{src}:{clean_q}"),
                InlineKeyboardButton(f"{c_news}📰 News", callback_data=f"search:cat:news:{sort_by}:{src}:{clean_q}"),
                InlineKeyboardButton(
                    f"{c_paper}📄 Papers", callback_data=f"search:cat:research:{sort_by}:{src}:{clean_q}"
                ),
            ]
        )

        # Row 3: Secondary Category Filter Chips
        c_sch = "● " if category == "scholarships" else ""
        c_uni = "● " if category == "universities" else ""
        c_crs = "● " if category in ("courses", "study_materials") else ""
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{c_sch}🎓 Awards", callback_data=f"search:cat:scholarships:{sort_by}:{src}:{clean_q}"
                ),
                InlineKeyboardButton(
                    f"{c_uni}🏛️ Unis", callback_data=f"search:cat:universities:{sort_by}:{src}:{clean_q}"
                ),
                InlineKeyboardButton(
                    f"{c_crs}📚 Courses", callback_data=f"search:cat:courses:{sort_by}:{src}:{clean_q}"
                ),
            ]
        )

        # Row 4: Sort Toggle
        rel_label = "🎯 Rank: Relevance" if sort_by == "relevance" else "🎯 Sort by Relevance"
        date_label = "📅 Rank: Newest" if sort_by == "date" else "📅 Sort by Date"
        buttons.append(
            [
                InlineKeyboardButton(rel_label, callback_data=f"search:sort:{category}:relevance:{src}:{clean_q}"),
                InlineKeyboardButton(date_label, callback_data=f"search:sort:{category}:date:{src}:{clean_q}"),
            ]
        )

        # Row 5: AI Search Synthesis Action (Stage 15)
        buttons.append(
            [
                InlineKeyboardButton(
                    "🧠 AI Synthesis & Insights",
                    callback_data=f"search:ai_sum:{category}:{src}:{clean_q}",
                )
            ]
        )

        # Row 6: Pagination Navigation
        pag_row: List[InlineKeyboardButton] = []
        if page > 1:
            prev_p = page - 1
            pag_row.append(
                InlineKeyboardButton(
                    "⬅️ Prev", callback_data=f"search:page:{prev_p}:{category}:{sort_by}:{src}:{clean_q}"
                )
            )
        pag_row.append(InlineKeyboardButton(f"📄 {page}/{max(1, total_pages)}", callback_data="search:noop"))
        if page < total_pages:
            next_p = page + 1
            pag_row.append(
                InlineKeyboardButton(
                    "Next ➡️", callback_data=f"search:page:{next_p}:{category}:{sort_by}:{src}:{clean_q}"
                )
            )
        buttons.append(pag_row)

        # Row 6: Navigation Back / Home
        buttons.append(nav_back_home_row(back_target="menu:search", home_target="menu:home"))
        return InlineKeyboardMarkup(buttons)


search_service = SearchService()
