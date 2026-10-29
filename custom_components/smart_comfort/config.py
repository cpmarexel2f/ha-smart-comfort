"""Typed settings built from the options dict (the YAML or the config entry options), defaults merged.

Pure Python: no Home Assistant import, so the engine and its tests stay independent of it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import time
from typing import Any

from .const import (
    CONF_ALERTS,
    CONF_CLEAR_WHEN_RESOLVED,
    CONF_CLIMATE,
    CONF_CLOSED_FOR,
    CONF_CLOSED_MODE,
    CONF_CLOSED_PRESET,
    CONF_CO2,
    CONF_CONTROL,
    CONF_COOL_ABOVE,
    CONF_CRITICAL_VOLUME,
    CONF_DELAY,
    CONF_DIGEST_WINDOW,
    CONF_ENABLED,
    CONF_END,
    CONF_ENTITY_ID,
    CONF_ESCALATION,
    CONF_FAN_MODE,
    CONF_FANS,
    CONF_HUMIDITY,
    CONF_HYSTERESIS,
    CONF_KEEP_ON,
    CONF_MANUAL_OVERRIDE,
    CONF_MAX_OUTDOOR,
    CONF_MIN_INDOOR,
    CONF_MIN_OUTDOOR,
    CONF_MODE_SELECT,
    CONF_NAME,
    CONF_NOTIFY,
    CONF_OFF_BELOW,
    CONF_OFF_ON_OPEN,
    CONF_OFF_PRESET,
    CONF_ON_ABOVE,
    CONF_OPEN_MODE,
    CONF_OPEN_PERCENTAGE,
    CONF_OPEN_PRESET,
    CONF_OPENINGS,
    CONF_OUTDOOR,
    CONF_OUTDOOR_AGGREGATE,
    CONF_PERCENTAGE,
    CONF_PRESENCE,
    CONF_PRESET,
    CONF_PURIFIERS,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REMINDER,
    CONF_ROOMS,
    CONF_SETPOINT,
    CONF_SEVERITY,
    CONF_SNOOZE_DURATION,
    CONF_START,
    CONF_STARTUP_GRACE,
    CONF_SUPPRESS_HANDLED,
    CONF_TAG,
    CONF_TEMPERATURE,
    CONF_THRESHOLD,
    CONF_URL,
    DEFAULT_ALERTS,
    DEFAULT_CONTROL,
    DEFAULT_CRITICAL_VOLUME,
    DEFAULT_DIGEST_WINDOW,
    DEFAULT_REMINDER,
    DEFAULT_SNOOZE,
    DEFAULT_STARTUP_GRACE,
    DEFAULT_TAG,
    KINDS,
    SEVERITY_INFO,
)


def slugify(text: str) -> str:
    """ASCII, lowercase, underscores: "Chambre Léa" -> "chambre_lea"."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_") or "room"


def parse_time(value: Any) -> time | None:
    """ "22:00", "22:00:00" or a time; None or "" for unset."""
    if value in (None, ""):
        return None
    if isinstance(value, time):
        return value
    parts = [int(p) for p in str(value).split(":")]
    if not 2 <= len(parts) <= 3:
        raise ValueError(f"Invalid time: {value}")
    return time(*parts)


def in_window(now: time, start: time | None, end: time | None) -> bool:
    """Whether now is in [start, end), the window may cross midnight. Unset or equal bounds: always."""
    if start is None or end is None or start == end:
        return True
    if start < end:
        return start <= now < end
    return now >= start or now < end


def _merge(base: dict[str, Any], *overrides: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base)
    for override in overrides:
        if override:
            merged.update({k: v for k, v in override.items() if k in base})
    return merged


def _float(value: Any) -> float | None:
    return None if value is None else float(value)


@dataclass(frozen=True)
class AlertSettings:
    """One alert kind for one room."""

    enabled: bool
    severity: str = SEVERITY_INFO
    threshold: float | None = None
    hysteresis: float = 0.0
    delay: int = 0
    escalation: float = 0.0
    min_outdoor: float | None = None
    max_outdoor: float | None = None
    min_indoor: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertSettings:
        return cls(
            enabled=bool(data.get(CONF_ENABLED, True)),
            severity=str(data.get(CONF_SEVERITY, SEVERITY_INFO)),
            threshold=_float(data.get(CONF_THRESHOLD)),
            hysteresis=float(data.get(CONF_HYSTERESIS) or 0),
            delay=int(data.get(CONF_DELAY) or 0),
            escalation=float(data.get(CONF_ESCALATION) or 0),
            min_outdoor=_float(data.get(CONF_MIN_OUTDOOR)),
            max_outdoor=_float(data.get(CONF_MAX_OUTDOOR)),
            min_indoor=_float(data.get(CONF_MIN_INDOOR)),
        )


@dataclass(frozen=True)
class ClimateDevice:
    entity_id: str
    cool_above: float
    off_below: float
    setpoint: float
    fan_mode: str | None
    closed_for: int
    off_on_open: int


@dataclass(frozen=True)
class FanDevice:
    entity_id: str
    on_above: float | None
    off_below: float | None
    percentage: int | None
    preset: str | None
    open_percentage: int | None
    open_preset: str | None
    off_preset: str | None


@dataclass(frozen=True)
class PurifierDevice:
    entity_id: str
    open_percentage: int | None
    open_preset: str | None
    closed_preset: str | None
    mode_select: str | None
    open_mode: str | None
    closed_mode: str | None
    keep_on: bool


def _device_items(raw: Any) -> list[tuple[str, dict[str, Any]]]:
    """A device list item is an entity id or a dict with entity_id and per-device overrides."""
    if raw is None:
        return []
    if isinstance(raw, (str, dict)):
        raw = [raw]
    items = []
    for item in raw:
        if isinstance(item, str):
            items.append((item, {}))
        else:
            items.append((str(item[CONF_ENTITY_ID]), dict(item)))
    return items


def _int(value: Any) -> int | None:
    return None if value is None else int(value)


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    temperature: str | None = None
    co2: str | None = None
    humidity: str | None = None
    openings: tuple[str, ...] = ()
    climate: ClimateDevice | None = None
    fans: tuple[FanDevice, ...] = ()
    purifiers: tuple[PurifierDevice, ...] = ()
    alerts: dict[str, AlertSettings] = field(default_factory=dict)

    @property
    def devices(self) -> list[str]:
        devices = [self.climate.entity_id] if self.climate else []
        return devices + [f.entity_id for f in self.fans] + [p.entity_id for p in self.purifiers]

    @property
    def sensors(self) -> list[str]:
        return [e for e in (self.temperature, self.co2, self.humidity) if e] + list(self.openings)


@dataclass(frozen=True)
class Settings:
    notify: tuple[str, ...] = ()
    outdoor: tuple[str, ...] = ()
    aggregate: str = "min"
    digest_window: int = DEFAULT_DIGEST_WINDOW
    startup_grace: int = DEFAULT_STARTUP_GRACE
    reminder: int = DEFAULT_REMINDER
    snooze: int = DEFAULT_SNOOZE
    quiet_start: time | None = None
    quiet_end: time | None = None
    presence: str | None = None
    clear_when_resolved: bool = True
    critical_volume: float = DEFAULT_CRITICAL_VOLUME
    url: str | None = None
    tag: str = DEFAULT_TAG
    control_enabled: bool = True
    control_start: time | None = None
    control_end: time | None = None
    manual_override: int = 60
    suppress_handled: bool = True
    rooms: tuple[Room, ...] = ()

    def room(self, room_id: str) -> Room | None:
        return next((r for r in self.rooms if r.id == room_id), None)


def _room(raw: dict[str, Any], alerts: dict[str, dict], control: dict[str, Any], used: set[str]) -> Room:
    name = str(raw[CONF_NAME])
    room_id = base = str(raw.get("id") or slugify(name))
    n = 2
    while room_id in used:
        room_id, n = f"{base}_{n}", n + 1
    used.add(room_id)
    room_alerts = raw.get(CONF_ALERTS) or {}
    room_control = raw.get(CONF_CONTROL) or {}

    climate = None
    if items := _device_items(raw.get(CONF_CLIMATE)):
        entity_id, own = items[0]
        c = _merge(control[CONF_CLIMATE], room_control.get(CONF_CLIMATE), own)
        climate = ClimateDevice(
            entity_id=entity_id,
            cool_above=float(c[CONF_COOL_ABOVE]),
            off_below=float(c[CONF_OFF_BELOW]),
            setpoint=float(c[CONF_SETPOINT]),
            fan_mode=c[CONF_FAN_MODE],
            closed_for=int(c[CONF_CLOSED_FOR]),
            off_on_open=int(c[CONF_OFF_ON_OPEN]),
        )
    fans = []
    for entity_id, own in _device_items(raw.get(CONF_FANS)):
        f = _merge(control[CONF_FANS], room_control.get(CONF_FANS), own)
        fans.append(
            FanDevice(
                entity_id=entity_id,
                on_above=_float(f[CONF_ON_ABOVE]),
                off_below=_float(f[CONF_OFF_BELOW]),
                percentage=_int(f[CONF_PERCENTAGE]),
                preset=f[CONF_PRESET],
                open_percentage=_int(f[CONF_OPEN_PERCENTAGE]),
                open_preset=f[CONF_OPEN_PRESET],
                off_preset=f[CONF_OFF_PRESET],
            )
        )
    purifiers = []
    for entity_id, own in _device_items(raw.get(CONF_PURIFIERS)):
        p = _merge(control[CONF_PURIFIERS], room_control.get(CONF_PURIFIERS), own)
        purifiers.append(
            PurifierDevice(
                entity_id=entity_id,
                open_percentage=_int(p[CONF_OPEN_PERCENTAGE]),
                open_preset=p[CONF_OPEN_PRESET],
                closed_preset=p[CONF_CLOSED_PRESET],
                mode_select=p[CONF_MODE_SELECT],
                open_mode=p[CONF_OPEN_MODE],
                closed_mode=p[CONF_CLOSED_MODE],
                keep_on=bool(p[CONF_KEEP_ON]),
            )
        )
    openings = raw.get(CONF_OPENINGS) or []
    return Room(
        id=room_id,
        name=name,
        temperature=raw.get(CONF_TEMPERATURE) or None,
        co2=raw.get(CONF_CO2) or None,
        humidity=raw.get(CONF_HUMIDITY) or None,
        openings=tuple([openings] if isinstance(openings, str) else openings),
        climate=climate,
        fans=tuple(fans),
        purifiers=tuple(purifiers),
        alerts={kind: AlertSettings.from_dict(_merge(alerts[kind], room_alerts.get(kind))) for kind in KINDS},
    )


def build_settings(options: dict[str, Any]) -> Settings:
    """Settings from the options, every missing value taken from the defaults."""
    alerts = {kind: _merge(DEFAULT_ALERTS[kind], (options.get(CONF_ALERTS) or {}).get(kind)) for kind in KINDS}
    raw_control = options.get(CONF_CONTROL) or {}
    control = _merge(DEFAULT_CONTROL, raw_control)
    for section in (CONF_CLIMATE, CONF_FANS, CONF_PURIFIERS):
        control[section] = _merge(DEFAULT_CONTROL[section], raw_control.get(section))
    used: set[str] = set()
    rooms = tuple(_room(r, alerts, control, used) for r in options.get(CONF_ROOMS) or [])
    notify = options.get(CONF_NOTIFY) or []
    outdoor = options.get(CONF_OUTDOOR) or []
    return Settings(
        notify=tuple(f"notify.{n.removeprefix('notify.')}" for n in ([notify] if isinstance(notify, str) else notify)),
        outdoor=tuple([outdoor] if isinstance(outdoor, str) else outdoor),
        aggregate=str(options.get(CONF_OUTDOOR_AGGREGATE) or "min"),
        digest_window=int(options.get(CONF_DIGEST_WINDOW, DEFAULT_DIGEST_WINDOW)),
        startup_grace=int(options.get(CONF_STARTUP_GRACE, DEFAULT_STARTUP_GRACE)),
        reminder=int(options.get(CONF_REMINDER, DEFAULT_REMINDER)),
        snooze=int(options.get(CONF_SNOOZE_DURATION, DEFAULT_SNOOZE)),
        quiet_start=parse_time(options.get(CONF_QUIET_START)),
        quiet_end=parse_time(options.get(CONF_QUIET_END)),
        presence=options.get(CONF_PRESENCE) or None,
        clear_when_resolved=bool(options.get(CONF_CLEAR_WHEN_RESOLVED, True)),
        critical_volume=float(options.get(CONF_CRITICAL_VOLUME, DEFAULT_CRITICAL_VOLUME)),
        url=options.get(CONF_URL) or None,
        tag=str(options.get(CONF_TAG) or DEFAULT_TAG),
        control_enabled=bool(control[CONF_ENABLED]),
        control_start=parse_time(control[CONF_START]),
        control_end=parse_time(control[CONF_END]),
        manual_override=int(control[CONF_MANUAL_OVERRIDE]),
        suppress_handled=bool(control[CONF_SUPPRESS_HANDLED]),
        rooms=rooms,
    )
