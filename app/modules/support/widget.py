"""Public website chat widget gateway for Nexus Support.

The WordPress plugin calls this router with a shared secret header
(X-Widget-Key). The key maps to ONE organization (WIDGET_ORG_ID), so the
website visitor can only ever reach that organization's knowledge base.
No user login / JWT is needed for website visitors.
"""
import hmac
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database.connection import get_db
from app.modules.support.knowledge.models import SupportTicketModel
from app.modules.support.knowledge.schemas import SourceCitationSchema
from app.modules.support.knowledge.services import RAGOrchestrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/support/widget", tags=["Website Chat Widget"])

NOT_FOUND_MARKER = "Information was not found"
ESCALATION_REPLY = (
    "I am sorry, I could not find verified information to answer that. "
    "A support ticket has been opened and our team will follow up."
)


class WidgetChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str = Field(..., min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class WidgetChatResponse(BaseModel):
    reply: str
    sources: List[SourceCitationSchema] = []
    escalated: bool = False


def require_widget_access(x_widget_key: str | None = Header(default=None)) -> uuid.UUID:
    """Validates the shared secret and returns the organization the widget is bound to."""
    expected_key = settings.WIDGET_API_KEY
    org_raw = settings.WIDGET_ORG_ID
    if not expected_key or not org_raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Website chat widget is not configured.",
        )
    if not x_widget_key or not hmac.compare_digest(
        x_widget_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid widget key.")
    try:
        return uuid.UUID(org_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Website chat widget is misconfigured.",
        )


@router.get("/ping")
def widget_ping(org_id: uuid.UUID = Depends(require_widget_access)):
    """Lets the WordPress admin page verify the URL + key without running the AI."""
    return {"ok": True}


@router.post("/chat", response_model=WidgetChatResponse)
def widget_chat(
    payload: WidgetChatRequest,
    org_id: uuid.UUID = Depends(require_widget_access),
    db: Session = Depends(get_db),
):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty message.")

    try:
        rag = RAGOrchestrationService.answer_customer_question(
            question=message, org_id=org_id, db=db
        )
    except Exception:
        logger.exception("Widget chat failed while generating an answer")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is temporarily unavailable.",
        )

    if NOT_FOUND_MARKER in rag.answer:
        # Same human-escalation rule as /support/agent/chat, but only ONE open
        # ticket per website session so visitors cannot flood the ticket list.
        customer_id = f"web-{payload.session_id}"
        already_open = (
            db.query(SupportTicketModel)
            .filter(
                SupportTicketModel.organization_id == org_id,
                SupportTicketModel.customer_id == customer_id,
                SupportTicketModel.status == "open",
            )
            .first()
        )
        if not already_open:
            db.add(
                SupportTicketModel(
                    organization_id=org_id,
                    customer_id=customer_id,
                    subject=f"Website chat escalation: {message[:30]}",
                    description=(
                        "Automated escalation from the website chat widget. "
                        f"No verified answer was found for: {message}"
                    ),
                    status="open",
                )
            )
            db.commit()
        return WidgetChatResponse(reply=ESCALATION_REPLY, sources=[], escalated=True)

    return WidgetChatResponse(reply=rag.answer, sources=rag.sources, escalated=False)
