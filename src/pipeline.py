import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

from src.sources.newsapi import fetch_from_newsapi
from src.sources.reddit  import fetch_from_reddit
from src.deduplicator    import deduplicate
from src.scorer          import score_batch
from src.classifier      import classify_batch
from src.clusterer       import cluster_stories
from src.controversy     import detect_controversy
from src.framer          import generate_frame, frame_quality_check
from src.debate_scorer   import score_debate
from src.angle_engine    import generate_angles
from src.summariser      import generate_summary_and_impact

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
MAX_STORIES = int(os.getenv("MAX_STORIES_PER_RUN", "12"))


def run_pipeline():
    start = datetime.now(timezone.utc)
    print(f"\n{'='*52}")
    print(f"HOF Pipeline — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*52}")

    print("\n[Layer 1] Ingesting stories...")
    raw = []
    raw.extend(fetch_from_newsapi())
    raw.extend(fetch_from_reddit())
    print(f"          Total ingested: {len(raw)}")
    if not raw:
        print("          No stories fetched.")
        return

    print("\n[Layer 2] Deduplicating...")
    unique, stats = deduplicate(raw)
    print(f"          URL dupes removed:      {stats['url_dupes']}")
    print(f"          Unique stories:         {stats['unique']}")
    if not unique:
        return

    print("\n[Layer 3] Scoring relevance...")
    scored = score_batch(unique)
    passed = [s for s in scored if s["verdict"] == "PASS"]
    review = [s for s in scored if s["verdict"] == "REVIEW"]
    print(f"          PASS:   {len(passed)}")
    print(f"          REVIEW: {len(review)} (manual queue)")
    print(f"          DROP:   {len(unique) - len(scored)}")
    _save_review_queue(review)
    if not passed:
        print("          No stories passed scoring.")
        return

    print("\n[Layer 3B] Classifying systemic vs personal...")
    passed = classify_batch(passed)
    print(f"           After classification: {len(passed)} stories")
    if not passed:
        return

    print("\n[Layer 3C] Clustering related stories...")
    passed = cluster_stories(passed)
    print(f"           After clustering: {len(passed)} debates")

    print("\n[Layer 4] Detecting controversy...")
    for story in passed:
        multiplier = detect_controversy(story)
        story["controversy_score"] = multiplier
        story["final_score"] = round(story.get("score", 0) * multiplier, 1)
        print(f"          [{multiplier:.1f}x] {story['title'][:55]}...")

    passed.sort(key=lambda x: x["final_score"], reverse=True)
    top = passed[:MAX_STORIES]
    print(f"          Top {len(top)} selected")

    print("\n[Layer 5] Generating debate frames...")
    saved = 0
    failed = 0

    for i, story in enumerate(top, 1):
        print(f"          [{i}/{len(top)}] Framing: {story['title'][:50]}...")
        try:
            frame = generate_frame(story)
            passes_qc, issues = frame_quality_check(frame)
            if not passes_qc:
                print(f"                    QC: {', '.join(issues)}")
                frame["needs_review"] = True
                frame["qc_issues"] = issues

            debate_meta = score_debate(story, frame)
            frame.update(debate_meta)
            print(f"                    Debate score: {debate_meta['debate_score']}/10")

            angles = generate_angles(story, frame)
            frame.update(angles)

            enrichment = generate_summary_and_impact(story, frame)
            frame.update(enrichment)
            print(f"                    Hook: {enrichment['hook'][:60]}...")

            _save_story(story, frame)
            saved += 1
        except Exception as e:
            print(f"                    Error: {e}")
            failed += 1

    elapsed = (datetime.now(timezone.utc) - start).seconds
    print(f"\n{'='*52}")
    print(f"Pipeline complete in {elapsed}s")
    print(f"Stories saved: {saved} | Failed: {failed}")
    print(f"{'='*52}\n")


def _save_story(story: dict, frame: dict):
    supabase.table("stories").insert({
        "title":             story.get("title"),
        "source":            story.get("source"),
        "url":               story.get("url"),
        "content":           story.get("content", "")[:5000],
        "score":             story.get("score"),
        "final_score":       story.get("final_score"),
        "controversy_score": story.get("controversy_score"),
        "score_breakdown":   story.get("score_breakdown"),
        "is_cluster":        story.get("is_cluster", False),
        "cluster_stories":   story.get("cluster_stories", []),
        "frame":             frame,
        "embedding":         story.get("_embedding"),
        "published_at":      story.get("published_at"),
        "source_type":       story.get("source_type"),
        "created_at":        datetime.now(timezone.utc).isoformat()
    }).execute()


def _save_review_queue(stories: list[dict]):
    for story in stories:
        try:
            supabase.table("review_queue").upsert({
                "title":      story.get("title"),
                "url":        story.get("url"),
                "score":      story.get("score"),
                "source":     story.get("source"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception:
            pass


if __name__ == "__main__":
    run_pipeline()
