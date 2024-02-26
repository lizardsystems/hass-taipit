"""Config flow for taipit integration."""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any

import aiohttp
from aiotaipit import SimpleTaipitAuth, TaipitApi
from aiotaipit.const import GUEST_PASSWORD, GUEST_USERNAME
from aiotaipit.exceptions import TaipitAuthError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithConfigEntry
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_TIMEOUT,
    CONF_METERS,
    CONF_UPDATE_PERIOD,
    DEFAULT_MIN_UPDATE_PERIOD,
    DEFAULT_UPDATE_PERIOD,
    DOMAIN,
)
from .exceptions import CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME, default=GUEST_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=GUEST_PASSWORD): str,
    }
)

REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        session = async_get_clientsession(hass)
        auth = SimpleTaipitAuth(
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            session=session,
        )
        api = TaipitApi(auth)

        async with asyncio.timeout(API_TIMEOUT):
            info = await api.async_get_meters()

        meters = {meter[CONF_ID]: meter for meter in info}

        return {"title": data[CONF_USERNAME].lower(), CONF_METERS: meters}

    except TaipitAuthError as exc:
        raise InvalidAuth from exc
    except (TimeoutError, aiohttp.ClientError) as exc:
        raise CannotConnect from exc


class TaipitConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for taipit."""

    VERSION = 1
    reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_USERNAME].lower()}")
            self._abort_if_unique_id_configured()
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle reauthorization request from Taipit."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm re-authentication with Taipit."""
        errors: dict[str, str] = {}

        if user_input:
            assert self.reauth_entry is not None
            password = user_input[CONF_PASSWORD]
            data = {
                CONF_USERNAME: self.reauth_entry.data[CONF_USERNAME],
                CONF_PASSWORD: password,
            }

            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.reauth_entry,
                    data={
                        **self.reauth_entry.data,
                        CONF_PASSWORD: password,
                    },
                )
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return TaipitOptionsFlowHandler(config_entry)


class TaipitOptionsFlowHandler(OptionsFlowWithConfigEntry):
    """Handle an options flow for Taipit."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            try:
                await validate_input(self.hass, data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(data=user_input)

        default_username = self.config_entry.data[CONF_USERNAME]
        default_password = self.config_entry.data[CONF_PASSWORD]
        default_update_interval = self.config_entry.options.get(
            CONF_UPDATE_PERIOD, DEFAULT_UPDATE_PERIOD
        )
        options_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=default_username): str,
                vol.Required(CONF_PASSWORD, default=default_password): str,
                vol.Optional(
                    CONF_UPDATE_PERIOD,
                    default=default_update_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=DEFAULT_MIN_UPDATE_PERIOD)),
            }
        )

        data_schema = self.add_suggested_values_to_schema(
            options_schema,
            user_input or self.options,
        )
        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=data_schema,
        )
