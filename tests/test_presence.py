"""Lights on presence: decisions (no Home Assistant) and their wiring in Home Assistant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.const import DOMAIN
from custom_components.smart_comfort.lighting import LightController, LightState, PresenceController

T0 = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
WEEKDAY = datetime(2026, 11, 2, 7, 0)  # Monday 7:00 (local).

# The entrance of the house: its light and the hallway's, like the automation they replace.
OPTIONS = {
    "control": {"night_start": "22:00", "night_end": "07:00"},
    "rooms": [
        {
            "name": "Entrée",
            "lights": ["light.entree"],
            "presence": {
                "sensors": ["binary_sensor.presence_entree"],
                "lights": ["light.entree", "light.couloir"],
                "lux": "sensor.lux_entree",
                "max_lux": 10,
                "off_after": 2,
                "not_during_naps": ["light.couloir"],
                "slots": [
                    {"start": "06:30", "end": "08:00", "days": ["mon", "tue", "wed", "thu", "fri"], "off": True},
                    {"start": "20:00", "end": "09:00", "lights": ["light.entree"], "brightness": 20},
                    {"start": "20:00", "end": "09:00", "lights": ["light.couloir"], "off": True},
                ],
            },
        },
        {"name": "Chambre", "naps": [{"start": "13:30", "end": "17:00"}]},
    ],
}


def local(hour, minute=0, day=31):
    return datetime(2026, 10, day, hour, minute)


def off():
    return {"light.entree": LightState(on=False), "light.couloir": LightState(on=False)}


def run(controller, lights, when, present, lux=2.0, states=None, now=T0, adaptive=True):
    s = controller.settings
    return {
        c.entity_id: (c.service, c.data)
        for c in controller.evaluate(now, when, 30, s.rooms[0], present, lux, states or off(), lights, adaptive)
    }


def test_presence_by_slot():
    s = build_settings(OPTIONS)
    p, lights = PresenceController(s), LightController(s)
    # Morning (10:00): both, at the brightness of the moment.
    assert run(p, lights, local(10), True) == {
        "light.entree": ("turn_on", {"transition": 1, "brightness_pct": 100}),
        "light.couloir": ("turn_on", {"transition": 1}),
    }
    # Evening (21:00): the entrance alone, at 20 %.
    assert run(PresenceController(s), lights, local(21), True) == {
        "light.entree": ("turn_on", {"transition": 1, "brightness_pct": 20})
    }
    # Weekdays 6:30-8:00: nothing; Saturday at the same time: the entrance at 20 %.
    assert run(PresenceController(s), lights, WEEKDAY, True) == {}
    assert run(PresenceController(s), lights, local(7), True) == {
        "light.entree": ("turn_on", {"transition": 1, "brightness_pct": 20})
    }
    # A nap in the house (14:00): not the hallway.
    assert run(PresenceController(s), lights, local(14), True) == {
        "light.entree": ("turn_on", {"transition": 1, "brightness_pct": 100})
    }
    # Bright enough: nothing.
    assert run(PresenceController(s), lights, local(10), True, lux=50) == {}


def test_presence_off_and_manual():
    s = build_settings(OPTIONS)
    p, lights = PresenceController(s), LightController(s)
    on = {"light.entree": LightState(on=True, brightness=100), "light.couloir": LightState(on=False)}
    # A light already on (by hand): left as it is.
    assert run(p, lights, local(10), True, states=on) == {}
    # No one: off once the delay is over, not before.
    assert run(p, lights, local(10), False, states=on, now=T0 + timedelta(minutes=1)) == {}
    assert run(p, lights, local(10), False, states=on, now=T0 + timedelta(minutes=2)) == {
        "light.entree": ("turn_off", {})
    }
    # Turned off by hand while someone is there: not back on until they leave.
    p.turned_off_by_hand(s.rooms[0])
    assert run(p, lights, local(10), True, now=T0 + timedelta(minutes=3)) == {}
    run(p, lights, local(10), False, now=T0 + timedelta(minutes=3))
    run(p, lights, local(10), False, now=T0 + timedelta(minutes=6))
    assert run(p, lights, local(10), True, now=T0 + timedelta(minutes=7))
    # Unknown presence: nothing.
    assert run(PresenceController(s), lights, local(10), None) == {}


def test_presence_night_light_and_adaptive():
    s = build_settings(
        {
            "control": {"night_start": "22:00", "night_end": "07:00"},
            "rooms": [
                {
                    "name": "Couloir",
                    "lights": ["light.couloir", {"entity_id": "light.veilleuse", "night_only": True}],
                    "presence": {"sensors": ["binary_sensor.couloir"]},
                }
            ],
        }
    )
    states = {"light.couloir": LightState(on=False), "light.veilleuse": LightState(on=False)}
    room = s.rooms[0]

    def turned_on(when):
        cmds = PresenceController(s).evaluate(T0, when, -30, room, True, None, states, LightController(s))
        return {c.entity_id: c.data for c in cmds}

    # At night: both, at the night level (the night light only at night).
    assert turned_on(local(23)) == {
        "light.couloir": {"transition": 1, "brightness_pct": 15},
        "light.veilleuse": {"transition": 1, "brightness_pct": 15},
    }
    # By day: the main light only.
    assert list(turned_on(local(12))) == ["light.couloir"]
    # Without the adaptive lighting: just turned on.
    cmds = PresenceController(s).evaluate(T0, local(23), -30, room, True, None, states, LightController(s), False)
    assert {c.entity_id: c.data for c in cmds}["light.couloir"] == {"transition": 1}


def test_schema():
    from custom_components.smart_comfort.schema import OPTIONS as SCHEMA

    room = SCHEMA(OPTIONS)["rooms"][0]
    assert room["presence"]["slots"][1]["brightness"] == 20
    assert build_settings(OPTIONS).rooms[0].presence_lights() == ("light.entree", "light.couloir")


async def test_presence_in_home_assistant(hass: HomeAssistant, freezer) -> None:
    freezer.move_to("2026-10-31 09:00:00+00:00")  # 10:00 in Paris.
    await hass.config.async_set_time_zone("Europe/Paris")
    hass.states.async_set("sun.sun", "above_horizon", {"elevation": 20})
    dim = {"supported_color_modes": ["brightness"]}
    hass.states.async_set("light.entree", "off", dim)
    hass.states.async_set("light.couloir", "off", dim)
    hass.states.async_set("binary_sensor.presence_entree", "off")
    hass.states.async_set("sensor.lux_entree", "2")
    on = async_mock_service(hass, "light", "turn_on")
    off_calls = async_mock_service(hass, "light", "turn_off")
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options={"startup_grace": 0, **OPTIONS})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    manager = entry.runtime_data
    # Someone comes in: both lights at once, without waiting for the debounce.
    hass.states.async_set("binary_sensor.presence_entree", "on")
    await hass.async_block_till_done()
    assert sorted(c.data["entity_id"] for c in on) == ["light.couloir", "light.entree"]
    hass.states.async_set("light.entree", "on", {**dim, "brightness": 255}, context=on[0].context)
    hass.states.async_set("light.couloir", "on", {**dim, "brightness": 255}, context=on[1].context)
    await hass.async_block_till_done()
    # They leave: off once the delay is over.
    hass.states.async_set("binary_sensor.presence_entree", "off")
    await hass.async_block_till_done()
    assert off_calls == []
    freezer.tick(timedelta(minutes=2, seconds=5))
    await manager.async_evaluate()
    await hass.async_block_till_done()
    assert sorted(c.data["entity_id"] for c in off_calls) == ["light.couloir", "light.entree"]
    # Turned off by hand while someone is there: not back on.
    hass.states.async_set("light.entree", "off", dim)
    hass.states.async_set("light.couloir", "off", dim)
    hass.states.async_set("binary_sensor.presence_entree", "on")
    await hass.async_block_till_done()
    count = len(on)
    hass.states.async_set("light.entree", "on", {**dim, "brightness": 255}, context=on[-1].context)
    await hass.async_block_till_done()
    hass.states.async_set("light.entree", "off", dim, context=Context())
    await manager.async_evaluate()
    await hass.async_block_till_done()
    assert len(on) == count


# The hallway: a blue night light from 20:00 to 10:00, the main light by day, nothing in the afternoon,
# only for a presence that lasts 5 seconds.
HALLWAY = {
    "rooms": [
        {
            "name": "Couloir",
            "lights": ["light.couloir", "light.veilleuse"],
            "presence": {
                "sensors": ["binary_sensor.couloir"],
                "on_after": 5,
                "slots": [
                    {
                        "start": "20:00",
                        "end": "10:00",
                        "lights": ["light.veilleuse"],
                        "brightness": 30,
                        "color": [0, 0, 255],
                    },
                    {"start": "20:00", "end": "10:00", "lights": ["light.couloir"], "off": True},
                    {"start": "10:00", "end": "20:00", "lights": ["light.veilleuse"], "off": True},
                    {"start": "13:30", "end": "17:00", "off": True},
                ],
            },
        }
    ]
}


def test_presence_color_and_on_after():
    s = build_settings(HALLWAY)
    room = s.rooms[0]
    states = {
        "light.couloir": LightState(on=False),
        "light.veilleuse": LightState(on=False, colored=True, min_kelvin=2000, max_kelvin=6500),
    }

    def cmds(p, lights, when, now):
        return {c.entity_id: c.data for c in p.evaluate(now, when, -20, room, True, None, states, lights)}

    p, lights = PresenceController(s), LightController(s)
    # Someone passing by: nothing; still there 5 seconds later: the night light, blue at 30 %.
    assert cmds(p, lights, local(23), T0) == {}
    assert cmds(p, lights, local(23), T0 + timedelta(seconds=5)) == {
        "light.veilleuse": {"transition": 1, "brightness_pct": 30, "rgb_color": [0, 0, 255]}
    }
    # The adaptive lighting leaves its color alone.
    assert "light.veilleuse" in lights.overrides
    # By day: the main light; the afternoon: nothing.
    p = PresenceController(s)
    cmds(p, lights, local(11), T0)
    assert list(cmds(p, lights, local(11), T0 + timedelta(seconds=6))) == ["light.couloir"]
    p = PresenceController(s)
    cmds(p, lights, local(15), T0)
    assert cmds(p, lights, local(15), T0 + timedelta(seconds=6)) == {}


def test_shared_light():
    """The hallway's light, turned on by the entrance and by the hallway: kept on while someone is in either."""
    s = build_settings(
        {
            "rooms": [
                {
                    "name": "Entrée",
                    "presence": {
                        "sensors": ["binary_sensor.entree"],
                        "lights": ["light.entree", "light.couloir"],
                        "off_after": 2,
                        "transition": 10,
                    },
                },
                {"name": "Couloir", "presence": {"sensors": ["binary_sensor.couloir"], "lights": ["light.couloir"]}},
            ]
        }
    )
    entree = s.rooms[0]
    p, lights = PresenceController(s), LightController(s)
    on = {"light.entree": LightState(on=True), "light.couloir": LightState(on=True)}
    kept = p.kept(entree, {"couloir"})
    assert kept == {"light.couloir"}
    assert p.kept(entree, set()) == frozenset()
    # Nobody left in the entrance, someone in the hallway: the entrance light only, with its transition.
    p.evaluate(T0, local(10), 30, entree, False, None, on, lights, kept=kept)
    cmds = p.evaluate(T0 + timedelta(minutes=2), local(10), 30, entree, False, None, on, lights, kept=kept)
    assert [(c.entity_id, c.service, c.data) for c in cmds] == [("light.entree", "turn_off", {"transition": 10})]
    # The hallway light on (someone there): coming into the entrance still turns its light on.
    lit = {"light.entree": LightState(on=False), "light.couloir": LightState(on=True)}
    cmds = PresenceController(s).evaluate(T0, local(10), 30, entree, True, None, lit, lights, False, kept)
    assert [(c.entity_id, c.data) for c in cmds] == [("light.entree", {"transition": 10})]


def test_yaml_off_key():
    """An unquoted `off: true` in YAML (read as a False key) still keeps the lights off."""
    import yaml

    from custom_components.smart_comfort.schema import OPTIONS as SCHEMA

    raw = yaml.safe_load(
        "rooms:\n- name: Entrée\n  presence:\n    sensors: [binary_sensor.p]\n"
        "    slots:\n    - {start: '06:30', end: '08:00', off: true}\n"
    )
    assert SCHEMA(raw)["rooms"][0]["presence"]["slots"][0]["off"] is True
