"""Data models for the Customer Success AI Agent."""

from .channel import Channel, ChannelConfig, CHANNEL_CONFIGS
from .customer import Customer, CustomerIdentifier
from .conversation import Conversation
from .message import Message
from .ticket import Ticket
from .knowledge_base import KnowledgeBaseEntry

__all__ = [
    "Channel",
    "ChannelConfig",
    "CHANNEL_CONFIGS",
    "Customer",
    "CustomerIdentifier",
    "Conversation",
    "Message",
    "Ticket",
    "KnowledgeBaseEntry",
]
