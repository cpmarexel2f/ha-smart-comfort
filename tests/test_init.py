"""Setup, YAML import, notifications, device commands, actions and options flow in Home Assistant."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.smart_comfort import async_import_yaml, yaml_hash
from custom_components.smart_comfort.config import build_settings
from custom_components.smart_comfort.const import ACTION_SNOOZE, COMMAND_RETRY, DOMAIN

OPTIONS = {
    "notify": ["notify.phone"],
    "outdoor_temperature": ["sensor.out1", "sensor.out2"],
    "digest_window": 0,
    "startup_grace": 0,
    "alerts": {"too_hot": {"delay": 0}, "ventilate": {"enabled": False}},
    "rooms": [
        {
            "name": "Séjour",
            "temperature": "sensor.t_sejour",
            "openings": ["binary_sensor.w_sejour"],
            "fans": ["fan.sejour"],
        },
        {"name": "Chambre", "temperature": "sensor.t_chambre"},
    ],
}


def _states(hass: HomeAssistant, sejour: float = 21.0, chambre: float = 21.0, window: str = "off") -> None:
    hass.states.async_set("sensor.out1", "24")
    hass.states.async_set("sensor.out2", "26")
    hass.states.async_set("sensor.t_sejour", str(sejour))
    hass.states.async_set("sensor.t_chambre", str(chambre))
    hass.states.async_set("binary_sensor.w_sejour", window)
    hass.states.async_set("fan.sejour", "off", {"percentage": 0})


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options=options or OPTIONS)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _evaluate(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_evaluate()
    await hass.async_block_till_done()


@pytest.fixture
def notify(hass: HomeAssistant):
    return async_mock_service(hass, "notify", "phone")


@pytest.fixture
def fan_calls(hass: HomeAssistant):
    return {s: async_mock_service(hass, "fan", s) for s in ("turn_on", "turn_off", "set_percentage", "set_preset_mode")}


async def test_one_grouped_notification(hass: HomeAssistant, notify, fan_calls) -> None:
    mobile = async_mock_service(hass, "notify", "mobile_app_phone")
    _states(hass, sejour=27.5, chambre=28.0)
    entry = await _setup(hass, {**OPTIONS, "notify": ["notify.phone", "notify.mobile_app_phone"]})
    await _evaluate(hass, entry)
    assert len(notify) == 1
    data = notify[0].data
    assert "2" in data["title"]
    assert "Séjour" in data["message"] and "Chambre" in data["message"]
    assert data["data"]["tag"] == "smart_comfort"
    assert [a["action"] for a in data["data"]["actions"]] == [ACTION_SNOOZE, "SMART_COMFORT_ACK"]
    # Still hot: nothing more, on the interval either.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await _evaluate(hass, entry)
    assert len(notify) == 1
    assert hass.states.get("sensor.smart_comfort_active_alerts").state == "2"
    # The fan of the room was turned on (23 °C by default), so the Séjour too_hot is handled now.
    assert fan_calls["turn_on"]
    # Back to normal: the notification is cleared, on the Companion app only.
    _states(hass)
    await _evaluate(hass, entry)
    assert mobile[-1].data == {"message": "clear_notification", "data": {"tag": "smart_comfort"}}
    assert len(mobile) == 2
    assert len(notify) == 1


async def test_snooze_action_from_notification(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass, chambre=28.0)
    entry = await _setup(hass)
    await _evaluate(hass, entry)
    assert len(notify) == 1
    hass.bus.async_fire("mobile_app_notification_action", {"action": ACTION_SNOOZE})
    await hass.async_block_till_done()
    ep = entry.runtime_data.engine.episodes["chambre|too_hot"]
    assert ep.snoozed_until is not None


async def test_services(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass)
    entry = await _setup(hass)
    await hass.services.async_call(DOMAIN, "snooze", {"rooms": ["Chambre"], "duration": 30}, blocking=True)
    _states(hass, chambre=28.0)
    await _evaluate(hass, entry)
    assert notify == []
    await hass.services.async_call(DOMAIN, "unsnooze", {}, blocking=True)
    await hass.async_block_till_done()
    assert len(notify) == 1
    result = await hass.services.async_call(DOMAIN, "notify_now", {}, blocking=True, return_response=True)
    assert result == {"sent": True}
    assert len(notify) == 2


async def test_notifications_switch(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass)
    entry = await _setup(hass)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.smart_comfort_notifications"}, blocking=True
    )
    _states(hass, chambre=28.0)
    await _evaluate(hass, entry)
    assert notify == []
    assert hass.states.get("sensor.smart_comfort_chambre_comfort").state == "too_hot"


async def test_state_survives_reload(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass, chambre=28.0)
    entry = await _setup(hass)
    await _evaluate(hass, entry)
    assert len(notify) == 1
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    await _evaluate(hass, entry)
    assert len(notify) == 1


async def test_yaml_import(hass: HomeAssistant, notify) -> None:
    _states(hass)
    yaml = {"notify": ["notify.phone"], "rooms": [{"name": "Séjour", "temperature": "sensor.t_sejour"}]}
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: yaml})
    await hass.async_block_till_done()
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.state is ConfigEntryState.LOADED
    assert entry.data["yaml_hash"] == yaml_hash(dict(entry.options))
    assert entry.options["rooms"][0]["name"] == "Séjour"


async def test_config_and_options_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"notify": ["phone"], "outdoor_temperature": [], "outdoor_aggregate": "min"}
    )
    assert result["type"] == "create_entry"
    entry = result["result"]
    assert entry.options["notify"] == ["notify.phone"]
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "menu"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "add_room"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "name": "Chambre Léa",
            "temperature": "sensor.t_lea",
            "fans": ["fan.lea"],
            "overrides": {"too_hot_threshold": 25, "fan_preset": "Brise Naturelle"},
        },
    )
    assert result["type"] == "create_entry"
    room = entry.options["rooms"][0]
    assert room["alerts"] == {"too_hot": {"threshold": 25.0}}
    assert room["control"] == {"fans": {"preset": "Brise Naturelle"}}

    # Same name again: refused.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "add_room"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "chambre lea", "overrides": {}}
    )
    assert result["errors"] == {"name": "name_exists"}

    # Alert settings.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"kind": "co2_high"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"enabled": True, "threshold": 1000, "hysteresis": 100, "delay": 5, "severity": "warning", "escalation": 300},
    )
    assert result["type"] == "create_entry"
    assert entry.options["alerts"]["co2_high"]["threshold"] == 1000
    assert entry.options["rooms"][0]["name"] == "Chambre Léa"


async def test_yaml_reimport_only_when_changed(hass: HomeAssistant) -> None:
    yaml = {"rooms": [{"name": "A"}]}

    async def import_(options: dict) -> None:
        async_import_yaml(hass, options)
        await hass.async_block_till_done()

    await import_(yaml)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    # Changed in the UI, same YAML at the next start: the UI change stays.
    hass.config_entries.async_update_entry(entry, options={"rooms": [{"name": "A"}, {"name": "B"}]})
    await hass.async_block_till_done()
    await import_(yaml)
    assert len(entry.options["rooms"]) == 2
    # YAML changed: it wins.
    await import_({"rooms": [{"name": "C"}]})
    assert entry.options["rooms"] == [{"name": "C"}]


async def test_failed_notification_is_sent_again(hass: HomeAssistant, fan_calls) -> None:
    calls = []

    async def failing(call) -> None:
        calls.append(call)
        if len(calls) == 1:
            raise RuntimeError("offline")

    hass.services.async_register("notify", "phone", failing)
    _states(hass, chambre=28.0)
    entry = await _setup(hass)  # First evaluation: the notifier fails.
    assert len(calls) == 1
    assert entry.runtime_data.last_notification is None
    assert entry.runtime_data.engine.episodes["chambre|too_hot"].notified_at is None
    await _evaluate(hass, entry)
    assert len(calls) == 2
    assert entry.runtime_data.last_notification is not None
    await _evaluate(hass, entry)
    assert len(calls) == 2


async def test_failed_command_is_retried(hass: HomeAssistant, notify, freezer) -> None:
    calls = []

    async def failing(call) -> None:
        calls.append(call)
        raise RuntimeError("timeout")

    hass.services.async_register("fan", "turn_on", failing)
    for service in ("set_percentage", "set_preset_mode", "turn_off"):
        async_mock_service(hass, "fan", service)
    _states(hass, sejour=24.0)
    entry = await _setup(hass)
    sent = len(calls)
    assert sent >= 1
    assert "fan.sejour" not in entry.runtime_data.controller.targets
    # Not at every evaluation (a lasting error would flood the log), but once the retry delay is over.
    await _evaluate(hass, entry)
    assert len(calls) == sent
    freezer.tick(timedelta(minutes=COMMAND_RETRY))
    await _evaluate(hass, entry)
    assert len(calls) == sent + 1


async def test_failed_command_applied_anyway_follows_manual_changes(hass: HomeAssistant, notify, freezer) -> None:
    calls = []

    async def failing(call) -> None:
        calls.append(call)
        raise RuntimeError("timeout")

    hass.services.async_register("fan", "turn_on", failing)
    for service in ("set_percentage", "set_preset_mode", "turn_off"):
        async_mock_service(hass, "fan", service)
    _states(hass, sejour=24.0)
    entry = await _setup(hass)
    controller = entry.runtime_data.controller
    sent = len(calls)
    # The command timed out but the fan turned on anyway: Smart Comfort's target, the room is handled.
    freezer.tick(timedelta(minutes=2))
    hass.states.async_set("fan.sejour", "on", {"percentage": 50})
    await _evaluate(hass, entry)
    assert controller.targets["fan.sejour"] == "on"
    assert "sejour" in entry.runtime_data.handled
    assert controller.failures == {}
    # Turned off by hand during what was the retry delay: a manual override, not turned on again.
    hass.states.async_set("fan.sejour", "off", {"percentage": 0})
    await hass.async_block_till_done()
    assert "fan.sejour" in controller.overrides
    freezer.tick(timedelta(minutes=COMMAND_RETRY))
    await _evaluate(hass, entry)
    assert len(calls) == sent


async def test_removed_outdoor_entity_ends_episodes(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass, window="on")
    hass.states.async_set("sensor.out1", "5")
    hass.states.async_set("sensor.out2", "6")
    alerts = {**OPTIONS["alerts"], "window_open_cold": {"enabled": True, "delay": 0}}
    entry = await _setup(hass, {**OPTIONS, "alerts": alerts})
    await _evaluate(hass, entry)
    episodes = entry.runtime_data.engine.episodes
    assert "sejour|window_open_cold" in episodes
    # One outdoor sensor deleted, the other one still there: still known.
    hass.states.async_remove("sensor.out1")
    await _evaluate(hass, entry)
    assert "sejour|window_open_cold" in episodes
    # The other one unavailable: unknown for now, the episode holds.
    hass.states.async_set("sensor.out2", "unavailable")
    await _evaluate(hass, entry)
    assert "sejour|window_open_cold" in episodes
    # Both deleted: gone for good, the episode ends.
    hass.states.async_remove("sensor.out2")
    await _evaluate(hass, entry)
    assert "sejour|window_open_cold" not in episodes


async def test_snooze_keys_survive_restart(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass, sejour=28.0, chambre=28.0)
    entry = await _setup(hass)
    await _evaluate(hass, entry)
    assert len(notify) == 1
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    # A new problem comes up after the notification: the Snooze button only covers what it showed.
    engine = entry.runtime_data.engine
    assert sorted(engine.last_keys) == ["chambre|too_hot", "sejour|too_hot"]
    hass.bus.async_fire("mobile_app_notification_action", {"action": ACTION_SNOOZE})
    await hass.async_block_till_done()
    assert "*" not in engine.snoozes
    assert engine.episodes["chambre|too_hot"].snoozed_until is not None


async def test_weather_and_fahrenheit_outdoor(hass: HomeAssistant, notify) -> None:
    entry = await _setup(hass, {**OPTIONS, "outdoor_temperature": ["weather.home", "sensor.out_f"]})
    hass.states.async_set("weather.home", "sunny", {"temperature": 20.0, "temperature_unit": "°C"})
    hass.states.async_set("sensor.out_f", "77", {"unit_of_measurement": "°F"})
    assert entry.runtime_data.outdoor() == 20.0
    hass.states.async_set("weather.home", "sunny", {"temperature": 86.0, "temperature_unit": "°F"})
    assert entry.runtime_data.outdoor() == 25.0


async def test_unavailable_opening_left_out(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass)
    entry = await _setup(hass)
    m = entry.runtime_data
    room = m.settings.rooms[0]
    hass.states.async_set("binary_sensor.w_sejour", "unavailable")
    now = dt_util.utcnow()
    assert m.reading(room, now)[0].open is None
    later = now + timedelta(minutes=11)
    assert m.reading(room, later)[0].open == []
    assert m.ignored_openings(room, later) == ["binary_sensor.w_sejour"]


async def test_removed_sensor_entity_ends_episode(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass, chambre=28.0)
    entry = await _setup(hass)
    await _evaluate(hass, entry)
    assert "chambre|too_hot" in entry.runtime_data.engine.episodes
    hass.states.async_set("sensor.t_chambre", "unavailable")
    await _evaluate(hass, entry)
    assert "chambre|too_hot" in entry.runtime_data.engine.episodes
    hass.states.async_remove("sensor.t_chambre")
    await _evaluate(hass, entry)
    assert "chambre|too_hot" not in entry.runtime_data.engine.episodes


async def test_stop_waits_for_the_evaluation(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass)
    entry = await _setup(hass)
    m = entry.runtime_data
    await m._lock.acquire()
    stop = hass.async_create_task(m.async_stop())
    await asyncio.sleep(0)
    assert not stop.done()
    m.engine.shown = True  # Changed by the evaluation in progress.
    m._lock.release()
    await stop
    assert hass.data[DOMAIN]["state"]["engine"]["shown"] is True


async def test_switch_states_restored_before_entities(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass)
    entry = await _setup(hass)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.smart_comfort_device_control"}, blocking=True
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN]["state"]["control_enabled"] is False


async def test_remove_entry_forgets_the_state(hass: HomeAssistant, notify, fan_calls) -> None:
    _states(hass, chambre=28.0)
    entry = await _setup(hass)
    await _evaluate(hass, entry)
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "state" not in hass.data.get(DOMAIN, {})


async def test_options_flow_keeps_emptied_fields_empty(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "control"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "enabled": True,
            "manual_override": 60,
            "suppress_when_handled": True,
            "climate": {"cool_above": 23, "off_below": 21, "setpoint": 22, "closed_for": 2, "off_on_open": 1},
            "fans": {},
            "purifiers": {"keep_on": False, "open_preset": "Turbo"},
        },
    )
    assert result["type"] == "create_entry"
    settings = build_settings(dict(entry.options))
    assert settings.control_start is None and settings.control_end is None
    control = entry.options["control"]
    assert control["fans"]["on_above"] is None and control["fans"]["off_below"] is None
    assert control["purifiers"]["open_percentage"] is None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "alerts"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"kind": "ventilate"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"enabled": True, "threshold": 2, "hysteresis": 0.5, "delay": 15, "severity": "info", "escalation": 2},
    )
    assert result["type"] == "create_entry"
    assert build_settings(dict(entry.options)).rooms == ()
    assert entry.options["alerts"]["ventilate"]["min_indoor"] is None


async def test_options_flow_invalid_value_shows_error(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Smart Comfort", data={}, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "general"})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "notify": ["notify."],
            "outdoor_temperature": [],
            "outdoor_aggregate": "min",
            "digest_window": 5,
            "reminder": 0,
            "snooze_duration": 240,
            "startup_grace": 10,
            "clear_when_resolved": True,
            "critical_volume": 0.5,
            "tag": "smart_comfort",
        },
    )
    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_options"}


async def test_renamed_room_keeps_its_sensor(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"notify": [], "outdoor_temperature": [], "outdoor_aggregate": "min"}
    )
    entry = result["result"]
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "add_room"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"name": "Bureau", "overrides": {}})
    assert entry.options["rooms"][0]["id"] == "bureau"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.smart_comfort_bureau_comfort") is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "edit_room"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"room": "0"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"name": "Office", "overrides": {}})
    await hass.async_block_till_done()
    assert entry.options["rooms"][0]["id"] == "bureau"
    registry = er.async_get(hass)
    sensors = [e for e in er.async_entries_for_config_entry(registry, entry.entry_id) if "_room_" in e.unique_id]
    assert [e.unique_id for e in sensors] == [f"{entry.entry_id}_room_bureau"]

    # Removed: its sensor leaves the registry.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "remove_room"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"rooms": ["0"]})
    await hass.async_block_till_done()
    sensors = [e for e in er.async_entries_for_config_entry(registry, entry.entry_id) if "_room_" in e.unique_id]
    assert sensors == []


PURIFIER_OPTIONS = {
    "notify": [],
    "outdoor_temperature": ["sensor.out1"],
    "digest_window": 0,
    "startup_grace": 0,
    "control": {"start": "00:00", "end": "00:00"},
    "rooms": [
        {
            "name": "Séjour",
            "temperature": "sensor.t_sejour",
            "openings": ["binary_sensor.w_sejour"],
            "purifiers": [
                {"entity_id": "fan.p", "mode_select": "select.p_mode", "open_mode": "manual", "closed_mode": "auto"}
            ],
        }
    ],
}


async def _purifier_setup(hass: HomeAssistant):
    select = async_mock_service(hass, "select", "select_option")
    for service in ("turn_on", "turn_off", "set_percentage", "set_preset_mode"):
        async_mock_service(hass, "fan", service)
    hass.states.async_set("sensor.out1", "20")
    hass.states.async_set("sensor.t_sejour", "21")
    hass.states.async_set("binary_sensor.w_sejour", "on")
    hass.states.async_set("fan.p", "on", {"preset_mode": "Auto", "percentage": 30})
    hass.states.async_set("select.p_mode", "auto")
    entry = await _setup(hass, PURIFIER_OPTIONS)
    await _evaluate(hass, entry)
    # The purifier applies the boost.
    hass.states.async_set("select.p_mode", "manual")
    hass.states.async_set("fan.p", "on", {"preset_mode": None, "percentage": 100})
    await hass.async_block_till_done()
    return entry, select


async def test_purifier_answer_to_mode_select_is_not_manual(hass: HomeAssistant, freezer) -> None:
    entry, select = await _purifier_setup(hass)
    controller = entry.runtime_data.controller
    # Window closed long after the boost: only the mode select is sent.
    freezer.tick(timedelta(minutes=10))
    hass.states.async_set("binary_sensor.w_sejour", "off")
    await _evaluate(hass, entry)
    assert [c.data["option"] for c in select] == ["manual", "auto"]
    # The purifier answers on its fan entity, in its own context: not a manual change.
    hass.states.async_set("select.p_mode", "auto")
    hass.states.async_set("fan.p", "on", {"preset_mode": "Auto", "percentage": 30})
    await hass.async_block_till_done()
    assert "fan.p" not in controller.overrides
    # Window opened again: boosted again.
    freezer.tick(timedelta(minutes=10))
    hass.states.async_set("binary_sensor.w_sejour", "on")
    await _evaluate(hass, entry)
    assert [c.data["option"] for c in select] == ["manual", "auto", "manual"]


async def test_purifier_changed_by_hand_after_mode_select_is_manual(hass: HomeAssistant, freezer) -> None:
    entry, select = await _purifier_setup(hass)
    controller = entry.runtime_data.controller
    freezer.tick(timedelta(minutes=10))
    hass.states.async_set("binary_sensor.w_sejour", "off")
    await _evaluate(hass, entry)
    hass.states.async_set("select.p_mode", "auto")
    hass.states.async_set("fan.p", "on", {"preset_mode": "Auto", "percentage": 30})
    await hass.async_block_till_done()
    # Changed by hand once the grace period of the command is over: control paused.
    freezer.tick(timedelta(minutes=5))
    hass.states.async_set("fan.p", "on", {"preset_mode": "Sleep", "percentage": 10})
    await hass.async_block_till_done()
    assert "fan.p" in controller.overrides
    hass.states.async_set("binary_sensor.w_sejour", "on")
    await _evaluate(hass, entry)
    assert [c.data["option"] for c in select] == ["manual", "auto"]


async def test_noise(hass: HomeAssistant, notify) -> None:
    hass.states.async_set("sensor.t", "21")
    hass.states.async_set("sensor.n", "72")
    hass.states.async_set("sensor.street", "70")
    hass.states.async_set("sensor.street2", "64")
    hass.states.async_set("binary_sensor.w", "on")
    options = {
        "notify": ["notify.phone"],
        "digest_window": 0,
        "startup_grace": 0,
        "outdoor_noise": ["sensor.street", "sensor.street2"],
        "alerts": {"noise_high": {"delay": 0}, "noisy_outside": {"delay": 0}},
        "rooms": [{"name": "Bureau", "temperature": "sensor.t", "noise": "sensor.n", "openings": ["binary_sensor.w"]}],
    }
    entry = await _setup(hass, options)
    await _evaluate(hass, entry)
    manager = entry.runtime_data
    assert manager.outdoor_noise() == 67.0  # Mean of the outdoor sensors.
    assert sorted(manager.engine.episodes) == ["bureau|noise_high", "bureau|noisy_outside"]
    assert len(notify) == 1
    assert "72 dB" in notify[0].data["message"]
    attrs = hass.states.get("sensor.smart_comfort_bureau_comfort").attributes
    assert attrs["noise"] == 72.0
