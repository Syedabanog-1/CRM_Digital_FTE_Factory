"""Core message processing loop — the heart of the agent prototype."""

import os
import uuid
from dataclasses import dataclass, field
from dotenv import load_dotenv

from src.models.channel import Channel
from src.models.message import Message
from src.models.ticket import Ticket
from src.services.knowledge_base import KnowledgeBaseService
from src.services.channel_formatter import ChannelFormatter
from src.services.escalation_engine import EscalationEngine
from src.services.sentiment_analyzer import SentimentAnalyzer
from src.services.customer_resolver import CustomerResolver
from src.memory.conversation_store import ConversationStore

load_dotenv()


@dataclass
class ProcessResult:
    """Result of processing a customer message."""

    response: str
    channel: Channel
    escalated: bool = False
    escalation_reason: str = ""
    ticket_id: str | None = None
    kb_results_count: int = 0
    guardrail_triggered: bool = False
    sentiment_score: float | None = None
    conversation_id: str | None = None


class MessageProcessor:
    """Processes customer messages through the full interaction loop."""

    def __init__(self, store: ConversationStore | None = None):
        self.kb_service = KnowledgeBaseService()
        self.kb_service.load_from_file()
        self.formatter = ChannelFormatter()
        self.escalation_engine = EscalationEngine()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.store = store or ConversationStore()
        self.resolver = CustomerResolver(self.store)
        self._failed_kb_searches: dict[str, int] = {}
        self._openai_client = None

    def _get_openai_client(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key and api_key != "sk-your-key-here":
                    self._openai_client = OpenAI(api_key=api_key)
            except ImportError:
                pass
        return self._openai_client

    async def process_message(
        self,
        message: str,
        channel: Channel,
        customer_email: str,
        customer_name: str | None = None,
        conversation_context: list[dict] | None = None,
    ) -> ProcessResult:
        """Process a customer message through the full interaction loop.

        Flow: resolve customer → load/create conversation → normalize →
              create ticket → analyze sentiment → check escalation →
              search KB → generate response → format → store message → return.
        """
        # 1. Resolve customer identity
        customer = self.resolver.resolve(
            email=customer_email, name=customer_name
        )

        # 2. Load or create conversation
        conv = self.store.get_active_conversation(customer.id, channel)
        if conv is None:
            conv = self.store.create_conversation(customer.id, channel)

        # 3. Normalize message
        normalized = message.strip()
        if not normalized:
            normalized = "(empty message)"

        # 4. Store inbound message
        inbound_msg = Message(
            conversation_id=conv.id,
            channel=channel,
            direction="inbound",
            role="customer",
            content=normalized,
        )
        self.store.add_message(inbound_msg)

        # 5. Analyze sentiment
        sentiment_score = self.sentiment_analyzer.analyze(normalized)
        self.store.update_conversation_sentiment(conv.id, sentiment_score)

        # 6. Create ticket before responding (constitution guardrail C2)
        ticket_id = f"TC-{uuid.uuid4().hex[:6].upper()}"
        ticket = Ticket(
            customer_id=customer.id,
            conversation_id=conv.id,
            source_channel=channel,
            priority="medium",
        )
        ticket.id = ticket_id
        self.store.add_ticket(ticket)

        # 7. Check escalation triggers (including sentiment)
        escalation = self.escalation_engine.check(
            normalized, sentiment_score=sentiment_score
        )
        if escalation.should_escalate:
            self.store.update_ticket_status(
                ticket_id, "escalated", reason=escalation.reason
            )
            self.store.update_conversation_status(conv.id, "escalated")
            escalation_response = self._build_escalation_response(
                escalation.reason, ticket_id, channel
            )
            formatted = self.formatter.format(
                escalation_response, channel, customer_name, ticket_id
            )
            return ProcessResult(
                response=formatted,
                channel=channel,
                escalated=True,
                escalation_reason=escalation.reason,
                ticket_id=ticket_id,
                guardrail_triggered=escalation.guardrail_triggered,
                sentiment_score=sentiment_score,
                conversation_id=conv.id,
            )

        # 8. Search knowledge base
        kb_results = self.kb_service.search(normalized)
        kb_context = self.kb_service.format_results(kb_results)

        # Track failed KB searches per customer
        if not kb_results:
            self._failed_kb_searches[customer_email] = (
                self._failed_kb_searches.get(customer_email, 0) + 1
            )
            if self._failed_kb_searches[customer_email] >= 2:
                gap_check = self.escalation_engine.check(
                    normalized, failed_kb_searches=2
                )
                if gap_check.should_escalate:
                    self.store.update_ticket_status(
                        ticket_id, "escalated", reason=gap_check.reason
                    )
                    escalation_response = self._build_escalation_response(
                        gap_check.reason, ticket_id, channel
                    )
                    formatted = self.formatter.format(
                        escalation_response, channel, customer_name, ticket_id
                    )
                    return ProcessResult(
                        response=formatted,
                        channel=channel,
                        escalated=True,
                        escalation_reason=gap_check.reason,
                        ticket_id=ticket_id,
                        sentiment_score=sentiment_score,
                        conversation_id=conv.id,
                    )
        else:
            self._failed_kb_searches[customer_email] = 0

        # 9. Build conversation context from memory
        if conversation_context is None:
            history_msgs = self.store.get_messages(conv.id)
            conversation_context = []
            for m in history_msgs[-10:]:  # last 10 messages
                role = "user" if m.role == "customer" else "assistant"
                conversation_context.append(
                    {"role": role, "content": m.content}
                )

        # 10. Generate response (LLM or fallback)
        raw_response = await self._generate_response(
            normalized, channel, kb_context, conversation_context
        )

        # 11. Format for channel
        formatted = self.formatter.format(
            raw_response, channel, customer_name, ticket_id
        )

        # 12. Store outbound message
        outbound_msg = Message(
            conversation_id=conv.id,
            channel=channel,
            direction="outbound",
            role="agent",
            content=formatted,
        )
        self.store.add_message(outbound_msg)

        return ProcessResult(
            response=formatted,
            channel=channel,
            escalated=False,
            ticket_id=ticket_id,
            kb_results_count=len(kb_results),
            sentiment_score=sentiment_score,
            conversation_id=conv.id,
        )

    async def _generate_response(
        self,
        message: str,
        channel: Channel,
        kb_context: str,
        conversation_context: list[dict] | None = None,
    ) -> str:
        """Generate a response using LLM or fallback to template."""
        client = self._get_openai_client()
        if client:
            return await self._call_llm(message, channel, kb_context, conversation_context)
        return self._fallback_response(message, kb_context)

    async def _call_llm(
        self,
        message: str,
        channel: Channel,
        kb_context: str,
        conversation_context: list[dict] | None = None,
    ) -> str:
        """Call OpenAI API for response generation."""
        channel_instructions = {
            Channel.EMAIL: "Respond formally. Be thorough and detailed.",
            Channel.WHATSAPP: "Respond concisely. Keep it under 200 characters if possible. Be conversational.",
            Channel.WEB_FORM: "Respond in a semi-formal tone. Include next steps.",
        }

        system_prompt = f"""You are TechCorp's customer support agent. Use ONLY the product documentation provided to answer questions.

Channel: {channel.value}
Style: {channel_instructions.get(channel, '')}

Rules:
- Only reference features documented below. Never promise undocumented features.
- Never discuss competitor products.
- If you cannot find relevant information, say so clearly.
- Be helpful, clear, and empathetic.

Product Documentation:
{kb_context}"""

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_context:
            for ctx in conversation_context[-5:]:  # last 5 messages for context
                messages.append(ctx)

        messages.append({"role": "user", "content": message})

        try:
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            response = self._get_openai_client().chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception:
            return self._fallback_response(message, kb_context)

    def _fallback_response(self, message: str, kb_context: str) -> str:
        """Template-based fallback when LLM is unavailable."""
        if "No relevant documentation found" in kb_context:
            return (
                "I wasn't able to find specific documentation about that topic. "
                "Let me connect you with a team member who can help with your question."
            )
        # Extract first KB result as response basis
        lines = kb_context.split("\n")
        snippet = ""
        for line in lines:
            if line and not line.startswith("**"):
                snippet = line.strip()
                break
        if snippet:
            return f"Based on our documentation: {snippet}"
        return (
            "Thank you for your question. I've found some relevant information "
            "in our documentation that should help. Please check our help center "
            "at docs.techcorp.io for detailed guides."
        )

    def _build_escalation_response(
        self, reason: str, ticket_id: str, channel: Channel
    ) -> str:
        """Build an escalation message for the customer."""
        if channel == Channel.WHATSAPP:
            return (
                f"Connecting you with our support team now. "
                f"Ref: {ticket_id}. They'll reach out shortly."
            )
        return (
            f"I understand this requires specialized assistance. "
            f"I'm connecting you with a member of our support team who can help. "
            f"Your reference number is {ticket_id}."
        )
