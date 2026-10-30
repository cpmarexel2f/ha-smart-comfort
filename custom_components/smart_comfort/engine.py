"""Alert engine: episodes with delay and hysteresis, reminders, escalation, snoozes and digests.

Pure Python, driven by `evaluate()` with readings and `step()` with the gates of the moment.
An episode is one problem of one room (room + kind). It starts pending when its condition becomes
true, becomes active once the condition has held for the delay, and ends when the condition is
false beyond the hysteresis. Unknown readings (unavailable sensors) leave it as it is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .config import AlertSettings, Room, Settings
from .const import (
    KIND_CLOSE_WINDOWS,
    KIND_CO2,
    KIND_HUMIDITY,
    KIND_NOISE,
    KIND_NOISY_OUTSIDE,
    KIND_TOO_COLD,
    KIND_TOO_HOT,
    KIND_VENTILATE,
    KIND_WINDOW_OPEN_COLD,
    KINDS,
    SEVERITIES,
    SEVERITY_CRITICAL,
)

REASON_NEW = "new"
REASON_REMINDER = "reminder"
REASON_WORSE = "worse"
REASON_ONGOING = "ongoing"

# Kinds a running air conditioner or fan takes care of: not notified when suppress_when_handled.
HANDLED_KINDS = frozenset({KIND_TOO_HOT})
# Kinds that need the outdoor temperature.
OUTDOOR_KINDS = frozenset({KIND_VENTILATE, KIND_CLOSE_WINDOWS, KIND_WINDOW_OPEN_COLD})
# Kinds that need the outdoor noise.
NOISE_OUTDOOR_KINDS = frozenset({KIND_NOISY_OUTSIDE})
# Readings each kind is computed from (RoomReading field names, "outdoor" for the outdoor temperature,
# "outdoor_noise" for the outdoor noise).
SOURCES: dict[str, tuple[str, ...]] = {
    KIND_TOO_HOT: ("temperature",),
    KIND_TOO_COLD: ("temperature",),
    KIND_VENTILATE: ("temperature", "outdoor"),
    KIND_CLOSE_WINDOWS: ("temperature", "outdoor"),
    KIND_WINDOW_OPEN_COLD: ("outdoor",),
    KIND_CO2: ("co2",),
    KIND_HUMIDITY: ("humidity",),
    KIND_NOISE: ("noise",),
    KIND_NOISY_OUTSIDE: ("outdoor_noise",),
}
GLOBAL_SOURCES = frozenset({"outdoor", "outdoor_noise"})
# Kinds whose value gets worse when it goes down.
DOWNWARD_KINDS = frozenset({KIND_TOO_COLD, KIND_WINDOW_OPEN_COLD})


@dataclass
class RoomReading:
    """What a room looks like right now. None: unknown (no sensor, or unavailable)."""

    temperature: float | None = None
    co2: float | None = None
    humidity: float | None = None
    noise: float | None = None
    # Outdoor noise level (same for every room), None when unknown or without a sensor.
    outdoor_noise: float | None = None
    # Names of the openings that are open; None when one of them is unknown.
    open: list[str] | None = field(default_factory=list)
    has_openings: bool = False
    # A fan or air conditioner of the room is working on it.
    handled: bool = False
    # Readings (field names) whose entity no longer exists: their problems end instead of holding.
    missing: frozenset[str] = frozenset()

    @property
    def any_open(self) -> bool | None:
        return None if self.open is None else bool(self.open)


@dataclass
class Check:
    """Result of a condition: state True/False, or None when it can't be told."""

    state: bool | None
    value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


def _above(value: float | None, threshold: float | None, hysteresis: float) -> bool | None:
    if value is None or threshold is None:
        return None
    return value > threshold - hysteresis


def _below(value: float | None, threshold: float | None, hysteresis: float) -> bool | None:
    if value is None or threshold is None:
        return None
    return value < threshold + hysteresis


def check(kind: str, s: AlertSettings, r: RoomReading, outdoor: float | None, active: bool) -> Check:
    """Evaluate one condition. `active`: the episode exists, hysteresis applies."""
    h = s.hysteresis if active else 0.0
    if kind == KIND_TOO_HOT:
        return Check(_above(r.temperature, s.threshold, h), r.temperature, {"threshold": s.threshold})
    if kind == KIND_TOO_COLD:
        return Check(_below(r.temperature, s.threshold, h), r.temperature, {"threshold": s.threshold})
    if kind == KIND_CO2:
        return Check(_above(r.co2, s.threshold, h), r.co2, {"threshold": s.threshold})
    if kind == KIND_HUMIDITY:
        return Check(_above(r.humidity, s.threshold, h), r.humidity, {"threshold": s.threshold})
    if kind == KIND_NOISE:
        return Check(_above(r.noise, s.threshold, h), r.noise, {"threshold": s.threshold})
    if kind == KIND_NOISY_OUTSIDE:
        if not r.has_openings:
            return Check(False)
        if r.outdoor_noise is None or r.any_open is None or s.threshold is None:
            return Check(None)
        details = {"outdoor_noise": r.outdoor_noise, "openings": list(r.open or [])}
        return Check(bool(r.any_open) and r.outdoor_noise > s.threshold - h, r.outdoor_noise, details)
    if kind == KIND_VENTILATE:
        if r.temperature is None or outdoor is None or s.threshold is None:
            return Check(None)
        diff = r.temperature - outdoor
        details = {"outdoor": outdoor, "temperature": r.temperature}
        if r.has_openings:
            if r.any_open is None:
                return Check(None, diff, details)
            if r.any_open:  # Already aired.
                return Check(False, diff, details)
        warm = s.min_indoor is None or r.temperature >= s.min_indoor - h
        # Not when it is too noisy outside to open (unknown noise: no objection).
        noisy = s.max_noise is not None and r.outdoor_noise is not None and r.outdoor_noise > s.max_noise
        return Check(warm and not noisy and diff >= s.threshold - h, diff, details)
    if kind == KIND_CLOSE_WINDOWS:
        if not r.has_openings:
            return Check(False)
        if r.temperature is None or outdoor is None or r.any_open is None or s.threshold is None:
            return Check(None)
        diff = outdoor - r.temperature
        details = {"outdoor": outdoor, "temperature": r.temperature, "openings": list(r.open or [])}
        hot = s.min_outdoor is None or outdoor >= s.min_outdoor - h
        return Check(bool(r.any_open) and hot and diff >= s.threshold - h, diff, details)
    if kind == KIND_WINDOW_OPEN_COLD:
        if not r.has_openings:
            return Check(False)
        if outdoor is None or r.any_open is None:
            return Check(None)
        details = {"outdoor": outdoor, "openings": list(r.open or [])}
        cold = s.max_outdoor is None or outdoor <= s.max_outdoor + h
        return Check(bool(r.any_open) and cold, outdoor, details)
    raise ValueError(kind)


def worsening(kind: str, value: float | None, previous: float | None) -> float:
    """How much worse value is than previous, in the unit of the kind (0 when better or unknown)."""
    if value is None or previous is None:
        return 0.0
    return max(0.0, previous - value if kind in DOWNWARD_KINDS else value - previous)


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass
class Episode:
    room: str
    kind: str
    since: datetime
    value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    active: bool = False
    notified_at: datetime | None = None
    notified_value: float | None = None
    acknowledged: bool = False
    snoozed_until: datetime | None = None

    @property
    def key(self) -> str:
        return f"{self.room}|{self.kind}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "room": self.room,
            "kind": self.kind,
            "since": _iso(self.since),
            "value": self.value,
            "details": self.details,
            "active": self.active,
            "notified_at": _iso(self.notified_at),
            "notified_value": self.notified_value,
            "acknowledged": self.acknowledged,
            "snoozed_until": _iso(self.snoozed_until),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        return cls(
            room=data["room"],
            kind=data["kind"],
            since=datetime.fromisoformat(data["since"]),
            value=data.get("value"),
            details=data.get("details") or {},
            active=bool(data.get("active")),
            notified_at=_dt(data.get("notified_at")),
            notified_value=data.get("notified_value"),
            acknowledged=bool(data.get("acknowledged")),
            snoozed_until=_dt(data.get("snoozed_until")),
        )


@dataclass
class Gates:
    """What may be sent right now."""

    enabled: bool = True
    # During the startup grace period nothing is sent.
    starting: bool = False
    # Quiet hours or nobody home: only critical alerts go out, the rest waits.
    hold: bool = False


@dataclass
class Item:
    episode: Episode
    room_name: str
    severity: str
    reason: str


@dataclass
class Digest:
    items: list[Item]
    severity: str

    @property
    def keys(self) -> list[str]:
        return [i.episode.key for i in self.items]


@dataclass
class Clear:
    """Every notified problem is over: clear the notification."""


def _severity_rank(severity: str) -> int:
    return SEVERITIES.index(severity) if severity in SEVERITIES else 0


class Engine:
    """Episodes of every room and kind, and what to send about them."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.episodes: dict[str, Episode] = {}
        # Snoozes by room id, "*" for every room.
        self.snoozes: dict[str, datetime] = {}
        self.batch_started: datetime | None = None
        # Notified problems are on screen: a Clear is due once none is left.
        self.shown = False
        # Episode keys of the last notification sent, for its Snooze / Got it buttons.
        self.last_keys: list[str] | None = None

    # Settings and persistence.

    def update_settings(self, settings: Settings) -> None:
        """New settings: episodes of removed rooms, disabled kinds or removed sensors go away."""
        self.settings = settings
        for key, ep in list(self.episodes.items()):
            room = settings.room(ep.room)
            if room is None or not room.alerts[ep.kind].enabled or not self._has_sources(room, ep.kind):
                del self.episodes[key]
        if self.last_keys is not None:
            self.last_keys = [k for k in self.last_keys if k in self.episodes]

    def _has_sources(self, room: Room, kind: str) -> bool:
        """The room still has the sensors the kind is computed from."""
        if kind in OUTDOOR_KINDS and not self.settings.outdoor:
            return False
        if kind in NOISE_OUTDOOR_KINDS and not self.settings.outdoor_noise:
            return False
        if kind in (KIND_CLOSE_WINDOWS, KIND_WINDOW_OPEN_COLD, KIND_NOISY_OUTSIDE) and not room.openings:
            return False
        return all(getattr(room, field) for field in SOURCES[kind] if field not in GLOBAL_SOURCES)

    def as_dict(self) -> dict[str, Any]:
        return {
            "episodes": [e.as_dict() for e in self.episodes.values()],
            "snoozes": {k: v.isoformat() for k, v in self.snoozes.items()},
            "shown": self.shown,
            "last_keys": self.last_keys,
        }

    def restore(self, data: dict[str, Any]) -> None:
        for raw in data.get("episodes") or []:
            try:
                ep = Episode.from_dict(raw)
            except (KeyError, TypeError, ValueError):
                continue
            if ep.kind in KINDS:
                self.episodes[ep.key] = ep
        for room, until in (data.get("snoozes") or {}).items():
            try:
                self.snoozes[room] = datetime.fromisoformat(until)
            except (TypeError, ValueError):
                continue
        self.shown = bool(data.get("shown"))
        if isinstance(last_keys := data.get("last_keys"), list):
            self.last_keys = [str(k) for k in last_keys]
        self.update_settings(self.settings)

    # Evaluation.

    def evaluate(self, now: datetime, readings: dict[str, RoomReading], outdoor: float | None) -> None:
        """Update the episodes from the readings."""
        for room in self.settings.rooms:
            reading = readings.get(room.id)
            if reading is None:
                continue
            for kind in KINDS:
                s = room.alerts[kind]
                key = f"{room.id}|{kind}"
                ep = self.episodes.get(key)
                if not s.enabled:
                    continue
                result = check(kind, s, reading, outdoor, ep is not None)
                if result.state is None:
                    # Unknown: the episode holds, unless its sensor is gone for good.
                    if ep is not None and reading.missing.intersection(SOURCES[kind]):
                        del self.episodes[key]
                    continue
                if not result.state:
                    self.episodes.pop(key, None)
                    continue
                if ep is None:
                    ep = self.episodes[key] = Episode(room.id, kind, now)
                ep.value, ep.details = result.value, result.details
                if not ep.active and now - ep.since >= timedelta(minutes=s.delay):
                    ep.active = True
        self.snoozes = {k: v for k, v in self.snoozes.items() if v > now}

    # Queries.

    def snoozed(self, ep: Episode, now: datetime) -> bool:
        until = [ep.snoozed_until, self.snoozes.get(ep.room), self.snoozes.get("*")]
        return any(u is not None and u > now for u in until)

    def suppressed(self, ep: Episode, room: Room, handled: set[str]) -> bool:
        return self.settings.suppress_handled and ep.kind in HANDLED_KINDS and room.id in handled

    def active(self) -> list[Episode]:
        order = {k: i for i, k in enumerate(KINDS)}
        rooms = {r.id: i for i, r in enumerate(self.settings.rooms)}
        return sorted(
            (e for e in self.episodes.values() if e.active),
            key=lambda e: (rooms.get(e.room, 99), order.get(e.kind, 99)),
        )

    def _reason(self, ep: Episode, s: AlertSettings, now: datetime) -> str | None:
        """Why the episode has to be (re)notified now, None if it doesn't."""
        if ep.notified_at is None:
            return REASON_NEW
        if ep.acknowledged:
            return None
        if ep.snoozed_until is not None and ep.notified_at < ep.snoozed_until <= now:
            # Snooze over while the problem goes on: its notification was cleared, notify it again.
            return REASON_REMINDER
        if s.escalation > 0 and worsening(ep.kind, ep.value, ep.notified_value) >= s.escalation:
            return REASON_WORSE
        reminder = self.settings.reminder
        if reminder > 0 and now - ep.notified_at >= timedelta(minutes=reminder):
            return REASON_REMINDER
        return None

    def visible(self, now: datetime, handled: set[str]) -> list[tuple[Episode, Room]]:
        out = []
        for ep in self.active():
            room = self.settings.room(ep.room)
            if room is None or self.snoozed(ep, now) or self.suppressed(ep, room, handled):
                continue
            out.append((ep, room))
        return out

    # Sending.

    def step(self, now: datetime, gates: Gates, handled: set[str]) -> Digest | Clear | None:
        """What to send now, if anything. The caller sends it, then marks a digest with `sent()`."""
        visible = self.visible(now, handled)
        if self.shown and not any(ep.notified_at for ep, _ in visible):
            self.shown = False
            self.batch_started = None
            return Clear() if self.settings.clear_when_resolved else None

        due: dict[str, str] = {}
        for ep, room in visible:
            if (reason := self._reason(ep, room.alerts[ep.kind], now)) is not None:
                due[ep.key] = reason
        if not due:
            self.batch_started = None
            return None
        if not gates.enabled or gates.starting:
            return None

        def sendable(ep: Episode, room: Room) -> bool:
            return not gates.hold or room.alerts[ep.kind].severity == SEVERITY_CRITICAL

        due_now = [(ep, room) for ep, room in visible if ep.key in due and sendable(ep, room)]
        if not due_now:
            return None
        if self.batch_started is None:
            self.batch_started = now
        urgent = any(room.alerts[ep.kind].severity == SEVERITY_CRITICAL for ep, room in due_now)
        if not urgent and now - self.batch_started < timedelta(minutes=self.settings.digest_window):
            return None
        return self._digest([(ep, room) for ep, room in visible if sendable(ep, room)], due)

    def _digest(self, items: list[tuple[Episode, Room]], due: dict[str, str]) -> Digest:
        out = [
            Item(ep, room.name, room.alerts[ep.kind].severity, due.get(ep.key, REASON_ONGOING)) for ep, room in items
        ]
        changed = [i.severity for i in out if i.reason != REASON_ONGOING] or [i.severity for i in out]
        return Digest(out, max(changed, key=_severity_rank))

    def sent(self, digest: Digest, now: datetime) -> None:
        """The digest went out: its episodes are notified. Not called when it could not be sent."""
        self.batch_started = None
        self.shown = True
        for item in digest.items:
            item.episode.notified_at, item.episode.notified_value = now, item.episode.value
        self.last_keys = digest.keys

    def summary(self, now: datetime, handled: set[str]) -> Digest | None:
        """Every visible problem, for "notify now": ignores the gates and the digest window."""
        visible = self.visible(now, handled)
        if not visible:
            return None
        due = {ep.key: (self._reason(ep, room.alerts[ep.kind], now) or REASON_ONGOING) for ep, room in visible}
        return self._digest(visible, due)

    # User actions.

    def _select(self, rooms: list[str] | None, kinds: list[str] | None, keys: list[str] | None) -> list[Episode]:
        return [
            e
            for e in self.episodes.values()
            if (rooms is None or e.room in rooms)
            and (kinds is None or e.kind in kinds)
            and (keys is None or e.key in keys)
        ]

    def snooze(
        self,
        now: datetime,
        minutes: int,
        rooms: list[str] | None = None,
        kinds: list[str] | None = None,
        keys: list[str] | None = None,
    ) -> int:
        """Snooze episodes. Without kinds nor keys, also the problems that come up meanwhile."""
        until = now + timedelta(minutes=minutes)
        if kinds is None and keys is None:
            for room in rooms or ["*"]:
                self.snoozes[room] = until
        selected = self._select(rooms, kinds, keys)
        for ep in selected:
            ep.snoozed_until = until
        return len(selected)

    def unsnooze(self, now: datetime, rooms: list[str] | None = None) -> None:
        if rooms is None:
            self.snoozes.clear()
        else:
            for room in rooms:
                self.snoozes.pop(room, None)
        for ep in self._select(rooms, None, None):
            # Ended now rather than forgotten, so that a problem notified before the snooze is notified again.
            if ep.snoozed_until is not None and ep.snoozed_until > now:
                ep.snoozed_until = now

    def acknowledge(
        self, rooms: list[str] | None = None, kinds: list[str] | None = None, keys: list[str] | None = None
    ) -> int:
        """No reminder nor escalation for these episodes until they end."""
        selected = self._select(rooms, kinds, keys)
        for ep in selected:
            ep.acknowledged = True
        return len(selected)
