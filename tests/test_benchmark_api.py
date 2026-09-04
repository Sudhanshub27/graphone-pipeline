from fastapi.testclient import TestClient
from config.settings import settings
from src.dashboard.main import app

client = TestClient(app)


def test_get_latest_benchmark_no_report(tmp_path, monkeypatch):
    """Test GET /api/benchmark/latest returns 404 when no benchmark report exists."""
    reports_dir = tmp_path / "evaluation" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)

    response = client.get("/api/benchmark/latest")
    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert "No benchmark report available" in detail


def test_get_latest_benchmark_with_report(tmp_path, monkeypatch):
    """Test GET /api/benchmark/latest returns valid JSON report data when report file exists."""
    reports_dir = tmp_path / "evaluation" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)

    sample_report = {
        "run": {"mode": "mock", "git_commit": "test-commit-123"},
        "pipeline": {"records_processed": 50, "records_per_second": 45.2},
        "scraper": {"p50_latency_ms": 200, "p95_latency_ms": 1100},
        "llm": {"total_calls": 48, "fallback_rate": 0.02},
        "resolution": {"duplicates_found": 12, "match_rate": 0.24},
        "vector_search": {"p50_latency_ms": 30, "p95_latency_ms": 80},
    }

    report_file = reports_dir / "benchmark_report.json"
    report_file.write_text(json.dumps(sample_report), encoding="utf-8")

    response = client.get("/api/benchmark/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["run"]["mode"] == "mock"
    assert data["pipeline"]["records_processed"] == 50
    assert data["llm"]["total_calls"] == 48


def test_get_latest_benchmark_selects_latest_by_mtime(tmp_path, monkeypatch):
    """Test GET /api/benchmark/latest selects the report file with the latest mtime."""
    reports_dir = tmp_path / "evaluation" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)

    old_report = {"run": {"id": "old_report"}}
    new_report = {"run": {"id": "new_report"}}

    file1 = reports_dir / "benchmark_2026-01-01.json"
    file2 = reports_dir / "benchmark_2026-09-03.json"

    file1.write_text(json.dumps(old_report), encoding="utf-8")
    time.sleep(0.05)
    file2.write_text(json.dumps(new_report), encoding="utf-8")

    latest = get_latest_actual_benchmark_report()
    assert latest is not None
    assert latest["run"]["id"] == "new_report"

    response = client.get("/api/benchmark/latest")
    assert response.status_code == 200
    assert response.json()["run"]["id"] == "new_report"
