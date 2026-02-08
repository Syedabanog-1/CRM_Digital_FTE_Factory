# Research: Stage 1 Incubation

**Feature**: 001-stage1-incubation
**Date**: 2026-02-07

## R1: Knowledge Base Search Strategy (Prototype)

**Decision**: Use TF-IDF-based text matching with Python's built-in capabilities.

**Rationale**: The prototype needs a simple, dependency-light search. TF-IDF via
`sklearn` or even basic keyword matching provides sufficient accuracy for a test
dataset of ~50 knowledge base articles. Vector search (pgvector) is explicitly
deferred to Stage 2.

**Alternatives considered**:
- Full vector embeddings (OpenAI) - overkill for prototype, adds API cost
- Whoosh full-text search - extra dependency, heavier than needed
- Simple `in` string matching - too inaccurate, high false negatives

**Chosen approach**: Use `difflib.SequenceMatcher` for fuzzy matching combined
with keyword extraction. Zero external dependencies beyond stdlib.

## R2: MCP Server Library

**Decision**: Use the `mcp` Python package (official MCP SDK).

**Rationale**: The official `mcp` package provides the Server class, Tool type
definitions, and stdio transport. It's the canonical implementation and will
make Stage 2 transition seamless.

**Alternatives considered**:
- Custom HTTP server mimicking MCP - non-standard, incompatible with MCP clients
- FastMCP wrapper - adds abstraction layer; direct `mcp` is clearer for prototype

**Chosen approach**: `mcp` package with `Server` class, `@server.tool()` decorators.

## R3: Sentiment Analysis Approach (Prototype)

**Decision**: Keyword-based heuristic scoring.

**Rationale**: The prototype needs basic sentiment detection to trigger escalation
at the 0.3 threshold. A keyword dictionary (positive/negative words) with score
aggregation is sufficient. ML models add complexity without proportional value
at this stage.

**Alternatives considered**:
- TextBlob - external dependency, moderate accuracy
- VADER (NLTK) - better for social media, adds large NLTK download
- OpenAI API call per message - adds latency and cost

**Chosen approach**: Custom keyword dictionary with weighted scoring. Positive
words (+0.1 each), negative words (-0.1 each), profanity (-0.3 each), legal
terms (-0.5 each). Normalized to 0.0-1.0 scale.

## R4: Channel Formatting Strategy

**Decision**: Template-based string formatting with channel-specific rules.

**Rationale**: Each channel has distinct requirements:
- Email: Greeting ("Dear Customer"), body, signature, ticket reference. Max 500 words.
- WhatsApp: No greeting, concise body, emoji-friendly footer. Max 300 chars preferred.
- Web Form: Brief greeting, body, help link. Max 300 words.

**Alternatives considered**:
- Jinja2 templates - adds dependency for simple string formatting
- LLM re-formatting per channel - expensive, unpredictable length

**Chosen approach**: Python f-string templates in `channel_formatter.py` with
per-channel config (max length, tone keywords, greeting/signature toggles).

## R5: In-Memory Storage Design

**Decision**: Python dictionaries keyed by customer ID and conversation ID.

**Rationale**: The prototype needs conversation persistence within a session but
not across restarts. Simple dicts provide O(1) lookup and are trivially
replaceable with PostgreSQL in Stage 2.

**Data structures**:
- `customers: Dict[str, Customer]` - keyed by email
- `conversations: Dict[str, Conversation]` - keyed by conversation_id
- `tickets: Dict[str, Ticket]` - keyed by ticket_id
- `customer_identifiers: Dict[str, str]` - maps phone/alt-email to primary email

**Alternatives considered**:
- SQLite - persistent but adds migration complexity for prototype
- Redis - requires running service, overkill

**Chosen approach**: Plain Python dicts in a `ConversationStore` singleton class.

## R6: LLM Integration for Response Generation

**Decision**: Use OpenAI API (`gpt-4o-mini`) for response generation with
knowledge base context injection.

**Rationale**: The agent needs natural language response generation. Using the
OpenAI API with a system prompt and knowledge base context produces high-quality
responses. `gpt-4o-mini` balances cost and quality for prototype.

**Alternatives considered**:
- Template-only responses (no LLM) - too rigid, poor customer experience
- Local model (Ollama) - requires GPU, complex setup
- Groq API - fast but less established ecosystem

**Chosen approach**: OpenAI `gpt-4o-mini` with system prompt containing channel
instructions and user message augmented with KB search results.
