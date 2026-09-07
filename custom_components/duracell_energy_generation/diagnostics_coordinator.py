from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DuracellApiClient, DuracellApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DuracellDiagnosticsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for inverter faults and account summary data."""

    def __init__(self, hass: HomeAssistant, api: DuracellApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Duracell diagnostics",
            update_interval=timedelta(minutes=5),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch diagnostics and account summary."""
        try:
            errors, member, inverter = await self._fetch_data()
        except DuracellApiError as err:
            raise UpdateFailed(str(err)) from err

        return {"errors": errors, "member": member, "inverter": inverter}

    async def _fetch_data(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        errors = await self.api.async_get_pvi_errors()
        member = await self.api.async_get_member_monitor()
        inverter = await self.api.async_get_inverter_summary()
        return errors, member, inverter
