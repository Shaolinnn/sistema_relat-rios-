"""Evolution API WhatsApp notification provider (open-source, popular in Brazil)."""

import os

import requests

from brandfield.notifications.base import BaseNotifier, NotificationError, NotificationMessage


class EvolutionNotifier(BaseNotifier):
    """
    Sends WhatsApp messages via Evolution API (self-hosted or cloud).

    Required environment variables:
        EVOLUTION_API_URL  — Base URL, e.g. http://localhost:8080
        EVOLUTION_API_KEY  — API key configured in Evolution API
        EVOLUTION_INSTANCE — Instance name created in Evolution API
    """

    @property
    def provider_name(self) -> str:
        return "evolution"

    def __init__(self, credentials: dict):
        self.base_url = (
            credentials.get("api_url") or os.environ.get("EVOLUTION_API_URL", "")
        ).rstrip("/")
        self.api_key = credentials.get("api_key") or os.environ.get("EVOLUTION_API_KEY", "")
        self.instance = credentials.get("instance") or os.environ.get("EVOLUTION_INSTANCE", "")

        if not all([self.base_url, self.api_key, self.instance]):
            raise NotificationError(
                "EvolutionNotifier requires EVOLUTION_API_URL, EVOLUTION_API_KEY, "
                "and EVOLUTION_INSTANCE environment variables."
            )

    def send_message(self, message: NotificationMessage) -> bool:
        url = f"{self.base_url}/message/sendText/{self.instance}"
        # Evolution API expects phone without the + prefix
        phone = message.recipient_phone.lstrip("+")

        payload = {
            "number": phone,
            "textMessage": {"text": message.text},
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "apikey": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            return True
        except requests.HTTPError as e:
            raise NotificationError(
                f"Evolution API error (HTTP {e.response.status_code}): {e.response.text}"
            ) from e
        except requests.RequestException as e:
            raise NotificationError(f"Evolution API request failed: {e}") from e
