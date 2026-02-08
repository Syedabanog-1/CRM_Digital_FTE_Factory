"""Tests for US1: Development Dossier validation."""

import json
import os
import pytest

CONTEXT_DIR = os.path.join(os.path.dirname(__file__), "..", "context")


class TestDossierFiles:
    """Verify all five context files exist."""

    REQUIRED_FILES = [
        "company-profile.md",
        "product-docs.md",
        "sample-tickets.json",
        "escalation-rules.md",
        "brand-voice.md",
    ]

    def test_all_five_files_exist(self):
        for fname in self.REQUIRED_FILES:
            path = os.path.join(CONTEXT_DIR, fname)
            assert os.path.isfile(path), f"Missing context file: {fname}"

    def test_files_are_not_empty(self):
        for fname in self.REQUIRED_FILES:
            path = os.path.join(CONTEXT_DIR, fname)
            size = os.path.getsize(path)
            assert size > 100, f"{fname} is too small ({size} bytes)"


class TestSampleTickets:
    """Verify sample-tickets.json has 50+ entries with balanced channels."""

    @pytest.fixture
    def tickets(self):
        path = os.path.join(CONTEXT_DIR, "sample-tickets.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_minimum_50_entries(self, tickets):
        assert len(tickets) >= 50, f"Expected 50+ tickets, got {len(tickets)}"

    def test_has_email_channel(self, tickets):
        email_count = sum(1 for t in tickets if t.get("channel") == "email")
        assert email_count >= 10, f"Expected 10+ email tickets, got {email_count}"

    def test_has_whatsapp_channel(self, tickets):
        wa_count = sum(1 for t in tickets if t.get("channel") == "whatsapp")
        assert wa_count >= 10, f"Expected 10+ whatsapp tickets, got {wa_count}"

    def test_has_web_form_channel(self, tickets):
        wf_count = sum(1 for t in tickets if t.get("channel") == "web_form")
        assert wf_count >= 10, f"Expected 10+ web_form tickets, got {wf_count}"

    def test_channel_balance(self, tickets):
        channels = {}
        for t in tickets:
            ch = t.get("channel", "unknown")
            channels[ch] = channels.get(ch, 0) + 1
        # No single channel should have more than 60% of tickets
        total = len(tickets)
        for ch, count in channels.items():
            assert count / total <= 0.6, f"Channel {ch} is over-represented: {count}/{total}"

    def test_has_escalation_tickets(self, tickets):
        escalations = [t for t in tickets if t.get("expected_action") == "escalate"]
        assert len(escalations) >= 10, f"Expected 10+ escalation tickets, got {len(escalations)}"

    def test_tickets_have_required_fields(self, tickets):
        required_fields = ["id", "customer_email", "channel", "message"]
        for t in tickets:
            for field in required_fields:
                assert field in t, f"Ticket {t.get('id', '?')} missing field: {field}"


class TestProductDocs:
    """Verify product-docs.md covers at least 5 features."""

    def test_covers_minimum_features(self):
        path = os.path.join(CONTEXT_DIR, "product-docs.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Count level-2 headings as feature sections
        headings = [line for line in content.split("\n") if line.startswith("## ")]
        assert len(headings) >= 5, f"Expected 5+ feature sections, got {len(headings)}"


class TestEscalationRules:
    """Verify escalation rules define all required triggers."""

    def test_defines_all_triggers(self):
        path = os.path.join(CONTEXT_DIR, "escalation-rules.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
        triggers = ["pricing", "refund", "legal", "lawyer", "profanity", "human"]
        for trigger in triggers:
            assert trigger in content, f"Escalation rules missing trigger: {trigger}"
