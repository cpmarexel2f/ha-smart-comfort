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
    colored: bool = False  # Supports RGB colors.
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


class PresenceController:
    """Lights turned on with presence and off after a while without it, per room.

    A light is turned on only when none of the room's presence lights is on (one turned on by hand is left as
    it is), the room is dark enough (light level sensor) and no slot keeps it off; a night light only at night
    and during the naps. A presence light turned off by hand while someone is there is not turned back on
    until the presence ends.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.last_seen: dict[str, datetime] = {}
        self.suppressed: set[str] = set()
        # Since when someone is in the room (for on_after).
        self.present_since: dict[str, datetime] = {}

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        rooms = {r.id for r in settings.rooms if r.presence}
        self.last_seen = {k: v for k, v in self.last_seen.items() if k in rooms}
        self.suppressed &= rooms
        self.present_since = {k: v for k, v in self.present_since.items() if k in rooms}

    def kept(self, room: Room, occupied: set[str]) -> frozenset[str]:
        """Presence lights of the room that another room with someone in it also has: theirs too."""
        mine = set(room.presence_lights())
        return frozenset(
            e
            for r in self.settings.rooms
            if r.id != room.id and r.id in occupied
            for e in r.presence_lights()
            if e in mine
        )

    def turned_off_by_hand(self, room: Room) -> None:
        """A presence light turned off by hand while someone is there: not turned back on before they leave."""
        self.suppressed.add(room.id)

    def evaluate(
        self,
        now: datetime,
        local: datetime,
        elevation: float | None,
        room: Room,
        present: bool | None,
        lux: float | None,
        states: dict[str, LightState],
        lights: LightController,
        adaptive: bool = True,
        kept: frozenset[str] = frozenset(),
    ) -> list[Command]:
        """Commands for the presence lights of a room; `adaptive`: give them the brightness of the moment.

        `kept`: lights shared with another room where someone is (the hallway's, from the entrance and the
        hallway): not turned off, and not counted as turned on by hand.
        """
        p = room.presence
        if p is None or present is None:
            return []
        managed = room.presence_lights()
        if not present:
            self.present_since.pop(room.id, None)
            seen = self.last_seen.setdefault(room.id, now)
            if now - seen < timedelta(minutes=p.off_after):
                return []
            self.suppressed.discard(room.id)
            off = {"transition": p.transition} if p.transition else {}
            return [
                Command(e, "light", "turn_off", dict(off), target="off", device=e)
                for e in managed
                if e not in kept and (s := states.get(e)) is not None and s.on
            ]
        self.last_seen[room.id] = now
        since = self.present_since.setdefault(room.id, now)
        if now - since < timedelta(seconds=p.on_after):
            return []  # A presence that doesn't last (someone passing by the sensor): nothing yet.
        own = [e for e in managed if e not in kept]
        if room.id in self.suppressed or any((s := states.get(e)) is not None and s.on for e in own):
            return []
        if p.max_lux is not None and lux is not None and lux > p.max_lux:
            return []
        moment = phase(self.settings, local, elevation, room)
        napping = any(r.napping(local) for r in self.settings.rooms)
        devices = {light.entity_id: light for light in room.lights}
        commands = []
        for entity_id in managed:
            state = states.get(entity_id)
            if state is None or state.on or (napping and entity_id in p.not_during_naps):
                continue
            slot = p.slot(entity_id, local)
            if slot is not None and slot.off:
                continue
            device = devices.get(entity_id)
            dark = moment in (PHASE_NIGHT, PHASE_NAP)
            if device is not None and device.night_only and not dark:
                continue
            data: dict[str, Any] = {"transition": p.transition or 1}
            wanted = None
            if slot is not None and slot.brightness is not None and state.dimmable:
                data["brightness_pct"] = slot.brightness
                # A set brightness: the adaptive lighting leaves the light alone until it is turned off.
                lights.overrides[entity_id] = now + timedelta(days=1)
            elif device is not None and adaptive:
                wanted = target(device, moment, day_share(elevation), state)
                if wanted is not None:
                    data["brightness_pct"] = wanted.brightness
                    if wanted.kelvin is not None:
                        data["color_temp_kelvin"] = wanted.kelvin
                    lights.targets[entity_id] = wanted
            if slot is not None and slot.color is not None and state.colored:
                data["rgb_color"] = list(slot.color)
                data.pop("color_temp_kelvin", None)
                # A set color: the adaptive lighting leaves the light alone until it is turned off.
                lights.overrides[entity_id] = now + timedelta(days=1)
                lights.targets.pop(entity_id, None)
            commands.append(Command(entity_id, "light", "turn_on", data, target="presence", device=entity_id))
        return commands
