from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
from .schedule import parse_device_shadow

_LOGGER = logging.getLogger(__name__)


class DuracellScheduleCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Duracell schedule/device-shadow data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DuracellApiClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Duracell schedule data",
            update_interval=timedelta(minutes=15),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and parse schedule data."""
        try:
            raw = await self.api.async_get_device_shadow()
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err

        return parse_device_shadow(raw)