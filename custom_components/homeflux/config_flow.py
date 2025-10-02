from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from aiohttp import ClientError

from .const import (
    DOMAIN,
    CONF_ENDPOINT,
    CONF_TOKEN,
    CONF_GRID_ENTITY,
    CONF_PV_ENTITY,
    CONF_INTERVAL,
    DEFAULT_ENDPOINT,
    DEFAULT_INTERVAL,
    # ✅ nieuw: optionele cumulatieve energie-entiteiten (kWh, total_increasing)
    CONF_GRID_IMPORT_TOTAL_ENTITY,
    CONF_GRID_EXPORT_TOTAL_ENTITY,
    CONF_PV_TOTAL_ENTITY,
)

# Interne excepties voor nette foutafhandeling
class CannotConnect(Exception):
    pass

class InvalidAuth(Exception):
    pass


class HomeFluxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN]
            try:
                await self._async_test_post(token)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                # Endpoint staat vast op DEFAULT_ENDPOINT (zoals in je huidige flow)
                data = {**user_input, CONF_ENDPOINT: DEFAULT_ENDPOINT}
                return self.async_create_entry(title="HomeFlux", data=data)

        schema = vol.Schema({
            vol.Required(CONF_TOKEN): str,
            vol.Required(CONF_GRID_ENTITY): selector.selector({
                "entity": {"domain": "sensor"}
            }),
            vol.Required(CONF_PV_ENTITY): selector.selector({
                "entity": {"domain": "sensor"}
            }),
            vol.Required(CONF_INTERVAL, default=DEFAULT_INTERVAL): int,

            # ✅ Nieuw: optioneel, kies cumulatieve energiesensoren (kWh, total_increasing)
            vol.Optional(CONF_GRID_IMPORT_TOTAL_ENTITY): selector.selector({
                "entity": {"domain": "sensor", "device_class": "energy"}
            }),
            vol.Optional(CONF_GRID_EXPORT_TOTAL_ENTITY): selector.selector({
                "entity": {"domain": "sensor", "device_class": "energy"}
            }),
            vol.Optional(CONF_PV_TOTAL_ENTITY): selector.selector({
                "entity": {"domain": "sensor", "device_class": "energy"}
            }),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_test_post(self, token: str) -> None:
        """Doe een minimale POST naar /ingest om token/endpoint te verifiëren."""
        session = async_get_clientsession(self.hass)
        url = f"{DEFAULT_ENDPOINT.rstrip('/')}/ingest"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        payload = {
            "grid_w": 0,
            "pv_w": 0,
            # ✅ nieuw: Wh totalen meezenden (0 is OK voor test)
            "grid_import_wh_total": 0,
            "grid_export_wh_total": 0,
            "pv_wh_total": 0,
            "ts": dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                if resp.status == 401:
                    raise InvalidAuth()
                if 200 <= resp.status < 300:
                    return
                raise CannotConnect()
        except ClientError:
            raise CannotConnect()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HomeFluxOptionsFlow(config_entry)


class HomeFluxOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        data = {**self.entry.data, **(self.entry.options or {})}
        if user_input is not None:
            merged = {**self.entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self.entry, data=merged)
            return self.async_create_entry(title="", data={})

        schema = vol.Schema({
            # Alleen interval als optie (endpoint/token/entiteiten blijven onderdeel van data)
            vol.Required(CONF_INTERVAL, default=data.get(CONF_INTERVAL, DEFAULT_INTERVAL)): int,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
