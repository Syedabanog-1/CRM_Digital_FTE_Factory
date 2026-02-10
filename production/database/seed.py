"""Seed the knowledge base from context/product-docs.md with vector embeddings."""

import asyncio
import os
import re
import sys

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from production.config import settings
from production.database import queries


async def generate_embedding(text: str) -> list[float] | None:
    """Generate embedding using OpenAI text-embedding-3-small."""
    if not settings.openai_api_key:
        print("WARNING: No OPENAI_API_KEY set. Skipping embeddings.")
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text[:8000],  # Limit input length
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"WARNING: Embedding generation failed: {e}")
        return None


def parse_product_docs(filepath: str) -> list[dict]:
    """Parse product-docs.md into knowledge base entries."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    entries = []
    sections = re.split(r"\n## ", content)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")
        title = lines[0].lstrip("# ").strip()
        body = "\n".join(lines[1:]).strip()

        if not title or not body:
            continue

        # Infer category from title
        title_lower = title.lower()
        if any(
            kw in title_lower for kw in ["analytics", "insight", "report", "dashboard"]
        ):
            category = "analytics"
        elif any(
            kw in title_lower for kw in ["integration", "api", "connect", "sync"]
        ):
            category = "integrations"
        elif any(kw in title_lower for kw in ["task", "project", "workflow", "board"]):
            category = "project_management"
        elif any(
            kw in title_lower for kw in ["security", "permission", "auth", "access"]
        ):
            category = "security"
        elif any(kw in title_lower for kw in ["start", "setup", "install", "quick"]):
            category = "getting_started"
        else:
            category = "general"

        entries.append(
            {
                "title": title,
                "content": body,
                "category": category,
            }
        )

    return entries


async def seed_knowledge_base(docs_path: str | None = None) -> int:
    """Load product docs into knowledge_base table with embeddings."""
    if docs_path is None:
        # Default path relative to repo root
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        docs_path = os.path.join(repo_root, "context", "product-docs.md")

    if not os.path.exists(docs_path):
        print(f"ERROR: Product docs not found at {docs_path}")
        return 0

    print(f"Parsing product docs from {docs_path}...")
    entries = parse_product_docs(docs_path)
    print(f"Found {len(entries)} knowledge base entries")

    await queries.create_pool()

    count = 0
    for entry in entries:
        print(f"  Seeding: {entry['title']}")
        # Generate embedding for the combined title + content
        embedding_text = f"{entry['title']}\n\n{entry['content']}"
        embedding = await generate_embedding(embedding_text)

        await queries.insert_knowledge_entry(
            title=entry["title"],
            content=entry["content"],
            category=entry["category"],
            embedding=embedding,
        )
        count += 1

    print(f"Seeded {count} knowledge base entries")
    await queries.close_pool()
    return count


async def run_schema(pool=None) -> None:
    """Apply the database schema."""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    if pool is None:
        pool = await queries.create_pool()

    await pool.execute(schema_sql)
    print("Schema applied successfully")


async def main() -> None:
    """Run schema and seed in sequence."""
    print("=== Stage 2 Database Initialization ===")
    await run_schema()
    count = await seed_knowledge_base()
    print(f"=== Done: {count} entries seeded ===")


if __name__ == "__main__":
    asyncio.run(main())
