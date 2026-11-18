"""Tests for multi-domain interest subscriptions, personalization-weighted ranking, and briefings."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.settings import interests_command, settings_callback_router
from app.config import settings
from app.database.models import Category, Source
from app.database.repository import Repository
from app.processors.ranking import ArticleRanker
from app.services.automation_service import AutomationService


@pytest.fixture
def mock_interests_update():
    """Mock Telegram update for interests command and callback queries."""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 778899
    user.first_name = "Marie"
    user.username = "mcurie"

    chat = MagicMock(spec=Chat)
    chat.id = 778899

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()
    message.edit_reply_markup = AsyncMock()

    query = MagicMock(spec=CallbackQuery)
    query.id = "query_int_1"
    query.data = "pref_cat:ai"
    query.message = message
    query.answer = AsyncMock()

    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = query
    return update


def test_article_ranker_personalization_boost():
    """Verify that articles matching user interests receive a personalization score boost."""
    ranker = ArticleRanker()
    title = "Advanced Actuator Kinematics in Humanoid Systems"
    categories = [("robotics", 0.95), ("embedded-systems", 0.8)]

    # 1. Base score without matching interests
    base_score = ranker.calculate_score(title=title, categories=categories, user_interests=["physics", "chemistry"])

    # 2. Score with matching interest ("robotics")
    boosted_score = ranker.calculate_score(title=title, categories=categories, user_interests=["robotics", "ai"])

    assert boosted_score > base_score
    assert boosted_score - base_score == 15.0


@pytest.mark.asyncio
async def test_repository_multi_category_filtering(test_session_factory):
    """Verify repository correctly retrieves articles matching any of multiple category slugs."""
    async with test_session_factory() as session:
        repo = Repository(session)

        # Retrieve seeded categories
        ai_cat = await repo.get_category_by_slug("ai")
        rob_cat = await repo.get_category_by_slug("robotics")
        phy_cat = await repo.get_category_by_slug("physics")
        if not phy_cat:
            phy_cat = Category(name="Physics", slug="physics")
            session.add(phy_cat)
            await session.commit()

        # Seed sample source and articles across different domains
        source = Source(name="TechLab", slug="techlab-multi", url="https://techlab.io")
        session.add(source)
        await session.flush()

        a1, _ = await repo.save_article(
            title="Transformer Scaling Laws",
            url="https://techlab.io/transformer",
            source_id=source.id,
            category_ids=[ai_cat.id],
        )
        a2, _ = await repo.save_article(
            title="Bipedal Dynamic Balance",
            url="https://techlab.io/bipedal",
            source_id=source.id,
            category_ids=[rob_cat.id],
        )
        a3, _ = await repo.save_article(
            title="Superconducting Qubits",
            url="https://techlab.io/qubits",
            source_id=source.id,
            category_ids=[phy_cat.id],
        )

        # Query using a list of slugs: ["ai", "robotics"]
        multi_articles = await repo.get_recent_articles(category_slugs=["ai", "robotics"])
        matched_titles = [a.title for a in multi_articles]

        assert "Transformer Scaling Laws" in matched_titles
        assert "Bipedal Dynamic Balance" in matched_titles
        assert "Superconducting Qubits" not in matched_titles

        # Count articles matching comma-delimited string
        count = await repo.count_articles(category_slug="ai,robotics")
        assert count >= 2


@pytest.mark.asyncio
async def test_repository_interest_toggling(test_session_factory):
    """Verify toggling categories adds and removes them correctly in persistent user preferences."""
    async with test_session_factory() as session:
        repo = Repository(session)
        uid = 445566

        # 1. Toggle AI -> should add "ai"
        slugs1, added1 = await repo.toggle_user_interest_category(uid, "ai")
        assert added1 is True
        assert slugs1 == ["ai"]

        # 2. Toggle Robotics -> should add "robotics", resulting in ["ai", "robotics"]
        slugs2, added2 = await repo.toggle_user_interest_category(uid, "robotics")
        assert added2 is True
        assert set(slugs2) == {"ai", "robotics"}

        # 3. Toggle AI again -> should remove "ai", leaving ["robotics"]
        slugs3, added3 = await repo.toggle_user_interest_category(uid, "ai")
        assert added3 is False
        assert slugs3 == ["robotics"]

        # 4. Toggle "all" -> should reset preferences to empty list
        slugs4, added4 = await repo.toggle_user_interest_category(uid, "all")
        assert added4 is False
        assert slugs4 == []


@pytest.mark.asyncio
async def test_interests_command_renders_panel(mock_interests_update, test_session_factory):
    """Verify /interests displays the multi-category subscription panel."""
    with patch("app.bot.handlers.settings.get_session_factory", return_value=test_session_factory):
        with patch.object(settings, "allowed_user_ids", [778899]):
            await interests_command(mock_interests_update, MagicMock())

    mock_interests_update.effective_message.reply_text.assert_called_once()
    reply_call = mock_interests_update.effective_message.reply_text.call_args
    text = reply_call[0][0]
    markup = reply_call[1]["reply_markup"]

    assert "Domain Subscriptions" in text
    assert len(markup.inline_keyboard) >= 5


@pytest.mark.asyncio
async def test_settings_callback_router_toggles_interest(mock_interests_update, test_session_factory):
    """Verify callback query pref_cat:<slug> toggles category and updates view in-place."""
    mock_interests_update.callback_query.data = "pref_cat:robotics"

    with patch("app.bot.handlers.settings.get_session_factory", return_value=test_session_factory):
        with patch.object(settings, "allowed_user_ids", [778899]):
            await settings_callback_router(mock_interests_update, MagicMock())

    mock_interests_update.callback_query.answer.assert_called_once()
    status_alert = mock_interests_update.callback_query.answer.call_args[0][0]
    assert "robotics" in status_alert.lower()


@pytest.mark.asyncio
async def test_automation_service_personalized_briefing(test_session_factory):
    """Verify daily briefings prioritize articles in the user's subscribed interest domains."""
    async with test_session_factory() as session:
        repo = Repository(session)
        uid = 889900

        # Subscribe user to "robotics"
        await repo.toggle_user_interest_category(uid, "robotics")

        ai_cat = await repo.get_category_by_slug("ai")
        rob_cat = await repo.get_category_by_slug("robotics")

        source = Source(name="BriefingLab", slug="briefing-lab", url="https://briefing.io")
        session.add(source)
        await session.flush()

        await repo.save_article(
            title="General AI News",
            url="https://briefing.io/ai",
            source_id=source.id,
            category_ids=[ai_cat.id],
        )
        await repo.save_article(
            title="Humanoid Actuator Milestone",
            url="https://briefing.io/robotics",
            source_id=source.id,
            category_ids=[rob_cat.id],
        )

        service = AutomationService()
        briefing_text, articles = await service.generate_daily_briefing(user_id=uid, user_name="Marie", session=session)

        assert len(articles) >= 1
        # The robotics article should be ranked first due to personalization boost
        assert any("Humanoid Actuator" in a.title for a in articles)
        assert "Briefing" in briefing_text
