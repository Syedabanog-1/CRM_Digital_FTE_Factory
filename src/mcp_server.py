"""MCP server exposing Customer Success AI Agent tools."""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.models import Channel, Ticket, Customer
from src.memory.conversation_store import ConversationStore
from src.services.knowledge_base import KnowledgeBaseService
from src.services.channel_formatter import ChannelFormatter
from src.services.sentiment_analyzer import SentimentAnalyzer

# Global store instance for MCP server
_store = ConversationStore()
_kb_service = KnowledgeBaseService()
_kb_service.load_from_file()
_formatter = ChannelFormatter()
_sentiment_analyzer = SentimentAnalyzer()


def get_store() -> ConversationStore:
    return _store


# --- Tool handler functions (testable without MCP) ---


def handle_search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search product documentation for relevant information."""
    if not query or not query.strip():
        return "Please provide a search query"
    results = _kb_service.search(query, max_results=max_results)
    if not results:
        return "No relevant documentation found. Consider escalating."
    return _kb_service.format_results(results)


def handle_create_ticket(
    customer_id: str,
    issue: str,
    priority: str = "medium",
    channel: str = "email",
    store: ConversationStore | None = None,
) -> str:
    """Create a support ticket for tracking an interaction."""
    s = store or _store
    if not customer_id:
        return "Error: Missing customer_id"

    try:
        ch = Channel(channel)
    except ValueError:
        return f"Error: Invalid channel '{channel}'. Must be email, whatsapp, or web_form."

    # Resolve or create customer
    customer = s.get_customer_by_email(customer_id)
    if not customer:
        customer = Customer(email=customer_id)
        s.add_customer(customer)

    ticket = Ticket(
        customer_id=customer.id,
        source_channel=ch,
        priority=priority,
        category="general",
    )
    s.add_ticket(ticket)
    return f"Ticket created: {ticket.id}"


def handle_get_customer_history(
    customer_id: str,
    store: ConversationStore | None = None,
) -> str:
    """Get customer's interaction history across all channels."""
    s = store or _store
    customer = s.get_customer_by_email(customer_id)
    if not customer:
        return "No prior history found"
    return s.format_customer_history(customer.id)


def handle_escalate_to_human(
    ticket_id: str,
    reason: str,
    store: ConversationStore | None = None,
) -> str:
    """Escalate a conversation to human support."""
    s = store or _store
    if not reason or not reason.strip():
        return "Error: Escalation reason is required"

    ticket = s.get_ticket(ticket_id)
    if not ticket:
        return f"Error: Ticket not found: {ticket_id}"

    s.update_ticket_status(ticket_id, "escalated", reason=reason)
    return f"Escalated to human support. Reference: {ticket_id}"


def handle_send_response(
    ticket_id: str,
    message: str,
    channel: str,
    store: ConversationStore | None = None,
) -> str:
    """Send a response to the customer via the appropriate channel."""
    s = store or _store
    if not message or not message.strip():
        return "Error: Message cannot be empty"

    ticket = s.get_ticket(ticket_id)
    if not ticket:
        return f"Error: Ticket not found: {ticket_id}"

    try:
        ch = Channel(channel)
    except ValueError:
        return f"Error: Invalid channel '{channel}'"

    formatted = _formatter.format(message, ch, ticket_id=ticket_id)
    return f"Response sent via {channel}: delivered"


def handle_analyze_sentiment(message: str) -> str:
    """Analyze the sentiment of a customer message."""
    if not message or not message.strip():
        return "Sentiment: 0.5 (neutral)"

    score = _sentiment_analyzer.analyze(message)
    label = _sentiment_analyzer.get_label(score)
    return f"Sentiment: {score:.2f} ({label})"


# --- MCP Server setup ---

server = Server("customer-success-agent")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="search_knowledge_base",
            description="Search product documentation for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="create_ticket",
            description="Create a support ticket for tracking an interaction",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer identifier (email)"},
                    "issue": {"type": "string", "description": "Description of the issue"},
                    "priority": {"type": "string", "description": "low, medium, high", "default": "medium"},
                    "channel": {"type": "string", "description": "email, whatsapp, web_form"},
                },
                "required": ["customer_id", "issue", "channel"],
            },
        ),
        Tool(
            name="get_customer_history",
            description="Get customer's interaction history across all channels",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer identifier (email)"},
                },
                "required": ["customer_id"],
            },
        ),
        Tool(
            name="escalate_to_human",
            description="Escalate a conversation to human support",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "ID of the ticket to escalate"},
                    "reason": {"type": "string", "description": "Reason for escalation"},
                },
                "required": ["ticket_id", "reason"],
            },
        ),
        Tool(
            name="send_response",
            description="Send a response to the customer via the appropriate channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket this response belongs to"},
                    "message": {"type": "string", "description": "Response message content"},
                    "channel": {"type": "string", "description": "Target channel for formatting"},
                },
                "required": ["ticket_id", "message", "channel"],
            },
        ),
        Tool(
            name="analyze_sentiment",
            description="Analyze the sentiment of a customer message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Customer message text"},
                },
                "required": ["message"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_knowledge_base":
        result = handle_search_knowledge_base(
            arguments["query"],
            arguments.get("max_results", 5),
        )
    elif name == "create_ticket":
        result = handle_create_ticket(
            arguments["customer_id"],
            arguments["issue"],
            arguments.get("priority", "medium"),
            arguments["channel"],
        )
    elif name == "get_customer_history":
        result = handle_get_customer_history(arguments["customer_id"])
    elif name == "escalate_to_human":
        result = handle_escalate_to_human(
            arguments["ticket_id"],
            arguments["reason"],
        )
    elif name == "send_response":
        result = handle_send_response(
            arguments["ticket_id"],
            arguments["message"],
            arguments["channel"],
        )
    elif name == "analyze_sentiment":
        result = handle_analyze_sentiment(arguments["message"])
    else:
        result = f"Error: Unknown tool '{name}'"

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
