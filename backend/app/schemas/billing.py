from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillingCheckoutRequest(BaseModel):
    installation_id: str = Field(min_length=3, max_length=128)
    country_code: str = Field(min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, min_length=1, max_length=32)


class BillingCheckoutResponse(BaseModel):
    checkout_url: str
    transaction_id: str
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    status: str


class BillingWebhookResponse(BaseModel):
    accepted: bool
    event_type: str
    event_id: str | None = None
    status: str
    duplicated: bool = False


class BillingWebhookEventRead(BaseModel):
    id: int
    provider: str
    event_id: str
    event_type: str
    status: str
    payload: str
    error_message: str | None
    received_at: datetime
    processed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    installation_id: int | None
    provider: str
    provider_customer_id: str | None
    provider_subscription_id: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)
