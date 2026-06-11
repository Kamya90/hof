# src/deduplicator.py
# Layer 2: Deduplication
#
# Simplified version — URL deduplication only.
# Semantic (embedding) deduplication is skipped for now because:
#   1. Free tier Gemini embeddings are rate-limited to 100/min
#   2. At early stage you have no stories in the DB to compare against
#   3. URL deduplication catches 80% of duplicates anyway
#
# Add semantic deduplication back in Month 2 when you have
# real story history and optionally a paid API tier.

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def url_exists(url: str) -> bool:
    """Check if this exact URL is already saved in the database."""
    result = (
        supabase.table("stories")
        .select("id")
        .eq("url", url)
        .limit(1)
        .execute()
    )
    return len(result.data) > 0


def deduplicate(stories: list[dict]) -> tuple[list[dict], dict]:
    """
    Remove duplicate stories using URL matching.

    Returns:
        unique_stories — stories not already in the database
        stats          — counts for pipeline logging
    """
    stats = {
        "total":          len(stories),
        "url_dupes":      0,
        "semantic_dupes": 0,
        "unique":         0
    }

    seen_urls = set()
    unique    = []

    for story in stories:
        url = story.get("url", "")

        # Skip if already in database
        if url and url_exists(url):
            stats["url_dupes"] += 1
            continue

        # Skip if already seen in this batch
        if url in seen_urls:
            stats["url_dupes"] += 1
            continue

        seen_urls.add(url)
        story["_embedding"] = None  # no embedding for now
        unique.append(story)

    stats["unique"] = len(unique)
    return unique, stats