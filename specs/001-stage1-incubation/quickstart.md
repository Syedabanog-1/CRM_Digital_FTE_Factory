# Quickstart: Stage 1 Incubation Prototype

**Feature**: 001-stage1-incubation
**Date**: 2026-02-07

## Prerequisites

- Python 3.11+
- pip (package manager)
- OpenAI API key (for LLM response generation)

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   # Create .env file
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   # OPENAI_API_KEY=sk-your-key-here
   ```

3. **Verify context files exist**:
   ```bash
   ls context/
   # Should show: company-profile.md, product-docs.md,
   # sample-tickets.json, escalation-rules.md, brand-voice.md
   ```

## Running the Prototype

### Interactive CLI Mode
```bash
python -m src.main
# Enter customer messages, specify channel, see formatted responses
```

### MCP Server Mode
```bash
python -m src.mcp_server
# Starts MCP server on stdio transport
```

### Running Tests
```bash
pytest tests/ -v
# Runs all prototype tests including edge cases
```

## Testing the Core Loop

1. Start the CLI: `python -m src.main`
2. Select a channel (email/whatsapp/web_form)
3. Enter a product question (e.g., "How do I reset my password?")
4. Verify the response matches channel formatting rules:
   - Email: formal greeting, detailed body, signature
   - WhatsApp: concise, under 300 chars
   - Web: semi-formal, balanced
5. Test escalation by asking about pricing
6. Test multi-turn by asking a follow-up question

## Validating Deliverables

```bash
# Check dossier completeness
python -c "import json; d=json.load(open('context/sample-tickets.json')); print(f'{len(d)} tickets')"
# Should print: 50+ tickets

# Run test suite
pytest tests/ -v --tb=short

# Check MCP tools
python -c "from src.mcp_server import server; print([t.name for t in server.tools])"
# Should list 5+ tool names
```

## File Structure Overview

| Path | Purpose |
|------|---------|
| `context/` | Development dossier (company context files) |
| `src/models/` | Pydantic data models |
| `src/services/` | Business logic (KB search, formatting, escalation) |
| `src/memory/` | In-memory conversation state |
| `src/mcp_server.py` | MCP server with agent tools |
| `src/main.py` | CLI testing entry point |
| `tests/` | pytest test suite |
