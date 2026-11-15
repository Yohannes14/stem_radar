"""Tests for configuration and authorization logic."""

from app.config import Settings


def test_settings_user_authorization():
    settings = Settings(allowed_telegram_user_ids="12345678, 87654321")

    assert settings.is_user_allowed(12345678) is True
    assert settings.is_user_allowed(87654321) is True
    assert settings.is_user_allowed(99999999) is False


def test_settings_empty_whitelist_allows_in_dev():
    settings = Settings(allowed_telegram_user_ids="")

    # If empty, default allows so new users can get started
    assert settings.is_user_allowed(12345) is True
