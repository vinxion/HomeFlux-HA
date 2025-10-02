# HomeFlux

Push je Home Assistant vermogenssensoren (grid & PV) en totale meterstanden elke *n* seconden naar je HomeFlux.

- Auth: **Bearer token**
- Interval: instelbaar (standaard 60s)
- Setup-validatie: doet een test-POST bij opslaan

## Installatie

### Via HACS (Custom Repository)
1. HACS → Integrations → ⋯ → **Custom repositories**
2. Voeg je GitHub-repo URL toe, **Category = Integration**
3. Zoek **HomeFlux** in HACS → **Install**
4. **Herstart Home Assistant**

### Handmatig
Kopieer `custom_components/homeflux/` naar je HA `config/` map en herstart.

## Configuratie
Instellingen → Apparaten & services → Integraties → **+** → **HomeFlux**

Vul in:
- **Token** (zonder `Bearer `)
- **Grid sensor** (W)
- **PV sensor** (W)
- **Meterstand import** (kWh)
- **Meterstand export** (kWh)
- **PV Totaal** (kWh)
- **Interval** (seconden)
