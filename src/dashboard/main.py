import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import configure_logging, settings
from src.dashboard.processed_reader import (
    get_all_processed_records,
    get_processed_entity_log,
    get_processed_stats,
    read_jsonl_records,
)

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
PROCESSED_DIR = settings.DATA_PROCESSED_DIR

# Global pipeline execution state
pipeline_state = {
    "status": "idle",  # "idle" | "running" | "completed" | "failed"
    "last_run_at": datetime.now(timezone.utc).isoformat(),
    "current_stage": None,
    "progress_pct": 0,
}


def load_mock_json(filename: str) -> Any:
    file_path = MOCK_DATA_DIR / filename
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.on_event("startup")
async def startup_event():
    settings.setup_directories()
    logger.info("Graphone Pipeline Dashboard backend started", mock_mode=settings.MOCK_MODE)


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    """Get runtime pipeline settings and mock_mode status."""
    return {"mockMode": settings.MOCK_MODE, "mock_mode": settings.MOCK_MODE}


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get aggregated statistics across entity types, 7-run sparklines, and LLM tier breakdown."""
    if settings.MOCK_MODE:
        stats_data = load_mock_json("stats.json")
        llm_data = load_mock_json("llm_stats.json")
        if isinstance(stats_data, dict):
            stats_data["status"] = pipeline_state["status"]
            if pipeline_state["status"] == "running":
                stats_data["currentStage"] = pipeline_state["current_stage"]
                stats_data["progressPct"] = pipeline_state["progress_pct"]
            stats_data["llm"] = llm_data
            stats_data["mockMode"] = True
            stats_data["mock_mode"] = True
            return stats_data

    # Real data processing pathway
    stats_data = get_processed_stats()
    stats_data["mockMode"] = settings.MOCK_MODE
    stats_data["mock_mode"] = settings.MOCK_MODE

    stats_data["status"] = pipeline_state["status"]
    if pipeline_state["status"] == "running":
        stats_data["currentStage"] = pipeline_state["current_stage"]
        stats_data["progressPct"] = pipeline_state["progress_pct"]

    return stats_data



@app.get("/api/records/{record_type}")
async def get_records(
    record_type: str,
    search: Optional[str] = Query(default=None, description="Client fuzzy search query"),
) -> List[Dict[str, Any]]:
    """Fetch entity records for startup, product, research_paper, job, or news."""
    type_mapping = {
        "startup": ("startups.jsonl", "startups.json"),
        "product": ("products.jsonl", "products.json"),
        "research_paper": ("research_papers.jsonl", "research_papers.json"),
        "job": ("jobs.jsonl", "jobs.json"),
        "news": ("news.jsonl", "news.json"),
    }

    if record_type not in type_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity record_type '{record_type}'. Must be one of {list(type_mapping.keys())}",
        )

    jsonl_file, mock_file = type_mapping[record_type]

    if settings.MOCK_MODE:
        records = load_mock_json(mock_file)
        records = records if isinstance(records, list) else []
    else:
        records = read_jsonl_records(jsonl_file)

    if search:
        query = search.lower()
        records = [
            r
            for r in records
            if any(query in str(v).lower() for v in r.values() if isinstance(v, (str, list, dict)))
        ]

    return records


@app.get("/api/entity-log")
async def get_entity_log() -> Dict[str, Any]:
    """Fetch Entity Resolution logs and method breakdown."""
    if settings.MOCK_MODE:
        mock_log = load_mock_json("entity_resolution_log.json")
        return mock_log if isinstance(mock_log, dict) else {"summary": {}, "entries": []}

    return get_processed_entity_log()


@app.get("/api/logs")
async def get_logs(
    source: str = Query(default="scrape.log", description="Log file source: scrape.log, llm_extraction.log, entity_resolution.log")
) -> List[Dict[str, Any]]:
    """Tail recent pipeline log entries color-coded by log level."""
    if source in ("llm_extraction.log", "llm_calls_log.jsonl"):
        llm_records = read_jsonl_records("llm_calls_log.jsonl")
        if llm_records:
            formatted_logs = []
            for r in llm_records[-50:]:
                succ = r.get("success", True)
                formatted_logs.append({
                    "timestamp": r.get("timestamp"),
                    "level": "INFO" if succ else "WARN",
                    "module": "src.llm.fallback_chain",
                    "message": f"[{r.get('provider')}] schema '{r.get('schema')}' {'succeeded' if succ else 'failed'} ({r.get('latency_ms')}ms, {r.get('token_count')} tokens)" + (f" - Error: {r.get('error')}" if r.get('error') else ""),
                })
            return formatted_logs

    logs_data = load_mock_json("logs.json")
    if isinstance(logs_data, dict):
        return logs_data.get(source, [])
    return []


async def execute_pipeline_background():
    """Background task executing the actual pipeline orchestrator asynchronously."""
    global pipeline_state
    try:
        pipeline_state["status"] = "running"
        pipeline_state["progress_pct"] = 15
        pipeline_state["current_stage"] = "Async Scraping & Source Crawling"
        await asyncio.sleep(1.5)

        pipeline_state["progress_pct"] = 45
        pipeline_state["current_stage"] = "LLM Multi-Tier Structured Extraction"

        from src.main import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(dry_run=True, limit=5)
        await orchestrator.run_all_pipelines()

        pipeline_state["progress_pct"] = 80
        pipeline_state["current_stage"] = "Entity Resolution & Schema Persistence"
        await asyncio.sleep(1.0)

        pipeline_state["progress_pct"] = 100
        pipeline_state["current_stage"] = "Completed"
        pipeline_state["status"] = "idle"
        pipeline_state["last_run_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error("Background pipeline execution failed", error=str(e))
        pipeline_state["status"] = "failed"
        pipeline_state["current_stage"] = "Failed"


@app.post("/api/run")
async def trigger_pipeline_run(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger pipeline execution background task from Dashboard UI button."""
    if pipeline_state["status"] == "running":
        return {"status": "already_running", "message": "Pipeline run is already in progress"}

    pipeline_state["status"] = "running"
    pipeline_state["progress_pct"] = 10
    pipeline_state["current_stage"] = "Initializing Pipeline Run"

    background_tasks.add_task(execute_pipeline_background)
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
