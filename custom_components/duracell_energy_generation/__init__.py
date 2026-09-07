from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DuracellApiClient
from .const import (
    CONF_GOODS_ID,
    CONF_MEMBER_AUTO_ID,
    CONF_MEMBER_ID,
    CONF_PASSWORD,
    DOMAIN,
)
from .coordinator import DuracellDataUpdateCoordinator
from .diagnostics_coordinator import DuracellDiagnosticsCoordinator
from .history_coordinator import DuracellHistoryCoordinator
from .http import async_register_http_views
from .monthly_coordinator import DuracellMonthlyCoordinator
from .store import DuracellDataStore
from .services import async_setup_services
from .schedule_coordinator import DuracellScheduleCoordinator
from .realtime_coordinator import DuracellRealtimeCoordinator
from .yearly_coordinator import DuracellYearlyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Duracell Energy Generation from a config entry."""

    session = async_get_clientsession(hass)

    api = DuracellApiClient(
        session=session,
        member_id=entry.data[CONF_MEMBER_ID],
        password=entry.data[CONF_PASSWORD],
        goods_id=entry.data[CONF_GOODS_ID],
        member_auto_id=entry.data[CONF_MEMBER_AUTO_ID],
    )

    store = DuracellDataStore(hass, entry.entry_id)

    live_coordinator = DuracellDataUpdateCoordinator(hass, api)
    history_coordinator = DuracellHistoryCoordinator(hass, api, store)
    monthly_coordinator = DuracellMonthlyCoordinator(hass, api, store)
    schedule_coordinator = DuracellScheduleCoordinator(hass, api)
    diagnostics_coordinator = DuracellDiagnosticsCoordinator(hass, api)
    realtime_coordinator = DuracellRealtimeCoordinator(hass, api)
    yearly_coordinator = DuracellYearlyCoordinator(hass, api)

    await live_coordinator.async_config_entry_first_refresh()
    await history_coordinator.async_config_entry_first_refresh()
    await monthly_coordinator.async_config_entry_first_refresh()
    await schedule_coordinator.async_config_entry_first_refresh()
    await diagnostics_coordinator.async_config_entry_first_refresh()
    await realtime_coordinator.async_config_entry_first_refresh()
    await yearly_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "store": store,
        "live": live_coordinator,
        "history": history_coordinator,
        "monthly": monthly_coordinator,
        "schedule": schedule_coordinator,
        "diagnostics": diagnostics_coordinator,
        "realtime": realtime_coordinator,
        "yearly": yearly_coordinator,
    }

    await async_register_http_views(hass)
    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Duracell Energy Generation config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok