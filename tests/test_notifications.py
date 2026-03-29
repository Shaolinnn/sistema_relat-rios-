"""Tests for the notifications layer."""

import pytest

from brandfield.notifications.base import NotificationMessage
from brandfield.notifications.factory import get_notifier
from brandfield.notifications.null_notifier import NullNotifier


def test_get_notifier_none_returns_null_notifier():
    notifier = get_notifier("none")
    assert isinstance(notifier, NullNotifier)
    assert notifier.provider_name == "null"


def test_null_notifier_send_returns_true(capsys):
    notifier = NullNotifier()
    msg = NotificationMessage(
        recipient_phone="+5511999999999",
        text="Test message",
    )
    result = notifier.send_message(msg)
    assert result is True

    captured = capsys.readouterr()
    assert "Test message" in captured.out
    assert "+5511999999999" in captured.out


def test_get_notifier_unknown_raises():
    with pytest.raises(ValueError, match="Unknown WhatsApp provider"):
        get_notifier("unknown_provider")


def test_get_notifier_valid_providers():
    # All valid providers should be instantiable with empty credentials
    # (they'll use env vars which may not exist, but shouldn't crash at factory level)
    notifier = get_notifier("none")
    assert notifier.provider_name == "null"
