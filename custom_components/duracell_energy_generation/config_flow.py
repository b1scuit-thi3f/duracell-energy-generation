from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import DuracellApiClient, DuracellApiError, DuracellAuthError
from .const import (
    CONF_GOODS_ID,
    CONF_INVERTER_AUTO_ID,
    CONF_INVERTER_NAME,
    CONF_MEMBER_AUTO_ID,
    CONF_MEMBER_ID,
    CONF_PASSWORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class DuracellConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Duracell Energy Generation."""

    VERSION = 1

    def __init__(self) -> None:
        self._member_id: str | None = None
        self._password: str | None = None
        self._member_auto_id: str | None = None
        self._groups: list[dict[str, Any]] = []

    async def async_step_user(self, user_input=None):
        """Handle Duracell account login."""

        errors: dict[str, str] = {}

        if user_input is not None:
            member_id = user_input[CONF_MEMBER_ID]
            password = user_input[CONF_PASSWORD]

            session = async_get_clientsession(self.hass)
            api = DuracellApiClient(
                session=session,
                member_id=member_id,
                password=password,
            )

            try:
                login_data = await api.async_login()
                groups = await api.async_get_group_list()
            except DuracellAuthError:
                errors["base"] = "invalid_auth"
            except DuracellApiError:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Unable to connect to Duracell API")
            except Exception:
                errors["base"] = "unknown"
                _LOGGER.exception("Unexpected error setting up Duracell integration")
            else:
                if not groups:
                    errors["base"] = "no_inverters"
                else:
                    self._member_id = member_id
                    self._password = password
                    self._member_auto_id = str(login_data["MemberAutoID"])
                    self._groups = groups

                    return await self.async_step_inverter()

        schema = vol.Schema(
            {
                vol.Required(CONF_MEMBER_ID): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_inverter(self, user_input=None):
        """Select inverter and optional friendly name."""

        errors: dict[str, str] = {}

        inverter_options: dict[str, str] = {}

        for group in self._groups:
            goods_id = str(group.get("GoodsTypeName") or "")
            if not goods_id:
                continue

            label_parts = [goods_id]

            curr_pac = group.get("CurrPac")
            last_update = group.get("LastUpdate")

            if curr_pac is not None:
                label_parts.append(f"{curr_pac} W")

            if last_update:
                label_parts.append(f"updated {last_update}")

            inverter_options[goods_id] = " - ".join(label_parts)

        if not inverter_options:
            return self.async_abort(reason="no_inverters")

        schema = vol.Schema(
            {
                vol.Required(CONF_GOODS_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": value, "label": label}
                            for value, label in inverter_options.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_INVERTER_NAME): selector.TextSelector(),
            }
        )

        if user_input is not None:
            goods_id = user_input[CONF_GOODS_ID]
            friendly_name = user_input.get(CONF_INVERTER_NAME)

            selected_group = next(
                (
                    group
                    for group in self._groups
                    if str(group.get("GoodsTypeName")) == goods_id
                ),
                None,
            )

            if selected_group is None:
                errors["base"] = "invalid_inverter"
            else:
                inverter_auto_id = str(selected_group.get("AutoID") or "")

                await self.async_set_unique_id(goods_id)
                self._abort_if_unique_id_configured()

                title = friendly_name or f"Duracell Inverter {goods_id}"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_MEMBER_ID: self._member_id,
                        CONF_PASSWORD: self._password,
                        CONF_MEMBER_AUTO_ID: self._member_auto_id,
                        CONF_GOODS_ID: goods_id,
                        CONF_INVERTER_AUTO_ID: inverter_auto_id,
                        CONF_INVERTER_NAME: title,
                    },
                )

        return self.async_show_form(
            step_id="inverter",
            data_schema=schema,
            errors=errors,
        )