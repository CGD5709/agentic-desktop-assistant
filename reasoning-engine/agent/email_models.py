from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EmailAccountType(str, Enum):
    """Email provider accounts supported by the execution service."""
    GMAIL = "GMAIL"
    OUTLOOK = "OUTLOOK"


class EmailCategory(str, Enum):
    """Official 5-category taxonomy for email classification."""
    URGENT = "URGENT"
    UNIVERSITY = "UNIVERSITY"
    NOTIFICATION = "NOTIFICATION"
    NOT_IMPORTANT = "NOT IMPORTANT"
    SPAM = "SPAM"


class RawEmailDTO(BaseModel):
    """Parsed email message received deterministically from the Java execution service."""
    id: str
    account: str = "GMAIL"
    account_address: str = Field("", alias="accountAddress")
    subject: str = "(Sin asunto)"
    from_name: str = Field("", alias="fromName")
    from_address: str = Field("", alias="fromAddress")
    reply_to_address: str = Field("", alias="replyToAddress")
    to_addresses: List[str] = Field(default_factory=list, alias="toAddresses")
    cc_addresses: List[str] = Field(default_factory=list, alias="ccAddresses")
    received_at: str = Field("", alias="receivedAt")
    body_snippet: str = Field("", alias="bodySnippet")
    body_text: str = Field("", alias="bodyText")
    has_attachments: bool = Field(False, alias="hasAttachments")
    attachment_names: List[str] = Field(default_factory=list, alias="attachmentNames")

    model_config = {
        "populate_by_name": True,
    }


class ClassifiedEmail(BaseModel):
    """Email message augmented with semantic categorization and actionability."""
    email: RawEmailDTO
    category: EmailCategory = EmailCategory.NOT_IMPORTANT
    urgency_score: int = Field(default=1, ge=1, le=5)
    summary: str = ""
    requires_reply: bool = False
    suggested_action: Optional[str] = None


class EmailDraftPayload(BaseModel):
    """Email draft card payload dispatched over WebSocket to the React central canvas."""
    type: str = "email_draft_view"
    draft_id: str = Field(default_factory=lambda: f"draft-{uuid.uuid4().hex[:8]}")
    original_message_id: str
    account: str
    account_address: str
    # DETERMINISTIC RECIPIENT FIELDS: Locked by code from original metadata
    recipient_name: str
    recipient_email: str
    subject: str
    original_snippet: str
    draft_body: str
    category: EmailCategory = EmailCategory.NOT_IMPORTANT
    urgency_score: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = {
        "populate_by_name": True,
    }


class SendEmailActionRequest(BaseModel):
    """Payload dispatched when user authorizes sending an email draft."""
    type: str = "send_email_action"
    draft_id: str
    account: str
    recipient: str
    subject: str
    body: str
    in_reply_to: Optional[str] = None
