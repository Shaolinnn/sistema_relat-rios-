"""Factory function for selecting a WhatsApp notification provider."""

from brandfield.notifications.base import BaseNotifier
from brandfield.notifications.evolution import EvolutionNotifier
from brandfield.notifications.meta_whatsapp import MetaWhatsAppNotifier
from brandfield.notifications.null_notifier import NullNotifier
from brandfield.notifications.twilio import TwilioNotifier

PROVIDER_MAP: dict[str, type[BaseNotifier]] = {
    "meta": MetaWhatsAppNotifier,
    "twilio": TwilioNotifier,
    "evolution": EvolutionNotifier,
    "none": NullNotifier,
}


def get_notifier(provider: str, credentials: dict | None = None) -> BaseNotifier:
    """
    Instantiate the correct notifier for the given provider name.

    Args:
        provider:    One of "meta", "twilio", "evolution", "none"
        credentials: Dict of provider-specific credentials. If None or empty,
                     each provider falls back to environment variables.

    Raises:
        ValueError: If provider name is not recognized.
    """
    cls = PROVIDER_MAP.get(provider)
    if cls is None:
        raise ValueError(
            f"Unknown WhatsApp provider: {provider!r}. "
            f"Valid options: {sorted(PROVIDER_MAP)}"
        )

    creds = credentials or {}

    # NullNotifier takes no credentials
    if provider == "none":
        return NullNotifier()

    return cls(creds)
