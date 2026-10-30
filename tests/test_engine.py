"""Alert engine: episodes, digests, gates, reminders, escalation, snoozes. No Home Assistant needed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.smart_comfort.config import build_settings, in_window, parse_time, slugify
from custom_components.smart_comfort.engine import (
    REASON_NEW,
    REASON_ONGOING,
    REASON_REMINDER,
    REASON_WORSE,
    Clear,
    Digest,
    Engine,
    Gates,
    Item,
    RoomReading,
)
from custom_components.smart_comfort.message import render

T0 = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
OPEN = Gates()


def settings(**extra):
    options = {
        "digest_window": 5,
        "rooms": [
            {"name": "Séjour", "temperature": "sensor.t1", "openings": ["binary_sensor.w1"]},
            {"name": "Chambre Léa", "temperature": "sensor.t2", "co2": "sensor.c2"},
        ],
        **extra,
    }
    return build_settings(options)


def run(engine, minutes, readings, outdoor=27.0, gates=OPEN, handled=frozenset()):
    """Evaluate once at T0 + minutes and step; returns (now, result)."""
    now = T0 + timedelta(minutes=minutes)
    engine.evaluate(now, readings, outdoor)
    result = engine.step(now, gates, set(handled))
    if isinstance(result, Digest):
        engine.sent(result, now)  # What the manager does once a notifier got it.
    return now, result


def hot(temp=28.0, **kw):
    return {"sejour": RoomReading(temperature=temp, has_openings=True, open=[]), **kw}


def test_slug_and_times():
    assert slugify("Chambre Léa") == "chambre_lea"
    assert parse_time("22:00") == parse_time("22:00:00")
    assert in_window(parse_time("23:30"), parse_time("22:00"), parse_time("08:00"))
    assert in_window(parse_time("07:59"), parse_time("22:00"), parse_time("08:00"))
    assert not in_window(parse_time("08:00"), parse_time("22:00"), parse_time("08:00"))
    assert in_window(parse_time("12:00"), None, None)


def test_delay_then_one_notification_only():
    e = Engine(settings())
    # Pending during the delay (15 min by default), then the digest window (5 min).
    assert run(e, 0, hot())[1] is None
    assert run(e, 14, hot())[1] is None
    assert run(e, 15, hot())[1] is None  # active, batch starts
    _, result = run(e, 20, hot())
    assert isinstance(result, Digest)
    assert [(i.episode.kind, i.reason) for i in result.items] == [("too_hot", REASON_NEW)]
    # Still hot for hours: nothing more (no reminder by default, no worsening).
    for minute in range(21, 400, 7):
        assert run(e, minute, hot(28.4))[1] is None


def test_hysteresis_and_clear():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    # 26.8 > 27 - 0.5: still a problem.
    assert run(e, 30, hot(26.8))[1] is None
    assert "sejour|too_hot" in e.episodes
    _, result = run(e, 31, hot(26.4))
    assert isinstance(result, Clear)
    assert not e.episodes
    # Back above the threshold: a new episode, delay again.
    assert run(e, 32, hot(27.2))[1] is None
    assert not e.episodes["sejour|too_hot"].active


def test_pending_flapping_is_absorbed():
    e = Engine(settings())
    run(e, 0, hot(27.2))
    run(e, 5, hot(26.8))  # within hysteresis: still pending, delay keeps counting
    run(e, 15, hot(27.1))
    assert e.episodes["sejour|too_hot"].active


def test_unknown_reading_keeps_episode():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    run(e, 30, {"sejour": RoomReading(temperature=None, has_openings=True, open=None)})
    assert e.episodes["sejour|too_hot"].active


def test_digest_groups_rooms():
    e = Engine(settings())
    readings = {
        "sejour": RoomReading(temperature=28.0, has_openings=True, open=[]),
        "chambre_lea": RoomReading(temperature=21.0, co2=1500),
    }
    run(e, 0, readings)
    run(e, 15, readings)
    _, result = run(e, 20, readings)
    assert isinstance(result, Digest)
    assert sorted(i.episode.kind for i in result.items) == ["co2_high", "too_hot"]
    title, message, _ = render(result, {"decimal": ","}, T0 + timedelta(minutes=20))
    assert "2" in title
    assert "Séjour: 28,0 °C" in message
    assert "Chambre Léa: CO₂ 1500 ppm" in message


def test_new_problem_resends_full_list():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    readings = {**hot(), "chambre_lea": RoomReading(temperature=21.0, co2=1500)}
    run(e, 30, readings)
    run(e, 40, readings)
    _, result = run(e, 45, readings)
    reasons = {i.episode.kind: i.reason for i in result.items}
    assert reasons == {"too_hot": REASON_ONGOING, "co2_high": REASON_NEW}
    assert result.severity == "info"


def test_escalation():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot(28.0))
    assert run(e, 30, hot(28.9))[1] is None
    run(e, 31, hot(29.0))  # +1 °C: due, waits the digest window
    _, result = run(e, 36, hot(29.0))
    assert result.items[0].reason == REASON_WORSE


def test_reminder():
    e = Engine(settings(reminder=120))
    for m in (0, 15, 20):
        run(e, m, hot())
    assert run(e, 130, hot())[1] is None
    run(e, 140, hot())
    _, result = run(e, 145, hot())
    assert result.items[0].reason == REASON_REMINDER
    assert "for 2 h 25" in render(result, {}, T0 + timedelta(minutes=145))[1]


def test_quiet_hours_hold_until_released():
    e = Engine(settings())
    held = Gates(hold=True)
    for m in (0, 15, 20, 60):
        assert run(e, m, hot(), gates=held)[1] is None
    run(e, 61, hot())
    _, result = run(e, 66, hot())
    assert isinstance(result, Digest)


def test_critical_bypasses_hold_and_window():
    e = Engine(settings(alerts={"too_hot": {"severity": "critical", "delay": 0}}))
    _, result = run(e, 0, hot(), gates=Gates(hold=True))
    assert isinstance(result, Digest)
    assert result.severity == "critical"


def test_startup_and_disabled_send_nothing():
    e = Engine(settings())
    for m in (0, 15, 20, 30):
        assert run(e, m, hot(), gates=Gates(starting=True))[1] is None
    for m in (31, 40):
        assert run(e, m, hot(), gates=Gates(enabled=False))[1] is None


def test_snooze_and_ack():
    e = Engine(settings(reminder=60))
    for m in (0, 15, 20):
        run(e, m, hot())
    assert e.acknowledge(rooms=["sejour"]) == 1
    assert run(e, 200, hot())[1] is None  # acknowledged: no reminder
    e2 = Engine(settings())
    e2.snooze(T0, 120)
    for m in (0, 15, 20, 60):
        assert run(e2, m, hot())[1] is None
    run(e2, 121, hot())
    _, result = run(e2, 126, hot())
    assert isinstance(result, Digest)


def test_handled_suppresses_too_hot():
    e = Engine(settings())
    for m in (0, 15, 20, 30):
        assert run(e, m, hot(), handled={"sejour"})[1] is None


def test_ventilate_and_close_windows():
    e = Engine(settings())
    closed = {"sejour": RoomReading(temperature=26.0, has_openings=True, open=[])}
    for m in (0, 15, 20):
        result = run(e, m, closed, outdoor=22.0)[1]
    assert [i.episode.kind for i in result.items] == ["ventilate"]
    # Opened: the ventilate problem is over.
    opened = {"sejour": RoomReading(temperature=26.0, has_openings=True, open=["binary_sensor.w1"])}
    run(e, 21, opened, outdoor=22.0)
    assert "sejour|ventilate" not in e.episodes
    # Hot outside with the window open: close it.
    e = Engine(settings())
    for m in (0, 5, 10):
        result = run(e, m, opened, outdoor=30.0)[1]
    assert [i.episode.kind for i in result.items] == ["close_windows"]
    assert "close binary_sensor.w1" in render(result, {}, T0)[1]


def test_window_open_cold_disabled_by_default_and_enabled():
    opened = {"sejour": RoomReading(temperature=20.0, has_openings=True, open=["binary_sensor.w1"])}
    e = Engine(settings())
    for m in (0, 30, 40):
        assert run(e, m, opened, outdoor=5.0)[1] is None
    e = Engine(settings(alerts={"window_open_cold": {"enabled": True, "delay": 0}}))
    run(e, 0, opened, outdoor=5.0)
    assert isinstance(run(e, 5, opened, outdoor=5.0)[1], Digest)


def test_room_override_and_disabled_kind():
    s = build_settings(
        {
            "alerts": {"co2_high": {"enabled": False}},
            "rooms": [{"name": "Bureau", "temperature": "sensor.t", "alerts": {"too_hot": {"threshold": 25}}}],
        }
    )
    room = s.rooms[0]
    assert room.alerts["too_hot"].threshold == 25
    assert room.alerts["too_cold"].threshold == 17
    assert not room.alerts["co2_high"].enabled


def test_persistence_roundtrip():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    e.snooze(T0, 30, rooms=["chambre_lea"])
    data = e.as_dict()
    restored = Engine(settings())
    restored.restore(data)
    assert restored.episodes["sejour|too_hot"].notified_at == e.episodes["sejour|too_hot"].notified_at
    assert "chambre_lea" in restored.snoozes
    # No notification again after the restore.
    assert run(restored, 25, hot())[1] is None


def test_removed_room_drops_episodes():
    e = Engine(settings())
    for m in (0, 15):
        run(e, m, hot())
    e.update_settings(build_settings({"rooms": [{"name": "Chambre Léa"}]}))
    assert not e.episodes


def test_snoozed_problem_notified_again_when_snooze_ends():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    e.snooze(T0 + timedelta(minutes=40), 60, keys=["sejour|too_hot"])
    # Hidden by the snooze: the notification is cleared.
    assert isinstance(run(e, 41, hot())[1], Clear)
    assert run(e, 99, hot())[1] is None
    # Snooze over, still too hot: notified again after the digest window.
    run(e, 100, hot())
    _, result = run(e, 105, hot())
    assert isinstance(result, Digest)
    assert result.items[0].reason == REASON_REMINDER
    # Once only.
    assert run(e, 200, hot())[1] is None


def test_unsnooze_notifies_again():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    e.snooze(T0 + timedelta(minutes=30), 240)
    run(e, 31, hot())
    e.unsnooze(T0 + timedelta(minutes=50))
    run(e, 50, hot())
    _, result = run(e, 55, hot())
    assert isinstance(result, Digest)


def test_removed_sensor_ends_its_episodes():
    e = Engine(settings())
    readings = {"chambre_lea": RoomReading(temperature=21.0, co2=1500)}
    for m in (0, 10, 15):
        run(e, m, readings)
    assert e.episodes["chambre_lea|co2_high"].active
    # The CO₂ sensor removed from the room in the options.
    e.update_settings(
        build_settings(
            {
                "rooms": [
                    {"name": "Séjour", "temperature": "sensor.t1"},
                    {"name": "Chambre Léa", "temperature": "sensor.t2"},
                ]
            }
        )
    )
    assert "chambre_lea|co2_high" not in e.episodes
    # The entity deleted: unknown for good, the episode ends instead of holding.
    e = Engine(settings())
    for m in (0, 10, 15):
        run(e, m, readings)
    run(e, 16, {"chambre_lea": RoomReading(temperature=21.0, missing=frozenset({"co2"}))})
    assert "chambre_lea|co2_high" not in e.episodes


def test_removed_outdoor_entity_ends_its_episodes():
    e = Engine(settings(outdoor_temperature=["sensor.out"], alerts={"window_open_cold": {"enabled": True, "delay": 0}}))
    opened = {"sejour": RoomReading(temperature=20.0, has_openings=True, open=["binary_sensor.w1"])}
    run(e, 0, opened, outdoor=8.0)
    assert "sejour|window_open_cold" in e.episodes
    # Outdoor sensor unavailable: unknown, the episode holds.
    run(e, 5, opened, outdoor=None)
    assert "sejour|window_open_cold" in e.episodes
    # Outdoor sensor deleted: the episode ends instead of holding for ever.
    gone = {
        "sejour": RoomReading(
            temperature=20.0, has_openings=True, open=["binary_sensor.w1"], missing=frozenset({"outdoor"})
        )
    }
    run(e, 10, gone, outdoor=None)
    assert "sejour|window_open_cold" not in e.episodes
    # A missing outdoor sensor doesn't end the problems that don't need it.
    e = Engine(settings())
    for m in (0, 15):
        run(e, m, hot())
    run(
        e,
        20,
        {"sejour": RoomReading(temperature=28.0, has_openings=True, open=[], missing=frozenset({"outdoor"}))},
        outdoor=None,
    )
    assert "sejour|too_hot" in e.episodes


def test_window_open_cold_worsens_when_colder():
    e = Engine(settings(alerts={"window_open_cold": {"enabled": True, "delay": 0, "escalation": 2}}))
    opened = {"sejour": RoomReading(temperature=20.0, has_openings=True, open=["binary_sensor.w1"])}
    run(e, 0, opened, outdoor=8.0)
    assert isinstance(run(e, 5, opened, outdoor=8.0)[1], Digest)
    # Warmer outside: not worse.
    run(e, 10, opened, outdoor=11.0)
    assert run(e, 20, opened, outdoor=11.0)[1] is None
    # Colder: worse.
    run(e, 21, opened, outdoor=5.0)
    _, result = run(e, 26, opened, outdoor=5.0)
    assert result.items[0].reason == REASON_WORSE


def test_equal_window_bounds_mean_always():
    assert in_window(parse_time("03:00"), parse_time("09:00"), parse_time("09:00"))


def test_last_keys_persisted():
    e = Engine(settings())
    for m in (0, 15, 20):
        run(e, m, hot())
    restored = Engine(settings())
    restored.restore(e.as_dict())
    assert restored.last_keys == ["sejour|too_hot"]


def test_digest_not_marked_until_sent():
    e = Engine(settings())
    for m in (0, 15):
        run(e, m, hot())
    now = T0 + timedelta(minutes=20)
    e.evaluate(now, hot(), 27.0)
    assert isinstance(e.step(now, OPEN, set()), Digest)
    # Not sent (every notifier failed): due again at the next evaluation.
    assert e.episodes["sejour|too_hot"].notified_at is None
    assert isinstance(run(e, 21, hot())[1], Digest)


def test_noise_alerts_and_noisy_outside():
    s = build_settings(
        {
            "outdoor_noise": ["sensor.street"],
            "alerts": {"noise_high": {"delay": 0}, "noisy_outside": {"delay": 0}, "ventilate": {"delay": 0}},
            "rooms": [
                {"name": "Bureau", "temperature": "sensor.t", "noise": "sensor.n", "openings": ["binary_sensor.w"]}
            ],
        }
    )
    e = Engine(s)
    quiet_closed = {"bureau": RoomReading(temperature=21, noise=45, has_openings=True, open=[], outdoor_noise=50)}
    run(e, 0, quiet_closed)
    assert not e.episodes
    # Loud room.
    loud = {"bureau": RoomReading(temperature=21, noise=70, has_openings=True, open=[], outdoor_noise=50)}
    run(e, 1, loud)
    assert e.episodes["bureau|noise_high"].active
    # Hysteresis: 57 dB is still a problem (60 - 5), 54 dB is over.
    run(e, 2, {"bureau": RoomReading(temperature=21, noise=57, has_openings=True, open=[], outdoor_noise=50)})
    assert "bureau|noise_high" in e.episodes
    run(e, 3, quiet_closed)
    assert "bureau|noise_high" not in e.episodes
    # Window open in the street noise: close it.
    open_loud = {
        "bureau": RoomReading(temperature=21, noise=50, has_openings=True, open=["binary_sensor.w"], outdoor_noise=72)
    }
    run(e, 4, open_loud)
    ep = e.episodes["bureau|noisy_outside"]
    assert ep.value == 72 and ep.details["openings"] == ["binary_sensor.w"]
    _title, message, _ = render(Digest([Item(ep, "Bureau", "info", "new")], "info"), {}, T0)
    assert message == "72 dB outside — close binary_sensor.w"


def test_no_ventilate_suggestion_when_noisy_outside():
    s = build_settings(
        {
            "outdoor_noise": ["sensor.street"],
            "alerts": {"ventilate": {"delay": 0}},
            "rooms": [{"name": "Bureau", "temperature": "sensor.t", "openings": ["binary_sensor.w"]}],
        }
    )
    e = Engine(s)
    warm = {"temperature": 27, "has_openings": True, "open": []}
    run(e, 0, {"bureau": RoomReading(**warm, outdoor_noise=70)}, outdoor=20)
    assert "bureau|ventilate" not in e.episodes
    run(e, 1, {"bureau": RoomReading(**warm, outdoor_noise=50)}, outdoor=20)
    assert "bureau|ventilate" in e.episodes
    # Unknown noise: no objection.
    run(e, 2, {"bureau": RoomReading(**warm, outdoor_noise=None)}, outdoor=20)
    assert "bureau|ventilate" in e.episodes
    # Noisy again: the suggestion is withdrawn.
    run(e, 3, {"bureau": RoomReading(**warm, outdoor_noise=70)}, outdoor=20)
    assert "bureau|ventilate" not in e.episodes
