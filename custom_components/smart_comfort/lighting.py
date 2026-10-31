"""Adaptive lighting: brightness (and warmth) of the lights that are on, by time of day.

Pure Python. Smart Comfort never turns a light on or off: a light just turned on gets the brightness
of the moment at once, then follows the day gradually (day with the sun up, evening once it is down,
night in the quiet night hours, the nap slots of its room, the quiet morning of the rooms that have it).
A brightness or warmth changed by hand pauses the light until it is turned off, or for `manual_override`
minutes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .config import LightDevice, Room, Settings
from .const import KELVIN_STEP, LIGHT_STEP, SUN_DAY, SUN_EVENING
from .control import Command

PHASE_DAY = "day"
PHASE_EVENING = "evening"
PHASE_NIGHT = "night"
PHASE_NAP = "nap"
PHASE_MORNING = "morning"


@dataclass
class LightState:
    """State of a light entity, None fields when unknown or not supported."""

    on: bool | None = None
    brightness: int | None = None  # Percent.
    kelvin: int | None = None
    dimmable: bool = True
    # Color temperature range when the light supports it, else None.
    min_kelvin: int | None = None
    max_kelvin: int | None = None


@dataclass(frozen=True)
class LightTarget:
    brightness: int
    kelvin: int | None = None

    def label(self) -> str:
        return f"{self.brightness} %" + (f" · {self.kelvin} K" if self.kelvin else "")


def day_share(elevation: float | None) -> float:
    """How much of the day it is, from 0 (evening) to 1 (day), by the sun elevation (day without sun data)."""
    if elevation is None:
        return 1.0
    share = (elevation - SUN_EVENING) / (SUN_DAY - SUN_EVENING)
    return min(1.0, max(0.0, share))


def phase(settings: Settings, local: datetime, elevation: float | None, room: Room | None = None) -> str:
    """Time of day for the lights of a room: night, nap, quiet morning (rooms that have it), day or evening."""
    if settings.night(local.time()):
        return PHASE_NIGHT
    if room is not None and room.napping(local):
        return PHASE_NAP
    if room is not None and any(light.quiet_morning for light in room.lights) and settings.morning(local.time()):
        return PHASE_MORNING
    return PHASE_DAY if day_share(elevation) >= 0.5 else PHASE_EVENING


def target(light: LightDevice, moment: str, share: float, state: LightState) -> LightTarget | None:
    """Brightness and warmth for the light now; None when it is left alone (a night light by day)."""
    if moment == PHASE_MORNING and not light.quiet_morning:
        moment = PHASE_DAY
    dark = moment in (PHASE_NIGHT, PHASE_NAP)
    if not state.dimmable or (light.night_only and not dark):
        return None
    if moment == PHASE_NIGHT:
        brightness, kelvin = light.night, light.night_kelvin
    elif moment == PHASE_NAP:
        brightness, kelvin = light.nap, light.nap_kelvin
    elif moment == PHASE_MORNING:
        brightness, kelvin = light.morning, light.morning_kelvin
    else:
        brightness = round(light.evening + share * (light.day - light.evening))
        kelvin = round(light.evening_kelvin + share * (light.day_kelvin - light.evening_kelvin))
    if not light.warmth or state.min_kelvin is None or state.max_kelvin is None:
        return LightTarget(max(1, min(100, brightness)))
    return LightTarget(max(1, min(100, brightness)), max(state.min_kelvin, min(state.max_kelvin, kelvin)))


class LightController:
    """Last brightness sent and manual pauses of every light."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.targets: dict[str, LightTarget] = {}
        self.overrides: dict[str, datetime] = {}

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        lights = {light.entity_id for r in settings.rooms for light in r.lights}
        self.targets = {k: v for k, v in self.targets.items() if k in lights}
        self.overrides = {k: v for k, v in self.overrides.items() if k in lights}

    def as_dict(self) -> dict[str, Any]:
        return {"overrides": {k: v.isoformat() for k, v in self.overrides.items()}}

    def restore(self, data: dict[str, Any]) -> None:
        for k, v in (data.get("overrides") or {}).items():
            try:
                self.overrides[str(k)] = datetime.fromisoformat(v)
            except (TypeError, ValueError):
                continue
        self.update_settings(self.settings)

    def manual_change(self, entity_id: str, now: datetime) -> None:
        """Brightness or warmth changed by hand: left alone until turned off, or for manual_override minutes."""
        if self.settings.manual_override > 0:
            self.overrides[entity_id] = now + timedelta(minutes=self.settings.manual_override)

    def turned_off(self, entity_id: str) -> None:
        """Off: the pause is over, the next turn-on gets the brightness of the moment."""
        self.targets.pop(entity_id, None)
        self.overrides.pop(entity_id, None)

    def evaluate(
        self, now: datetime, local: datetime, elevation: float | None, room: Room, states: dict[str, LightState]
    ) -> list[Command]:
        """Commands for the lights of a room; `local`: the local date and time (naps have days)."""
        moment = phase(self.settings, local, elevation, room)
        share = day_share(elevation)
        commands = []
        for light in room.lights:
            entity_id = light.entity_id
            state = states.get(entity_id)
            if state is None or not state.on:
                if state is not None and state.on is False:
                    self.turned_off(entity_id)
                continue
            if (until := self.overrides.get(entity_id)) is not None:
                if until > now:
                    continue
                del self.overrides[entity_id]
            wanted = target(light, moment, share, state)
            if wanted is None:
                continue
            # Compared with what was sent, not with the state: a light in its transition is not sent again.
            first = entity_id not in self.targets
            if not first and not _differs(wanted, self.targets[entity_id]):
                continue
            data: dict[str, Any] = {"brightness_pct": wanted.brightness}
            if wanted.kelvin is not None:
                data["color_temp_kelvin"] = wanted.kelvin
            # Just turned on: at once (no fade from its last brightness); then gradually.
            data["transition"] = 1 if first else self.settings.transition
            self.targets[entity_id] = wanted
            commands.append(Command(entity_id, "light", "turn_on", data, target=wanted.label(), device=entity_id))
        return commands


def _differs(wanted: LightTarget, sent: LightTarget) -> bool:
    if abs(sent.brightness - wanted.brightness) >= LIGHT_STEP:
        return True
    if (wanted.kelvin is None) != (sent.kelvin is None):
        return True
    return wanted.kelvin is not None and sent.kelvin is not None and abs(sent.kelvin - wanted.kelvin) >= KELVIN_STEP
