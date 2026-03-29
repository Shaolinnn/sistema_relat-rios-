"""Pydantic v2 models for client configuration validation."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class MetaAdsConfig(BaseModel):
    enabled: bool = True
    date_preset: Literal[
        "yesterday", "last_7d", "last_14d", "last_30d", "this_month", "last_month"
    ] = "last_7d"
    campaign_ids: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(
        default=["impressions", "clicks", "spend", "cpm", "cpc", "purchase_roas"]
    )


class MetaOrganicConfig(BaseModel):
    enabled: bool = True
    metrics: list[str] = Field(
        default=["reach", "impressions", "follower_count", "profile_views"]
    )


class MetaConfig(BaseModel):
    ad_account_id: str
    instagram_business_id: str
    access_token_env: str = Field(
        description="Name of the environment variable holding the Meta access token"
    )
    ads: MetaAdsConfig = Field(default_factory=MetaAdsConfig)
    organic: MetaOrganicConfig = Field(default_factory=MetaOrganicConfig)

    @model_validator(mode="after")
    def at_least_one_source_enabled(self) -> "MetaConfig":
        if not self.ads.enabled and not self.organic.enabled:
            raise ValueError("At least one of meta.ads or meta.organic must be enabled.")
        return self


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    provider: Literal["meta", "twilio", "evolution", "none"] = "none"
    recipient_phone: str = ""

    @model_validator(mode="after")
    def phone_required_when_enabled(self) -> "WhatsAppConfig":
        if self.enabled and self.provider != "none" and not self.recipient_phone:
            raise ValueError(
                "notifications.whatsapp.recipient_phone is required when WhatsApp is enabled."
            )
        return self


class NotificationsConfig(BaseModel):
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)


class ReportScheduleConfig(BaseModel):
    daily: bool = True
    weekly: bool = True


class KpiCard(BaseModel):
    metric: str
    label: str
    format: Literal["currency", "number", "percent", "multiplier"] = "number"


class ReportConfig(BaseModel):
    schedule: ReportScheduleConfig = Field(default_factory=ReportScheduleConfig)
    kpi_cards: Optional[list[str]] = None  # None = use defaults


class ClientConfig(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    display_name: str
    timezone: str = "America/Sao_Paulo"
    meta: MetaConfig
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
