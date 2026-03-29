"""Twilio WhatsApp notification provider."""

import os

import requests
from requests.auth import HTTPBasicAuth

from brandfield.notifications.base import BaseNotifier, NotificationError, NotificationMessage

TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"


class TwilioNotifier(BaseNotifier):
    """
    Sends WhatsApp messages via Twilio's WhatsApp sandbox or verified number.

    Required environment variables:
        TWILIO_ACCOUNT_SID — Twilio account SID
        TWILIO_AUTH_TOKEN  — Twilio auth token
        TWILIO_WA_FROM     — Sender number in E.164 with whatsapp: prefix
                             e.g. whatsapp:+14155238886
    """

    @property
    def provider_name(self) -> str:
        return "twilio"

    def __init__(self, credentials: dict):
        self.account_sid = credentials.get("account_sid") or os.environ.get(
            "TWILIO_ACCOUNT_SID", ""
        )
        self.auth_token = credentials.get("auth_token") or os.environ.get(
            "TWILIO_AUTH_TOKEN", ""
        )
        self.from_number = credentials.get("from_number") or os.environ.get(
            "TWILIO_WA_FROM", ""
        )

        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise NotificationError(
                "TwilioNotifier requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                "and TWILIO_WA_FROM environment variables."
            )

    def send_message(self, message: NotificationMessage) -> bool:
        url = TWILIO_MESSAGES_URL.format(account_sid=self.account_sid)
        to = f"whatsapp:{message.recipient_phone}"

        try:
            resp = requests.post(
                url,
                data={"From": self.from_number, "To": to, "Body": message.text},
                auth=HTTPBasicAuth(self.account_sid, self.auth_token),
                timeout=30,
            )
            resp.raise_for_status()
            return True
        except requests.HTTPError as e:
            raise NotificationError(
                f"Twilio API error (HTTP {e.response.status_code}): {e.response.text}"
            ) from e
        except requests.RequestException as e:
            raise NotificationError(f"Twilio request failed: {e}") from e
