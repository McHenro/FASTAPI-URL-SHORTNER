from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel


class WebhookEvent(str, Enum):
    URL_CREATED = "url.created"
    URL_CLICKED = "url.clicked"
    URL_DELETED = "url.deleted"


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[WebhookEvent]


class WebhookResponse(BaseModel):
    id: int
    name: str
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
