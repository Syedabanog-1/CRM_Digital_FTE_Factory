"""Knowledge base search service using fuzzy text matching."""

import os
import re
from difflib import SequenceMatcher
from src.models.knowledge_base import KnowledgeBaseEntry


class KnowledgeBaseService:
    """Searches product documentation for relevant information."""

    def __init__(self):
        self.entries: list[KnowledgeBaseEntry] = []

    def load_from_file(self, path: str | None = None) -> None:
        """Load and parse product-docs.md into searchable entries."""
        if path is None:
            path = os.path.join(
                os.path.dirname(__file__), "..", "..", "context", "product-docs.md"
            )
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.entries = self._parse_markdown(content)

    def _parse_markdown(self, content: str) -> list[KnowledgeBaseEntry]:
        """Parse markdown into knowledge base entries by ## headings."""
        entries = []
        sections = re.split(r"^## ", content, flags=re.MULTILINE)

        for section in sections[1:]:  # skip content before first ##
            lines = section.strip().split("\n")
            title = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if not body:
                continue

            # Extract keywords from title and ### subheadings
            keywords = self._extract_keywords(title + " " + body)
            entries.append(
                KnowledgeBaseEntry(
                    title=title,
                    content=body,
                    category=self._infer_category(title),
                    keywords=keywords,
                )
            )
        return entries

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract significant keywords from text."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "and",
            "but", "or", "nor", "not", "so", "yet", "both", "each",
            "how", "what", "which", "who", "whom", "this", "that",
            "these", "those", "it", "its", "i", "you", "your", "we",
            "they", "my", "our", "his", "her", "if", "then", "than",
        }
        words = re.findall(r"[a-zA-Z]{3,}", text.lower())
        seen = set()
        keywords = []
        for w in words:
            if w not in stop_words and w not in seen:
                seen.add(w)
                keywords.append(w)
        return keywords[:20]

    def _infer_category(self, title: str) -> str:
        """Infer category from section title."""
        title_lower = title.lower()
        if any(w in title_lower for w in ("task", "project", "kanban", "sprint")):
            return "project_management"
        if any(w in title_lower for w in ("analytic", "report", "insight", "dashboard")):
            return "analytics"
        if any(w in title_lower for w in ("integrat", "connect", "slack", "github")):
            return "integrations"
        if any(w in title_lower for w in ("notif", "alert", "digest")):
            return "notifications"
        if any(w in title_lower for w in ("api", "dev", "webhook", "rest")):
            return "developer"
        if any(w in title_lower for w in ("collab", "team", "comment", "share")):
            return "collaboration"
        if any(w in title_lower for w in ("account", "password", "billing", "sso")):
            return "account"
        return "general"

    def search(self, query: str, max_results: int = 5) -> list[KnowledgeBaseEntry]:
        """Search entries by fuzzy matching query against titles and content."""
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        query_keywords = set(re.findall(r"[a-zA-Z]{3,}", query_lower))

        scored: list[tuple[float, KnowledgeBaseEntry]] = []

        for entry in self.entries:
            score = self._score_entry(query_lower, query_keywords, entry)
            if score > 0.15:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]

    def _score_entry(
        self, query: str, query_keywords: set[str], entry: KnowledgeBaseEntry
    ) -> float:
        """Score an entry's relevance to the query."""
        title_lower = entry.title.lower()
        content_lower = entry.content.lower()[:500]  # first 500 chars for speed

        # Title similarity (highest weight)
        title_sim = SequenceMatcher(None, query, title_lower).ratio()

        # Keyword overlap
        entry_keywords = set(kw.lower() for kw in entry.keywords)
        if query_keywords and entry_keywords:
            overlap = len(query_keywords & entry_keywords) / len(query_keywords)
        else:
            overlap = 0.0

        # Content substring match
        content_match = 0.0
        for kw in query_keywords:
            if kw in content_lower:
                content_match += 0.15

        score = (title_sim * 0.4) + (overlap * 0.35) + min(content_match, 0.25)
        return score

    def format_results(self, results: list[KnowledgeBaseEntry]) -> str:
        """Format search results for display or LLM context injection."""
        if not results:
            return "No relevant documentation found. Consider escalating."

        parts = []
        for i, entry in enumerate(results, 1):
            snippet = entry.content[:300].strip()
            if len(entry.content) > 300:
                snippet += "..."
            parts.append(f"**{i}. {entry.title}**\n{snippet}")

        return "\n\n".join(parts)
