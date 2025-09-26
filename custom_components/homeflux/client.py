from __future__ import annotations

import logging
from typing import Optional
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HomeFluxClient:
    def __init__(self, hass: HomeAssistant, endpoint: str, token: str,
                 grid_entity_id: str, pv_entity_id: str) -> None:
        self.hass = hass
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.grid_entity_id = grid_entity_id
        self.pv_entity_id = pv_entity_id

    def _num(self, st: Optional[State]) -> float:
        if not st or st.state in (None, "", "unknown", "unavailable"):
            return 0.0
        try:
            return float(st.state)
        except Exception:
            return 0.0

    async def send_once(self) -> bool:
        grid_w = round(self._num(self.hass.states.get(self.grid_entity_id)))
        pv_w   = round(self._num(self.hass.states.get(self.pv_entity_id)))
        ts = dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {"grid_w": grid_w, "pv_w": pv_w, "ts": ts}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        session = async_get_clientsession(self.hass)
        url = f"{self.endpoint}/ingest"
        try:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                text = await resp.text()
                if 200 <= resp.status < 300:
                    _LOGGER.debug("%s posted ok: %s", DOMAIN, text)
                    return True
                _LOGGER.warning("%s post failed %s: %s", DOMAIN, resp.status, text)
                return False
        except Exception as e:
            _LOGGER.error("%s post error: %s", DOMAIN, e)
            return False
