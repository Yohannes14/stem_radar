"""Unit and integration tests for Stage 7: Public-User Management, Role-Based Access & DB Hardening."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from app.bot.filters.auth import (
    _USER_REQUEST_TIMESTAMPS,
    admin_only,
    authorized_only,
    check_rate_limit,
)
from app.bot.handlers.news import collect_command
from app.bot.handlers.user_management import (
    ban_command,
    delete_account_command,
    export_command,
    feedback_command,
    privacy_command,
    unban_command,
)
from app.config import settings
from app.database.repository import Repository


@pytest.fixture
def mock_bot_user():
    user = MagicMock(spec=User)
    user.id = 887766
    user.first_name = "Grace"
    user.last_name = "Hopper"
    user.username = "ghopper"
    return user


@pytest.fixture
def mock_mgmt_update(mock_bot_user):
    update = MagicMock(spec=Update)
    chat = MagicMock(spec=Chat)
    chat.id = mock_bot_user.id

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    update.effective_user = mock_bot_user
    update.effective_chat = chat
    update.effective_message = message
    update.callback_query = None
    return update


@pytest.fixture
def mock_mgmt_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    return context


# ------------------ 1. Rate Limiting Tests ------------------


def test_check_rate_limit_sliding_window():
    """Verify rate limit tracking allows requests within bounds and enforces cooldown when exceeded."""
    test_user_id = 12345999
    _USER_REQUEST_TIMESTAMPS.pop(test_user_id, None)

    # 3 requests allowed with limit of 3
    assert check_rate_limit(test_user_id, max_requests=3, window_seconds=10)[0] is True
    assert check_rate_limit(test_user_id, max_requests=3, window_seconds=10)[0] is True
    assert check_rate_limit(test_user_id, max_requests=3, window_seconds=10)[0] is True

    # 4th request should be rate-limited
    is_allowed, retry_after = check_rate_limit(test_user_id, max_requests=3, window_seconds=10)
    assert is_allowed is False
    assert retry_after > 0


# ------------------ 2. Repository User Management Tests ------------------


@pytest.mark.asyncio
async def test_get_or_create_user(test_session_factory):
    """Verify public user auto-registration, admin assignment, and profile updates."""
    async with test_session_factory() as session:
        repo = Repository(session)

        # 1. Register new public user
        user, created = await repo.get_or_create_user(
            telegram_id=987654,
            username="newuser",
            first_name="New",
            last_name="User",
        )
        assert created is True
        assert user.telegram_id == 987654
        assert user.username == "newuser"
        assert user.is_active is True
        assert user.is_banned is False

        # 2. Second access updates last_active_at without duplicate creation
        user2, created2 = await repo.get_or_create_user(
            telegram_id=987654,
            username="updated_user",
            first_name="New",
        )
        assert created2 is False
        assert user2.id == user.id
        assert user2.username == "updated_user"


@pytest.mark.asyncio
async def test_user_ban_and_admin_checks(test_session_factory):
    """Verify admin check and banning mechanics in repository."""
    async with test_session_factory() as session:
        repo = Repository(session)
        user, _ = await repo.get_or_create_user(telegram_id=111222)

        # Default: not admin, not banned
        assert await repo.is_user_admin(111222) is False

        # Ban user
        await repo.set_user_ban_status(111222, is_banned=True)
        fetched = await repo.get_user_by_telegram_id(111222)
        assert fetched.is_banned is True
        assert fetched.is_active is False

        # Unban user
        await repo.set_user_ban_status(111222, is_banned=False)
        fetched2 = await repo.get_user_by_telegram_id(111222)
        assert fetched2.is_banned is False
        assert fetched2.is_active is True


@pytest.mark.asyncio
async def test_user_feedback_storage(test_session_factory):
    """Verify storing user feedback entries."""
    async with test_session_factory() as session:
        repo = Repository(session)
        fb = await repo.save_user_feedback(
            telegram_id=333444,
            message="Great technology radar implementation!",
            category="praise",
        )
        assert fb.id is not None
        assert fb.user_id == 333444
        assert fb.category == "praise"
        assert "technology radar" in fb.message


@pytest.mark.asyncio
async def test_user_data_export_and_deletion(test_session_factory):
    """Verify full data export and complete data deletion compliance."""
    async with test_session_factory() as session:
        repo = Repository(session)
        uid = 444555

        # Create user profile and preference
        await repo.get_or_create_user(uid, username="export_user")
        pref = await repo.get_or_create_preference(uid)
        pref.preferred_categories = "ai,robotics"
        await session.commit()

        # Add watchlist
        await repo.add_watchlist_keyword(uid, "fusion")

        # 1. Export data
        exported = await repo.export_user_data(uid)
        assert exported["telegram_id"] == uid
        assert exported["profile"]["username"] == "export_user"
        assert exported["preferences"]["preferred_categories"] == "ai,robotics"
        assert "fusion" in exported["watchlist_keywords"]

        # 2. Delete data
        del_result = await repo.delete_user_data(uid)
        assert del_result["status"] == "deleted"

        # Verify deletion across tables
        cleared_watchlist = await repo.get_user_watchlist(uid)
        assert len(cleared_watchlist) == 0


# ------------------ 3. Authorization & Admin Security Decorators ------------------


@pytest.mark.asyncio
async def test_authorized_only_blocks_banned_user(mock_mgmt_update, test_session_factory):
    """Verify authorized_only blocks banned users from interacting."""
    target_func = AsyncMock()
    decorated = authorized_only(target_func)

    with patch("app.bot.filters.auth.get_session_factory", return_value=test_session_factory):
        async with test_session_factory() as session:
            repo = Repository(session)
            user, _ = await repo.get_or_create_user(mock_mgmt_update.effective_user.id)
            user.is_banned = True
            await session.commit()

        # Execute decorated function
        await decorated(mock_mgmt_update, MagicMock())

    target_func.assert_not_called()
    mock_mgmt_update.effective_message.reply_text.assert_called_once()
    reply = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
    assert "Account Suspended" in reply


@pytest.mark.asyncio
async def test_admin_only_blocks_regular_user(mock_mgmt_update, test_session_factory):
    """Verify admin_only decorator restricts regular non-admin users."""
    target_func = AsyncMock()
    decorated = admin_only(target_func)

    with patch("app.bot.filters.auth.get_session_factory", return_value=test_session_factory):
        with patch.object(settings, "allowed_user_ids", []):
            await decorated(mock_mgmt_update, MagicMock())

    target_func.assert_not_called()
    mock_mgmt_update.effective_message.reply_text.assert_called_once()
    reply = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
    assert "Admin Access Required" in reply


@pytest.mark.asyncio
async def test_admin_only_allows_admin_user(mock_mgmt_update, test_session_factory):
    """Verify admin_only decorator allows users configured in settings or database as admin."""
    target_func = AsyncMock()
    decorated = admin_only(target_func)

    with patch.object(settings, "allowed_user_ids", [mock_mgmt_update.effective_user.id]):
        await decorated(mock_mgmt_update, MagicMock())

    target_func.assert_called_once()


@pytest.mark.asyncio
async def test_collect_command_is_protected_by_admin_only(mock_mgmt_update, test_session_factory):
    """Verify /collect command cannot be triggered by regular users."""
    with patch("app.bot.filters.auth.get_session_factory", return_value=test_session_factory):
        with patch.object(settings, "allowed_user_ids", []):
            await collect_command(mock_mgmt_update, MagicMock())

    mock_mgmt_update.effective_message.reply_text.assert_called_once()
    reply = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
    assert "Admin Access Required" in reply


# ------------------ 4. User Management Command Handlers ------------------


@pytest.mark.asyncio
async def test_feedback_command_handling(mock_mgmt_update, mock_mgmt_context, test_session_factory):
    """Test /feedback command saves feedback and thanks the user."""
    with patch("app.bot.handlers.user_management.get_session_factory", return_value=test_session_factory):
        # 1. No arguments prompt
        mock_mgmt_context.args = []
        await feedback_command(mock_mgmt_update, mock_mgmt_context)
        reply = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
        assert "Feedback & Issue Reporting" in reply

        # 2. Submit feedback
        mock_mgmt_context.args = ["Awesome", "bot", "keep", "it", "up!"]
        mock_mgmt_update.effective_message.reply_text.reset_mock()
        await feedback_command(mock_mgmt_update, mock_mgmt_context)
        reply2 = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
        assert "Feedback Received" in reply2


@pytest.mark.asyncio
async def test_privacy_and_export_commands(mock_mgmt_update, mock_mgmt_context, test_session_factory):
    """Test /privacy and /export commands."""
    with patch("app.bot.handlers.user_management.get_session_factory", return_value=test_session_factory):
        # 1. /privacy
        await privacy_command(mock_mgmt_update, mock_mgmt_context)
        reply_p = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
        assert "Privacy Policy & Data Protection" in reply_p
        assert "What we do not do" in reply_p

        # 2. /export
        mock_mgmt_update.effective_message.reply_text.reset_mock()
        await export_command(mock_mgmt_update, mock_mgmt_context)
        reply_e = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
        assert "Exported Personal Data" in reply_e


@pytest.mark.asyncio
async def test_delete_account_command(mock_mgmt_update, mock_mgmt_context, test_session_factory):
    """Test /delete_account requires confirmation and purges data."""
    with patch("app.bot.handlers.user_management.get_session_factory", return_value=test_session_factory):
        # 1. Without confirmation
        mock_mgmt_context.args = []
        await delete_account_command(mock_mgmt_update, mock_mgmt_context)
        reply1 = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
        assert "Confirm Permanent Data Deletion" in reply1

        # 2. With confirmation
        mock_mgmt_context.args = ["confirm"]
        mock_mgmt_update.effective_message.reply_text.reset_mock()
        await delete_account_command(mock_mgmt_update, mock_mgmt_context)
        reply2 = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
        assert "User Data Deleted" in reply2


@pytest.mark.asyncio
async def test_admin_ban_and_unban_commands(mock_mgmt_update, mock_mgmt_context, test_session_factory):
    """Test admin moderation /ban and /unban commands."""
    with patch("app.bot.handlers.user_management.get_session_factory", return_value=test_session_factory):
        with patch.object(settings, "allowed_user_ids", [mock_mgmt_update.effective_user.id]):
            # Ban
            mock_mgmt_context.args = ["776655"]
            await ban_command(mock_mgmt_update, mock_mgmt_context)
            reply_ban = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
            assert "User 776655 has been banned" in reply_ban

            # Unban
            mock_mgmt_context.args = ["776655"]
            mock_mgmt_update.effective_message.reply_text.reset_mock()
            await unban_command(mock_mgmt_update, mock_mgmt_context)
            reply_unban = mock_mgmt_update.effective_message.reply_text.call_args[0][0]
            assert "User 776655 has been unbanned" in reply_unban
