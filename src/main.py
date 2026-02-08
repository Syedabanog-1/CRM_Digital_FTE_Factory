"""CLI entry point for testing the Customer Success AI Agent prototype."""

import asyncio
import sys

from src.models.channel import Channel
from src.memory.conversation_store import ConversationStore
from src.services.message_processor import MessageProcessor
from src.services.sentiment_analyzer import SentimentAnalyzer


def print_header():
    print("=" * 60)
    print("  TechCorp Customer Success AI Agent — Prototype CLI")
    print("=" * 60)
    print()


def select_channel() -> Channel:
    print("Select channel:")
    print("  1. Email")
    print("  2. WhatsApp")
    print("  3. Web Form")
    while True:
        choice = input("\nChannel (1/2/3): ").strip()
        if choice == "1":
            return Channel.EMAIL
        elif choice == "2":
            return Channel.WHATSAPP
        elif choice == "3":
            return Channel.WEB_FORM
        print("Invalid choice. Enter 1, 2, or 3.")


async def main():
    print_header()

    store = ConversationStore()
    processor = MessageProcessor(store=store)
    sentiment_analyzer = SentimentAnalyzer()

    # Get customer info
    email = input("Customer email: ").strip()
    if not email:
        email = "demo@example.com"

    name = input("Customer name (optional): ").strip() or None
    channel = select_channel()

    print(f"\nChannel: {channel.value} | Customer: {email}")
    print("Commands: 'quit' to exit, 'channel' to switch, 'status' for conversation info")
    print("-" * 60)

    while True:
        try:
            message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if message.lower() == "quit":
            print("Goodbye!")
            break

        if message.lower() == "channel":
            channel = select_channel()
            print(f"Switched to {channel.value}")
            continue

        if message.lower() == "status":
            customer = store.get_customer_by_email(email)
            if customer:
                convs = store.get_conversations_by_customer(customer.id)
                tickets = store.get_tickets_by_customer(customer.id)
                print(f"\n  Customer: {email}")
                print(f"  Conversations: {len(convs)}")
                print(f"  Tickets: {len(tickets)}")
                for c in convs:
                    sentiment_label = ""
                    if c.sentiment_score is not None:
                        label = sentiment_analyzer.get_label(c.sentiment_score)
                        sentiment_label = f" | Sentiment: {c.sentiment_score:.2f} ({label})"
                    print(f"    - {c.initial_channel.value} | {c.status}{sentiment_label}")
            else:
                print("  No conversation history yet.")
            continue

        if not message:
            continue

        result = await processor.process_message(
            message=message,
            channel=channel,
            customer_email=email,
            customer_name=name,
        )

        # Display result
        status = "[ESCALATED]" if result.escalated else "[RESPONSE]"
        sentiment_info = ""
        if result.sentiment_score is not None:
            label = sentiment_analyzer.get_label(result.sentiment_score)
            sentiment_info = f" | Sentiment: {result.sentiment_score:.2f} ({label})"

        print(f"\n{status} (Ticket: {result.ticket_id}{sentiment_info})")
        if result.escalated:
            print(f"Reason: {result.escalation_reason}")
        print("-" * 40)
        print(result.response)
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
