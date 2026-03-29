"""Abstract base class and message model for WhatsApp notifications."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationMessage:
    recipient_phone: str   # E.164 format: +5511999999999
    text: str
    # Extension point for future attachment support
    attachment_url: Optional[str] = None


class NotificationError(Exception):
    """Raised when a notification provider fails to send a message."""


class BaseNotifier(ABC):
    """
    Contract for all WhatsApp notification providers.

    Implementors must:
    - Accept credentials in __init__
    - Implement send_message() — return True on success
    - Wrap all provider-specific exceptions as NotificationError
    - Never raise provider SDK exceptions directly
    """

    @abstractmethod
    def send_message(self, message: NotificationMessage) -> bool:
        """Send a WhatsApp message. Returns True on success."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name for logs."""
