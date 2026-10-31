"""Activity log: entries (no Home Assistant) and their feed in Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smart_comfort.activity import Activity
from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.const import ACTIVITY_SIZE, DOMAIN
from custom_components.smart_comfort.control import Command

T0 = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = build_settings(
    {
        "rooms": [
            {
                "name": "Séjour",
                "fans": [{"entity_id": "fan.sejour", "display": "light.voyant"}],
                "purifiers": [{"entity_id": "fan.purif", "mode_select": "select.mode", "open_mode": "manual"}],
                "lights": ["light.salon"],
            }
        ]
    }
)


def test_commands_grouped_by_device():
    a = Activity(SETTINGS)
    sent = [
        (Command("fan.sejour", "fan", "turn_on", target="boost", device="fan.sejour"), True),
        (Command("fan.sejour", "fan", "set_preset_mode", {"preset_mode": "Standard"}, "boost", "fan.sejour"), True),
        (Command("select.mode", "select", "select_option", {"option": "manual"}, "boost", "fan.purif"), False),
        (
            Command("light.salon", "light", "turn_on", {"brightness_pct": 60, "transition": 1}, "60 %", "light.salon"),
            True,
        ),
        (Command("light.voyant", "light", "turn_off", target="display_off", device="light.voyant"), True),
    ]
    entries = a.commands(T0, sent)
    assert [(e["kind"], e["entity_id"], e.get("target")) for e in entries] == [
        ("device", "fan.sejour", "boost"),
        ("failed", "fan.purif", "boost"),
        ("lighting", "light.salon", "60 %"),
        ("display", "light.voyant", "display_off"),
    ]
    assert entries[0]["data"] == {"preset_mode": "Standard"} and entries[0]["room"] == "Séjour"
    assert entries[1]["failed"] == "select.select_option"
    assert entries[2]["data"] == {"brightness_pct": 60}
    # Most recent first.
    assert a.as_list(1)[0]["entity_id"] == "light.voyant"


def test_size_and_restore():
    a = Activity(SETTINGS)
    for i in range(ACTIVITY_SIZE + 5):
        a.add(T0 + timedelta(seconds=i), "manual", "light.salon")
    assert len(a.as_list()) == ACTIVITY_SIZE
    again = Activity(SETTINGS)
    again.restore([*a.as_dict(), {"kind": "unknown", "at": "x"}, "junk"])
    assert len(again.as_list()) == ACTIVITY_SIZE


async def test_feed(hass: HomeAssistant, hass_ws_client, hass_read_only_access_token) -> None:
    hass.states.async_set("sun.sun", "below_horizon", {"elevation": -12})
    hass.states.async_set("light.salon", "off", {"supported_color_modes": ["brightness"]})
    async_mock_service(hass, "light", "turn_on")
    options = {"startup_grace": 0, "rooms": [{"name": "Séjour", "lights": ["light.salon"]}]}
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # Any user can follow it (the card), not only the administrators.
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": f"{DOMAIN}/activity", "limit": 10})
    assert (await client.receive_json())["success"]
    assert (await client.receive_json())["event"] == {"entries": []}
    hass.states.async_set(
        "light.salon", "on", {"supported_color_modes": ["brightness"], "brightness": 255}, context=Context()
    )
    await hass.async_block_till_done()
    added = (await client.receive_json())["event"]["added"]
    assert added[0]["kind"] == "lighting" and added[0]["room"] == "Séjour"
    assert "brightness_pct" in added[0]["data"]
