"""Setup, YAML import, notifications, device commands, actions and options flow in Home Assistant."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.smart_comfort import async_import_yaml, yaml_hash
from custom_components.smart_comfort.const import ACTION_SNOOZE, DOMAIN

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
    _states(hass, sejour=27.5, chambre=28.0)
    entry = await _setup(hass)
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
    # Back to normal: the notification is cleared.
    _states(hass)
    await _evaluate(hass, entry)
    assert notify[-1].data == {"message": "clear_notification", "data": {"tag": "smart_comfort"}}


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
