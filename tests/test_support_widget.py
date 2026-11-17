import uuid
from unittest.mock import patch

import pytest

from app.config import settings
from app.modules.support.knowledge.models import SupportTicketModel
from app.modules.support.knowledge.schemas import RAGStructuredOutputSchema, SourceCitationSchema

KEY = "test-widget-key"
SESSION = "sess_1234567890abcdef"
RAG_PATH = "app.modules.support.widget.RAGOrchestrationService.answer_customer_question"


@pytest.fixture
def widget_org(monkeypatch):
    org_id = uuid.uuid4()
    monkeypatch.setattr(settings, "WIDGET_API_KEY", KEY)
    monkeypatch.setattr(settings, "WIDGET_ORG_ID", str(org_id))
    return org_id


def _post(client, message="Hello?", session=SESSION, key=KEY):
    headers = {"X-Widget-Key": key} if key else {}
    return client.post("/support/widget/chat", json={"message": message, "session_id": session}, headers=headers)


def test_widget_not_configured_returns_503(test_client, monkeypatch):
    monkeypatch.setattr(settings, "WIDGET_API_KEY", None)
    monkeypatch.setattr(settings, "WIDGET_ORG_ID", None)
    assert _post(test_client).status_code == 503


def test_widget_rejects_missing_or_wrong_key(test_client, widget_org):
    assert _post(test_client, key=None).status_code == 401
    assert _post(test_client, key="wrong").status_code == 401


def test_widget_ping_requires_key(test_client, widget_org):
    assert test_client.get("/support/widget/ping").status_code == 401
    ok = test_client.get("/support/widget/ping", headers={"X-Widget-Key": KEY})
    assert ok.status_code == 200 and ok.json() == {"ok": True}


def test_widget_rejects_bad_session_id(test_client, widget_org):
    assert _post(test_client, session="bad id!").status_code == 422


def test_widget_returns_grounded_answer(test_client, widget_org):
    fake = RAGStructuredOutputSchema(
        answer="The return period is 30 days.",
        sources=[SourceCitationSchema(document="return-policy.pdf", page="3")],
    )
    with patch(RAG_PATH, return_value=fake) as mocked:
        res = _post(test_client, "What is the return policy?")
    assert res.status_code == 200
    body = res.json()
    assert "30 days" in body["reply"]
    assert body["sources"][0]["document"] == "return-policy.pdf"
    assert body["escalated"] is False
    # the widget must be bound to the configured organization
    assert mocked.call_args.kwargs["org_id"] == widget_org


def test_widget_escalates_once_per_session(test_client, db_session, widget_org):
    missing = RAGStructuredOutputSchema(answer="Information was not found in the knowledge base.", sources=[])
    with patch(RAG_PATH, return_value=missing):
        first = _post(test_client, "What is the CEO's favourite food?")
        second = _post(test_client, "And what about the CTO?")
    assert first.json()["escalated"] is True and second.json()["escalated"] is True

    tickets = db_session.query(SupportTicketModel).filter(
        SupportTicketModel.organization_id == widget_org,
        SupportTicketModel.customer_id == f"web-{SESSION}",
    ).all()
    assert len(tickets) == 1


def test_widget_ai_failure_returns_502(test_client, widget_org):
    with patch(RAG_PATH, side_effect=RuntimeError("llm down")):
        assert _post(test_client).status_code == 502
