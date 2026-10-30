"""Configuration panel: WebSocket commands and sidebar registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smart_comfort.const import DOMAIN, PANEL_URL

OPTIONS = {
    "notify": ["notify.phone"],
    "startup_grace": 0,
    "rooms": [{"name": "Living room", "temperature": "sensor.t"}],
}


async def _setup(hass: HomeAssistant, data: dict | None = None) -> MockConfigEntry:
    hass.states.async_set("sensor.t", "21")
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data=data or {}, options=OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_get_config(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass, {"yaml_hash": "x"})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/config"})
    msg = await client.receive_json()
    assert msg["success"]
    result = msg["result"]
    assert result["loaded"] is True
    assert result["yaml"] is True
    assert result["options"]["rooms"][0]["name"] == "Living room"
    assert result["defaults"]["alerts"]["too_hot"]["threshold"] == 27.0
    assert "climate" in result["defaults"]["control"]
    assert result["kinds"][0] == "too_hot"


async def test_save_config(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup(hass, {"yaml_hash": "x"})
    client = await hass_ws_client(hass)
    options = {
        **OPTIONS,
        "quiet_start": "22:30",
        "rooms": [
            {"name": "Living room", "temperature": "sensor.t", "fans": [{"entity_id": "fan.f", "preset": "Natural"}]},
            {"name": "Bedroom"},
        ],
    }
    await client.send_json_auto_id({"type": f"{DOMAIN}/config/save", "options": options})
    msg = await client.receive_json()
    assert msg["success"], msg
    await hass.async_block_till_done()
    assert entry.options["quiet_start"] == "22:30:00"
    assert [r["name"] for r in entry.options["rooms"]] == ["Living room", "Bedroom"]
    # Saved from the panel: the YAML hash is kept, so an unchanged YAML doesn't override it.
    assert entry.data["yaml_hash"] == "x"
    assert [r.name for r in entry.runtime_data.settings.rooms] == ["Living room", "Bedroom"]


async def test_save_rejects_invalid(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/config/save", "options": {"rooms": [{"name": "A"}, {"name": "a"}]}}
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_format"
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/config/save", "options": {"alerts": {"too_hot": {"severity": "loud"}}}}
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert entry.options == OPTIONS


async def test_subscribe_follows_reloads(hass: HomeAssistant, hass_ws_client) -> None:
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/subscribe"})
    msg = await client.receive_json()
    assert msg["success"]
    msg = await client.receive_json()
    status = msg["event"]["status"]
    assert status["rooms"][0]["name"] == "Living room"
    assert status["rooms"][0]["temperature"] == 21.0
    assert status["notifications_enabled"] is True
    # A reload (options saved) keeps the subscription alive.
    hass.config_entries.async_update_entry(entry, options={**OPTIONS, "rooms": [{"name": "Office"}]})
    await hass.async_block_till_done()
    # The setup sends the new status at once, not at the next evaluation. Before it, the unload may send
    # none (no loaded entry) or, on older Home Assistant versions, the status of the entry being unloaded.
    for _ in range(3):
        msg = await client.receive_json()
        status = msg["event"]["status"]
        if status is not None and [r["name"] for r in status["rooms"]] == ["Office"]:
            break
    else:
        raise AssertionError("no status with the new rooms")


async def test_not_admin(hass: HomeAssistant, hass_ws_client, hass_read_only_access_token) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": f"{DOMAIN}/config"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"


async def test_panel_registered(hass: HomeAssistant) -> None:
    # The frontend itself isn't needed (its package may not be installed): only its panel registry.
    hass.config.components.add("frontend")
    hass.http = Mock(async_register_static_paths=AsyncMock())
    await _setup(hass)
    paths = hass.http.async_register_static_paths.call_args.args[0]
    assert paths[0].url_path == "/smart_comfort_static"
    panels = hass.data["frontend_panels"]
    assert PANEL_URL in panels
    panel = panels[PANEL_URL]
    assert panel.require_admin
    assert panel.config["_panel_custom"]["name"] == "smart-comfort-panel"
    assert panel.config["_panel_custom"]["module_url"].startswith("/smart_comfort_static/smart-comfort-panel.js?v=")
    # Reloading the entry keeps the panel (an open panel must not vanish when its options are saved).
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL in hass.data["frontend_panels"]
    assert hass.http.async_register_static_paths.call_count == 1
    # Removing the integration removes the panel.
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL not in hass.data["frontend_panels"]
