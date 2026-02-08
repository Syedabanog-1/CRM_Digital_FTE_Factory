"""Channel-aware response formatting service."""

from src.models.channel import Channel


class ChannelFormatter:
    """Formats agent responses appropriately for each channel."""

    WHATSAPP_PREFERRED_LIMIT = 300
    WHATSAPP_ABSOLUTE_LIMIT = 1600
    EMAIL_WORD_LIMIT = 500
    WEB_FORM_WORD_LIMIT = 300

    def format(
        self,
        message: str,
        channel: Channel,
        customer_name: str | None = None,
        ticket_id: str | None = None,
    ) -> str:
        """Format a response message for the target channel."""
        if channel == Channel.EMAIL:
            return self._format_email(message, customer_name, ticket_id)
        elif channel == Channel.WHATSAPP:
            return self._format_whatsapp(message)
        elif channel == Channel.WEB_FORM:
            return self._format_web_form(message, customer_name)
        return message

    def _format_email(
        self,
        message: str,
        customer_name: str | None = None,
        ticket_id: str | None = None,
    ) -> str:
        """Email: formal greeting, body, signature, ticket ref."""
        name = customer_name or "Customer"
        greeting = f"Dear {name},"
        body = self._truncate_by_words(message, self.EMAIL_WORD_LIMIT - 30)

        signature = "\nBest regards,\nTechCorp Support Team"
        if ticket_id:
            signature += f"\nReference: {ticket_id}"

        return f"{greeting}\n\n{body}\n{signature}"

    def _format_whatsapp(self, message: str) -> str:
        """WhatsApp: concise, no greeting, truncate at absolute limit."""
        # No greeting, no signature — just the body
        if len(message) <= self.WHATSAPP_PREFERRED_LIMIT:
            return message

        if len(message) <= self.WHATSAPP_ABSOLUTE_LIMIT:
            return message

        # Truncate at absolute limit
        return message[: self.WHATSAPP_ABSOLUTE_LIMIT - 3] + "..."

    def _format_web_form(
        self, message: str, customer_name: str | None = None
    ) -> str:
        """Web form: brief greeting, body, next-steps footer."""
        name = customer_name or "there"
        greeting = f"Hi {name},"
        body = self._truncate_by_words(message, self.WEB_FORM_WORD_LIMIT - 20)
        footer = "\nNeed more help? Visit our support center or reply to this message."

        return f"{greeting}\n\n{body}\n{footer}"

    def _truncate_by_words(self, text: str, max_words: int) -> str:
        """Truncate text to a maximum word count."""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
