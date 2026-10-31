"""Indicator lights and displays of the devices: off in their hours and during the naps of the room.

Pure Python. A display is an on/off light or switch, a brightness number (off = its minimum) or a select
(off = its "off" option). Smart Comfort acts only when the wanted state changes (the hours start or end, a
nap starts or ends), like a timed automation: a display turned back on by hand stays on until the next
change. Turned back on, a display gets the brightness or option it had before.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config import Room, Settings, slugify
from .control import Command

# Options of a display select that turn it off (slug form, several languages).
OFF_WORDS = ("off", "ferme", "eteint", "close", "aus", "apagad", "cerrad", "none", "aucun", "disable")


def off_option(options: list[str] | tuple[str, ...]) -> str | None:
    """The option of a display select that turns it off."""
    return next((o for o in options if any(w == slugify(o) or slugify(o).startswith(w) for w in OFF_WORDS)), None)


@dataclass
class DisplayState:
    """State of a display entity, None fields when unknown."""

    domain: str
    value: str | None = None  # The state: on/off, a number, an option.
    options: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None

    @property
    def off(self) -> bool | None:
        if self.value is None:
            return None
        if self.domain == "number":
            try:
                return float(self.value) <= (self.minimum or 0)
            except ValueError:
                return None
        if self.domain == "select":
            return self.value == off_option(self.options)
        return self.value == "off"


@dataclass
class DisplayController:
    """Wanted state of every display (True: off) and the value each had before it was turned off."""

    settings: Settings
    wanted: dict[str, bool] = field(default_factory=dict)
    before: dict[str, str] = field(default_factory=dict)

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        displays = {d for r in settings.rooms for d in r.displays}
        self.wanted = {k: v for k, v in self.wanted.items() if k in displays}
        self.before = {k: v for k, v in self.before.items() if k in displays}

    def as_dict(self) -> dict[str, Any]:
        return {"wanted": self.wanted, "before": self.before}

    def restore(self, data: dict[str, Any]) -> None:
        self.wanted = {str(k): bool(v) for k, v in (data.get("wanted") or {}).items()}
        self.before = {str(k): str(v) for k, v in (data.get("before") or {}).items()}
        self.update_settings(self.settings)

    def off_now(self, room: Room, local: datetime) -> bool:
        """Displays off: in their hours, or during a nap of the room."""
        return self.settings.displays_off(local.time()) or room.napping(local)

    def evaluate(self, local: datetime, room: Room, states: dict[str, DisplayState]) -> list[Command]:
        """Commands for the displays of a room, when their wanted state changes."""
        off = self.off_now(room, local)
        commands = []
        for entity_id in room.displays:
            state = states.get(entity_id)
            if state is None or state.off is None or self.wanted.get(entity_id) == off:
                continue
            self.wanted[entity_id] = off
            if state.off == off:
                continue
            if off:
                self.before[entity_id] = state.value or ""
            if (cmd := self._command(entity_id, state, off)) is not None:
                cmd.target, cmd.device = ("display_off" if off else "display_on"), entity_id
                commands.append(cmd)
        return commands

    def _command(self, entity_id: str, state: DisplayState, off: bool) -> Command | None:
        before = self.before.pop(entity_id, None) if not off else None
        if state.domain == "number":
            if off:
                value: float = state.minimum or 0
            else:
                try:
                    value = float(before) if before else state.maximum or 100
                except ValueError:
                    value = state.maximum or 100
                if value <= (state.minimum or 0):
                    value = state.maximum or 100
            return Command(entity_id, "number", "set_value", {"value": value})
        if state.domain == "select":
            off_opt = off_option(state.options)
            if off_opt is None:
                return None
            if off:
                return Command(entity_id, "select", "select_option", {"option": off_opt})
            others = [o for o in state.options if o != off_opt]
            option = before if before in others else (others[0] if others else None)
            return None if option is None else Command(entity_id, "select", "select_option", {"option": option})
        return Command(entity_id, state.domain, "turn_off" if off else "turn_on")
