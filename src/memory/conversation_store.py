"""In-memory conversation state management."""

from src.models import (
    Channel,
    Customer,
    CustomerIdentifier,
    Conversation,
    Message,
    Ticket,
)


class ConversationStore:
    """Singleton-style in-memory store for all entities."""

    def __init__(self):
        self.customers: dict[str, Customer] = {}  # email -> Customer
        self.conversations: dict[str, Conversation] = {}  # id -> Conversation
        self.messages: dict[str, list[Message]] = {}  # conversation_id -> [Message]
        self.tickets: dict[str, Ticket] = {}  # id -> Ticket
        self.identifiers: dict[str, str] = {}  # (type:value) -> customer_id

    # --- Customer operations ---

    def add_customer(self, customer: Customer) -> None:
        self.customers[customer.email.lower()] = customer

    def get_customer_by_email(self, email: str) -> Customer | None:
        return self.customers.get(email.lower())

    def get_customer_by_id(self, customer_id: str) -> Customer | None:
        for customer in self.customers.values():
            if customer.id == customer_id:
                return customer
        return None

    # --- Conversation operations ---

    def create_conversation(
        self, customer_id: str, channel: Channel
    ) -> Conversation:
        conv = Conversation(customer_id=customer_id, initial_channel=channel)
        self.conversations[conv.id] = conv
        self.messages[conv.id] = []
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self.conversations.get(conversation_id)

    def get_conversations_by_customer(
        self, customer_id: str
    ) -> list[Conversation]:
        return [
            c for c in self.conversations.values()
            if c.customer_id == customer_id
        ]

    def get_active_conversation(
        self, customer_id: str, channel: Channel
    ) -> Conversation | None:
        for conv in self.conversations.values():
            if (
                conv.customer_id == customer_id
                and conv.status == "active"
                and conv.initial_channel == channel
            ):
                return conv
        return None

    def update_conversation_status(
        self, conversation_id: str, status: str
    ) -> None:
        conv = self.conversations.get(conversation_id)
        if conv:
            conv.status = status

    def update_conversation_sentiment(
        self, conversation_id: str, score: float
    ) -> None:
        conv = self.conversations.get(conversation_id)
        if conv:
            conv.sentiment_score = score

    # --- Message operations ---

    def add_message(self, message: Message) -> None:
        if message.conversation_id not in self.messages:
            self.messages[message.conversation_id] = []
        self.messages[message.conversation_id].append(message)

    def get_messages(self, conversation_id: str) -> list[Message]:
        return self.messages.get(conversation_id, [])

    # --- Ticket operations ---

    def add_ticket(self, ticket: Ticket) -> None:
        self.tickets[ticket.id] = ticket

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self.tickets.get(ticket_id)

    def get_tickets_by_customer(self, customer_id: str) -> list[Ticket]:
        return [
            t for t in self.tickets.values() if t.customer_id == customer_id
        ]

    def update_ticket_status(
        self,
        ticket_id: str,
        status: str,
        reason: str | None = None,
    ) -> None:
        ticket = self.tickets.get(ticket_id)
        if ticket:
            ticket.status = status
            if reason:
                ticket.escalation_reason = reason

    # --- Identifier mapping ---

    def add_identifier(
        self, id_type: str, id_value: str, customer_id: str
    ) -> None:
        key = f"{id_type}:{id_value}"
        self.identifiers[key] = customer_id

    def resolve_customer_id(
        self, id_type: str, id_value: str
    ) -> str | None:
        key = f"{id_type}:{id_value}"
        return self.identifiers.get(key)

    # --- History formatting ---

    def format_customer_history(self, customer_id: str) -> str:
        conversations = self.get_conversations_by_customer(customer_id)
        if not conversations:
            return "No prior history found"

        parts = []
        for conv in conversations:
            msgs = self.get_messages(conv.id)
            msg_count = len(msgs)
            parts.append(
                f"- {conv.initial_channel.value} | {conv.started_at.strftime('%Y-%m-%d')} | "
                f"Status: {conv.status} | Messages: {msg_count}"
            )
        return "\n".join(parts)
