"""Device control decisions. No Home Assistant needed."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.const import COMMAND_RETRY
from custom_components.smart_comfort.control import Controller, DeviceState, RoomContext

T0 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
NOON = time(12, 0)
NIGHT = time(23, 0)
RETRY = timedelta(minutes=COMMAND_RETRY)


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
        ("climate.ac", "climate.set_hvac_mode", {"hvac_mode": "cool"}),
        ("climate.ac", "climate.set_temperature", {"temperature": 22.0}),
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
    c.command_failed(cmds[0], T0)
    assert "fan.p" not in c.targets
    assert c.evaluate(T0 + RETRY, NOON, room, ctx(21.0, opened=True), auto) != []


def test_failed_restore_after_boost_is_retried():
    s = room_settings(purifiers=["fan.p"])
    c, room = Controller(s), s.rooms[0]
    normal = {"fan.p": DeviceState(on=True, percentage=30)}
    boosted = {"fan.p": DeviceState(on=True, percentage=100)}
    c.evaluate(T0, NOON, room, ctx(21.0), normal)
    c.evaluate(T0, NOON, room, ctx(21.0, opened=True), normal)
    cmds = c.evaluate(T0, NOON, room, ctx(21.0), boosted)
    assert calls(cmds) == [("fan.p", "fan.set_percentage", {"percentage": 30})]
    for cmd in cmds:
        c.command_failed(cmd, T0)
    # The restore is not lost: it is sent again once the retry delay is over.
    later = T0 + RETRY
    assert calls(c.evaluate(later, NOON, room, ctx(21.0), boosted)) == [
        ("fan.p", "fan.set_percentage", {"percentage": 30})
    ]
    assert c.before_boost == {}


def test_failed_restore_then_new_boost_keeps_the_state_before_the_first_one():
    s = room_settings(purifiers=["fan.p"])
    c, room = Controller(s), s.rooms[0]
    normal = {"fan.p": DeviceState(on=True, percentage=30)}
    boosted = {"fan.p": DeviceState(on=True, percentage=100)}
    c.evaluate(T0, NOON, room, ctx(21.0), normal)
    c.evaluate(T0, NOON, room, ctx(21.0, opened=True), normal)
    for cmd in c.evaluate(T0, NOON, room, ctx(21.0), boosted):
        c.command_failed(cmd, T0)
    # Opened again during the retry delay: the boost is not held back, already boosted.
    assert c.evaluate(T0 + timedelta(seconds=30), NOON, room, ctx(21.0, opened=True), boosted) == []
    # Closed: back to 30 %, not to the 100 % the purifier had when the second boost started.
    assert calls(c.evaluate(T0 + timedelta(minutes=1), NOON, room, ctx(21.0), boosted)) == [
        ("fan.p", "fan.set_percentage", {"percentage": 30})
    ]


def test_failing_command_backs_off():
    s = room_settings(fans=["fan.f"])
    c, room = Controller(s), s.rooms[0]
    off = {"fan.f": DeviceState(on=False)}
    now = T0
    for delay in (RETRY, 2 * RETRY, 4 * RETRY):
        cmds = c.evaluate(now, NOON, room, ctx(24.0), off)
        assert cmds != []
        for cmd in cmds:
            c.command_failed(cmd, now)
        # Not sent again at every evaluation: only once the delay, doubled at each failure, is over.
        assert c.evaluate(now + timedelta(seconds=30), NOON, room, ctx(24.0), off) == []
        assert c.evaluate(now + delay - timedelta(seconds=1), NOON, room, ctx(24.0), off) == []
        now += delay
    # A success resets the delay.
    cmds = c.evaluate(now, NOON, room, ctx(24.0), off)
    c.command_succeeded(cmds[0].device)
    c.targets.pop("fan.f")
    for cmd in c.evaluate(now, NOON, room, ctx(24.0), off):
        c.command_failed(cmd, now)
    assert c.evaluate(now + RETRY, NOON, room, ctx(24.0), off) != []


def test_backoff_does_not_hold_another_target():
    s = room_settings(fans=["fan.f"])
    c, room = Controller(s), s.rooms[0]
    off = {"fan.f": DeviceState(on=False)}
    for cmd in c.evaluate(T0, NOON, room, ctx(24.0), off):
        c.command_failed(cmd, T0)
    # Window opened meanwhile: the boost is a different target, sent right away.
    assert c.evaluate(T0 + timedelta(seconds=30), NOON, room, ctx(24.0, opened=True), off) != []


def test_failed_command_applied_anyway_is_the_target_during_the_retry_delay():
    s = room_settings(climate="climate.ac")
    c, room = Controller(s), s.rooms[0]
    off = {"climate.ac": DeviceState(on=False, hvac_mode="off")}
    cooling = {"climate.ac": DeviceState(on=True, hvac_mode="cool")}
    for cmd in c.evaluate(T0, NOON, room, ctx(24.0), off):
        c.command_failed(cmd, T0)
    # Timed out but applied anyway (slow cloud air conditioner): it cools, on Smart Comfort's command.
    assert c.evaluate(T0 + timedelta(seconds=30), NOON, room, ctx(24.0), cooling) == []
    assert c.targets["climate.ac"] == "cool"
    assert c.handled(room, cooling)
    assert c.retry == {} and c.failures == {}
    # The failures in a row start over: the next isolated failure waits the first delay, not twice as long.
    c.targets.pop("climate.ac")
    for cmd in c.evaluate(T0 + RETRY, NOON, room, ctx(24.0), off):
        c.command_failed(cmd, T0 + RETRY)
    assert c.failures == {"climate.ac": 1}
    assert c.evaluate(T0 + 2 * RETRY, NOON, room, ctx(24.0), off) != []


def test_retry_delay_still_holds_while_the_device_is_not_in_the_wanted_state():
    s = room_settings(climate="climate.ac")
    c, room = Controller(s), s.rooms[0]
    off = {"climate.ac": DeviceState(on=False, hvac_mode="off")}
    for cmd in c.evaluate(T0, NOON, room, ctx(24.0), off):
        c.command_failed(cmd, T0)
    assert c.evaluate(T0 + timedelta(minutes=1), NOON, room, ctx(24.0), off) == []
    assert "climate.ac" not in c.targets and c.failures == {"climate.ac": 1}
    # Unavailable meanwhile: nothing changes either.
    gone = {"climate.ac": DeviceState(available=False)}
    assert c.evaluate(T0 + timedelta(minutes=2), NOON, room, ctx(24.0), gone) == []
    assert "climate.ac" not in c.targets and "climate.ac" in c.retry


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


MORNING = time(7, 30)


def test_fan_quieter_at_night():
    s = room_settings(
        fans=[{"entity_id": "fan.f", "preset": "Natural", "night_preset": "Sleep", "night_percentage": 20}]
    )
    c, room = Controller(s), s.rooms[0]
    off = {"fan.f": DeviceState(on=False)}
    assert calls(c.evaluate(T0, NIGHT, room, ctx(24.0), off)) == [
        ("fan.f", "fan.turn_on", {}),
        ("fan.f", "fan.set_preset_mode", {"preset_mode": "Sleep"}),
        ("fan.f", "fan.set_percentage", {"percentage": 20}),
    ]
    on_night = {"fan.f": DeviceState(on=True, preset="Sleep", percentage=20)}
    assert c.handled(room, on_night)
    assert c.evaluate(T0, NIGHT, room, ctx(24.0), on_night) == []
    # Morning, still warm: day settings again.
    assert calls(c.evaluate(T0, MORNING, room, ctx(24.0), on_night))[1:] == [
        ("fan.f", "fan.set_preset_mode", {"preset_mode": "Natural"}),
        ("fan.f", "fan.set_percentage", {"percentage": 50}),
    ]


def test_no_window_boost_at_night_for_quiet_devices():
    s = build_settings(
        {
            "control": {"start": "00:00", "end": "23:59"},  # Boost hours all day long.
            "rooms": [
                {
                    "name": "Séjour",
                    "temperature": "sensor.t",
                    "openings": ["binary_sensor.w"],
                    "fans": [{"entity_id": "fan.quiet", "night_percentage": 20}, "fan.loud"],
                    "purifiers": [{"entity_id": "fan.p", "night_preset": "Sleep"}],
                }
            ],
        }
    )
    c, room = Controller(s), s.rooms[0]
    states = {
        "fan.quiet": DeviceState(on=False),
        "fan.loud": DeviceState(on=False),
        "fan.p": DeviceState(on=True, preset="Auto", percentage=30),
    }
    cmds = calls(c.evaluate(T0, NIGHT, room, ctx(21.0, opened=True), states))
    # The fan without night settings still boosts; the quiet one and the purifier don't.
    assert ("fan.loud", "fan.set_percentage", {"percentage": 100}) in cmds
    assert not any(e == "fan.quiet" for e, _, _ in cmds)
    assert cmds[-1] == ("fan.p", "fan.set_preset_mode", {"preset_mode": "Sleep"})


def test_purifier_night_mode_and_restore():
    s = room_settings(
        purifiers=[
            {"entity_id": "fan.p", "mode_select": "select.p_mode", "night_mode": "sleep", "night_percentage": 10}
        ]
    )
    c, room = Controller(s), s.rooms[0]
    day = {"fan.p": DeviceState(on=True, option="auto", preset="Auto", percentage=40)}
    assert c.evaluate(T0, NOON, room, ctx(21.0), day) == []
    assert calls(c.evaluate(T0, NIGHT, room, ctx(21.0), day)) == [
        ("select.p_mode", "select.select_option", {"option": "sleep"}),
        ("fan.p", "fan.set_percentage", {"percentage": 10}),
    ]
    night = {"fan.p": DeviceState(on=True, option="sleep", preset="Auto", percentage=10)}
    # Morning: the state before the night comes back (no closed preset or mode configured).
    assert calls(c.evaluate(T0, MORNING, room, ctx(21.0), night)) == [
        ("select.p_mode", "select.select_option", {"option": "auto"}),
        ("fan.p", "fan.set_preset_mode", {"preset_mode": "Auto"}),
    ]
    # Off at night stays off.
    c2 = Controller(s)
    assert c2.evaluate(T0, NIGHT, room, ctx(21.0), {"fan.p": DeviceState(on=False)}) == []


def test_climate_silent_at_night():
    s = room_settings(climate={"entity_id": "climate.ac", "fan_mode": "auto", "night_fan_mode": "silent"})
    c, room = Controller(s), s.rooms[0]
    off = {"climate.ac": DeviceState(on=False, hvac_mode="off")}
    assert calls(c.evaluate(T0, NIGHT, room, ctx(24.0), off))[-1] == (
        "climate.ac",
        "climate.set_fan_mode",
        {"fan_mode": "silent"},
    )
    cooling_night = {"climate.ac": DeviceState(on=True, hvac_mode="cool", fan_mode="silent")}
    assert c.handled(room, cooling_night)
    assert c.evaluate(T0, NIGHT, room, ctx(23.0), cooling_night) == []
    # Morning in the hysteresis band: still cooling, the day fan mode only.
    assert calls(c.evaluate(T0, MORNING, room, ctx(22.0), cooling_night)) == [
        ("climate.ac", "climate.set_fan_mode", {"fan_mode": "auto"}),
    ]


def test_no_night_settings_no_change():
    s = room_settings(fans=["fan.f"])
    c, room = Controller(s), s.rooms[0]
    assert calls(c.evaluate(T0, NIGHT, room, ctx(24.0), {"fan.f": DeviceState(on=False)}))[-1] == (
        "fan.f",
        "fan.set_percentage",
        {"percentage": 50},
    )
    assert not s.night(NOON) and s.night(NIGHT) and s.night(time(3, 0)) and not s.night(MORNING)
