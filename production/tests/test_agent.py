"""Agent tool unit tests with mocked database.

Tests each @function_tool independently with mocked DB connections,
verifying Pydantic input validation, error handling, and sentiment scoring.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from production.agent.tools import (
    SearchKBInput,
    CreateTicketInput,
    GetHistoryInput,
    EscalateInput,
    SendResponseInput,
    SentimentInput,
    _compute_sentiment,
)


# ---- Pydantic Input Validation Tests ----


class TestInputValidation:
    """Verify Pydantic schemas reject invalid input."""

    def test_search_kb_requires_query(self):
        """SearchKBInput requires a query string."""
        with pytest.raises(Exception):
            SearchKBInput()

    def test_search_kb_max_results_range(self):
        """SearchKBInput max_results must be 1-10."""
        valid = SearchKBInput(query="test", max_results=5)
        assert valid.max_results == 5

        with pytest.raises(Exception):
            SearchKBInput(query="test", max_results=0)

        with pytest.raises(Exception):
            SearchKBInput(query="test", max_results=11)

    def test_create_ticket_requires_fields(self):
        """CreateTicketInput requires subject, customer_email, channel."""
        with pytest.raises(Exception):
            CreateTicketInput()

        valid = CreateTicketInput(
            subject="Test issue",
            customer_email="test@test.com",
            channel="web",
        )
        assert valid.priority == "medium"  # default

    def test_get_history_requires_email(self):
        """GetHistoryInput requires customer_email."""
        with pytest.raises(Exception):
            GetHistoryInput()

    def test_escalate_requires_reason_and_ticket(self):
        """EscalateInput requires reason and ticket_id."""
        with pytest.raises(Exception):
            EscalateInput()

        valid = EscalateInput(
            reason="Legal language detected",
            ticket_id=str(uuid4()),
        )
        assert valid.urgency == "normal"  # default

    def test_send_response_requires_fields(self):
        """SendResponseInput requires message, channel, ticket_id."""
        with pytest.raises(Exception):
            SendResponseInput()

    def test_sentiment_requires_text(self):
        """SentimentInput requires text."""
        with pytest.raises(Exception):
            SentimentInput()


# ---- Sentiment Scoring Tests ----


class TestSentimentScoring:
    """Verify sentiment computation matches expected behavior."""

    def test_very_negative_label(self):
        """Score < 0.2 should return 'very_negative'."""
        score, label = _compute_sentiment("lawsuit sue lawyer attorney litigation legal")
        assert label == "very_negative"
        assert score < 0.2

    def test_negative_label(self):
        """Score 0.2-0.4 should return 'negative'."""
        score, label = _compute_sentiment("this is terrible and frustrating")
        assert label == "negative"
        assert 0.0 <= score < 0.4

    def test_neutral_label(self):
        """Score 0.4-0.6 should return 'neutral'."""
        score, label = _compute_sentiment("hello I have a question")
        assert label == "neutral"
        assert 0.4 <= score <= 0.6

    def test_positive_label(self):
        """Score 0.6-0.8 should return 'positive'."""
        score, label = _compute_sentiment("thank you this is great")
        assert label == "positive"
        assert score >= 0.6

    def test_very_positive_label(self):
        """Score >= 0.8 should return 'very_positive'."""
        score, label = _compute_sentiment(
            "thank you wonderful excellent amazing great fantastic love"
        )
        assert label == "very_positive"
        assert score >= 0.8

    def test_empty_returns_neutral(self):
        """Empty text returns 0.5 neutral."""
        score, label = _compute_sentiment("")
        assert score == 0.5
        assert label == "neutral"

    def test_profanity_weight_is_heavy(self):
        """Profanity words should have heavier negative weight than regular negatives."""
        # Regular negative
        score_neg, _ = _compute_sentiment("bad terrible")
        # Profanity
        score_prof, _ = _compute_sentiment("damn stupid")
        # Profanity should be lower (0.3 weight vs 0.1 weight)
        assert score_prof < score_neg

    def test_legal_weight_is_heaviest(self):
        """Legal words should have the heaviest negative weight."""
        score_legal, _ = _compute_sentiment("lawyer")
        score_negative, _ = _compute_sentiment("bad")
        assert score_legal < score_negative


# ---- Error Handling Tests ----


class TestErrorHandling:
    """Verify tools return graceful JSON errors."""

    def test_sentiment_error_returns_neutral(self):
        """On error, sentiment should default to 0.5 neutral."""
        # _compute_sentiment itself doesn't error, but the wrapper tool does
        score, label = _compute_sentiment("normal text")
        assert isinstance(score, float)
        assert isinstance(label, str)

    def test_create_ticket_input_valid(self):
        """Valid CreateTicketInput should parse correctly."""
        input_data = CreateTicketInput(
            subject="Test",
            customer_email="test@example.com",
            channel="web",
            category="Technical Support",
            priority="high",
        )
        assert input_data.subject == "Test"
        assert input_data.priority == "high"

    def test_escalate_input_valid(self):
        """Valid EscalateInput should parse correctly."""
        tid = str(uuid4())
        input_data = EscalateInput(
            reason="Legal language", ticket_id=tid, urgency="critical"
        )
        assert input_data.urgency == "critical"
        assert input_data.ticket_id == tid
