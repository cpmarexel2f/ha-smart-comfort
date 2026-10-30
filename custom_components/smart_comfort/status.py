"""Status of the alerts and rooms, shared by the sensors and the configuration panel."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.util import dt as dt_util

from .config import Room
from .engine import HANDLED_KINDS, Episode

if TYPE_CHECKING:
    from .manager import SmartComfort


def episode_info(manager: SmartComfort, ep: Episode, now: datetime) -> dict[str, Any]:
    room = manager.settings.room(ep.room)
    return {
        "room": ep.room,
        "room_name": room.name if room else ep.room,
        "kind": ep.kind,
        "value": ep.value,
        "since": ep.since.isoformat(),
        "notified_at": ep.notified_at.isoformat() if ep.notified_at else None,
        "snoozed": manager.engine.snoozed(ep, now),
        "acknowledged": ep.acknowledged,
        # Suppressed because a running device takes care of it (too_hot only).
        "handled": ep.room in manager.handled and ep.kind in HANDLED_KINDS,
        **{k: v for k, v in ep.details.items() if k != "openings"},
        "openings": ep.details.get("openings", []),
    }


def room_info(manager: SmartComfort, room: Room, now: datetime) -> dict[str, Any]:
    reading, _ctx = manager.reading(room, now)
    controller = manager.controller
    return {
        "room_id": room.id,
        "temperature": reading.temperature,
        "co2": reading.co2,
        "humidity": reading.humidity,
        "noise": reading.noise,
        "open": reading.open,
        "ignored_openings": manager.ignored_openings(room, now),
        "alerts": [e.kind for e in manager.engine.active() if e.room == room.id],
        "handled": room.id in manager.handled,
        "devices": {
            d: {
                "target": controller.targets.get(d),
                "override_until": controller.overrides[d].isoformat()
                if d in controller.overrides and controller.overrides[d] > now
                else None,
            }
            for d in room.devices
        },
    }


def status(manager: SmartComfort, now: datetime) -> dict[str, Any]:
    """Everything the panel shows about the current state."""
    engine = manager.engine
    return {
        "alerts": [episode_info(manager, ep, now) for ep in engine.active()],
        "snoozes": {k: v.isoformat() for k, v in engine.snoozes.items() if v > now},
        "outdoor_temperature": manager.outdoor(),
        "outdoor_noise": manager.outdoor_noise(),
        "outdoor_air": manager.outdoor_air(),
        "night": manager.settings.night(dt_util.as_local(now).time()),
        "rooms": [{"name": r.name, **room_info(manager, r, now)} for r in manager.settings.rooms],
        "notifications_enabled": manager.notifications_enabled,
        "control_enabled": manager.control_enabled,
        "last_notification": manager.last_notification,
    }
