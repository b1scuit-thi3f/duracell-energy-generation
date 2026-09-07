from __future__ import annotations

from datetime import date
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN


def _bad_request(message: str) -> web.Response:
    return web.json_response({"error": message}, status=400)

def _not_found(message: str) -> web.Response:
    return web.json_response({"error": message}, status=404)


def _parse_date(value: str | None) -> str | None:
    """Return an ISO date, or None when the query value is invalid."""
    if value is None:
        return date.today().isoformat()

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None

    return parsed.isoformat()


def _get_entry_data(hass: HomeAssistant, entry_id: str | None):
    """Return the requested Duracell entry data, or the only configured entry."""

    entries = hass.data.get(DOMAIN, {})

    if entry_id:
        return entries.get(entry_id)

    # Ignore non-entry keys, such as the HTTP registration marker.
    entry_values = [
        value
        for value in entries.values()
        if isinstance(value, dict) and "store" in value
    ]

    if len(entry_values) == 1:
        return entry_values[0]

    return None

class DuracellDayDataView(HomeAssistantView):
    """HTTP view for stored Duracell day data."""

    url = "/api/duracell_energy_generation/day"
    name = "api:duracell_energy_generation:day"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]

        entry_id = request.query.get("entry_id")
        target_date = _parse_date(request.query.get("date"))
        if target_date is None:
            return _bad_request("Invalid date; expected YYYY-MM-DD")

        entry_data = _get_entry_data(hass, entry_id)

        if not entry_data:
            return _not_found(
                "Duracell entry not found. If you have multiple entries, pass entry_id."
            )

        store = entry_data["store"]
        data = await store.async_read_day(target_date)

        if data is None:
            return _not_found("Day data not found")

        return web.json_response(data)


class DuracellMonthDataView(HomeAssistantView):
    """HTTP view for stored Duracell month data."""

    url = "/api/duracell_energy_generation/month"
    name = "api:duracell_energy_generation:month"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]

        entry_id = request.query.get("entry_id")
        year_string = request.query.get("year")
        month_string = request.query.get("month")

        today = date.today()

        try:
            year = int(year_string) if year_string else today.year
            month = int(month_string) if month_string else today.month
        except (TypeError, ValueError):
            return _bad_request("Invalid year or month")

        if year < 1 or not 1 <= month <= 12:
            return _bad_request("Invalid year or month")

        entry_data = _get_entry_data(hass, entry_id)

        if not entry_data:
            return _not_found(
                "Duracell entry not found. If you have multiple entries, pass entry_id."
            )

        store = entry_data["store"]
        data = await store.async_read_month(year, month)

        if data is None:
            return _not_found("Month data not found")

        return web.json_response(data)


async def async_register_http_views(hass: HomeAssistant) -> None:
    """Register Duracell HTTP API views once."""

    registered_key = f"{DOMAIN}_http_registered"

    if hass.data.get(registered_key):
        return

    hass.http.register_view(DuracellDayDataView)
    hass.http.register_view(DuracellMonthDataView)

    hass.data[registered_key] = True