from __future__ import annotations

from datetime import time
from typing import Any


FREQUENCY_MAP = {
    0: "Once",
    1: "Everyday",
}

def _to_int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def decode_packed_time(value: Any) -> str | None:
    """Decode time stored as high-byte hour, low-byte minute.

    Examples:
    257 = 0x0101 = 01:01
    258 = 0x0102 = 01:02
    513 = 0x0201 = 02:01
    5888 = 0x1700 = 23:00
    """

    raw = _to_int(value)
    if raw is None:
        return None

    hour = (raw >> 8) & 0xFF
    minute = raw & 0xFF

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return f"{hour:02d}:{minute:02d}"

def encode_packed_time(time_string: str | time) -> int:
    """Encode HH:MM as high-byte hour, low-byte minute."""
    if isinstance(time_string, time):
        hour = time_string.hour
        minute = time_string.minute
    else:
        hour_string, minute_string = time_string.split(":", 1)
        hour = int(hour_string)
        minute = int(minute_string)

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time: {time_string}")

    return (hour << 8) | minute

SCHEDULE_REGISTER_MAP = [
    {
        "index": 1,
        "frequency": "2101",
        "charge_start": "2102",
        "charge_end": "2103",
        "discharge_start": "2104",
        "discharge_end": "2105",
        "charge_power": "2169",
        "charge_end_soc": "216A",
        "discharge_power": "216D",
        "discharge_end_soc": "216E",
        "reserved": ["2168", "216B", "216C", "216F"],
    },
    {
        "index": 2,
        "frequency": "2106",
        "charge_start": "2107",
        "charge_end": "2108",
        "discharge_start": "2109",
        "discharge_end": "210A",
        "charge_power": "2171",
        "charge_end_soc": "2172",
        "discharge_power": "2175",
        "discharge_end_soc": "2176",
        "reserved": ["2170", "2173", "2174", "2177"],
    },
    {
        "index": 3,
        "frequency": "210B",
        "charge_start": "210C",
        "charge_end": "210D",
        "discharge_start": "210E",
        "discharge_end": "210F",
        "charge_power": "2179",
        "charge_end_soc": "217A",
        "discharge_power": "217D",
        "discharge_end_soc": "217E",
        "reserved": ["2178", "217B", "217C", "217F"],
    },
]

def _frequency_label(value: Any) -> str | None:
    code = _to_int(value)

    if code is None:
        return None

    return FREQUENCY_MAP.get(code, f"Unknown ({code})")

def parse_device_shadow(raw: dict[str, str]) -> dict[str, Any]:
    """Parse Duracell charge/discharge schedule registers."""

    schedules: list[dict[str, Any]] = []

    for mapping in SCHEDULE_REGISTER_MAP:
        frequency_register = mapping["frequency"]
        charge_start_register = mapping["charge_start"]
        charge_end_register = mapping["charge_end"]
        discharge_start_register = mapping["discharge_start"]
        discharge_end_register = mapping["discharge_end"]
        charge_power_register = mapping["charge_power"]
        charge_soc_register = mapping["charge_end_soc"]
        discharge_power_register = mapping["discharge_power"]
        discharge_soc_register = mapping["discharge_end_soc"]

        frequency_code = _to_int(raw.get(frequency_register))

        reserved = {
            register: raw.get(register)
            for register in mapping["reserved"]
            if register in raw
        }

        schedules.append(
            {
                "schedule": mapping["index"],
                "frequency": _frequency_label(raw.get(frequency_register)),
                "frequency_code": frequency_code,
                "charge": {
                    "start_time": decode_packed_time(raw.get(charge_start_register)),
                    "end_time": decode_packed_time(raw.get(charge_end_register)),
                    "power_w": _to_int(raw.get(charge_power_register)),
                    "end_soc_percent": _to_int(raw.get(charge_soc_register)),
                    "registers": {
                        "start_time": charge_start_register,
                        "end_time": charge_end_register,
                        "power_w": charge_power_register,
                        "end_soc_percent": charge_soc_register,
                    },
                },
                "discharge": {
                    "start_time": decode_packed_time(raw.get(discharge_start_register)),
                    "end_time": decode_packed_time(raw.get(discharge_end_register)),
                    "power_w": _to_int(raw.get(discharge_power_register)),
                    "end_soc_percent": _to_int(raw.get(discharge_soc_register)),
                    "registers": {
                        "start_time": discharge_start_register,
                        "end_time": discharge_end_register,
                        "power_w": discharge_power_register,
                        "end_soc_percent": discharge_soc_register,
                    },
                },
                "registers": {
                    "frequency": frequency_register,
                },
                "reserved": reserved,
            }
        )

    return {
        "mode_register": raw.get("1A18"),
        "schedule_count": len(schedules),
        "schedules": schedules,
        "raw": raw,
    }

def build_schedule_registers(
    schedule_index: int,
    frequency: str | None = None,
    charge: dict[str, Any] | None = None,
    discharge: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Build device-shadow register values for a schedule update."""

    mapping = next((item for item in SCHEDULE_REGISTER_MAP if item["index"] == schedule_index), None)

    if mapping is None:
        raise ValueError(f"Invalid schedule index: {schedule_index}")

    registers: dict[str, int] = {}

    if frequency is not None:
        frequency_code = next((code for code, label in FREQUENCY_MAP.items() if label == frequency), None)
        if frequency_code is None:
            raise ValueError(f"Invalid frequency: {frequency}")
        registers[mapping["frequency"]] = frequency_code

    if charge:
        if charge.get("start_time") is not None:
            registers[mapping["charge_start"]] = encode_packed_time(charge["start_time"])
        if charge.get("end_time") is not None:
            registers[mapping["charge_end"]] = encode_packed_time(charge["end_time"])
        if charge.get("power_w") is not None:
            registers[mapping["charge_power"]] = int(charge["power_w"])
        if charge.get("end_soc_percent") is not None:
            registers[mapping["charge_end_soc"]] = int(charge["end_soc_percent"])

    if discharge:
        if discharge.get("start_time") is not None:
            registers[mapping["discharge_start"]] = encode_packed_time(discharge["start_time"])
        if discharge.get("end_time") is not None:
            registers[mapping["discharge_end"]] = encode_packed_time(discharge["end_time"])
        if discharge.get("power_w") is not None:
            registers[mapping["discharge_power"]] = int(discharge["power_w"])
        if discharge.get("end_soc_percent") is not None:
            registers[mapping["discharge_end_soc"]] = int(discharge["end_soc_percent"])

    if not registers:
        raise ValueError("At least one schedule value must be provided")

    return registers