"""Cross-channel customer identification service."""

from src.models import Customer
from src.memory.conversation_store import ConversationStore


class CustomerResolver:
    """Resolves customer identity across channels."""

    def __init__(self, store: ConversationStore):
        self.store = store

    def resolve(
        self,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
    ) -> Customer | None:
        """Resolve a customer by email (primary) or phone (secondary).

        If email is provided and customer exists, return them.
        If email is new, create a new customer.
        If only phone is provided, look up via identifier mapping.
        """
        # Primary: email lookup
        if email:
            existing = self.store.get_customer_by_email(email.lower())
            if existing:
                return existing

            # Create new customer
            customer = Customer(email=email, phone=phone, name=name)
            self.store.add_customer(customer)

            # Register identifiers
            if phone:
                self.store.add_identifier("phone", phone, customer.id)

            return customer

        # Secondary: phone lookup via identifier mapping
        if phone:
            customer_id = self.store.resolve_customer_id("phone", phone)
            if customer_id:
                return self.store.get_customer_by_id(customer_id)

        return None
