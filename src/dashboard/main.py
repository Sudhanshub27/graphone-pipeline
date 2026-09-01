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


def read_processed_jsonl(filename: str) -> List[Dict[str, Any]]:
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        return []
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except Exception as e:
        logger.error("Failed reading JSONL file", filename=filename, error=str(e))
    return records


@app.on_event("startup")
async def startup_event():
    settings.setup_directories()
    logger.info("Graphone Pipeline Dashboard backend started", mock_mode=settings.MOCK_MODE)


@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
    """Get aggregated statistics across entity types, 7-run sparklines, and LLM tier breakdown."""
    startups = read_processed_jsonl("startups.jsonl")
    products = read_processed_jsonl("products.jsonl")
    papers = read_processed_jsonl("research_papers.jsonl")
    jobs = read_processed_jsonl("jobs.jsonl")
    news = read_processed_jsonl("news.jsonl")

    total_real = len(startups) + len(products) + len(papers) + len(jobs) + len(news)

    # Base mock fallback stats
    stats_data = load_mock_json("stats.json")
    llm_data = load_mock_json("llm_stats.json")

    if not isinstance(stats_data, dict):
        stats_data = {
            "status": "idle",
            "lastRunAt": pipeline_state["last_run_at"],
            "totalRecords": 0,
            "entities": {
                "startup": {"count": 0, "sparkline": [0, 0, 0, 0, 0, 0, 0]},
                "product": {"count": 0, "sparkline": [0, 0, 0, 0, 0, 0, 0]},
                "research_paper": {"count": 0, "sparkline": [0, 0, 0, 0, 0, 0, 0]},
                "job": {"count": 0, "sparkline": [0, 0, 0, 0, 0, 0, 0]},
                "news": {"count": 0, "sparkline": [0, 0, 0, 0, 0, 0, 0]},
            },
        }

    # If real data exists, update counts
    if total_real > 0:
        stats_data["totalRecords"] = total_real
        stats_data["entities"]["startup"]["count"] = max(len(startups), stats_data["entities"]["startup"].get("count", 0))
        stats_data["entities"]["product"]["count"] = max(len(products), stats_data["entities"]["product"].get("count", 0))
        stats_data["entities"]["research_paper"]["count"] = max(len(papers), stats_data["entities"]["research_paper"].get("count", 0))
        stats_data["entities"]["job"]["count"] = max(len(jobs), stats_data["entities"]["job"].get("count", 0))
        stats_data["entities"]["news"]["count"] = max(len(news), stats_data["entities"]["news"].get("count", 0))

    stats_data["status"] = pipeline_state["status"]
    if pipeline_state["status"] == "running":
        stats_data["currentStage"] = pipeline_state["current_stage"]
        stats_data["progressPct"] = pipeline_state["progress_pct"]

    stats_data["llm"] = llm_data
    return stats_data


@app.get("/api/records/{record_type}")
async def get_records(
    record_type: str,
    search: Optional[str] = Query(default=None, description="Client fuzzy search query"),
) -> List[Dict[str, Any]]:
    """Fetch entity records for startup, product, research_paper, job, or news."""
    jsonl_mapping = {
        "startup": ("startups.jsonl", "startups.json"),
        "product": ("products.jsonl", "products.json"),
        "research_paper": ("research_papers.jsonl", "research_papers.json"),
        "job": ("jobs.jsonl", "jobs.json"),
        "news": ("news.jsonl", "news.json"),
    }

    if record_type not in jsonl_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity record_type '{record_type}'. Must be one of {list(jsonl_mapping.keys())}",
        )

    jsonl_file, mock_file = jsonl_mapping[record_type]
    records = read_processed_jsonl(jsonl_file)

    # Fallback to mock records if processed file is empty
    if not records:
        mock_res = load_mock_json(mock_file)
        records = mock_res if isinstance(mock_res, list) else []

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
    raw_logs = read_processed_jsonl("entity_mapping_log.jsonl")
    if raw_logs:
        formatted_entries = []
        for idx, r in enumerate(raw_logs):
            raw_name = r.get("raw_name") or r.get("entity_name") or "Unknown Entity"
            canon_name = r.get("canonical_name") or r.get("entity_name") or raw_name
            method = r.get("method_used", "unresolved")
            conf = float(r.get("confidence_score", 0.5))
            
            entry = {
                "id": r.get("id") or f"er-{idx + 1001}",
                "entity_name": canon_name if canon_name else raw_name,
                "raw_name": raw_name,
                "canonical_name": canon_name,
                "entity_type": r.get("entity_type") or "startup",
                "method_used": method,
                "confidence_score": conf,
                "status": r.get("status") or ("merged" if canon_name and method != "unresolved" else ("needs_review" if conf >= 0.5 else "kept_separate")),
                "timestamp": r.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            }
            formatted_entries.append(entry)

        exact = sum(1 for r in formatted_entries if r["method_used"] == "exact")
        norm = sum(1 for r in formatted_entries if r["method_used"] == "normalized")
        fuzzy = sum(1 for r in formatted_entries if r["method_used"] == "fuzzy")
        unres = sum(1 for r in formatted_entries if r["method_used"] == "unresolved")
        total = len(formatted_entries) or 1

        return {
            "summary": {
                "totalProcessed": total,
                "exactMatchCount": exact,
                "exactMatchPct": round((exact / total) * 100, 1),
                "normalizedCount": norm,
                "normalizedPct": round((norm / total) * 100, 1),
                "fuzzyCount": fuzzy,
                "fuzzyPct": round((fuzzy / total) * 100, 1),
                "unresolvedCount": unres,
                "unresolvedPct": round((unres / total) * 100, 1),
            },
            "entries": formatted_entries,
        }

    mock_log = load_mock_json("entity_resolution_log.json")
    return mock_log if isinstance(mock_log, dict) else {"summary": {}, "entries": []}


@app.get("/api/logs")
async def get_logs(
    source: str = Query(default="scrape.log", description="Log file source: scrape.log, llm_extraction.log, entity_resolution.log")
) -> List[Dict[str, Any]]:
    """Tail recent pipeline log entries color-coded by log level."""
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
