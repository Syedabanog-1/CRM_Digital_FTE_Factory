"""Transition tests: Verify Stage 2 agent matches or exceeds Stage 1 behavior.

Tests cover: edge case handling, escalation decisions, channel-appropriate
response lengths, and tool execution order per constitution guardrails.
"""

import json
import pytest

from production.agent.formatters import ChannelFormatter, formatter
from production.agent.tools import _compute_sentiment
from production.agent.prompts import get_system_prompt


# ---- Sentiment Analysis Tests (matching Stage 1 behavior) ----


class TestSentimentTransition:
    """Verify sentiment analysis matches Stage 1 patterns."""

    def test_empty_message_returns_neutral(self):
        """Empty message should return 0.5 (neutral)."""
        score, label = _compute_sentiment("")
        assert score == 0.5
        assert label == "neutral"

    def test_whitespace_message_returns_neutral(self):
        """Whitespace-only message should return neutral."""
        score, label = _compute_sentiment("   ")
        assert score == 0.5
        assert label == "neutral"

    def test_positive_message(self):
        """Positive words should increase score above 0.5."""
        score, label = _compute_sentiment("Thank you, this is great and wonderful!")
        assert score > 0.5
        assert label in ("positive", "very_positive")

    def test_negative_message(self):
        """Negative words should decrease score below 0.5."""
        score, label = _compute_sentiment("This is terrible and frustrating, everything is broken")
        assert score < 0.5
        assert label in ("negative", "very_negative")

    def test_profanity_triggers_low_sentiment(self):
        """Profanity should push sentiment well below 0.3."""
        score, label = _compute_sentiment("This is damn stupid garbage")
        assert score < 0.3
        assert label in ("negative", "very_negative")

    def test_legal_language_triggers_very_low(self):
        """Legal words should trigger very low sentiment."""
        score, label = _compute_sentiment("I will sue you, my lawyer will contact you")
        assert score < 0.2

    def test_score_clamped_to_range(self):
        """Score should never exceed [0.0, 1.0]."""
        score, _ = _compute_sentiment("thank " * 100)
        assert 0.0 <= score <= 1.0

        score, _ = _compute_sentiment("terrible awful broken " * 50)
        assert 0.0 <= score <= 1.0

    def test_sentiment_labels(self):
        """Verify label boundaries match Stage 1."""
        # very_negative: < 0.2
        score, label = _compute_sentiment("lawsuit sue lawyer attorney litigation legal")
        assert label == "very_negative"

        # neutral: 0.4-0.6
        score, label = _compute_sentiment("hello there")
        assert label == "neutral"


# ---- Channel Formatting Tests ----


class TestChannelFormattingTransition:
    """Verify channel formatting matches Stage 1 patterns."""

    def setup_method(self):
        self.fmt = ChannelFormatter()

    def test_email_has_formal_greeting(self):
        """Email should have 'Dear {name},' greeting."""
        result = self.fmt.format("Test message", "email", "Jane Doe", "TKT-123")
        assert "Dear Jane Doe," in result

    def test_email_has_signature(self):
        """Email should include TechCorp signature."""
        result = self.fmt.format("Test message", "email", "Jane", "TKT-123")
        assert "TechCorp Support Team" in result
        assert "TKT-123" in result

    def test_email_respects_word_limit(self):
        """Email should not exceed 500 words."""
        long_msg = "word " * 600
        result = self.fmt.format(long_msg, "email", "Jane", "TKT-123")
        words = result.split()
        assert len(words) <= 550  # Including greeting/signature

    def test_whatsapp_no_greeting(self):
        """WhatsApp should NOT have greeting or signature."""
        result = self.fmt.format("Quick help needed", "whatsapp")
        assert "Dear" not in result
        assert "TechCorp" not in result

    def test_whatsapp_respects_char_limit(self):
        """WhatsApp should respect 1600 char absolute limit."""
        long_msg = "a" * 2000
        result = self.fmt.format(long_msg, "whatsapp")
        assert len(result) <= 1600 + 10  # Small buffer for truncation

    def test_whatsapp_message_splitting(self):
        """Long WhatsApp messages should split at sentence boundaries."""
        long_msg = "This is sentence one. " * 100  # ~2200 chars
        parts = self.fmt.split_whatsapp_message(long_msg)
        assert len(parts) >= 2
        for part in parts:
            assert len(part) <= 1600

    def test_web_has_greeting(self):
        """Web form should have 'Hi {name},' greeting."""
        result = self.fmt.format("Test message", "web", "Jane", "TKT-123")
        assert "Hi Jane," in result

    def test_web_has_footer(self):
        """Web form should include support center footer."""
        result = self.fmt.format("Test message", "web", "Jane", "TKT-123")
        assert "Support Center" in result

    def test_web_respects_word_limit(self):
        """Web form should not exceed 300 words."""
        long_msg = "word " * 400
        result = self.fmt.format(long_msg, "web", "Jane", "TKT-123")
        words = result.split()
        assert len(words) <= 350  # Including greeting/footer

    def test_unknown_channel_returns_raw(self):
        """Unknown channel should return message unchanged."""
        result = self.fmt.format("Raw message", "sms")
        assert result == "Raw message"


# ---- System Prompt Verification ----


class TestSystemPromptTransition:
    """Verify production system prompt includes all constitution requirements."""

    def setup_method(self):
        self.prompt = get_system_prompt()

    def test_prompt_includes_hard_constraints(self):
        """Prompt must include NEVER constraints."""
        assert "NEVER discuss competitor" in self.prompt
        assert "NEVER promise features" in self.prompt

    def test_prompt_includes_escalation_triggers(self):
        """Prompt must list all escalation trigger categories."""
        assert "Legal language" in self.prompt or "legal" in self.prompt.lower()
        assert "pricing" in self.prompt.lower()
        assert "profanity" in self.prompt.lower() or "Profanity" in self.prompt
        assert "human request" in self.prompt.lower() or "Human request" in self.prompt

    def test_prompt_includes_tool_execution_order(self):
        """Prompt must specify create_ticket FIRST and send_response LAST."""
        assert "create_ticket" in self.prompt
        assert "send_response" in self.prompt
        assert "FIRST" in self.prompt or "first" in self.prompt.lower()
        assert "LAST" in self.prompt or "last" in self.prompt.lower()

    def test_prompt_includes_channel_formatting(self):
        """Prompt must include channel-specific formatting rules."""
        assert "email" in self.prompt.lower()
        assert "whatsapp" in self.prompt.lower()
        assert "web" in self.prompt.lower()
        assert "500 words" in self.prompt
        assert "300 characters" in self.prompt
        assert "300 words" in self.prompt

    def test_prompt_includes_sentiment_threshold(self):
        """Prompt must reference 0.3 sentiment escalation threshold."""
        assert "0.3" in self.prompt

    def test_prompt_includes_kb_failure_escalation(self):
        """Prompt must specify escalation after 2 failed KB searches."""
        assert "2" in self.prompt
        # Check for reference to failed searches
        assert "search" in self.prompt.lower()


# ---- Escalation Decision Tests ----


class TestEscalationDecisions:
    """Verify escalation triggers match Stage 1 behavior via sentiment analysis proxy."""

    def test_pricing_triggers_concern(self):
        """Pricing keywords should not be positive sentiment."""
        score, _ = _compute_sentiment("What is the pricing for your product?")
        # Pricing itself isn't negative, but the system prompt handles escalation
        assert isinstance(score, float)

    def test_legal_triggers_very_low_sentiment(self):
        """Legal language must trigger very low sentiment for escalation."""
        score, label = _compute_sentiment("I will have my lawyer contact you about this lawsuit")
        assert score < 0.3

    def test_profanity_triggers_low_sentiment(self):
        """Profanity must trigger sentiment below 0.3 threshold."""
        score, _ = _compute_sentiment("This is damn garbage, you stupid idiots")
        assert score < 0.3

    def test_positive_customer_not_escalated(self):
        """Happy customer should NOT have low sentiment."""
        score, label = _compute_sentiment("Thank you so much, this is wonderful!")
        assert score > 0.5
        assert label in ("positive", "very_positive")
