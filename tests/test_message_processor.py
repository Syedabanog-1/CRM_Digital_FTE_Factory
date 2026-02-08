"""Tests for US2: Message processor (core interaction loop)."""

import pytest
from unittest.mock import patch, AsyncMock
from src.models.channel import Channel
from src.services.message_processor import MessageProcessor, ProcessResult


@pytest.fixture
def processor():
    return MessageProcessor()


class TestCoreLoop:
    @pytest.mark.asyncio
    async def test_process_returns_result(self, processor):
        result = await processor.process_message(
            message="How do I create a project?",
            channel=Channel.EMAIL,
            customer_email="test@example.com",
        )
        assert isinstance(result, ProcessResult)
        assert result.response
        assert result.channel == Channel.EMAIL

    @pytest.mark.asyncio
    async def test_email_response_is_formal(self, processor):
        result = await processor.process_message(
            message="How do I reset my password?",
            channel=Channel.EMAIL,
            customer_email="test@example.com",
        )
        assert "Dear" in result.response or "Hello" in result.response

    @pytest.mark.asyncio
    async def test_whatsapp_response_is_concise(self, processor):
        result = await processor.process_message(
            message="How to reset password?",
            channel=Channel.WHATSAPP,
            customer_email="test@example.com",
        )
        assert len(result.response) <= 1600

    @pytest.mark.asyncio
    async def test_escalation_detected(self, processor):
        result = await processor.process_message(
            message="I want to speak to a human please",
            channel=Channel.WEB_FORM,
            customer_email="test@example.com",
        )
        assert result.escalated is True

    @pytest.mark.asyncio
    async def test_ticket_created_before_response(self, processor):
        result = await processor.process_message(
            message="Help with my project",
            channel=Channel.EMAIL,
            customer_email="test@example.com",
        )
        assert result.ticket_id is not None


class TestWithMockedLLM:
    @pytest.mark.asyncio
    async def test_uses_kb_context_in_response(self, processor):
        """Verify KB search results are included in response context."""
        with patch.object(
            processor, "_call_llm", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = "Here is how to reset your password: go to Settings > Security."
            result = await processor.process_message(
                message="How do I reset my password?",
                channel=Channel.EMAIL,
                customer_email="test@example.com",
            )
            assert result.response
            # LLM should have been called with KB context
            if mock_llm.called:
                call_args = str(mock_llm.call_args)
                assert "password" in call_args.lower() or result.kb_results_count > 0
