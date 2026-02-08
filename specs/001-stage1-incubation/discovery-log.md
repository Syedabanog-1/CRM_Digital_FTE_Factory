# Discovery Log: Stage 1 Incubation

**Feature**: 001-stage1-incubation
**Date**: 2026-02-08
**Status**: Complete

## Discovered Requirements

1. **Ticket-before-response guardrail**: Constitution requires creating a ticket before generating any response. Implemented in message processor flow.
2. **Sentiment-before-close guardrail**: Must check sentiment score before allowing conversation status to transition to "resolved."
3. **Competitor filtering**: Agent must never discuss competitor products. Implemented as an escalation trigger with guardrail flag.
4. **Feature-promise prevention**: LLM system prompt explicitly instructs "never promise undocumented features."
5. **WhatsApp absolute limit**: Constitution specifies 1600-character absolute max in addition to 300-character preferred limit.
6. **Non-English handling**: Prototype responds in English regardless of input language. Non-English messages are treated as normal queries.

## Channel-Specific Patterns

### Email Patterns
- Customers write longer, more formal messages (avg 150-300 words)
- Expect detailed responses with step-by-step instructions
- Include signatures and context from prior conversations
- Higher expectation for ticket reference numbers
- Billing and legal issues are more common via email

### WhatsApp Patterns
- Messages are short (avg 10-30 words)
- Casual tone with abbreviations and emojis
- Expect quick responses under 300 characters
- More likely to send follow-up messages rapidly
- Technical troubleshooting is harder due to brevity

### Web Form Patterns
- Medium-length messages (avg 50-100 words)
- Semi-formal tone
- Often include structured information (steps, browser, OS)
- Expect a "next steps" section in responses
- Bug reports are most common via web form

## Refined Escalation Rules

- **Pricing disguised as features**: Queries like "What features come with each subscription tier?" trigger escalation because "subscription" is a pricing keyword.
- **Compound triggers**: Messages with legal threats AND profanity get the highest-priority escalation reason (legal > emergency > human request > pricing > profanity).
- **Competitor comparisons**: Any mention of Asana, Jira, Monday.com, Trello, ClickUp, etc. triggers guardrail escalation.

## Edge Cases — Email Channel (10+)

1. **Empty email body**: Agent responds with "I notice your message appears empty. Could you please describe how I can help you?"
2. **Extremely long email (5000+ chars)**: Processed normally; response truncated to 500-word limit
3. **Non-English email**: Agent responds in English with help documentation
4. **Email with only attachment reference**: Agent cannot process attachments, responds with text-only notice
5. **Pricing disguised as feature inquiry**: Escalated via pricing keyword detection
6. **Multiple questions in one email**: Agent addresses the most relevant KB match; conversation memory tracks topics
7. **Reply to closed ticket**: Creates a new conversation/ticket
8. **Email from two different addresses (same person)**: Treated as separate customers in Stage 1
9. **Email with legal threat AND feature question**: Legal trigger takes priority, entire message escalated
10. **Formal complaint without profanity**: Not escalated unless explicit human request or legal terms present
11. **Auto-generated emails (OOO, delivery receipts)**: Processed as normal messages

## Edge Cases — WhatsApp Channel (10+)

1. **Emoji-only message**: Agent responds asking for clarification in text
2. **Single character message ("?")**: Treated as empty-ish, agent asks for more detail
3. **Message exceeding 1600 chars**: Truncated with "..." before delivery
4. **Media attachment (image, document)**: Not supported in Stage 1; agent responds text-only
5. **Rapid successive messages (<5s apart)**: Each processed independently, same conversation
6. **WhatsApp from new number not linked to email**: CustomerResolver returns None; agent asks for email
7. **Mixed language message (English + emoji)**: Processed for English keywords
8. **Message with only special characters**: Agent asks for clarification
9. **Profanity in casual context**: Still triggers escalation (keyword-based, no context awareness)
10. **URL-only message**: Processed as-is, likely no KB match
11. **Voice message transcription**: Not supported in Stage 1

## Edge Cases — Web Form Channel (10+)

1. **Form submitted with empty message field**: Agent responds with empty message handler
2. **HTML/script injection in message**: Pydantic model stores raw text; no rendering risk in CLI prototype
3. **Very long form submission (2000+ words)**: Processed normally; response truncated to 300 words
4. **Form submitted multiple times rapidly**: Each creates a separate ticket
5. **Non-ASCII characters in name field**: Handled by Python str, no encoding issues
6. **Feature request via web form**: Not escalated; agent acknowledges and provides relevant docs
7. **Bug report with detailed steps**: Agent matches against KB troubleshooting sections
8. **Web form from guest (no account)**: Agent processes without customer history
9. **Feedback-only message (no question)**: Agent acknowledges positively
10. **Ambiguous sentiment near threshold (0.3-0.35)**: Currently not escalated; threshold is strict < 0.3
11. **Multiple topics in one submission**: Agent uses KB search to find most relevant match

## Performance Baseline

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| Response time (without LLM) | <3s | ~0.05s | PASS |
| Response time (with LLM fallback) | <3s | ~0.5s | PASS |
| KB search accuracy | >85% | ~90% on sample queries | PASS |
| Escalation detection accuracy | 100% for defined triggers | 100% on sample tickets | PASS |
| Channel formatting correctness | All 3 channels | All 3 pass | PASS |
| Test suite pass rate | 100% | 128/128 (100%) | PASS |
| Sample ticket count | 50+ | 55 | PASS |
| Edge cases documented | 30+ (10/channel) | 33 | PASS |
