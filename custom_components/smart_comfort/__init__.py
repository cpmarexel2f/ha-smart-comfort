"""Smart Comfort: fewer, smarter comfort alerts, and control of air conditioners, fans and purifiers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import CoreState, HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .config import build_settings, slugify
from .const import (
    DOMAIN,
    KINDS,
    MAX_MINUTES,
    SERVICE_ACKNOWLEDGE,
    SERVICE_NOTIFY_NOW,
    SERVICE_SNOOZE,
    SERVICE_UNSNOOZE,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .manager import SmartComfort
from .schema import CONFIG_SCHEMA as _CONFIG_SCHEMA

PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]
CONFIG_SCHEMA = _CONFIG_SCHEMA

type SmartComfortConfigEntry = ConfigEntry[SmartComfort]

ROOMS = vol.All(cv.ensure_list, [cv.string])
KIND_LIST = vol.All(cv.ensure_list, [vol.In(KINDS)])


def yaml_hash(options: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(options, sort_keys=True, default=str).encode()).hexdigest()


@callback
def async_import_yaml(hass: HomeAssistant, options: dict[str, Any]) -> None:
    """Create the entry from the YAML, or replace its options when the YAML changed since the last import.

    Unchanged YAML leaves the options alone, so changes made in the UI stay until the YAML changes.
    The import flow only creates: a single-entry integration can't run a flow once its entry exists.
    """
    digest = yaml_hash(options)
    if entries := hass.config_entries.async_entries(DOMAIN, include_ignore=False):
        entry = entries[0]
        if entry.data.get("yaml_hash") != digest:
            hass.config_entries.async_update_entry(entry, data={**entry.data, "yaml_hash": digest}, options=options)
        return
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data={"options": options, "yaml_hash": digest}
        )
    )


def _manager(hass: HomeAssistant) -> SmartComfort:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")


def _rooms(manager: SmartComfort, raw: list[str] | None) -> list[str] | None:
    """Room ids from ids or names."""
    if not raw:
        return None
    by_key = {}
    for room in manager.settings.rooms:
        by_key[room.id] = room.id
        by_key[slugify(room.name)] = room.id
    out = []
    for value in raw:
        if (room_id := by_key.get(slugify(value))) is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_room", translation_placeholders={"room": value}
            )
        out.append(room_id)
    return out


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import the YAML configuration and register the actions."""
    if (options := config.get(DOMAIN)) is not None:
        async_import_yaml(hass, options)

    async def snooze(call: ServiceCall) -> None:
        m = _manager(hass)
        await m.async_snooze(call.data.get("duration"), _rooms(m, call.data.get("rooms")), call.data.get("kinds"))

    async def unsnooze(call: ServiceCall) -> None:
        m = _manager(hass)
        await m.async_unsnooze(_rooms(m, call.data.get("rooms")))

    async def acknowledge(call: ServiceCall) -> None:
        m = _manager(hass)
        await m.async_acknowledge(_rooms(m, call.data.get("rooms")), call.data.get("kinds"))

    async def notify_now(call: ServiceCall) -> dict[str, Any]:
        sent = await _manager(hass).async_notify_now()
        return {"sent": sent}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SNOOZE,
        snooze,
        vol.Schema(
            {
                vol.Optional("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_MINUTES * 7)),
                vol.Optional("rooms"): ROOMS,
                vol.Optional("kinds"): KIND_LIST,
            }
        ),
    )
    hass.services.async_register(DOMAIN, SERVICE_UNSNOOZE, unsnooze, vol.Schema({vol.Optional("rooms"): ROOMS}))
    hass.services.async_register(
        DOMAIN,
        SERVICE_ACKNOWLEDGE,
        acknowledge,
        vol.Schema({vol.Optional("rooms"): ROOMS, vol.Optional("kinds"): KIND_LIST}),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY_NOW, notify_now, vol.Schema({}), supports_response=SupportsResponse.OPTIONAL
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SmartComfortConfigEntry) -> bool:
    manager = SmartComfort(hass, build_settings(dict(entry.options)))
    await manager.async_start(starting=hass.state is not CoreState.running)
    entry.runtime_data = manager
    entry.async_on_unload(manager.async_stop)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def first(_hass: HomeAssistant) -> None:
        await manager.async_evaluate()

    entry.async_on_unload(async_at_started(hass, first))
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartComfortConfigEntry) -> bool:
    # Waits for an evaluation in progress, so that the next instance starts from its final state.
    await entry.runtime_data.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: SmartComfortConfigEntry) -> None:
    """Forget the episodes, snoozes and targets: a new entry starts afresh."""
    hass.data.get(DOMAIN, {}).pop("state", None)
    await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()


async def _async_reload(hass: HomeAssistant, entry: SmartComfortConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
