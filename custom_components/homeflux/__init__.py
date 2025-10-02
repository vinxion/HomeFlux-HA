from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

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
from .client import HomeFluxClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = []  # geen entiteiten

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = entry.data

    endpoint = data.get(CONF_ENDPOINT, DEFAULT_ENDPOINT)
    token = data[CONF_TOKEN]
    grid_entity = data[CONF_GRID_ENTITY]
    pv_entity = data[CONF_PV_ENTITY]
    interval = int(data.get(CONF_INTERVAL, DEFAULT_INTERVAL))

    # ✅ optioneel: extra total_increasing entiteiten (kunnen None zijn)
    grid_import_total_entity = data.get(CONF_GRID_IMPORT_TOTAL_ENTITY)
    grid_export_total_entity = data.get(CONF_GRID_EXPORT_TOTAL_ENTITY)
    pv_total_entity = data.get(CONF_PV_TOTAL_ENTITY)

    client = HomeFluxClient(
        hass,
        endpoint,
        token,
        grid_entity,
        pv_entity,
        grid_import_total_entity,  # kWh → Wh in client
        grid_export_total_entity,  # kWh → Wh in client
        pv_total_entity,           # kWh → Wh in client
    )

    async def _interval_callback(now):
        await client.send_once()

    unsub = async_track_time_interval(
        hass,
        _interval_callback,
        timedelta(seconds=interval),
    )

    # 1x direct versturen bij toevoegen
    hass.async_create_task(client.send_once())

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = unsub
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unsub = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if unsub:
        try:
            unsub()
        except Exception:
            pass
    return True
