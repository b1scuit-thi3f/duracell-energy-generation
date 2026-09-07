from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .store import normalize_day_response, normalize_month_response
from .schedule import build_schedule_registers

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH_TODAY = "refresh_today"
SERVICE_REFRESH_MONTH = "refresh_month"
SERVICE_BACKFILL_DAY = "backfill_day"
SERVICE_REFRESH_SCHEDULE = "refresh_schedule"
SERVICE_SET_SCHEDULE = "set_schedule"

BACKFILL_DAY_SCHEMA = vol.Schema(
    {
        vol.Required("date"): cv.date,
    }
)

SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("schedule"): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
        vol.Optional("frequency"): vol.In(["Once", "Everyday"]),
        vol.Optional("charge_start_time"): cv.time,
        vol.Optional("charge_end_time"): cv.time,
        vol.Optional("charge_power_w"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("charge_end_soc_percent"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
        vol.Optional("discharge_start_time"): cv.time,
        vol.Optional("discharge_end_time"): cv.time,
        vol.Optional("discharge_power_w"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("discharge_end_soc_percent"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=100)
        ),
    }
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _get_single_entry_data(hass: HomeAssistant) -> dict[str, Any]:
    """Return the only configured Duracell entry data."""

    entries = hass.data.get(DOMAIN, {})

    entry_values = [
        value
        for value in entries.values()
        if isinstance(value, dict)
        and "api" in value
        and "store" in value
        and "history" in value
        and "monthly" in value
    ]

    if len(entry_values) != 1:
        raise HomeAssistantError(
            f"Expected exactly one Duracell entry, found {len(entry_values)}"
        )

    return entry_values[0]


def _set_service_result(
    hass: HomeAssistant,
    *,
    service: str,
    success: bool,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Store latest service result in hass.data."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["last_service_result"] = {
        "service": service,
        "success": success,
        "message": message,
        "details": details or {},
        "updated_at": _now(),
    }

async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Duracell services."""

    if hass.services.has_service(DOMAIN, SERVICE_REFRESH_TODAY):
        return

    async def async_refresh_today(call: ServiceCall) -> None:
        """Force refresh today's stored 5-minute data."""

        service_name = SERVICE_REFRESH_TODAY

        try:
            entry_data = _get_single_entry_data(hass)
            await entry_data["history"].async_request_refresh()

            data = entry_data["history"].data or {}
            totals = data.get("totals") or {}

            message = (
                "Refreshed today's Duracell data. "
                f"Points: {data.get('point_count')}. "
                f"Production: {totals.get('production_kwh')} kWh. "
                f"Consumption: {totals.get('consumption_kwh')} kWh."
            )

            _set_service_result(
                hass,
                service=service_name,
                success=True,
                message=message,
                details={
                    "point_count": data.get("point_count"),
                    "updated_at": data.get("updated_at"),
                    "totals": totals,
                },
            )
            _LOGGER.info(message)

        except Exception as err:
            message = f"Failed to refresh today's Duracell data: {err}"
            _set_service_result(
                hass,
                service=service_name,
                success=False,
                message=message,
            )
            _LOGGER.exception(message)
            raise HomeAssistantError(message) from err

    async def async_refresh_month(call: ServiceCall) -> None:
        """Force refresh current month's stored daily data."""

        service_name = SERVICE_REFRESH_MONTH

        try:
            entry_data = _get_single_entry_data(hass)
            await entry_data["monthly"].async_request_refresh()

            data = entry_data["monthly"].data or {}
            totals = data.get("totals") or {}

            message = (
                "Refreshed current month's Duracell data. "
                f"Days: {data.get('day_count')}. "
                f"Production: {totals.get('production_kwh')} kWh. "
                f"Consumption: {totals.get('consumption_kwh')} kWh."
            )

            _set_service_result(
                hass,
                service=service_name,
                success=True,
                message=message,
                details={
                    "day_count": data.get("day_count"),
                    "updated_at": data.get("updated_at"),
                    "totals": totals,
                },
            )
            _LOGGER.info(message)

        except Exception as err:
            message = f"Failed to refresh current month's Duracell data: {err}"
            _set_service_result(
                hass,
                service=service_name,
                success=False,
                message=message,
            )
            _LOGGER.exception(message)
            raise HomeAssistantError(message) from err

    async def async_refresh_schedule(call: ServiceCall) -> None:
        """Force refresh Duracell schedule/device-shadow data."""

        service_name = SERVICE_REFRESH_SCHEDULE

        try:
            entry_data = _get_single_entry_data(hass)
            await entry_data["schedule"].async_request_refresh()

            data = entry_data["schedule"].data or {}
            schedules = data.get("schedules") or []

            message = f"Refreshed Duracell schedule data. Schedules: {len(schedules)}."

            _set_service_result(
                hass,
                service=service_name,
                success=True,
                message=message,
                details={
                    "schedules": schedules,
                    "mode_register": data.get("mode_register"),
                },
            )
            _LOGGER.info(message)

        except Exception as err:
            message = f"Failed to refresh Duracell schedule data: {err}"
            _set_service_result(
                hass,
                service=service_name,
                success=False,
                message=message,
            )
            _LOGGER.exception(message)
            raise HomeAssistantError(message) from err

    async def async_backfill_day(call: ServiceCall) -> None:
        """Fetch and store a specific day's 5-minute data."""

        service_name = SERVICE_BACKFILL_DAY

        try:
            entry_data = _get_single_entry_data(hass)

            target_date: date = call.data["date"]
            api = entry_data["api"]
            store = entry_data["store"]

            raw = await api.async_get_day_chart(target_date)
            normalized = normalize_day_response(raw, target_date)

            await store.async_write_day(target_date, normalized)

            totals = normalized.get("totals") or {}

            message = (
                f"Backfilled Duracell day data for {target_date.isoformat()}. "
                f"Points: {normalized.get('point_count')}. "
                f"Production: {totals.get('production_kwh')} kWh. "
                f"Consumption: {totals.get('consumption_kwh')} kWh."
            )

            _set_service_result(
                hass,
                service=service_name,
                success=True,
                message=message,
                details={
                    "date": target_date.isoformat(),
                    "point_count": normalized.get("point_count"),
                    "updated_at": normalized.get("updated_at"),
                    "totals": totals,
                },
            )
            _LOGGER.info(message)

        except Exception as err:
            message = f"Failed to backfill Duracell day data: {err}"
            _set_service_result(
                hass,
                service=service_name,
                success=False,
                message=message,
            )
            _LOGGER.exception(message)
            raise HomeAssistantError(message) from err

    async def async_set_schedule(call: ServiceCall) -> None:
        """Set one or more values on a Duracell schedule."""

        try:
            entry_data = _get_single_entry_data(hass)

            schedule_index = call.data["schedule"]
            frequency = call.data.get("frequency")
            charge = {
                "start_time": call.data.get("charge_start_time"),
                "end_time": call.data.get("charge_end_time"),
                "power_w": call.data.get("charge_power_w"),
                "end_soc_percent": call.data.get("charge_end_soc_percent"),
            }

            discharge = {
                "start_time": call.data.get("discharge_start_time"),
                "end_time": call.data.get("discharge_end_time"),
                "power_w": call.data.get("discharge_power_w"),
                "end_soc_percent": call.data.get("discharge_end_soc_percent"),
            }

            registers = build_schedule_registers(
                schedule_index,
                frequency=frequency,
                charge=charge,
                discharge=discharge,
            )

            result = await entry_data["api"].async_set_device_shadow(registers)

            if not result.get("status"):
                raise HomeAssistantError("Duracell rejected the schedule update")

            await entry_data["api"].async_wait_for_device_shadow_update()
            await entry_data["schedule"].async_request_refresh()

            message = f"Updated Duracell schedule {schedule_index}."

            _set_service_result(
                hass,
                service=SERVICE_SET_SCHEDULE,
                success=True,
                message=message,
                details={
                    "schedule": schedule_index,
                    "registers": registers,
                },
            )
            _LOGGER.info(message)

        except Exception as err:
            message = f"Failed to update Duracell schedule: {err}"
            _set_service_result(
                hass,
                service=SERVICE_SET_SCHEDULE,
                success=False,
                message=message,
            )
            _LOGGER.exception(message)
            raise HomeAssistantError(message) from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_TODAY,
        async_refresh_today,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_MONTH,
        async_refresh_month,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_SCHEDULE,
        async_refresh_schedule,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_BACKFILL_DAY,
        async_backfill_day,
        schema=BACKFILL_DAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        async_set_schedule,
        schema=SET_SCHEDULE_SCHEMA,
    )