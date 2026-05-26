from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABASE_URL", "mysql+aiomysql://test:test@127.0.0.1:3306/test_db")
os.environ.setdefault("INFLUXDB_URL", "http://localhost:8086")
os.environ.setdefault("INFLUXDB_TOKEN", "test-token")
os.environ.setdefault("DEVICE_SERVICE_URL", "http://localhost:8000")
os.environ.setdefault("REPORTING_SERVICE_URL", "http://localhost:8085")
os.environ.setdefault("ENERGY_SERVICE_URL", "http://localhost:8010")
os.environ.setdefault("MINIO_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("MINIO_EXTERNAL_URL", "http://localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minio")
os.environ.setdefault("MINIO_SECRET_KEY", "minio123")

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "waste-analysis-service"))
sys.path.insert(1, str(ROOT))

from src.tasks import waste_task  # noqa: E402


def test_canonical_loss_overlay_is_rejected_when_idle_and_loss_conflict():
    result = SimpleNamespace(
        overall_quality="high",
        idle_energy_kwh=1.98,
        offhours_energy_kwh=10.21,
        overconsumption_energy_kwh=0.0,
    )
    canonical = {
        "success": True,
        "totals": {
            "idle_kwh": 0.09,
            "offhours_kwh": 8.66,
            "overconsumption_kwh": 0.0,
            "loss_kwh": 8.75,
        },
        "days": [{"date": "2026-05-18", "idle_kwh": 0.09, "offhours_kwh": 8.66, "loss_kwh": 8.75}],
    }

    accepted, reason = waste_task._should_apply_canonical_loss_overlay(result, canonical)

    assert accepted is False
    assert reason in {
        "canonical_loss_materially_conflicts_with_local",
        "canonical_idle_materially_conflicts_with_local",
    }


def test_canonical_financial_totals_apply_even_when_loss_overlay_is_rejected():
    result = SimpleNamespace(
        overall_quality="high",
        total_energy_kwh=12.19,
        total_cost=79.24,
        idle_energy_kwh=1.98,
        offhours_energy_kwh=10.21,
        overconsumption_energy_kwh=0.0,
        warnings=[],
    )
    canonical = {
        "success": True,
        "totals": {
            "energy_kwh": 8.75,
            "energy_cost_inr": 56.88,
            "idle_kwh": 0.09,
            "offhours_kwh": 8.66,
            "overconsumption_kwh": 0.0,
            "loss_kwh": 8.75,
        },
        "days": [{"date": "2026-05-18", "energy_kwh": 8.75, "loss_kwh": 8.75}],
    }

    financial_applied, financial_reason = waste_task._apply_canonical_financial_totals(result, canonical, 6.5)
    loss_accepted, loss_reason = waste_task._should_apply_canonical_loss_overlay(result, canonical)

    assert financial_applied is True
    assert financial_reason == "canonical_financial_total_accepted"
    assert result.total_energy_kwh == 8.75
    assert result.total_cost == 56.88
    assert "canonical_energy_projection_applied" in result.warnings
    assert loss_accepted is False
    assert loss_reason in {
        "canonical_loss_materially_conflicts_with_local",
        "canonical_idle_materially_conflicts_with_local",
    }


@pytest.mark.asyncio
async def test_query_accounting_rows_uses_chunked_one_minute_queries(monkeypatch):
    calls: list[dict] = []

    async def fake_query_telemetry(**kwargs):
        calls.append(kwargs)
        return [{"timestamp": datetime(2026, 5, 18, 0, 0, tzinfo=timezone.utc), "power": 100.0}]

    monkeypatch.setattr(waste_task.settings, "INFLUX_ACCOUNTING_WINDOW", "1m", raising=False)
    monkeypatch.setattr(waste_task.settings, "INFLUX_ACCOUNTING_CHUNK_HOURS", 2, raising=False)
    monkeypatch.setattr(waste_task.influx_reader, "query_telemetry", fake_query_telemetry)

    rows = await waste_task._query_accounting_rows(
        device_id="DEVICE-1",
        start_dt=datetime(2026, 5, 18, 0, 0, tzinfo=timezone.utc),
        end_dt=datetime(2026, 5, 18, 5, 0, tzinfo=timezone.utc),
        fields=["power", "current"],
    )

    assert len(calls) == 3
    assert all(call["aggregation_window"] == "1m" for call in calls)
    assert rows
