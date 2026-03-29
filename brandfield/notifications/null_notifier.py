"""No-op notifier for dry-run and testing — logs to stdout instead of sending."""

from brandfield.notifications.base import BaseNotifier, NotificationMessage


class NullNotifier(BaseNotifier):
    """
    Safe for CI, local development, and test suites.
    Prints the message to stdout so it's visible in logs.
    """

    @property
    def provider_name(self) -> str:
        return "null"

    def send_message(self, message: NotificationMessage) -> bool:
        print(
            f"[NullNotifier] Would send to {message.recipient_phone}:\n"
            f"{'-' * 60}\n"
            f"{message.text}\n"
            f"{'-' * 60}"
        )
        return True
