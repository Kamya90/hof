# main.py
# HOF Entry Point
#
# Starts the FastAPI web server AND the background scheduler.
# The scheduler runs the pipeline every 6 hours.
# The API serves stories to the frontend.
#
# Run locally:  python main.py
# Production:   uvicorn main:app --host 0.0.0.0 --port $PORT

import os
import threading
import schedule
import time
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from supabase import create_client

from src.pipeline import run_pipeline

app = FastAPI(title="HOF API")

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


# ── API ROUTES ────────────────────────────────────────────────────────────────

@app.get("/api/stories")
def get_stories(limit: int = 12, offset: int = 0):
    """
    Fetch the latest framed stories for the frontend.
    Returns stories sorted by final_score descending.
    """
    result = (
        supabase.table("stories")
        .select("id, title, source, url, score, final_score, frame, published_at, created_at")
        .order("final_score", desc=True)
        .limit(limit)
        .offset(offset)
        .execute()
    )
    return {"stories": result.data, "count": len(result.data)}


@app.get("/api/stories/{story_id}")
def get_story(story_id: str):
    """Fetch a single story with its full debate frame."""
    result = (
        supabase.table("stories")
        .select("*")
        .eq("id", story_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Story not found")
    return result.data[0]


@app.post("/api/votes")
def cast_vote(payload: dict):
    """
    Record a reader vote (Made Me Think / More Context).
    This is your feedback loop data — it improves the scorer over time.

    Body: { "story_id": "uuid", "vote_type": "think" | "context" }
    """
    story_id  = payload.get("story_id")
    vote_type = payload.get("vote_type")

    if not story_id or vote_type not in ("think", "context"):
        raise HTTPException(status_code=400, detail="Invalid payload")

    supabase.table("votes").insert({
        "story_id":  story_id,
        "vote_type": vote_type
    }).execute()

    return {"status": "logged"}


@app.get("/api/health")
def health():
    """Health check endpoint for Railway."""
    return {"status": "ok", "service": "HOF"}


# ── SERVE FRONTEND ────────────────────────────────────────────────────────────

# Serve the HOF website from the /public folder
if os.path.exists("public"):
    app.mount("/static", StaticFiles(directory="public"), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse("public/index.html")


# ── SCHEDULER ────────────────────────────────────────────────────────────────

def run_scheduler():
    """
    Background thread that runs the pipeline on a schedule.
    Runs at 6am, 12pm, 6pm, and 12am IST every day.
    """
    schedule.every().day.at("00:30").do(run_pipeline)  # 6am IST
    schedule.every().day.at("06:30").do(run_pipeline)  # 12pm IST
    schedule.every().day.at("12:30").do(run_pipeline)  # 6pm IST
    schedule.every().day.at("18:30").do(run_pipeline)  # 12am IST

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    import uvicorn

    print("HOF starting...")

    # Run pipeline once immediately on startup
    print("Running initial pipeline...")
    threading.Thread(target=run_pipeline, daemon=True).start()

    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Scheduler started — pipeline runs every 6 hours")

    # Start the web server
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
