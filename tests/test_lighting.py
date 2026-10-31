"""Adaptive lighting: decisions (no Home Assistant) and its wiring in Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.const import DOMAIN
from custom_components.smart_comfort.lighting import LightController, LightState, day_share, phase

T0 = datetime(2026, 10, 31, 19, 0, tzinfo=UTC)
# Local date and time (Saturday 31 October 2026).
EVENING = datetime(2026, 10, 31, 19, 0)
NIGHT = datetime(2026, 10, 31, 23, 30)


def at(hour, minute=0, day=31):
    return datetime(2026, 10, day, hour, minute)


WARM = {"min_kelvin": 2000, "max_kelvin": 6500}


def settings(**lighting):
    return build_settings(
        {
            "lighting": lighting,
            "rooms": [
                {
                    "name": "Séjour",
                    "lights": [
                        "light.salon",
                        {"entity_id": "light.veilleuse", "night_only": True},
                        {"entity_id": "light.canape", "evening": 40, "warmth": False},
                    ],
                }
            ],
        }
    )


def calls(cmds):
    return {c.entity_id: c.data for c in cmds}


def test_day_share_and_phase():
    assert day_share(None) == 1.0
    assert day_share(30) == 1.0
    assert day_share(-10) == 0.0
    assert day_share(0) == 0.5
    s = settings()
    assert phase(s, at(12), 30) == "day"
    assert phase(s, EVENING, -8) == "evening"
    assert phase(s, NIGHT, -30) == "night"


def test_brightness_by_time_of_day():
    s = settings()
    c = LightController(s)
    room = s.rooms[0]
    on = {
        "light.salon": LightState(on=True, brightness=100, kelvin=4000, **WARM),
        "light.veilleuse": LightState(on=True, brightness=50),
        "light.canape": LightState(on=True, brightness=100, **WARM),
    }
    # Evening (sun down): 60 % and warm; the night light is left alone; the sofa has its own level, no warmth.
    sent = calls(c.evaluate(T0, EVENING, -10, room, on))
    assert sent["light.salon"] == {"brightness_pct": 60, "color_temp_kelvin": 2700, "transition": 1}
    assert sent["light.canape"] == {"brightness_pct": 40, "transition": 1}
    assert "light.veilleuse" not in sent
    # Nothing new: nothing sent (a light in its transition is not sent again).
    assert c.evaluate(T0 + timedelta(minutes=1), EVENING, -10, room, on) == []
    # Night: the night level, gradually; the night light too.
    sent = calls(c.evaluate(T0 + timedelta(hours=4), NIGHT, -30, room, on))
    assert sent["light.salon"] == {"brightness_pct": 15, "color_temp_kelvin": 2200, "transition": 120}
    assert sent["light.veilleuse"] == {"brightness_pct": 15, "transition": 1}


def test_dawn_blend_and_kelvin_range():
    s = settings()
    c = LightController(s)
    state = {"light.salon": LightState(on=True, brightness=50, min_kelvin=3000, max_kelvin=5000)}
    # Sun at 0°: halfway between evening and day; warmth kept within what the light can do.
    sent = calls(c.evaluate(T0, at(8), 0, s.rooms[0], state))
    assert sent["light.salon"]["brightness_pct"] == 80
    assert sent["light.salon"]["color_temp_kelvin"] == 3350


def test_quiet_morning_and_naps():
    s = build_settings(
        {
            "control": {"night_start": "22:00", "night_end": "07:00"},
            "lighting": {"morning_end": "09:30"},
            "rooms": [
                {
                    "name": "Chambre",
                    "lights": ["light.chambre", {"entity_id": "light.veilleuse", "night_only": True}],
                    "lighting": {"quiet_morning": True, "morning": 30},
                    "naps": [{"start": "13:30", "end": "15:30", "days": ["sat", "sun"]}],
                },
                {"name": "Séjour", "lights": ["light.salon"]},
            ],
        }
    )
    bedroom, living = s.rooms
    on = {
        "light.chambre": LightState(on=True, brightness=100, **WARM),
        "light.veilleuse": LightState(on=True, brightness=100),
        "light.salon": LightState(on=True, brightness=100, **WARM),
    }
    # 8:00 with the sun up: the bedroom stays dim until 9:30, the living room is at its day level.
    assert phase(s, at(8), 10, bedroom) == "morning"
    assert phase(s, at(8), 10, living) == "day"
    sent = calls(LightController(s).evaluate(T0, at(8), 10, bedroom, on))
    assert sent == {"light.chambre": {"brightness_pct": 30, "color_temp_kelvin": 3000, "transition": 1}}
    assert calls(LightController(s).evaluate(T0, at(8), 10, living, on))["light.salon"]["brightness_pct"] == 100
    assert phase(s, at(9, 30), 10, bedroom) == "day"
    # Saturday's nap: dim, the night light too; not on a weekday (Monday 2 November).
    assert phase(s, at(14), 30, bedroom) == "nap"
    sent = calls(LightController(s).evaluate(T0, at(14), 30, bedroom, on))
    assert sent["light.chambre"] == {"brightness_pct": 15, "color_temp_kelvin": 2200, "transition": 1}
    assert sent["light.veilleuse"]["brightness_pct"] == 15
    assert phase(s, datetime(2026, 11, 2, 14, 0), 30, bedroom) == "day"
    assert phase(s, at(14), 30, living) == "day"


def test_warmth_can_be_turned_off():
    s = settings(warmth=False)
    c = LightController(s)
    state = {"light.salon": LightState(on=True, brightness=100, **WARM)}
    assert calls(c.evaluate(T0, EVENING, -10, s.rooms[0], state))["light.salon"] == {
        "brightness_pct": 60,
        "transition": 1,
    }


def test_off_lights_untouched_and_manual_pause():
    s = settings()
    c = LightController(s)
    room = s.rooms[0]
    # Off or on/off only: never touched (Smart Comfort doesn't turn lights on).
    assert c.evaluate(T0, EVENING, -10, room, {"light.salon": LightState(on=False)}) == []
    assert c.evaluate(T0, EVENING, -10, room, {"light.salon": LightState(on=True, dimmable=False)}) == []
    on = {"light.salon": LightState(on=True, brightness=100)}
    assert c.evaluate(T0, EVENING, -10, room, on)
    # Changed by hand: paused, even when the target changes.
    c.manual_change("light.salon", T0)
    assert c.evaluate(T0 + timedelta(minutes=30), NIGHT, -30, room, on) == []
    # Turned off: the pause ends; turned on again, the level of the moment at once.
    c.evaluate(T0 + timedelta(hours=4), NIGHT, -30, room, {"light.salon": LightState(on=False)})
    assert "light.salon" not in c.overrides
    sent = calls(c.evaluate(T0 + timedelta(hours=4), NIGHT, -30, room, on))
    assert sent["light.salon"]["transition"] == 1


def test_state_survives_restart():
    s = settings()
    c = LightController(s)
    c.manual_change("light.salon", T0)
    c.overrides["light.unknown"] = T0
    again = LightController(s)
    again.restore(c.as_dict())
    assert list(again.overrides) == ["light.salon"]


OPTIONS = {
    "startup_grace": 0,
    "control": {"night_start": "23:00", "night_end": "07:00", "manual_override": 600},
    "rooms": [{"name": "Séjour", "lights": ["light.salon"]}],
}
DIMMABLE = {"supported_color_modes": ["brightness"], "brightness": 255}


async def test_lighting_in_home_assistant(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-31 18:00:00+00:00")  # 19:00 in Paris, after sunset.
    await hass.config.async_set_time_zone("Europe/Paris")
    hass.states.async_set("sun.sun", "below_horizon", {"elevation": -12})
    hass.states.async_set("light.salon", "off", {"supported_color_modes": ["brightness"]})
    light_on = async_mock_service(hass, "light", "turn_on")
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options=OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    manager = entry.runtime_data
    assert light_on == []
    # Turned on: its evening brightness at once, without waiting for the debounce.
    hass.states.async_set("light.salon", "on", DIMMABLE, context=Context())
    await hass.async_block_till_done()
    assert [c.data for c in light_on] == [{"entity_id": "light.salon", "brightness_pct": 60, "transition": 1}]
    status = hass.states.get("switch.smart_comfort_adaptive_lighting") or hass.states.get(
        "switch.smart_comfort_lighting"
    )
    assert status is not None and status.state == "on"
    # Dimmed by hand (after the grace of our command): left alone.
    freezer.tick(timedelta(minutes=5))
    hass.states.async_set("light.salon", "on", {**DIMMABLE, "brightness": 30}, context=Context())
    await hass.async_block_till_done()
    assert "light.salon" in manager.lights.overrides
    freezer.move_to("2026-10-31 22:30:00+00:00")  # Night.
    await manager.async_evaluate()
    await hass.async_block_till_done()
    assert len(light_on) == 1
    # Off then on again: the night level.
    hass.states.async_set("light.salon", "off", {"supported_color_modes": ["brightness"]}, context=Context())
    await hass.async_block_till_done()
    hass.states.async_set("light.salon", "on", DIMMABLE, context=Context())
    await hass.async_block_till_done()
    assert light_on[-1].data["brightness_pct"] == 15
    # Lighting switch off: nothing more.
    manager.set_lighting(False)
    hass.states.async_set("light.salon", "off", {"supported_color_modes": ["brightness"]}, context=Context())
    hass.states.async_set("light.salon", "on", DIMMABLE, context=Context())
    await hass.async_block_till_done()
    assert len(light_on) == 2


def test_schema():
    import pytest
    import voluptuous as vol

    from custom_components.smart_comfort.schema import OPTIONS

    room = {"name": "Chambre", "lights": ["light.c"], "naps": [{"start": "13:30", "end": "15:00", "days": ["sat"]}]}
    assert OPTIONS({"lighting": {"morning_end": "9:30"}, "rooms": [room]})["rooms"][0]["naps"][0]["days"] == ["sat"]
    with pytest.raises(vol.Invalid):
        OPTIONS({"rooms": [{**room, "naps": [{"start": "13:30", "end": "15:00", "days": ["saturday"]}]}]})
