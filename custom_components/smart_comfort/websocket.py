"""WebSocket commands of the configuration panel: read and save the options, follow the status."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util
from voluptuous.humanize import humanize_error

from . import const as k
from .config import slugify
from .schema import OPTIONS
from .status import status

GENERAL_DEFAULTS = {
    k.CONF_OUTDOOR_AGGREGATE: "min",
    k.CONF_DIGEST_WINDOW: k.DEFAULT_DIGEST_WINDOW,
    k.CONF_REMINDER: k.DEFAULT_REMINDER,
    k.CONF_SNOOZE_DURATION: k.DEFAULT_SNOOZE,
    k.CONF_STARTUP_GRACE: k.DEFAULT_STARTUP_GRACE,
    k.CONF_CLEAR_WHEN_RESOLVED: True,
    k.CONF_CRITICAL_VOLUME: k.DEFAULT_CRITICAL_VOLUME,
    k.CONF_TAG: k.DEFAULT_TAG,
}


def _entry(hass: HomeAssistant) -> ConfigEntry | None:
    entries = hass.config_entries.async_entries(k.DOMAIN, include_ignore=False)
    return entries[0] if entries else None


def _manager(hass: HomeAssistant) -> Any:
    entry = _entry(hass)
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        return None
    return entry.runtime_data


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_get_config)
    websocket_api.async_register_command(hass, ws_save_config)
    websocket_api.async_register_command(hass, ws_subscribe)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{k.DOMAIN}/config"})
@callback
def ws_get_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """The options and the defaults they fall back to."""
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Comfort is not set up")
        return
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "loaded": entry.state is ConfigEntryState.LOADED,
            "yaml": bool(entry.data.get("yaml_hash")),
            "options": dict(entry.options),
            "defaults": {
                "general": GENERAL_DEFAULTS,
                "alerts": k.DEFAULT_ALERTS,
                "control": k.DEFAULT_CONTROL,
            },
            "kinds": list(k.KINDS),
            "severities": list(k.SEVERITIES),
            "aggregates": list(k.AGGREGATES),
        },
    )


def _check_rooms(options: dict[str, Any]) -> str | None:
    seen: set[str] = set()
    for room in options.get(k.CONF_ROOMS) or []:
        key = str(room.get("id") or slugify(room[k.CONF_NAME]))
        if key in seen:
            return f"Two rooms have the same name: {room[k.CONF_NAME]}"
        seen.add(key)
    return None


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{k.DOMAIN}/config/save", vol.Required("options"): dict})
@callback
def ws_save_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Validate and store the options; the integration reloads with them."""
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Smart Comfort is not set up")
        return
    try:
        options = OPTIONS(msg["options"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid_format", humanize_error(msg["options"], err))
        return
    if (problem := _check_rooms(options)) is not None:
        connection.send_error(msg["id"], "invalid_format", problem)
        return
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], {"options": options})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{k.DOMAIN}/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Status now and after every evaluation, across reloads of the integration."""

    @callback
    def send() -> None:
        manager = _manager(hass)
        payload = status(manager, dt_util.utcnow()) if manager is not None else None
        connection.send_message(websocket_api.event_message(msg["id"], {"status": payload}))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, k.SIGNAL_UPDATE, send)
    connection.send_result(msg["id"])
    send()
