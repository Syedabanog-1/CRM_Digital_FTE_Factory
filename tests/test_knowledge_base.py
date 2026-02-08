"""Tests for US2: Knowledge base search service."""

import pytest
from src.services.knowledge_base import KnowledgeBaseService


@pytest.fixture
def kb_service():
    service = KnowledgeBaseService()
    service.load_from_file()
    return service


class TestKnowledgeBaseSearch:
    def test_exact_match_returns_results(self, kb_service):
        results = kb_service.search("password reset")
        assert len(results) > 0
        assert any("password" in r.content.lower() for r in results)

    def test_fuzzy_match_returns_results(self, kb_service):
        results = kb_service.search("how to reset my pasword")  # typo
        assert len(results) > 0

    def test_empty_query_returns_message(self, kb_service):
        results = kb_service.search("")
        assert len(results) == 0

    def test_no_match_returns_empty(self, kb_service):
        results = kb_service.search("quantum teleportation warp drive")
        assert len(results) == 0

    def test_max_results_limit(self, kb_service):
        results = kb_service.search("project", max_results=2)
        assert len(results) <= 2

    def test_results_have_title_and_content(self, kb_service):
        results = kb_service.search("integration")
        if results:
            assert results[0].title
            assert results[0].content

    def test_default_max_results_is_5(self, kb_service):
        results = kb_service.search("how")
        assert len(results) <= 5

    def test_search_is_case_insensitive(self, kb_service):
        results_lower = kb_service.search("api")
        results_upper = kb_service.search("API")
        assert len(results_lower) == len(results_upper)
