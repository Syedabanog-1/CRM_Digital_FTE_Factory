"""Tests for US2: Escalation engine service."""

import pytest
from src.services.escalation_engine import EscalationEngine


@pytest.fixture
def engine():
    return EscalationEngine()


class TestPricingEscalation:
    def test_pricing_question_escalates(self, engine):
        result = engine.check("How much does the Pro plan cost?")
        assert result.should_escalate is True
        assert "pricing" in result.reason.lower() or "billing" in result.reason.lower()

    def test_refund_request_escalates(self, engine):
        result = engine.check("I want a refund for last month's charge")
        assert result.should_escalate is True

    def test_billing_inquiry_escalates(self, engine):
        result = engine.check("There's an error on my invoice")
        assert result.should_escalate is True


class TestLegalEscalation:
    def test_lawyer_mention_escalates(self, engine):
        result = engine.check("I'm going to contact my lawyer about this")
        assert result.should_escalate is True
        assert "legal" in result.reason.lower()

    def test_sue_mention_escalates(self, engine):
        result = engine.check("I will sue your company")
        assert result.should_escalate is True

    def test_attorney_mention_escalates(self, engine):
        result = engine.check("My attorney will be in touch")
        assert result.should_escalate is True


class TestProfanityEscalation:
    def test_profanity_escalates(self, engine):
        result = engine.check("This damn product is garbage!")
        assert result.should_escalate is True

    def test_aggressive_language_escalates(self, engine):
        result = engine.check("This is the worst service I've ever seen, you people are useless!")
        assert result.should_escalate is True


class TestHumanRequestEscalation:
    def test_speak_to_human_escalates(self, engine):
        result = engine.check("I want to speak to a human please")
        assert result.should_escalate is True

    def test_real_person_escalates(self, engine):
        result = engine.check("Can I talk to a real person?")
        assert result.should_escalate is True

    def test_manager_request_escalates(self, engine):
        result = engine.check("Let me speak to your manager")
        assert result.should_escalate is True


class TestSentimentEscalation:
    def test_low_sentiment_escalates(self, engine):
        result = engine.check("This is terrible awful horrible", sentiment_score=0.2)
        assert result.should_escalate is True

    def test_high_sentiment_does_not_escalate(self, engine):
        result = engine.check("Thanks for the help!", sentiment_score=0.8)
        assert result.should_escalate is False


class TestNoEscalation:
    def test_normal_question_no_escalation(self, engine):
        result = engine.check("How do I create a new project in TaskFlow?")
        assert result.should_escalate is False

    def test_feature_request_no_escalation(self, engine):
        result = engine.check("It would be nice to have dark mode")
        assert result.should_escalate is False

    def test_positive_feedback_no_escalation(self, engine):
        result = engine.check("The new dashboard is great, love it!")
        assert result.should_escalate is False


class TestEdgeCases:
    def test_disguised_pricing_escalates(self, engine):
        result = engine.check("What features come with each subscription tier?")
        assert result.should_escalate is True

    def test_competitor_mention_flagged(self, engine):
        result = engine.check("Can you compare TechCorp to Asana?")
        assert result.should_escalate is True or result.guardrail_triggered is True
