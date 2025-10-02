from __future__ import annotations

import logging
import math
from typing import Optional

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    INGEST_PATH,  # "/ingest"
)

_LOGGER = logging.getLogger(__name__)


class HomeFluxClient:
    def __init__(
        self,
        hass: HomeAssistant,
        endpoint: str,
        token: str,
        grid_entity_id: Optional[str],
        pv_entity_id: Optional[str],
        grid_import_total_entity_id: Optional[str] = None,  # kWh (total_increasing)
        grid_export_total_entity_id: Optional[str] = None,  # kWh (total_increasing)
        pv_total_entity_id: Optional[str] = None,           # kWh (total_increasing)
    ) -> None:
        self.hass = hass
        self.endpoint = endpoint.rstrip("/")
        self.token = token

        self.grid_entity_id = grid_entity_id
        self.pv_entity_id = pv_entity_id

        self.grid_import_total_entity_id = grid_import_total_entity_id
        self.grid_export_total_entity_id = grid_export_total_entity_id
        self.pv_total_entity_id = pv_total_entity_id

    # ---------- helpers ----------

    def _state_as_float(self, entity_id: Optional[str]) -> Optional[float]:
        """Lees een sensorwaarde als float, of None bij onbekend/onbeschikbaar."""
        if not entity_id:
            return None
        st: Optional[State] = self.hass.states.get(entity_id)
        if not st or st.state in (None, "", "unknown", "unavailable"):
            return None
        try:
            v = float(str(st.state))
            return v if math.isfinite(v) else None
        except Exception:
            return None

    @staticmethod
    def _kwh_to_wh_int(v_kwh: Optional[float]) -> Optional[int]:
        """Converteer kWh → Wh (integer, ≥0)."""
        if v_kwh is None:
            return None
        wh = int(round(v_kwh * 1000.0))
        return max(0, wh)

    def _build_payload(self) -> dict:
        """Bouw de JSON payload met alleen aanwezige velden."""
        grid_w = self._state_as_float(self.grid_entity_id)
        pv_w = self._state_as_float(self.pv_entity_id)

        imp_kwh = self._state_as_float(self.grid_import_total_entity_id)
        exp_kwh = self._state_as_float(self.grid_export_total_entity_id)
        pv_kwh = self._state_as_float(self.pv_total_entity_id)

        payload: dict = {
            "ts": dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        if grid_w is not None:
            payload["grid_w"] = round(grid_w)
        if pv_w is not None:
            payload["pv_w"] = round(pv_w)

        gi = self._kwh_to_wh_int(imp_kwh)
        ge = self._kwh_to_wh_int(exp_kwh)
        pvt = self._kwh_to_wh_int(pv_kwh)

        if gi is not None:
            payload["grid_import_wh_total"] = gi
        if ge is not None:
            payload["grid_export_wh_total"] = ge
        if pvt is not None:
            payload["pv_wh_total"] = pvt

        return payload

    # ---------- public API ----------

    async def send_once(self) -> bool:
        """Post een sample naar /ingest. Retourneert True bij 2xx, anders False.

        Stuurt alleen velden mee die beschikbaar zijn. Als géén enkele meetwaarde
        aanwezig is (alleen ts), dan wordt niet gepost.
        """
        payload = self._build_payload()

        # Vereis minstens één meetveld naast ts
        has_measurement = any(
            k in payload
            for k in ("grid_w", "pv_w", "grid_import_wh_total", "grid_export_wh_total", "pv_wh_total")
        )
        if not has_measurement:
            _LOGGER.debug("%s no values to send; skipping post", DOMAIN)
            return True  # niets te doen is niet per se een fout

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        session = async_get_clientsession(self.hass)
        url = f"{self.endpoint}{INGEST_PATH}"

        try:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                text = await resp.text()
                if 200 <= resp.status < 300:
                    _LOGGER.debug("%s posted ok (%s): %s", DOMAIN, resp.status, text)
                    return True
                _LOGGER.warning("%s post failed %s: %s", DOMAIN, resp.status, text)
                return False
        except Exception as e:
            _LOGGER.error("%s post error: %s", DOMAIN, e)
            return False
