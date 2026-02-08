"""Channel enum and formatting configuration."""

from enum import Enum
from pydantic import BaseModel


class Channel(str, Enum):
    """Supported communication channels."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


class ChannelConfig(BaseModel):
    """Formatting configuration for a channel."""

    channel: Channel
    max_length: int
    tone: str
    greeting: bool
    signature: bool
    display_label: str


CHANNEL_CONFIGS: dict[Channel, ChannelConfig] = {
    Channel.EMAIL: ChannelConfig(
        channel=Channel.EMAIL,
        max_length=500,  # words
        tone="formal",
        greeting=True,
        signature=True,
        display_label="Email",
    ),
    Channel.WHATSAPP: ChannelConfig(
        channel=Channel.WHATSAPP,
        max_length=300,  # characters preferred, 1600 absolute
        tone="conversational",
        greeting=False,
        signature=False,
        display_label="WhatsApp",
    ),
    Channel.WEB_FORM: ChannelConfig(
        channel=Channel.WEB_FORM,
        max_length=300,  # words
        tone="semi-formal",
        greeting=True,
        signature=False,
        display_label="Web Form",
    ),
}
