from __future__ import annotations

import base64
import logging
from typing import Any

from datetime import date
import json
import asyncio

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad
from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import BASE_API_ROOT, INVERTER_API_PATH, IOT_API_PATH, SIGN_ONE, SIGN_TWO

_LOGGER = logging.getLogger(__name__)

SCHEDULE_MODBUS_REGISTERS: list[str] = [
    "1A18",
    "2101", "2102", "2103", "2104", "2105",
    "2106", "2107", "2108", "2109", "210A",
    "210B", "210C", "210D", "210E", "210F",
    "2115", "2117", "2124", "2148", "214C",
    "2168", "2169", "216A", "216B", "216C", "216D", "216E", "216F",
    "2170", "2171", "2172", "2173", "2174", "2175", "2176", "2177",
    "2178", "2179", "217A", "217B", "217C", "217D", "217E", "217F",
]

class DuracellApiError(Exception):
    """Base Duracell API error."""


class DuracellAuthError(DuracellApiError):
    """Duracell authentication error."""


class DuracellApiClient:
    """Async API client for Duracell Energy."""

    def __init__(
        self,
        session: ClientSession,
        member_id: str,
        password: str,
        goods_id: str | None = None,
        member_auto_id: str | None = None,
    ) -> None:
        self._session = session
        self._member_id = member_id
        self._password = password
        self._goods_id = goods_id
        self._member_auto_id = member_auto_id
        self._token: str | None = None

    @staticmethod
    def _sign_code(input_data: dict[str, Any]) -> str:
        """Generate Duracell request signature."""

        keys: list[str] = []

        for key, value in input_data.items():
            if value == "" or value is None or isinstance(value, bool):
                continue
            keys.append(key)

        data_parts: list[str] = []

        for key in sorted(keys):
            value = input_data[key]
            if isinstance(value, list):
                data_parts.append(f"{key}=Array")
            else:
                data_parts.append(f"{key}={value}")

        data_string = "&".join(data_parts)
        data_string += f"&{SIGN_ONE}"

        cipher = AES.new(
            SIGN_ONE.encode("utf-8"),
            AES.MODE_CBC,
            iv=SIGN_TWO.encode("utf-8"),
        )

        cipher_text = cipher.encrypt(pad(data_string.encode("utf-8"), AES.block_size))
        return base64.b64encode(cipher_text).decode("utf-8")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._token or "null",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
        }

    async def async_login(self) -> dict[str, Any]:
        """Login and store JWT token and MemberAutoID."""

        payload: dict[str, Any] = {
            "MemberID": self._member_id,
            "Password": self._password,
            "type": "1",
        }
        payload["sign"] = self._sign_code(payload)

        try:
            async with self._session.post(
                f"{BASE_API_ROOT}/{INVERTER_API_PATH}/UserLogin_v1",
                json=payload,
                headers={
                    "Authorization": "null",
                    "accept": "application/json, text/plain, */*",
                    "content-type": "application/json",
                },
                timeout=30,
            ) as response:
                if response.status in (401, 403):
                    raise DuracellAuthError("Invalid Duracell credentials")

                response.raise_for_status()
                data = await response.json(content_type=None)

        except ClientResponseError as err:
            raise DuracellApiError(f"Login HTTP error: {err}") from err
        except ClientError as err:
            raise DuracellApiError(f"Login connection error: {err}") from err

        token = data.get("token")
        member_auto_id = data.get("MemberAutoID")

        if not token:
            _LOGGER.debug("Duracell login response did not contain token: %s", data)
            raise DuracellAuthError("Login succeeded but token was not found")

        if not member_auto_id:
            _LOGGER.debug("Duracell login response did not contain MemberAutoID: %s", data)
            raise DuracellAuthError("Login succeeded but MemberAutoID was not found")

        self._token = token
        self._member_auto_id = str(member_auto_id)

        return data

    async def async_make_request(
        self,
        endpoint: str,
        payload: dict[str, Any],
        base_path: str = INVERTER_API_PATH,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make a signed Duracell API request."""

        if not self._token:
            await self.async_login()

        request_payload = dict(payload)

        for attempt in range(2):
            request_payload["sign"] = self._sign_code(payload)

            try:
                async with self._session.post(
                    f"{BASE_API_ROOT}/{base_path}/{endpoint}",
                    json=request_payload,
                    headers=self._headers,
                    timeout=30,
                ) as response:
                    if response.status in (401, 403) and attempt == 0:
                        self._token = None
                        await self.async_login()
                        continue

                    response.raise_for_status()
                    data = await response.json(content_type=None)
                    break

            except ClientResponseError as err:
                raise DuracellApiError(f"Request HTTP error: {err}") from err
            except ClientError as err:
                raise DuracellApiError(f"Request connection error: {err}") from err
        else:
            raise DuracellAuthError("Duracell authentication failed")

        return data

    async def async_get_inverter_detail(self) -> dict[str, Any]:
        """Fetch inverter/battery detail data."""

        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        if not self._member_auto_id:
            await self.async_login()

        return await self.async_make_request(
            "InverterDetailInfoNewone",
            {
                "GoodsID": self._goods_id,
                "MemberAutoID": self._member_auto_id,
            },
        )

    async def async_get_member_monitor(self) -> dict[str, Any]:
        """Fetch account-level generation and income summary."""
        if not self._member_auto_id:
            await self.async_login()

        data = await self.async_make_request(
            "MemberMonitor",
            {"MemberAutoID": self._member_auto_id},
        )

        if not isinstance(data, dict):
            raise DuracellApiError("MemberMonitor response was not an object")

        return data

    async def async_get_pvi_errors(self) -> dict[str, Any]:
        """Fetch current inverter faults."""
        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        data = await self.async_make_request(
            "getPvierrorRealtime",
            {"GoodsID": self._goods_id},
        )

        if not isinstance(data, dict):
            raise DuracellApiError("PVI error response was not an object")

        return data

    async def async_get_realtime_flow(self) -> dict[str, Any]:
        """Fetch the portal's real-time inverter flow data."""
        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")
        data = await self.async_make_request(
            "getHybridFlowgraphRealTimeData_v1",
            {"GoodsID": self._goods_id},
        )

        if not isinstance(data, dict):
            raise DuracellApiError("Real-time flow response was not an object")

        return data

    async def async_get_inverter_summary(self) -> dict[str, Any]:
        """Fetch the portal's dedicated inverter identity and totals."""
        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")
        if not self._member_auto_id:
            await self.async_login()

        data = await self.async_make_request(
            "InverterDetail",
            {
                "GoodsID": self._goods_id,
                "MemberAutoID": self._member_auto_id,
            },
        )

        if not isinstance(data, dict):
            raise DuracellApiError("Inverter summary response was not an object")

        return data

    async def async_get_year_summary(self, year: int) -> dict[str, Any]:
        """Fetch annual production and consumption totals."""
        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        data = await self.async_make_request(
            "yeartwopiechartNew",
            {"GoodsID": self._goods_id, "inDate": str(year)},
        )

        if not isinstance(data, dict):
            raise DuracellApiError("Year summary response was not an object")

        return data

    async def async_get_year_chart(self, year: int) -> dict[str, Any]:
        """Fetch monthly production and consumption data for a year."""
        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        data = await self.async_make_request(
            "yearProductionAndConsumptionArea",
            {"GoodsID": self._goods_id, "date": str(year)},
        )

        if not isinstance(data, dict):
            raise DuracellApiError("Year chart response was not an object")

        return data

    async def async_get_day_chart(self, target_date: date | str) -> dict[str, Any]:
        """Fetch 5-minute production/consumption data for one day."""

        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        if not self._member_auto_id:
            await self.async_login()

        if isinstance(target_date, date):
            target_date = target_date.isoformat()

        return await self.async_make_request(
            "dayProductionAndConsumptionAreaTime",
            {
                "GoodsID": self._goods_id,
                "MemberAutoID": self._member_auto_id,
                "date": target_date,
            },
        )

    async def async_get_month_chart(self, year: int, month: int) -> dict[str, Any]:
        """Fetch daily production/consumption data for one month."""

        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        return await self.async_make_request(
            "monthProductionAndConsumptionArea",
            {
                "GoodsID": self._goods_id,
                "date": f"{year}-{month:02d}",
            },
        )

    async def async_get_group_list(self, input_value: str = "") -> list[dict[str, Any]]:
        """Fetch available inverter groups for the logged-in member."""

        if not self._member_auto_id:
            await self.async_login()

        data = await self.async_make_request(
            "GroupList",
            {
                "MemberAutoID": self._member_auto_id,
                "inputValue": input_value,
            },
        )

        groups = data.get("AllGroupList")

        if not isinstance(groups, list):
            raise DuracellApiError("GroupList response did not contain AllGroupList")

        return groups

    async def async_get_device_shadow(self) -> dict[str, str]:
        """Fetch Duracell inverter schedule/device-shadow registers."""

        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        data = await self.async_make_request(
            "getDeviceShadow_v2",
            {
                "GoodsID": self._goods_id,
                "pageFlage": 1,
                "ModbusArr": json.dumps(SCHEDULE_MODBUS_REGISTERS),
            },
            base_path=IOT_API_PATH,
        )

        if not isinstance(data, list):
            raise DuracellApiError("Device shadow response was not a list")

        merged: dict[str, str] = {}

        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    merged[str(key)] = str(value)

        return merged

    async def async_set_device_shadow(self, registers: dict[str, int | str]) -> dict[str, Any]:
        """Set the Duracell inverter schedule/device-shadown registers."""

        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        if not registers:
            raise DuracellApiError("Registers should contain at least one value")

        data = await self.async_make_request(
            "setDeviceShadow",
            {
                "GoodsID": self._goods_id,
                "pageFlage": 1,
                "ModbusArr": json.dumps(registers),
            },
            base_path=IOT_API_PATH,
        )

        if not isinstance(data, dict):
            raise DuracellApiError("Set device shadow response was not an object")

        return data


    async def async_get_device_shadow_status(self) -> bool:
        """Check whether the Duracell inverter has applied a device-shadow update."""

        if not self._goods_id:
            raise DuracellApiError("Missing GoodsID")

        data = await self.async_make_request(
            "getDeviceShadowStatus_v2",
            {
                "GoodsID": self._goods_id,
                "pageFlage": 1,
            },
            base_path=IOT_API_PATH,
        )

        if not isinstance(data, dict) or "status" not in data:
            raise DuracellApiError("Invalid device shadow status response")

        return bool(data["status"])

    async def async_wait_for_device_shadow_update(self, timeout: float = 30, interval: float = 1) -> None:
        """Wait for the Duracell inverter to apply a device-shadow update."""

        deadline = asyncio.get_running_loop().time() + timeout

        while asyncio.get_running_loop().time() < deadline:
            if await self.async_get_device_shadow_status():
                return

            await asyncio.sleep(interval)

        raise DuracellApiError("Timed out waiting for device shadow update")