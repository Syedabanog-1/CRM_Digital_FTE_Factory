"""Escalation decision engine."""

import re
from dataclasses import dataclass


@dataclass
class EscalationResult:
    """Result of an escalation check."""

    should_escalate: bool
    reason: str
    guardrail_triggered: bool = False


class EscalationEngine:
    """Checks messages for escalation triggers per constitution rules."""

    PRICING_KEYWORDS = {
        "price", "pricing", "cost", "how much", "subscription",
        "billing", "invoice", "refund", "charge", "payment",
        "cancel subscription", "downgrade", "upgrade cost",
        "subscription tier", "plan cost", "monthly fee", "annual fee",
    }

    LEGAL_KEYWORDS = {
        "lawyer", "legal", "sue", "attorney", "lawsuit",
        "court", "litigation", "legal action", "regulatory",
    }

    PROFANITY_KEYWORDS = {
        "damn", "hell", "crap", "crap", "crap",
        "crap", "garbage", "useless", "worst", "terrible",
        "awful", "horrible", "pathetic", "incompetent", "stupid",
        "idiot", "ridiculous", "waste of money", "scam",
    }

    HUMAN_REQUEST_KEYWORDS = {
        "speak to a human", "talk to someone", "real person",
        "human agent", "transfer me", "manager", "supervisor",
        "speak to someone", "talk to a human", "real human",
        "live agent", "live person", "human support",
    }

    COMPETITOR_KEYWORDS = {
        "asana", "jira", "monday.com", "trello", "clickup",
        "basecamp", "notion", "linear", "wrike", "smartsheet",
    }

    EMERGENCY_KEYWORDS = {
        "data loss", "security breach", "hacked", "all data gone",
        "system down", "outage", "data deleted",
    }

    SENTIMENT_THRESHOLD = 0.3

    def check(
        self,
        message: str,
        sentiment_score: float | None = None,
        failed_kb_searches: int = 0,
    ) -> EscalationResult:
        """Check a message for escalation triggers."""
        message_lower = message.lower().strip()

        # 1. Legal threats (highest priority)
        if self._matches_any(message_lower, self.LEGAL_KEYWORDS):
            return EscalationResult(
                should_escalate=True,
                reason="Legal threat detected",
            )

        # 2. Emergency
        if self._matches_any(message_lower, self.EMERGENCY_KEYWORDS):
            return EscalationResult(
                should_escalate=True,
                reason="Technical emergency detected",
            )

        # 3. Explicit human request
        if self._matches_any(message_lower, self.HUMAN_REQUEST_KEYWORDS):
            return EscalationResult(
                should_escalate=True,
                reason="Customer requested human agent",
            )

        # 4. Pricing/billing
        if self._matches_any(message_lower, self.PRICING_KEYWORDS):
            return EscalationResult(
                should_escalate=True,
                reason="Pricing/billing inquiry detected",
            )

        # 5. Profanity/aggression
        if self._matches_any(message_lower, self.PROFANITY_KEYWORDS):
            return EscalationResult(
                should_escalate=True,
                reason="Aggressive language detected",
            )

        # 6. Low sentiment
        if sentiment_score is not None and sentiment_score < self.SENTIMENT_THRESHOLD:
            return EscalationResult(
                should_escalate=True,
                reason=f"Low sentiment score ({sentiment_score:.2f})",
            )

        # 7. Failed KB searches
        if failed_kb_searches >= 2:
            return EscalationResult(
                should_escalate=True,
                reason="Unable to find relevant information after multiple searches",
            )

        # 8. Competitor mention (guardrail, not necessarily escalation)
        if self._matches_any(message_lower, self.COMPETITOR_KEYWORDS):
            return EscalationResult(
                should_escalate=True,
                reason="Competitor comparison requested",
                guardrail_triggered=True,
            )

        return EscalationResult(should_escalate=False, reason="")

    def _matches_any(self, text: str, keywords: set[str]) -> bool:
        """Check if text contains any of the keywords."""
        for keyword in keywords:
            if keyword in text:
                return True
        return False
