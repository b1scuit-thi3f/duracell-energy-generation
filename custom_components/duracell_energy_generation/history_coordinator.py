from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
from .store import DuracellDataStore, normalize_day_response

_LOGGER = logging.getLogger(__name__)


class DuracellHistoryCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Duracell day chart data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DuracellApiClient,
        store: DuracellDataStore,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Duracell day chart data",
            update_interval=timedelta(hours=1),
        )
        self.api = api
        self.store = store

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch, normalize, and store today's chart data."""
        target_date = date.today()

        try:
            raw = await self.api.async_get_day_chart(target_date)
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err

        normalized = normalize_day_response(raw, target_date)
        await self.store.async_write_day(target_date, normalized)

        return normalized