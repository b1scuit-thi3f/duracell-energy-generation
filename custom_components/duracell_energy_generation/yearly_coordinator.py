from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
from .store import normalize_year_response

_LOGGER = logging.getLogger(__name__)


class DuracellYearlyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for annual summary and monthly curve data."""

    def __init__(self, hass: HomeAssistant, api: DuracellApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Duracell yearly data",
            update_interval=timedelta(hours=12),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        year = date.today().year

        try:
            summary, chart = await self._fetch_data(year)
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err

        return normalize_year_response(summary, chart, year)

    async def _fetch_data(
        self, year: int
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        summary = await self.api.async_get_year_summary(year)
        chart = await self.api.async_get_year_chart(year)
        return summary, chart
