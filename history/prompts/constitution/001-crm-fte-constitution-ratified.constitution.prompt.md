---
id: 001
title: CRM FTE Constitution Ratified
stage: constitution
date: 2026-02-07
surface: agent
model: claude-opus-4-6
feature: none
branch: master
user: student
command: /sp.constitution
labels: ["constitution", "project-setup", "principles"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
---

## Prompt

CRM Digital FTE Factory - A 24/7 AI Customer Success Employee hackathon project. Core principles: 1) Multi-Channel First - Every feature must work across Gmail, WhatsApp, and Web Form channels with channel-appropriate responses. 2) Agent Factory Paradigm - Claude Code (General Agent) builds the Custom Agent (OpenAI SDK); incubation discovers, specialization produces. 3) PostgreSQL as CRM - No external CRM; the database IS the CRM with customers, conversations, tickets, messages tables. 4) Event-Driven Architecture - Kafka for all message routing between channels and agent processing. 5) Production-Grade Quality - Error handling, Pydantic validation, structured logging, health checks on all components. 6) Test-First Development - Edge cases documented during incubation become automated tests in specialization. Tech stack: Python, FastAPI, OpenAI Agents SDK, PostgreSQL with pgvector, Apache Kafka, Kubernetes, Next.js/React (web form only), MCP protocol. Constraints: No external CRM, no full website (only support form), Twilio sandbox for WhatsApp, response limits (Email 500 words, WhatsApp 300 chars, Web 300 words). Security: No hardcoded secrets, .env for credentials, webhook signature validation.

## Response snapshot

Created the CRM Digital FTE Factory Constitution v1.0.0 with 6 core principles (Multi-Channel First, Agent Factory Paradigm, PostgreSQL as CRM, Event-Driven Architecture, Production-Grade Quality, Test-First Development), technology stack table, hard constraints, escalation rules, guardrails, security requirements, and governance section. All template placeholders filled. Sync impact report confirms compatibility with plan, spec, and tasks templates.

## Outcome

- Impact: Project constitution established; all development governed by 6 principles
- Tests: N/A (governance document)
- Files: .specify/memory/constitution.md (created)
- Next prompts: /sp.specify for stage1-incubation, /sp.plan, /sp.tasks, /sp.implement
- Reflection: Constitution covers all hackathon requirements including multi-channel, CRM-as-database, and staged delivery

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): PASS - all placeholders filled, no bracket tokens remaining
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Begin Stage 1 incubation specification
