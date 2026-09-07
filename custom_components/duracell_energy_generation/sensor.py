from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GOODS_ID, CONF_INVERTER_NAME, DOMAIN
from .coordinator import DuracellDataUpdateCoordinator
from .diagnostics_coordinator import DuracellDiagnosticsCoordinator
from .realtime_coordinator import DuracellRealtimeCoordinator
from .yearly_coordinator import DuracellYearlyCoordinator


def _to_float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_float(value: Any) -> float | None:
    if isinstance(value, list) and value:
        return _to_float(value[0])
    return _to_float(value)


@dataclass(frozen=True, kw_only=True)
class DuracellSensorEntityDescription(SensorEntityDescription):
    """Duracell sensor description."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[DuracellSensorEntityDescription, ...] = (
    DuracellSensorEntityDescription(
        key="solar_power",
        name="Solar Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        value_fn=lambda data: _to_float(data.get("TotalDCpower")),
    ),
    DuracellSensorEntityDescription(
        key="battery_soc",
        name="Battery State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn=lambda data: _to_float(data.get("SOC")),
    ),
    DuracellSensorEntityDescription(
        key="battery_soh",
        name="Battery State of Health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-heart",
        value_fn=lambda data: _to_float(data.get("SOH")),
    ),
    DuracellSensorEntityDescription(
        key="battery_charge_power",
        name="Battery Charge Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-up",
        value_fn=lambda data: _to_float(data.get("toPbat")),
    ),
    DuracellSensorEntityDescription(
        key="battery_discharge_power",
        name="Battery Discharge Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
        value_fn=lambda data: _to_float(data.get("fromPbat")),
    ),
    DuracellSensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
        value_fn=lambda data: _to_float(data.get("volt")),
    ),
    DuracellSensorEntityDescription(
        key="battery_current",
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-dc",
        value_fn=lambda data: _to_float(data.get("cur")),
    ),
    DuracellSensorEntityDescription(
        key="battery_temperature",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        value_fn=lambda data: _to_float(data.get("BMS_temp")),
    ),
    DuracellSensorEntityDescription(
        key="daily_generation",
        name="Daily Generation",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-panel",
        value_fn=lambda data: _to_float(data.get("EToday")),
    ),
    DuracellSensorEntityDescription(
        key="total_generation",
        name="Total Generation",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-panel-large",
        value_fn=lambda data: _to_float(data.get("ETotal")),
    ),
    DuracellSensorEntityDescription(
        key="total_export",
        name="Total Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
        value_fn=lambda data: _to_float(data.get("ETTotal")),
    ),
    DuracellSensorEntityDescription(
        key="import",
        name="Total Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
        value_fn=lambda data: _to_float(data.get("EFTotal")),
    ),
    DuracellSensorEntityDescription(
        key="load_power",
        name="Load Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        value_fn=lambda data: _first_float(data.get("loadCurrpac")),
    ),
    DuracellSensorEntityDescription(
        key="daily_load_energy",
        name="Daily Load Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-battery",
        value_fn=lambda data: _to_float(data.get("ELDay")),
    ),
    DuracellSensorEntityDescription(
        key="total_load_energy",
        name="Total Load Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-battery",
        value_fn=lambda data: _to_float(data.get("ELTotal")),
    ),
    DuracellSensorEntityDescription(
        key="grid_voltage",
        name="Grid Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        value_fn=lambda data: _first_float(data.get("gridVac")),
    ),
    DuracellSensorEntityDescription(
        key="grid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
        value_fn=lambda data: _first_float(data.get("gridCurrpac")),
    ),
    DuracellSensorEntityDescription(
        key="wifi_strength",
        name="Wi-Fi Strength",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi",
        value_fn=lambda data: _to_float(data.get("WifiStrength")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Duracell sensors."""

    entry_data = hass.data[DOMAIN][entry.entry_id]

    coordinator: DuracellDataUpdateCoordinator = entry_data["live"]
    history_coordinator = entry_data["history"]
    monthly_coordinator = entry_data["monthly"]
    schedule_coordinator = entry_data["schedule"]
    diagnostics_coordinator: DuracellDiagnosticsCoordinator = entry_data["diagnostics"]
    realtime_coordinator: DuracellRealtimeCoordinator = entry_data["realtime"]
    yearly_coordinator: DuracellYearlyCoordinator = entry_data["yearly"]

    entities = [ DuracellSensor(coordinator, entry, description) for description in SENSORS ]

    entities.extend(
        [
            DuracellTodayProductionSensor(history_coordinator, entry),
            DuracellTodayConsumptionSensor(history_coordinator, entry),
            DuracellTodayToGridSensor(history_coordinator, entry),
            DuracellTodayFromGridSensor(history_coordinator, entry),
            DuracellMonthProductionSensor(monthly_coordinator, entry),
            DuracellMonthConsumptionSensor(monthly_coordinator, entry),
            DuracellScheduleSensor(schedule_coordinator, entry),
            DuracellServiceResultSensor(entry, hass),
            DuracellTodayBatteryChargeSensor(history_coordinator, entry),
            DuracellTodayBatteryDischargeSensor(history_coordinator, entry),
            DuracellFaultSensor(entry, diagnostics_coordinator),
            DuracellIncomeSensor(entry, diagnostics_coordinator, "Income Today", "IncomeToday"),
            DuracellIncomeSensor(entry, diagnostics_coordinator, "Income Total", "IncomeTotal"),
            DuracellRealtimeSensor(
                entry,
                realtime_coordinator,
                "online",
                "Online",
                "mdi:access-point-network",
            ),
            DuracellDeviceSummarySensor(entry, diagnostics_coordinator),
            DuracellYearSensor(
                entry, yearly_coordinator, "production_kwh", "Year Production"
            ),
            DuracellYearSensor(
                entry, yearly_coordinator, "consumption_kwh", "Year Consumption"
            ),
            DuracellYearSensor(
                entry, yearly_coordinator, "to_grid_kwh", "Year Export"
            ),
            DuracellYearSensor(
                entry, yearly_coordinator, "from_grid_kwh", "Year Import"
            ),
        ]
    )

    for schedule_index in (1, 2, 3):
        entities.append(
            DuracellScheduleSlotSensor(
                schedule_coordinator,
                entry,
                schedule_index,
                "charge",
            )
        )
        entities.append(
            DuracellScheduleSlotSensor(
                schedule_coordinator,
                entry,
                schedule_index,
                "discharge",
            )
        )

    async_add_entities(entities)


class DuracellSensor(CoordinatorEntity[DuracellDataUpdateCoordinator], SensorEntity):
    """Duracell sensor."""

    entity_description: DuracellSensorEntityDescription

    def __init__(
        self,
        coordinator: DuracellDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DuracellSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
            model=coordinator.data.get("modelName") if coordinator.data else None,
            serial_number=entry.data.get("goods_id"),
        )

    @property
    def native_value(self):
        """Return native sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        data = self.coordinator.data or {}

        return {
            "goods_id": data.get("GoodsID"),
            "goods_name": data.get("GoodsName"),
            "operating_mode": data.get("Operatingmode"),
            "operating_status": data.get("Operatingstatus"),
            "firmware_version": data.get("FirmwareVersion"),
            "esp32_status": (data.get("ESP32Version") or {}).get("Status")
            if isinstance(data.get("ESP32Version"), dict)
            else None,
            "battery_count": data.get("Batterynum"),
            "brand": data.get("brand"),
        }


class DuracellFaultSensor(CoordinatorEntity[DuracellDiagnosticsCoordinator], SensorEntity):
    """Diagnostic sensor showing the current inverter fault count."""

    _attr_name = "Duracell Faults"
    _attr_icon = "mdi:alert-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DuracellDiagnosticsCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_faults"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )

    @property
    def native_value(self) -> int:
        return int((self.coordinator.data or {}).get("errors", {}).get("total_error_num") or 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"faults": (self.coordinator.data or {}).get("errors", {}).get("infoerror")}


class DuracellIncomeSensor(
    CoordinatorEntity[DuracellDiagnosticsCoordinator], SensorEntity
):
    """Diagnostic sensor showing an account income value."""

    _attr_icon = "mdi:cash"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DuracellDiagnosticsCoordinator,
        name: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key.lower()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )

    @property
    def native_value(self) -> float | None:
        value = (self.coordinator.data or {}).get("member", {}).get(self._key)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        member = (self.coordinator.data or {}).get("member", {})
        return {"currency": member.get("unit"), "price": member.get("Price")}


class DuracellRealtimeSensor(
    CoordinatorEntity[DuracellRealtimeCoordinator], SensorEntity
):
    """Sensor backed by the portal's real-time flow response."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DuracellRealtimeCoordinator,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_realtime_{key.lower()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )

    @property
    def native_value(self) -> float | str | None:
        data = self.coordinator.data or {}
        value = data.get(self._key)
        if value is None and isinstance(data.get("realTime"), dict):
            value = data["realTime"].get(self._key)
        if value is None and isinstance(data.get("inverter_realtime"), dict):
            value = data["inverter_realtime"].get(self._key)
        if self._key == "online":
            return value if isinstance(value, str) else bool(value)
        return _to_float(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "timestamp": data.get("timestamp") or data.get("time"),
            "mode": data.get("Mode"),
            "status": data.get("status"),
        }


class DuracellDeviceSummarySensor(
    CoordinatorEntity[DuracellDiagnosticsCoordinator], SensorEntity
):
    """Diagnostic sensor exposing the portal's inverter summary."""

    _attr_name = "Inverter Summary"
    _attr_icon = "mdi:information-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DuracellDiagnosticsCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_inverter_summary"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )

    @property
    def native_value(self) -> str | None:
        data = (self.coordinator.data or {}).get("inverter", {})
        return data.get("DataTime") or data.get("Light")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = (self.coordinator.data or {}).get("inverter", {})
        return {
            "goods_id": data.get("GoodsID"),
            "model": data.get("ModelName"),
            "firmware": data.get("MDSPVersion"),
            "online": data.get("Light"),
            "current_power_w": _to_float(data.get("CurrPac")),
            "today_generation_kwh": _to_float(data.get("EToday")),
            "total_generation_kwh": _to_float(data.get("ETotal")),
            "data_time": data.get("DataTime"),
        }


class DuracellYearSensor(
    CoordinatorEntity[DuracellYearlyCoordinator], SensorEntity
):
    """Annual energy total from the portal's year summary."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: DuracellYearlyCoordinator,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = "mdi:chart-line"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("totals", {}).get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {"year": data.get("year"), "months": data.get("months")}

class DuracellStoredTotalSensor(CoordinatorEntity, SensorEntity):
    """Sensor for totals from stored Duracell chart data."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:chart-line"

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        unique_suffix: str,
        name: str,
        total_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = name
        self._total_key = total_key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        totals = data.get("totals") or {}
        return totals.get(self._total_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}

        return {
            "stored_data_updated_at": data.get("updated_at"),
            "point_count": data.get("point_count"),
            "day_count": data.get("day_count"),
        }


class DuracellTodayProductionSensor(DuracellStoredTotalSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_production_calculated",
            "Duracell Today Production Calculated",
            "production_kwh",
        )


class DuracellTodayConsumptionSensor(DuracellStoredTotalSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_consumption_calculated",
            "Duracell Today Consumption Calculated",
            "consumption_kwh",
        )


class DuracellTodayToGridSensor(DuracellStoredTotalSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_to_grid_calculated",
            "Duracell Today Export Calculated",
            "to_grid_kwh",
        )


class DuracellTodayFromGridSensor(DuracellStoredTotalSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "today_from_grid_calculated",
            "Duracell Today Import Calculated",
            "from_grid_kwh",
        )


class DuracellMonthProductionSensor(DuracellStoredTotalSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "month_production",
            "Duracell Month Production",
            "production_kwh",
        )


class DuracellMonthConsumptionSensor(DuracellStoredTotalSensor):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "month_consumption",
            "Duracell Month Consumption",
            "consumption_kwh",
        )

class DuracellServiceResultSensor(SensorEntity):
    """Diagnostic sensor showing the last Duracell service result."""

    _attr_name = "Duracell Last Service Result"
    _attr_icon = "mdi:clipboard-pulse"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: ConfigEntry, hass: HomeAssistant) -> None:
        self.hass = hass
        self._attr_unique_id = f"{entry.entry_id}_last_service_result"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
        )

    @property
    def native_value(self):
        result = self.hass.data.get(DOMAIN, {}).get("last_service_result") or {}

        if not result:
            return "No service call yet"

        return "Success" if result.get("success") else "Failed"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        result = self.hass.data.get(DOMAIN, {}).get("last_service_result") or {}

        return {
            "service": result.get("service"),
            "message": result.get("message"),
            "updated_at": result.get("updated_at"),
            "details": result.get("details"),
        }

class DuracellScheduleSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor showing Duracell schedule data."""

    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_schedule"
        self._attr_name = "Duracell Schedule"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
            serial_number=entry.data.get(CONF_GOODS_ID),
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        schedules = data.get("schedules") or []
        return f"{len(schedules)} schedules"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}

        return {
            "mode_register": data.get("mode_register"),
            "schedule_count": data.get("schedule_count"),
            "schedules": data.get("schedules"),
            "raw": data.get("raw"),
        }

class DuracellScheduleSlotSensor(CoordinatorEntity, SensorEntity):
    """Readable sensor for one Duracell charge/discharge schedule."""

    _attr_icon = "mdi:calendar-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        schedule_index: int,
        direction: str,
    ) -> None:
        super().__init__(coordinator)
        self._schedule_index = schedule_index
        self._direction = direction

        self._attr_unique_id = (
            f"{entry.entry_id}_schedule_{schedule_index}_{direction}"
        )
        self._attr_name = (
            f"Duracell Schedule {schedule_index} {direction.title()}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
            serial_number=entry.data.get(CONF_GOODS_ID),
        )

    def _schedule(self) -> dict[str, Any] | None:
        schedules = (self.coordinator.data or {}).get("schedules") or []

        for schedule in schedules:
            if schedule.get("schedule") == self._schedule_index:
                return schedule

        return None

    @property
    def native_value(self):
        schedule = self._schedule()

        if not schedule:
            return None

        item = schedule.get(self._direction) or {}

        start = item.get("start_time")
        end = item.get("end_time")
        power = item.get("power_w")
        soc = item.get("end_soc_percent")

        if not start or not end:
            return "Not configured"

        return f"{start}–{end}, {power} W, to {soc}%"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        schedule = self._schedule() or {}
        item = schedule.get(self._direction) or {}

        return {
            "schedule": self._schedule_index,
            "direction": self._direction,
            "frequency": schedule.get("frequency"),
            "frequency_code": schedule.get("frequency_code"),
            "start_time": item.get("start_time"),
            "end_time": item.get("end_time"),
            "power_w": item.get("power_w"),
            "end_soc_percent": item.get("end_soc_percent"),
            "registers": item.get("registers"),
        }

class DuracellTodayBatteryChargeSensor(CoordinatorEntity, SensorEntity):
    """Today's calculated battery charge energy."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:battery-arrow-up"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_today_battery_charge_calculated"
        self._attr_name = "Duracell Today Battery Charge Calculated"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
            serial_number=entry.data.get(CONF_GOODS_ID),
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        totals = data.get("totals") or {}
        return totals.get("to_battery_kwh")


class DuracellTodayBatteryDischargeSensor(CoordinatorEntity, SensorEntity):
    """Today's calculated battery discharge energy."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:battery-arrow-down"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_today_battery_discharge_calculated"
        self._attr_name = "Duracell Today Battery Discharge Calculated"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_INVERTER_NAME, "Duracell Energy"),
            manufacturer="Duracell",
            serial_number=entry.data.get(CONF_GOODS_ID),
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        totals = data.get("totals") or {}
        return totals.get("from_battery_kwh")