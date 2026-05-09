from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from app.core.database import Base


class DeadLetterWebhook(Base):
    __tablename__ = "dead_letter_webhooks"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    webhook_id     = Column(Integer, nullable=False, index=True)
    webhook_url    = Column(String(2048), nullable=False)
    payload        = Column(JSON, nullable=False)
    failure_reason = Column(Text, nullable=True)
    attempt_count  = Column(Integer, default=0)
    failed_at      = Column(DateTime, default=datetime.utcnow, index=True)
    is_resolved    = Column(Boolean, default=False)
    replayed_at    = Column(DateTime, nullable=True)
