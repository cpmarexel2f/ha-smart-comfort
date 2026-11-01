"""Activity log: what Smart Comfort did and why, most recent last.

Pure Python. One entry per device and target of an evaluation (its commands together), per notification sent
or cleared, per change by hand that pauses a device or a light, and per reset time. Kept across restarts, the
most recent `ACTIVITY_SIZE` entries.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from .config import Settings
from .const import ACTIVITY_SIZE
from .control import Command

# Kinds of entries.
DEVICE = "device"  # A climate, fan or purifier to its target (cool, boost, night…).
LIGHTING = "lighting"  # A light to the brightness of the moment.
PRESENCE_ON = "presence_on"
PRESENCE_OFF = "presence_off"
DISPLAY = "display"  # An indicator light or display off / on.
NOTIFIED = "notified"
CLEARED = "cleared"
MANUAL = "manual"  # Changed by hand: paused.
RESET = "reset"  # Back to normal at its reset time.
FAILED = "failed"  # A command that could not be sent.
KINDS = (DEVICE, LIGHTING, PRESENCE_ON, PRESENCE_OFF, DISPLAY, NOTIFIED, CLEARED, MANUAL, RESET, FAILED)


def rooms_of(settings: Settings) -> dict[str, str]:
    """Room name of every entity Smart Comfort acts on."""
    out: dict[str, str] = {}
    for room in settings.rooms:
        for entity_id in (
            *room.devices,
            *(light.entity_id for light in room.lights),
            *room.presence_lights(),
            *room.displays,
        ):
            out.setdefault(entity_id, room.name)
    return out


def kind_of(cmd: Command) -> str:
    if cmd.target in ("display_off", "display_on"):
        return DISPLAY
    if cmd.domain == "light":
        if cmd.target == "presence":
            return PRESENCE_ON
        return PRESENCE_OFF if cmd.service == "turn_off" else LIGHTING
    return DEVICE


class Activity:
    """The entries, oldest first."""

    def __init__(self, settings: Settings) -> None:
        self.entries: deque[dict[str, Any]] = deque(maxlen=ACTIVITY_SIZE)
        self.rooms = rooms_of(settings)

    def update_settings(self, settings: Settings) -> None:
        self.rooms = rooms_of(settings)

    def add(self, now: datetime, kind: str, entity_id: str | None = None, **extra: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {"at": now.isoformat(), "kind": kind}
        if entity_id:
            entry["entity_id"] = entity_id
            if room := self.rooms.get(entity_id):
                entry["room"] = room
        entry.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
        self.entries.append(entry)
        return entry

    def commands(self, now: datetime, sent: Iterable[tuple[Command, bool]]) -> list[dict[str, Any]]:
        """One entry per device and target, with its actions; a failed one as such."""
        groups: dict[tuple[str, str | None], list[tuple[Command, bool]]] = {}
        for cmd, ok in sent:
            groups.setdefault((cmd.device or cmd.entity_id, cmd.target), []).append((cmd, ok))
        added = []
        for (device, target), cmds in groups.items():
            first = cmds[0][0]
            failed = [c for c, ok in cmds if not ok]
            data: dict[str, Any] = {}
            for c, _ok in cmds:
                data.update(c.data)
            data.pop("transition", None)
            added.append(
                self.add(
                    now,
                    FAILED if failed else kind_of(first),
                    device,
                    target=target,
                    action=f"{first.domain}.{first.service}",
                    data=data,
                    failed=f"{failed[0].domain}.{failed[0].service}" if failed else None,
                )
            )
        return added

    def as_list(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Most recent first."""
        entries = list(reversed(self.entries))
        return entries[:limit] if limit else entries

    def as_dict(self) -> list[dict[str, Any]]:
        return list(self.entries)

    def restore(self, data: Any) -> None:
        if isinstance(data, list):
            self.entries.extend(e for e in data if isinstance(e, dict) and e.get("kind") in KINDS and e.get("at"))
