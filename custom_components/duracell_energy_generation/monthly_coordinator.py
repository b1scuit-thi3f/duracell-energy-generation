from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
from .store import DuracellDataStore, normalize_month_response

_LOGGER = logging.getLogger(__name__)


class DuracellMonthlyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Duracell monthly chart data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DuracellApiClient,
        store: DuracellDataStore,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Duracell monthly chart data",
            update_interval=timedelta(hours=6),
        )
        self.api = api
        self.store = store

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch, normalize, and store current month data."""
        today = date.today()

        try:
            raw = await self.api.async_get_month_chart(today.year, today.month)
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err

        normalized = normalize_month_response(raw, today.year, today.month)
        await self.store.async_write_month(today.year, today.month, normalized)

        return normalized