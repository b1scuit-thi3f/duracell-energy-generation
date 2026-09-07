from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DuracellDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Duracell Energy data."""

    def __init__(self, hass: HomeAssistant, api: DuracellApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data."""
        try:
            return await self.api.async_get_inverter_detail()
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err