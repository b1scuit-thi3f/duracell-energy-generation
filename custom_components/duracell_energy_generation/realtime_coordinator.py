from __future__ import annotations

import logging
import json
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
_LOGGER = logging.getLogger(__name__)


class DuracellRealtimeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for the portal's real-time flow endpoint."""

    def __init__(self, hass: HomeAssistant, api: DuracellApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Duracell real-time flow",
            update_interval=timedelta(seconds=30),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.async_get_realtime_flow()
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err

        inverter = data.get("inverter")
        if isinstance(inverter, dict):
            nested = inverter.get("RealTimeData")
            if isinstance(nested, str):
                try:
                    nested = json.loads(nested)
                except json.JSONDecodeError:
                    nested = None
            if isinstance(nested, dict):
                nested = nested.get("InvRealTimeData", nested)
                data["inverter_realtime"] = nested

        return data
