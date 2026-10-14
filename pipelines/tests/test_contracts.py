import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipelines.ingestion.runner import hash_record, normalise
from pipelines.transformations.calendar import calendar_rows, settlement_start
from pipelines.validation.models import CarbonInterval, Share

START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 15, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "day,periods", [(date(2026, 3, 29), 46), (date(2026, 10, 25), 50), (date(2026, 6, 1), 48)]
)
def test_british_settlement_days(day, periods):
    a = settlement_start(day, 1)
    b = settlement_start(day + timedelta(days=1), 1)
    rows = list(calendar_rows(a, b))
    assert len(rows) == periods
    assert rows[-1]["settlement_period"] == periods
    with pytest.raises(ValueError):
        settlement_start(day, periods + 1)


def test_repeated_local_hour_is_unambiguous():
    rows = list(
        calendar_rows(settlement_start(date(2026, 10, 25), 1), settlement_start(date(2026, 10, 26), 1))
    )
    repeated = [r for r in rows if r["local_hour"] == 1]
    assert len(repeated) == 4
    assert len({r["period_start"] for r in repeated}) == 4


def test_official_regional_sample_has_no_actuals():
    body = json.loads((ROOT / "docs/contracts/regional.json").read_text())
    rows = list(normalise("regional", body, START, END))
    assert len([r for r in rows if r[0] == "region"]) == 17
    assert all(row["actual"] is None for name, row, _ in rows if name == "carbon_observation")
    assert not [r for r in rows if r[0] == "quarantine"]


def test_elexon_signed_interconnector_preserved():
    body = json.loads((ROOT / "docs/contracts/elexon.json").read_text())
    rows = list(normalise("elexon", body, START, END))
    assert rows and all(n == "generation_outturn" for n, _, _ in rows)
    source = {"data": [{"startTime": "2026-10-12T00:00Z", "fuelType": "INTNEM", "generation": -42}]}
    assert list(normalise("elexon", source, START, END))[0][1]["power_mw"] == -42


def test_invalid_source_values_are_quarantined():
    body = {"data": [{"from": "2026-10-12T00:00Z", "to": "2026-10-12T00:30Z", "intensity": {"forecast": -1}}]}
    assert list(normalise("carbon", body, START, END))[0][0] == "quarantine"
    with pytest.raises(ValidationError):
        Share(fuel="wind", perc=101)


def test_missing_actual_remains_null():
    c = CarbonInterval.model_validate(
        {"from": "2026-10-12T00:00Z", "to": "2026-10-12T00:30Z", "intensity": {"forecast": 0}}
    )
    assert c.intensity.actual is None and c.intensity.forecast == 0


def test_hash_order_independent_and_revision_sensitive():
    assert hash_record({"a": 1, "b": 2}) == hash_record({"b": 2, "a": 1})
    assert hash_record({"a": 1}) != hash_record({"a": 2})


def test_future_demand_rows_retain_forecast_label():
    body = json.loads((ROOT / "docs/contracts/neso.json").read_text())
    rows = list(normalise("demand", body, START, END + timedelta(days=20)))
    assert all(r["observation_kind"] == "F" for n, r, _ in rows if n == "demand_observation")
