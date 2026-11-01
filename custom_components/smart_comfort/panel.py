"""Sidebar panel: a web component served from frontend/, registered when the frontend is loaded."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ICON, PANEL_URL, TITLE

STATIC_URL = f"/{DOMAIN}_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
MODULE = "smart-comfort-panel.js"
# The activity card, loaded on every dashboard.
CARD = "smart-comfort-activity-card.js"
ELEMENT = "smart-comfort-panel"


def _version() -> str:
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))
    return str(manifest.get("version", "0"))


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the panel's module (once per run) and add the panel to the sidebar, for administrators."""
    if "frontend" not in hass.config.components:
        return
    from homeassistant.components import frontend

    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("static_registered"):
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), False)])
        data["static_registered"] = True
    version = await hass.async_add_executor_job(_version)
    if not data.get("card_registered") and frontend.DATA_EXTRA_MODULE_URL in hass.data:
        frontend.add_extra_js_url(hass, f"{STATIC_URL}/{CARD}?v={version}")
        data["card_registered"] = True
    if PANEL_URL in hass.data.get(frontend.DATA_PANELS, {}):
        return
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL,
        require_admin=True,
        config={
            "_panel_custom": {
                "name": ELEMENT,
                "module_url": f"{STATIC_URL}/{MODULE}?v={version}",
                "embed_iframe": False,
                "trust_external": False,
            }
        },
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    if "frontend" not in hass.config.components:
        return
    from homeassistant.components import frontend

    if PANEL_URL in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL)
