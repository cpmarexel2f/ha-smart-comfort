"""Device control decisions. No Home Assistant needed."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.control import Controller, DeviceState, RoomContext

T0 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
NOON = time(12, 0)
NIGHT = time(23, 0)


def room_settings(**room):
    return build_settings(
        {"rooms": [{"name": "Séjour", "temperature": "sensor.t", "openings": ["binary_sensor.w"], **room}]}
    )


def ctx(temp, opened=False, minutes=10):
    since = T0 - timedelta(minutes=minutes)
    return RoomContext(
        temperature=temp,
        any_open=opened,
        closed_since=None if opened else since,
        open_since=since if opened else None,
        has_openings=True,
    )


def calls(cmds):
    return [(c.entity_id, f"{c.domain}.{c.service}", c.data) for c in cmds]


def test_fan_hysteresis_and_boost():
    s = room_settings(
        fans=[{"entity_id": "fan.f", "preset": "Naturel", "open_preset": "Standard", "off_preset": "Naturel"}]
    )
    c, room = Controller(s), s.rooms[0]
    off = {"fan.f": DeviceState(on=False)}
    assert calls(c.evaluate(T0, NOON, room, ctx(23.5), off)) == [
        ("fan.f", "fan.turn_on", {}),
        ("fan.f", "fan.set_preset_mode", {"preset_mode": "Naturel"}),
        ("fan.f", "fan.set_percentage", {"percentage": 50}),
    ]
    on = {"fan.f": DeviceState(on=True, preset="Naturel", percentage=50)}
    # In the band: holds.
    assert c.evaluate(T0, NOON, room, ctx(22.5), on) == []
    # Window opened during the day: boost.
    assert calls(c.evaluate(T0, NOON, room, ctx(22.5, opened=True), on))[1:] == [
        ("fan.f", "fan.set_preset_mode", {"preset_mode": "Standard"}),
        ("fan.f", "fan.set_percentage", {"percentage": 100}),
    ]
    # Closed again, temperature in the band: off (preset reset first).
    assert calls(c.evaluate(T0, NOON, room, ctx(22.5), on)) == [
        ("fan.f", "fan.set_preset_mode", {"preset_mode": "Naturel"}),
        ("fan.f", "fan.turn_off", {}),
    ]


def test_fan_no_boost_at_night():
    s = room_settings(fans=["fan.f"])
    c, room = Controller(s), s.rooms[0]
    on = {"fan.f": DeviceState(on=True, percentage=50)}
    c.targets["fan.f"] = "on"
    assert c.evaluate(T0, NIGHT, room, ctx(23.5, opened=True), on) == []


def test_climate_needs_closed_and_stops_on_open():
    s = room_settings(climate={"entity_id": "climate.ac", "fan_mode": "silent"})
    c, room = Controller(s), s.rooms[0]
    off = {"climate.ac": DeviceState(on=False, hvac_mode="off")}
    # Closed only 1 min (2 required): nothing.
    assert c.evaluate(T0, NOON, room, ctx(24.0, minutes=1), off) == []
    assert calls(c.evaluate(T0, NOON, room, ctx(24.0, minutes=3), off)) == [
        ("climate.ac", "climate.set_temperature", {"hvac_mode": "cool", "temperature": 22.0}),
        ("climate.ac", "climate.set_fan_mode", {"fan_mode": "silent"}),
    ]
    cooling = {"climate.ac": DeviceState(on=True, hvac_mode="cool")}
    assert c.handled(room, cooling)
    # Window open for less than a minute: wait. Then off.
    assert c.evaluate(T0, NOON, room, ctx(24.0, opened=True, minutes=0), cooling) == []
    assert calls(c.evaluate(T0, NOON, room, ctx(24.0, opened=True, minutes=2), cooling)) == [
        ("climate.ac", "climate.turn_off", {})
    ]


def test_climate_heating_left_alone():
    s = room_settings(climate="climate.ac")
    c, room = Controller(s), s.rooms[0]
    assert c.evaluate(T0, NOON, room, ctx(25.0), {"climate.ac": DeviceState(on=True, hvac_mode="heat")}) == []


def test_manual_override_pauses_then_reapplies():
    s = room_settings(fans=["fan.f"])
    c, room = Controller(s), s.rooms[0]
    c.evaluate(T0, NOON, room, ctx(24.0), {"fan.f": DeviceState(on=False)})
    c.manual_change("fan.f", T0)
    off = {"fan.f": DeviceState(on=False)}
    assert c.evaluate(T0 + timedelta(minutes=30), NOON, room, ctx(24.0), off) == []
    assert c.evaluate(T0 + timedelta(minutes=61), NOON, room, ctx(24.0), off) != []


def test_purifier_mode_select_and_keep_on():
    s = room_settings(
        purifiers=[
            {
                "entity_id": "fan.p",
                "mode_select": "select.p_mode",
                "open_mode": "manual",
                "closed_mode": "automatic",
                "keep_on": True,
            }
        ]
    )
    c, room = Controller(s), s.rooms[0]
    auto = {"fan.p": DeviceState(on=True, option="automatic")}
    assert c.evaluate(T0, NOON, room, ctx(21.0), auto) == []  # already normal
    assert calls(c.evaluate(T0, NOON, room, ctx(21.0, opened=True), auto)) == [
        ("select.p_mode", "select.select_option", {"option": "manual"}),
        ("fan.p", "fan.set_percentage", {"percentage": 100}),
    ]
    off = {"fan.p": DeviceState(on=False, option="manual", off_since=T0 - timedelta(seconds=30))}
    cmds = calls(c.evaluate(T0, NOON, room, ctx(21.0, opened=True), off))
    assert cmds == [("fan.p", "fan.turn_on", {})]


def test_unknown_openings_do_nothing():
    s = room_settings(fans=["fan.f"], climate="climate.ac")
    c, room = Controller(s), s.rooms[0]
    unknown = RoomContext(temperature=30, any_open=None, closed_since=None, open_since=None, has_openings=True)
    states = {"fan.f": DeviceState(on=False), "climate.ac": DeviceState(on=False, hvac_mode="off")}
    assert c.evaluate(T0, NOON, room, unknown, states) == []


def test_disabled_control():
    s = build_settings(
        {"control": {"enabled": False}, "rooms": [{"name": "A", "temperature": "sensor.t", "fans": ["fan.f"]}]}
    )
    c = Controller(s)
    assert c.evaluate(T0, NOON, s.rooms[0], ctx(30), {"fan.f": DeviceState(on=False)}) == []


def test_purifier_back_to_its_state_before_the_boost():
    s = room_settings(purifiers=["fan.p"])
    c, room = Controller(s), s.rooms[0]
    normal = {"fan.p": DeviceState(on=True, percentage=40)}
    assert c.evaluate(T0, NOON, room, ctx(21.0), normal) == []
    assert calls(c.evaluate(T0, NOON, room, ctx(21.0, opened=True), normal)) == [
        ("fan.p", "fan.set_percentage", {"percentage": 100}),
    ]
    boosted = {"fan.p": DeviceState(on=True, percentage=100)}
    assert calls(c.evaluate(T0, NOON, room, ctx(21.0), boosted)) == [
        ("fan.p", "fan.set_percentage", {"percentage": 40}),
    ]
    assert c.before_boost == {}
    # A preset before the boost is restored as a preset.
    auto = {"fan.p": DeviceState(on=True, preset="Auto", percentage=30)}
    c.evaluate(T0, NOON, room, ctx(21.0, opened=True), auto)
    assert calls(c.evaluate(T0, NOON, room, ctx(21.0), boosted)) == [
        ("fan.p", "fan.set_preset_mode", {"preset_mode": "Auto"}),
    ]


def test_failed_command_is_retried():
    s = room_settings(
        purifiers=[{"entity_id": "fan.p", "mode_select": "select.p_mode", "open_mode": "manual", "closed_mode": "auto"}]
    )
    c, room = Controller(s), s.rooms[0]
    auto = {"fan.p": DeviceState(on=True, option="auto")}
    cmds = c.evaluate(T0, NOON, room, ctx(21.0, opened=True), auto)
    assert cmds[0].entity_id == "select.p_mode" and cmds[0].device == "fan.p"
    c.command_failed(cmds[0])
    assert "fan.p" not in c.targets
    assert c.evaluate(T0, NOON, room, ctx(21.0, opened=True), auto) != []


def test_keep_on_respects_manual_override():
    s = room_settings(purifiers=[{"entity_id": "fan.p", "keep_on": True}])
    c, room = Controller(s), s.rooms[0]
    off = {"fan.p": DeviceState(on=False, off_since=T0 - timedelta(seconds=30))}
    c.manual_change("fan.p", T0 - timedelta(seconds=30))
    assert c.evaluate(T0, NOON, room, ctx(21.0), off) == []
    later = T0 + timedelta(minutes=61)
    assert ("fan.p", "fan.turn_on", {}) in calls(c.evaluate(later, NOON, room, ctx(21.0), off))


def test_climate_heating_turned_off_when_open():
    s = room_settings(climate="climate.ac")
    c, room = Controller(s), s.rooms[0]
    heating = {"climate.ac": DeviceState(on=True, hvac_mode="heat")}
    # Cold room: target off, but heating is left alone by the temperature control.
    assert c.evaluate(T0, NOON, room, ctx(19.0), heating) == []
    assert calls(c.evaluate(T0, NOON, room, ctx(19.0, opened=True, minutes=2), heating)) == [
        ("climate.ac", "climate.turn_off", {})
    ]


def test_fan_without_temperature_control():
    s = build_settings(
        {
            "control": {"fans": {"on_above": None, "off_below": None}},
            "rooms": [{"name": "A", "temperature": "sensor.t", "openings": ["binary_sensor.w"], "fans": ["fan.f"]}],
        }
    )
    c, room = Controller(s), s.rooms[0]
    off = {"fan.f": DeviceState(on=False)}
    assert c.evaluate(T0, NOON, room, ctx(30.0), off) == []
    assert c.evaluate(T0, NOON, room, ctx(30.0, opened=True), off) != []
