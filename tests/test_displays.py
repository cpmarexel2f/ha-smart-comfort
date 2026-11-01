"""Indicator lights and displays of the devices, and the reset times: decisions and their wiring in Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.const import DOMAIN
from custom_components.smart_comfort.control import Controller
from custom_components.smart_comfort.displays import DisplayController, DisplayState, off_option

OPTIONS = {
    "control": {"night_start": "22:00", "night_end": "07:00", "display_off": "20:00", "display_on": "10:00"},
    "rooms": [
        {
            "name": "Séjour",
            "fans": [{"entity_id": "fan.sejour", "display": "number.sejour_ecran"}],
            "purifiers": [{"entity_id": "fan.purif", "display": "light.purif_voyant"}],
        },
        {
            "name": "Chambre",
            "fans": [{"entity_id": "fan.chambre", "display": "select.chambre_voyant"}],
            "purifiers": [{"entity_id": "fan.chambre_purif", "closed_preset": "Auto", "reset_at": "20:40"}],
            "naps": [{"start": "13:30", "end": "15:30"}],
        },
    ],
}
OPTIONS_SELECT = ("Typiquement", "Sombre", "Fermer")


def at(hour, minute=0):
    return datetime(2026, 10, 31, hour, minute)


def states(screen="100", light="on", select="Typiquement"):
    return {
        "number.sejour_ecran": DisplayState("number", screen, minimum=0, maximum=100),
        "light.purif_voyant": DisplayState("light", light),
        "select.chambre_voyant": DisplayState("select", select, options=OPTIONS_SELECT),
    }


def run(controller, room, when, current):
    return {c.entity_id: (c.service, c.data) for c in controller.evaluate(when, room, current)}


def test_off_option():
    assert off_option(OPTIONS_SELECT) == "Fermer"
    assert off_option(["bright", "dim", "off"]) == "off"
    assert off_option(["Hell", "Dunkel", "Aus"]) == "Aus"
    assert off_option(["auto", "low"]) is None


def test_displays_by_hours():
    s = build_settings(OPTIONS)
    c = DisplayController(s)
    living, bedroom = s.rooms
    # By day: on already, nothing to do.
    assert run(c, living, at(12), states()) == {}
    # 20:00: off, the number at its minimum.
    assert run(c, living, at(20), states()) == {
        "number.sejour_ecran": ("set_value", {"value": 0}),
        "light.purif_voyant": ("turn_off", {}),
    }
    # Turned back on by hand in the evening: left on until the next change.
    assert run(c, living, at(21), states(light="on", screen="0")) == {}
    # 10:00: on again, at the brightness it had.
    assert run(c, living, at(10), states(screen="0", light="off")) == {
        "number.sejour_ecran": ("set_value", {"value": 100.0}),
        "light.purif_voyant": ("turn_on", {}),
    }
    # A select: its "off" option, then the one it had.
    assert run(c, bedroom, at(20), states()) == {"select.chambre_voyant": ("select_option", {"option": "Fermer"})}
    assert run(c, bedroom, at(10), states(select="Fermer")) == {
        "select.chambre_voyant": ("select_option", {"option": "Typiquement"})
    }


def test_displays_off_during_naps():
    s = build_settings(OPTIONS)
    c = DisplayController(s)
    living, bedroom = s.rooms
    run(c, bedroom, at(12), states(select="Sombre"))
    # The nap of the bedroom: its displays off, not those of the living room; back as they were after.
    assert run(c, bedroom, at(14), states(select="Sombre")) == {
        "select.chambre_voyant": ("select_option", {"option": "Fermer"})
    }
    assert run(c, living, at(14), states()) == {}
    assert run(c, bedroom, at(15, 30), states(select="Fermer")) == {
        "select.chambre_voyant": ("select_option", {"option": "Sombre"})
    }


def test_displays_follow_the_night_without_hours():
    s = build_settings({**OPTIONS, "control": {"night_start": "22:00", "night_end": "07:00"}})
    c = DisplayController(s)
    assert run(c, s.rooms[0], at(21), states()) == {}
    assert "light.purif_voyant" in run(c, s.rooms[0], at(23), states())


def test_state_survives_restart():
    s = build_settings(OPTIONS)
    c = DisplayController(s)
    run(c, s.rooms[0], at(20), states(screen="60"))
    again = DisplayController(s)
    again.restore(c.as_dict())
    # Same wanted state: not sent again; back on at the brightness of before.
    assert run(again, s.rooms[0], at(21), states(screen="0", light="off")) == {}
    assert run(again, s.rooms[0], at(10), states(screen="0", light="off"))["number.sejour_ecran"] == (
        "set_value",
        {"value": 60.0},
    )


def test_reset_at():
    s = build_settings(OPTIONS)
    c = Controller(s)
    now = datetime(2026, 10, 31, 19, 0, tzinfo=UTC)
    c.targets["fan.chambre_purif"] = "normal"
    c.manual_change("fan.chambre_purif", now)
    assert c.reset_due(at(20, 30)) == []  # First check: nothing to compare with.
    assert c.reset_due(at(20, 39)) == []
    assert c.reset_due(at(20, 40)) == ["fan.chambre_purif"]
    assert "fan.chambre_purif" not in c.overrides and "fan.chambre_purif" not in c.targets
    assert c.reset_due(at(20, 41)) == []
    # Past midnight: the next day's.
    assert c.reset_due(datetime(2026, 11, 1, 20, 40, 30)) == ["fan.chambre_purif"]


async def test_in_home_assistant(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-31 18:58:00+00:00")  # 19:58 in Paris.
    await hass.config.async_set_time_zone("Europe/Paris")
    hass.states.async_set("fan.purif", "on")
    hass.states.async_set("light.purif_voyant", "on", {"supported_color_modes": ["onoff"]})
    hass.states.async_set("fan.chambre_purif", "on", {"preset_mode": "Auto", "preset_modes": ["Auto", "Favorite"]})
    off = async_mock_service(hass, "light", "turn_off")
    preset = async_mock_service(hass, "fan", "set_preset_mode")
    options = {
        "startup_grace": 0,
        "control": OPTIONS["control"],
        "rooms": [
            {"name": "Séjour", "purifiers": [{"entity_id": "fan.purif", "display": "light.purif_voyant"}]},
            OPTIONS["rooms"][1],
        ],
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    manager = entry.runtime_data
    await manager.async_evaluate()
    assert off == []
    # 20:00: the indicator off.
    freezer.move_to("2026-10-31 19:00:10+00:00")
    await manager.async_evaluate()
    await hass.async_block_till_done()
    assert [c.data["entity_id"] for c in off] == ["light.purif_voyant"]
    # Favorite by hand: paused, then back to Auto at 20:40.
    freezer.move_to("2026-10-31 19:10:00+00:00")
    hass.states.async_set("fan.chambre_purif", "on", {"preset_mode": "Favorite", "preset_modes": ["Auto", "Favorite"]})
    await hass.async_block_till_done()
    await manager.async_evaluate()
    assert preset == []
    freezer.move_to("2026-10-31 19:40:05+00:00")
    await manager.async_evaluate()
    await hass.async_block_till_done()
    assert [c.data for c in preset] == [{"entity_id": "fan.chambre_purif", "preset_mode": "Auto"}]
