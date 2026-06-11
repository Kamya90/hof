# src/sources/reddit.py
# Layer 1: Reddit Source — RSS version
#
# No API key needed. No authentication. No rate limits.
# Every subreddit has a public RSS feed at:
# https://www.reddit.com/r/SUBREDDIT_NAME/top.rss?t=day
#
# We fetch the top posts from the last 24 hours from each
# subreddit. RSS gives us the title, link, and a text snippet
# for each post — enough for the scorer and deduplicator to work.
#
# Why these subreddits:
# r/india          — general Indian news and discussion
# r/IndiaSpeaks    — policy and political debate
# r/IndiaInvestments — economy, markets, finance
# r/developersIndia — tech policy, startup ecosystem
# r/LegalAdviceIndia — law, Supreme Court, rights
# r/delhi / r/mumbai — city-level issues

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SUBREDDITS = [
    "india",
    "IndiaSpeaks",
    "IndiaInvestments",
    "delhi",
    "mumbai"
]

# RSS namespace Reddit uses in its feed
RSS_NS = {
    "media": "http://search.yahoo.com/mrss/",
    "dc":    "http://purl.org/dc/elements/1.1/"
}

HEADERS = {
    # Reddit blocks requests with no user agent
    # This is a standard browser-style header — no login needed
    "User-Agent": "Mozilla/5.0 (compatible; hof-rss-reader/1.0)"
}


def fetch_from_reddit() -> list[dict]:
    """
    Fetch top posts from HOF subreddits via RSS.
    Returns a list of normalised story dicts.
    """
    stories  = []
    seen_urls = set()

    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/top.rss?t=day&limit=15"

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)

            # Reddit returns 429 if you hit it too fast
            # In that case skip this sub and move on
            if response.status_code == 429:
                print(f"[reddit-rss] Rate limited on r/{sub} — skipping")
                continue

            if response.status_code != 200:
                print(f"[reddit-rss] r/{sub} returned {response.status_code} — skipping")
                continue

            # Parse the RSS XML
            root = ET.fromstring(response.content)

            # RSS structure: feed > entry (one per post)
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):

                # Extract title
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                title = title_el.text.strip() if title_el is not None else ""

                # Extract link to the Reddit post
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""

                # Extract the post content / snippet
                content_el = entry.find("{http://www.w3.org/2005/Atom}content")
                content = ""
                if content_el is not None and content_el.text:
                    # RSS content contains HTML — strip the tags
                    content = _strip_html(content_el.text)

                # Extract published date
                published_el = entry.find("{http://www.w3.org/2005/Atom}published")
                published = published_el.text if published_el is not None else ""

                # Skip empty or duplicate posts
                if not title or not link:
                    continue
                if link in seen_urls:
                    continue
                # Skip posts that are just images or videos with no text
                if len(content) < 30 and len(title) < 20:
                    continue

                seen_urls.add(link)

                stories.append({
                    "title":        title,
                    "content":      content[:2000],
                    "url":          link,
                    "source":       f"r/{sub}",
                    "published_at": published,
                    "source_type":  "reddit_rss"
                })

                import time
                time.sleep(1)

        except ET.ParseError as e:
            print(f"[reddit-rss] XML parse error on r/{sub}: {e}")
            continue
        except Exception as e:
            print(f"[reddit-rss] Error fetching r/{sub}: {e}")
            continue

    print(f"[reddit-rss] Fetched {len(stories)} posts across {len(SUBREDDITS)} subreddits")
    return stories


def _strip_html(html: str) -> str:
    """
    Remove HTML tags from RSS content.
    Reddit wraps post content in <div>, <p>, <a> etc.
    We just want the plain text.
    """
    import re
    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse multiple spaces and newlines
    text = re.sub(r"\s+", " ", text)
    return text.strip()