"""Meta WhatsApp Business API notification provider."""

import os

import requests

from brandfield.notifications.base import BaseNotifier, NotificationError, NotificationMessage

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class MetaWhatsAppNotifier(BaseNotifier):
    """
    Sends WhatsApp messages via the official Meta WhatsApp Business API.

    Required environment variables:
        META_WA_TOKEN    — WhatsApp access token
        META_WA_PHONE_ID — WhatsApp phone number ID (from Meta Business dashboard)
    """

    @property
    def provider_name(self) -> str:
        return "meta"

    def __init__(self, credentials: dict):
        self.token = credentials.get("token") or os.environ.get("META_WA_TOKEN", "")
        self.phone_id = credentials.get("phone_id") or os.environ.get("META_WA_PHONE_ID", "")

        if not self.token or not self.phone_id:
            raise NotificationError(
                "MetaWhatsAppNotifier requires META_WA_TOKEN and META_WA_PHONE_ID "
                "environment variables."
            )

    def send_message(self, message: NotificationMessage) -> bool:
        url = f"{GRAPH_API_BASE}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": message.recipient_phone,
            "type": "text",
            "text": {"body": message.text, "preview_url": False},
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            return True
        except requests.HTTPError as e:
            raise NotificationError(
                f"Meta WhatsApp API error (HTTP {e.response.status_code}): "
                f"{e.response.text}"
            ) from e
        except requests.RequestException as e:
            raise NotificationError(f"Meta WhatsApp request failed: {e}") from e
