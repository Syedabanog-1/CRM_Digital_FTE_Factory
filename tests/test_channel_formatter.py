"""Tests for US2: Channel formatter service."""

import pytest
from src.models.channel import Channel
from src.services.channel_formatter import ChannelFormatter


@pytest.fixture
def formatter():
    return ChannelFormatter()


class TestEmailFormatting:
    def test_email_has_greeting(self, formatter):
        result = formatter.format("Here is your answer.", Channel.EMAIL, customer_name="Alice")
        assert "Dear Alice" in result or "Hello Alice" in result

    def test_email_has_signature(self, formatter):
        result = formatter.format("Here is your answer.", Channel.EMAIL)
        assert "TechCorp Support" in result or "Best regards" in result

    def test_email_is_formal_tone(self, formatter):
        result = formatter.format("Fix it.", Channel.EMAIL)
        # Should expand into a formal response
        assert len(result) > len("Fix it.")

    def test_email_respects_word_limit(self, formatter):
        long_text = " ".join(["word"] * 600)
        result = formatter.format(long_text, Channel.EMAIL)
        word_count = len(result.split())
        assert word_count <= 550  # some slack for greeting/signature


class TestWhatsAppFormatting:
    def test_whatsapp_no_greeting(self, formatter):
        result = formatter.format("Your answer.", Channel.WHATSAPP)
        assert not result.startswith("Dear")
        assert not result.startswith("Hello")

    def test_whatsapp_concise(self, formatter):
        result = formatter.format("Short answer here.", Channel.WHATSAPP)
        assert len(result) <= 1600  # absolute max

    def test_whatsapp_truncates_long_messages(self, formatter):
        long_text = "A" * 2000
        result = formatter.format(long_text, Channel.WHATSAPP)
        assert len(result) <= 1600
        assert result.endswith("...")

    def test_whatsapp_preferred_length(self, formatter):
        result = formatter.format("Quick fix: go to Settings.", Channel.WHATSAPP)
        # Short messages should stay under preferred 300 chars
        assert len(result) <= 300


class TestWebFormFormatting:
    def test_web_form_has_brief_greeting(self, formatter):
        result = formatter.format("Your answer.", Channel.WEB_FORM, customer_name="Bob")
        assert "Hi Bob" in result or "Hello Bob" in result

    def test_web_form_no_signature(self, formatter):
        result = formatter.format("Answer.", Channel.WEB_FORM)
        assert "Best regards" not in result

    def test_web_form_includes_next_steps(self, formatter):
        result = formatter.format("Here is info.", Channel.WEB_FORM)
        assert "help" in result.lower() or "next" in result.lower() or "support" in result.lower()

    def test_web_form_respects_word_limit(self, formatter):
        long_text = " ".join(["word"] * 400)
        result = formatter.format(long_text, Channel.WEB_FORM)
        word_count = len(result.split())
        assert word_count <= 350  # some slack for greeting
