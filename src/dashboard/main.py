import json

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog

from config.settings import configure_logging, settings

configure_logging(settings.LOG_LEVEL)
logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Graphone Pipeline Dashboard API",
    description="FastAPI Backend and Management Interface for Async Ingestion System",
    version="1.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_DATA_DIR = settings.BASE_DIR / "src" / "dashboard" / "mock_data"
FRONTEND_DIST_DIR = settings.BASE_DIR / "src" / "dashboard" / "frontend" / "dist"

# Global pipeline execution state
pipeline_state = {
    "status": "idle",  # "idle" | "running" | "completed" | "failed"
    "last_run_at": "2026-09-01T15:33:00Z",
    "current_stage": None,
    "progress_pct": 0,
}


def load_mock_json(filename: str) -> Any:
    file_path = MOCK_DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=440, detail=f"Mock data file {filename} not found.")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.on_event("startup")
async def startup_event():
    settings.setup_directories()
    logger.info("Graphone Pipeline Dashboard backend started", mock_mode=settings.MOCK_MODE)


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get aggregated statistics across entity types, 7-run sparklines, and LLM tier breakdown."""
    if settings.MOCK_MODE:
        stats_data = load_mock_json("stats.json")
        llm_data = load_mock_json("llm_stats.json")
        stats_data["status"] = pipeline_state["status"]
        if pipeline_state["status"] == "running":
            stats_data["currentStage"] = pipeline_state["current_stage"]
            stats_data["progressPct"] = pipeline_state["progress_pct"]
        stats_data["llm"] = llm_data
        return stats_data
    else:
        # Real pipeline database aggregation logic will be implemented here
        return {"status": "idle", "entities": {}, "totalRecords": 0}


@app.get("/api/records/{record_type}")
async def get_records(
    record_type: str,
    search: Optional[str] = Query(default=None, description="Client fuzzy search query"),
) -> List[Dict[str, Any]]:
    """Fetch entity records for startup, product, research_paper, job, or news."""
    valid_types = {
        "startup": "startups.json",
        "product": "products.json",
        "research_paper": "research_papers.json",
        "job": "jobs.json",
        "news": "news.json",
    }
    if record_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity record_type '{record_type}'. Must be one of {list(valid_types.keys())}",
        )

    if settings.MOCK_MODE:
        filename = valid_types[record_type]
        records = load_mock_json(filename)
        if search:
            query = search.lower()
            records = [
                r
                for r in records
                if any(query in str(v).lower() for v in r.values() if isinstance(v, (str, list)))
            ]
        return records
    else:
        return []


@app.get("/api/entity-log")
async def get_entity_log() -> Dict[str, Any]:
    """Fetch Entity Resolution logs and method breakdown."""
    if settings.MOCK_MODE:
        return load_mock_json("entity_resolution_log.json")
    else:
        return {"summary": {}, "entries": []}


@app.get("/api/logs")
async def get_logs(
    source: str = Query(default="scrape.log", description="Log file source: scrape.log, llm_extraction.log, entity_resolution.log")
) -> List[Dict[str, Any]]:
    """Tail recent pipeline log entries color-coded by log level."""
    if settings.MOCK_MODE:
        logs_data = load_mock_json("logs.json")
        return logs_data.get(source, [])
    else:
        return []


def simulate_pipeline_run():
    import time
    pipeline_state["status"] = "running"
    pipeline_state["progress_pct"] = 15
    pipeline_state["current_stage"] = "Async Scraping"
    time.sleep(2)
    pipeline_state["progress_pct"] = 50
    pipeline_state["current_stage"] = "LLM Structured Extraction"
    time.sleep(2)
    pipeline_state["progress_pct"] = 85
    pipeline_state["current_stage"] = "Entity Resolution & Deduplication"
    time.sleep(2)
    pipeline_state["status"] = "idle"
    pipeline_state["progress_pct"] = 100
    pipeline_state["current_stage"] = "Completed"
    from datetime import datetime, timezone
    pipeline_state["last_run_at"] = datetime.now(timezone.utc).isoformat()


@app.post("/api/run")
async def trigger_pipeline_run(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger pipeline execution subprocess/background task."""
    if pipeline_state["status"] == "running":
        return {"status": "already_running", "message": "Pipeline run is already in progress"}

    pipeline_state["status"] = "running"
    pipeline_state["progress_pct"] = 10
    pipeline_state["current_stage"] = "Initializing"

    background_tasks.add_task(simulate_pipeline_run)
    return {
        "status": "started",
        "message": "Pipeline run initiated successfully",
        "timestamp": pipeline_state["last_run_at"],
    }


# Mount built frontend static files if dist folder exists
if FRONTEND_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
