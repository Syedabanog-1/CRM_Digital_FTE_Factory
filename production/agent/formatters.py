"""Channel-specific response formatting for production agent.

Transforms agent responses into channel-appropriate format per Constitution Principle I.
"""

# Channel limits per constitution
WHATSAPP_PREFERRED_LIMIT = 300  # characters
WHATSAPP_ABSOLUTE_LIMIT = 1600  # characters
EMAIL_WORD_LIMIT = 500
WEB_WORD_LIMIT = 300


class ChannelFormatter:
    """Format agent responses for specific channels."""

    def format(
        self,
        message: str,
        channel: str,
        customer_name: str | None = None,
        ticket_id: str | None = None,
    ) -> str:
        """Route to channel-specific formatter."""
        if channel == "email":
            return self._format_email(message, customer_name, ticket_id)
        elif channel == "whatsapp":
            return self._format_whatsapp(message)
        elif channel == "web":
            return self._format_web(message, customer_name, ticket_id)
        else:
            return message

    def _format_email(
        self,
        message: str,
        customer_name: str | None = None,
        ticket_id: str | None = None,
    ) -> str:
        """Format for email: formal greeting, body, signature, ticket ref. Max 500 words."""
        name = customer_name or "Valued Customer"
        greeting = f"Dear {name},\n\n"
        body = self._truncate_by_words(message, EMAIL_WORD_LIMIT - 30)  # Room for greeting/signature

        signature_parts = [
            "\n\nBest regards,",
            "TechCorp Support Team",
        ]
        if ticket_id:
            signature_parts.append(f"Reference: {ticket_id}")

        signature = "\n".join(signature_parts)
        return f"{greeting}{body}{signature}"

    def _format_whatsapp(self, message: str) -> str:
        """Format for WhatsApp: concise, no greeting. Max 300 chars preferred, 1600 absolute."""
        # Truncate to preferred limit
        if len(message) <= WHATSAPP_PREFERRED_LIMIT:
            return message

        # If within absolute limit, keep as is but add continuation prompt
        if len(message) <= WHATSAPP_ABSOLUTE_LIMIT:
            return message

        # Split at sentence boundaries for messages exceeding absolute limit
        return self._truncate_at_sentence(message, WHATSAPP_ABSOLUTE_LIMIT)

    def _format_web(
        self,
        message: str,
        customer_name: str | None = None,
        ticket_id: str | None = None,
    ) -> str:
        """Format for web: semi-formal, greeting, footer. Max 300 words."""
        name = customer_name or "there"
        greeting = f"Hi {name},\n\n"
        body = self._truncate_by_words(message, WEB_WORD_LIMIT - 20)  # Room for greeting/footer

        footer_parts = ["\n\nNeed more help? Visit our Support Center."]
        if ticket_id:
            footer_parts.append(f"Your ticket reference: {ticket_id}")

        footer = "\n".join(footer_parts)
        return f"{greeting}{body}{footer}"

    @staticmethod
    def _truncate_by_words(text: str, max_words: int) -> str:
        """Truncate text to a maximum number of words."""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."

    @staticmethod
    def _truncate_at_sentence(text: str, max_chars: int) -> str:
        """Truncate at the last complete sentence within the character limit."""
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        # Find last sentence boundary
        for sep in [". ", "! ", "? "]:
            last_sep = truncated.rfind(sep)
            if last_sep > 0:
                return truncated[: last_sep + 1]

        # No sentence boundary found, truncate at word boundary
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space] + "..."
        return truncated[:max_chars]

    def split_whatsapp_message(self, message: str) -> list[str]:
        """Split a long message into multiple WhatsApp messages at sentence boundaries."""
        if len(message) <= WHATSAPP_ABSOLUTE_LIMIT:
            return [message]

        parts = []
        remaining = message

        while remaining:
            if len(remaining) <= WHATSAPP_ABSOLUTE_LIMIT:
                parts.append(remaining)
                break

            chunk = self._truncate_at_sentence(remaining, WHATSAPP_ABSOLUTE_LIMIT)
            parts.append(chunk)
            remaining = remaining[len(chunk):].strip()

        return parts


# Module-level instance
formatter = ChannelFormatter()
