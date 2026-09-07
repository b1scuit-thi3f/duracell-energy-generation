from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

DATA_DIR_NAME = "duracell_energy_generation"


def _to_float(value: Any) -> float | None:
    """Convert Duracell string/number values to float."""
    if value in (None, "", "-"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _energy_from_5min_power(rows: list[dict[str, Any]], key: str) -> float:
    """Convert 5-minute watt samples into kWh."""
    total_wh = 0.0

    for row in rows:
        watts = _to_float(row.get(key))
        if watts is None:
            continue

        total_wh += watts * (5 / 60)

    return round(total_wh / 1000, 3)


def normalize_day_response(
    raw: dict[str, Any],
    target_date: date,
) -> dict[str, Any]:
    """Normalize Duracell day chart response."""

    rows = raw.get("Data") or []
    points: list[dict[str, Any]] = []

    for row in rows:
        power_to_grid = _to_float(row.get("powerToGrid")) or 0.0
        power_from_grid = _to_float(row.get("powerFromGrid")) or 0.0

        power_to_battery = _to_float(row.get("powerToBattery")) or 0.0
        power_from_battery = _to_float(row.get("powerFromBattery")) or 0.0

        points.append(
            {
                "time": row.get("inTime"),
                "production_w": _to_float(row.get("Production")),
                "consumption_w": _to_float(row.get("Consumption")),
                "load_w": _to_float(row.get("load")),
                "grid_power_w": round(power_from_grid - power_to_grid, 3),
                "to_grid_w": power_to_grid,
                "from_grid_w": power_from_grid,
                "battery_power_w": round(power_to_battery - power_from_battery, 3),
                "battery_charge_w": power_to_battery,
                "battery_discharge_w": power_from_battery,
                "soc": _to_float(row.get("SOC")),
                "mode": row.get("mode"),
            }
        )

    return {
        "kind": "day",
        "date": target_date.isoformat(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "point_count": len(points),
        "totals": {
            "production_kwh": _energy_from_5min_power(rows, "Production"),
            "consumption_kwh": _energy_from_5min_power(rows, "Consumption"),
            "load_kwh": _energy_from_5min_power(rows, "load"),
            "to_grid_kwh": _energy_from_5min_power(rows, "powerToGrid"),
            "from_grid_kwh": _energy_from_5min_power(rows, "powerFromGrid"),
            "to_battery_kwh": _energy_from_5min_power(rows, "powerToBattery"),
            "from_battery_kwh": _energy_from_5min_power(rows, "powerFromBattery"),
            "consumed_directly_kwh": _energy_from_5min_power(rows, "ConsumedDirectly"),
        },
        "points": points,
    }


def normalize_month_response(
    raw: dict[str, Any],
    year: int,
    month: int,
) -> dict[str, Any]:
    """Normalize Duracell monthly chart response."""

    rows = raw.get("Data") or []
    days: list[dict[str, Any]] = []

    for row in rows:
        days.append(
            {
                "day": row.get("day"),
                "production_kwh": _to_float(row.get("Production")),
                "consumption_kwh": _to_float(row.get("Consumption")),
                "to_grid_kwh": _to_float(row.get("powerToGrid")),
                "from_grid_kwh": _to_float(row.get("powerFromGrid")),
                "to_battery_kwh": _to_float(row.get("powerToBattery")),
                "from_battery_kwh": _to_float(row.get("powerFromBattery")),
                "consumed_directly_kwh": _to_float(row.get("ConsumedDirectly")),
                "grid_to_battery_kwh": _to_float(row.get("gridToBattery")),
                "pv_to_grid_kwh": _to_float(row.get("PVToGrid")),
                "pv_to_battery_kwh": _to_float(row.get("PVToBattery")),
                "load_from_grid_kwh": _to_float(row.get("loadFromGrid")),
                "load_from_battery_kwh": _to_float(row.get("loadFromBattery")),
            }
        )

    totals = {
        "production_kwh": round(sum(day["production_kwh"] or 0 for day in days), 3),
        "consumption_kwh": round(sum(day["consumption_kwh"] or 0 for day in days), 3),
        "to_grid_kwh": round(sum(day["to_grid_kwh"] or 0 for day in days), 3),
        "from_grid_kwh": round(sum(day["from_grid_kwh"] or 0 for day in days), 3),
        "to_battery_kwh": round(sum(day["to_battery_kwh"] or 0 for day in days), 3),
        "from_battery_kwh": round(sum(day["from_battery_kwh"] or 0 for day in days), 3),
        "consumed_directly_kwh": round(
            sum(day["consumed_directly_kwh"] or 0 for day in days), 3
        ),
    }

    return {
        "kind": "month",
        "year": year,
        "month": month,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "day_count": len(days),
        "totals": totals,
        "days": days,
    }


def normalize_year_response(
    summary: dict[str, Any],
    chart: dict[str, Any],
    year: int,
) -> dict[str, Any]:
    """Normalize annual totals and monthly curve data."""
    rows = chart.get("Data") or []
    months = [
        {
            "month": row.get("month"),
            "production_kwh": _to_float(row.get("Production")),
            "consumption_kwh": _to_float(row.get("Consumption")),
            "to_grid_kwh": _to_float(row.get("powerToGrid")),
            "from_grid_kwh": _to_float(row.get("powerFromGrid")),
            "to_battery_kwh": _to_float(row.get("powerToBattery")),
            "from_battery_kwh": _to_float(row.get("powerFromBattery")),
            "consumed_directly_kwh": _to_float(row.get("ConsumedDirectly")),
        }
        for row in rows
    ]

    def total(key: str) -> float | None:
        return _to_float(summary.get(key))

    return {
        "kind": "year",
        "year": year,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "month_count": len(months),
        "totals": {
            "production_kwh": total("Production"),
            "to_grid_kwh": total("ToGrid"),
            "self_consumption_kwh": total("SelfConsumption"),
            "consumption_kwh": total("Consumption"),
            "from_grid_kwh": total("FromGrid"),
            "self_production_kwh": total("SelfProduction"),
        },
        "months": months,
    }


class DuracellDataStore:
    """Local JSON store for Duracell chart data."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.base_path = Path(hass.config.path(DATA_DIR_NAME)) / entry_id

    def _ensure_dirs(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "days").mkdir(parents=True, exist_ok=True)
        (self.base_path / "months").mkdir(parents=True, exist_ok=True)

    def _day_path(self, target_date: date | str) -> Path:
        if isinstance(target_date, date):
            target_date = target_date.isoformat()
        return self.base_path / "days" / f"{target_date}.json"

    def _month_path(self, year: int, month: int) -> Path:
        return self.base_path / "months" / f"{year}-{month:02d}.json"

    def _write_json_sync(self, path: Path, data: dict[str, Any]) -> None:
        self._ensure_dirs()

        tmp_path = path.with_suffix(".json.tmp")

        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, separators=(",", ":"))

        tmp_path.replace(path)

    def _read_json_sync(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None

        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    async def async_write_day(self, target_date: date, data: dict[str, Any]) -> None:
        """Write one day file."""
        path = self._day_path(target_date)
        await self.hass.async_add_executor_job(self._write_json_sync, path, data)

    async def async_read_day(self, target_date: date | str) -> dict[str, Any] | None:
        """Read one day file."""
        path = self._day_path(target_date)
        return await self.hass.async_add_executor_job(self._read_json_sync, path)

    async def async_write_month(
        self,
        year: int,
        month: int,
        data: dict[str, Any],
    ) -> None:
        """Write one month file."""
        path = self._month_path(year, month)
        await self.hass.async_add_executor_job(self._write_json_sync, path, data)

    async def async_read_month(self, year: int, month: int) -> dict[str, Any] | None:
        """Read one month file."""
        path = self._month_path(year, month)
        return await self.hass.async_add_executor_job(self._read_json_sync, path)