"""Typed settings built from the options dict (the YAML or the config entry options), defaults merged.

Pure Python: no Home Assistant import, so the engine and its tests stay independent of it.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from .const import (
    CONF_AIR_QUALITY,
    CONF_ALERTS,
    CONF_AREA,
    CONF_CLEAR_WHEN_RESOLVED,
    CONF_CLIMATE,
    CONF_CLOSED_FOR,
    CONF_CLOSED_MODE,
    CONF_CLOSED_PRESET,
    CONF_CO2,
    CONF_CONTROL,
    CONF_COOL_ABOVE,
    CONF_CRITICAL_VOLUME,
    CONF_DAY,
    CONF_DAY_KELVIN,
    CONF_DAYS,
    CONF_DELAY,
    CONF_DIGEST_WINDOW,
    CONF_ENABLED,
    CONF_END,
    CONF_ENTITY_ID,
    CONF_ESCALATION,
    CONF_EVENING,
    CONF_EVENING_KELVIN,
    CONF_FAN_MODE,
    CONF_FANS,
    CONF_HUMIDITY,
    CONF_HYSTERESIS,
    CONF_KEEP_ON,
    CONF_LIGHTING,
    CONF_LIGHTS,
    CONF_MANUAL_OVERRIDE,
    CONF_MAX_AIR,
    CONF_MAX_NOISE,
    CONF_MAX_OUTDOOR,
    CONF_MIN_INDOOR,
    CONF_MIN_OUTDOOR,
    CONF_MODE_SELECT,
    CONF_MORNING,
    CONF_MORNING_END,
    CONF_MORNING_KELVIN,
    CONF_NAME,
    CONF_NAP,
    CONF_NAP_KELVIN,
    CONF_NAPS,
    CONF_NIGHT,
    CONF_NIGHT_END,
    CONF_NIGHT_FAN_MODE,
    CONF_NIGHT_KELVIN,
    CONF_NIGHT_MODE,
    CONF_NIGHT_ONLY,
    CONF_NIGHT_PERCENTAGE,
    CONF_NIGHT_PRESET,
    CONF_NIGHT_START,
    CONF_NOISE,
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
    CONF_OUTDOOR_AIR,
    CONF_OUTDOOR_NOISE,
    CONF_OUTDOORS,
    CONF_PERCENTAGE,
    CONF_PRESENCE,
    CONF_PRESET,
    CONF_PURIFIERS,
    CONF_QUIET_END,
    CONF_QUIET_MORNING,
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
    CONF_TRANSITION,
    CONF_URL,
    CONF_WARMTH,
    DEFAULT_ALERTS,
    DEFAULT_CONTROL,
    DEFAULT_CRITICAL_VOLUME,
    DEFAULT_DIGEST_WINDOW,
    DEFAULT_LIGHTING,
    DEFAULT_REMINDER,
    DEFAULT_SNOOZE,
    DEFAULT_STARTUP_GRACE,
    DEFAULT_TAG,
    KINDS,
    SEVERITY_INFO,
    WEEKDAYS,
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
    max_noise: float | None = None
    max_air: float | None = None

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
            max_noise=_float(data.get(CONF_MAX_NOISE)),
            max_air=_float(data.get(CONF_MAX_AIR)),
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
    night_fan_mode: str | None = None


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
    night_percentage: int | None = None
    night_preset: str | None = None

    @property
    def quiet(self) -> bool:
        """Has night settings: quieter at night."""
        return self.night_percentage is not None or bool(self.night_preset)


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
    night_percentage: int | None = None
    night_preset: str | None = None
    night_mode: str | None = None

    @property
    def quiet(self) -> bool:
        """Has night settings: quieter at night."""
        return (
            self.night_percentage is not None or bool(self.night_preset) or bool(self.mode_select and self.night_mode)
        )


@dataclass(frozen=True)
class LightDevice:
    """A dimmable light: its brightness (%) and warmth (K) by time of day."""

    entity_id: str
    day: int = 100
    evening: int = 60
    night: int = 15
    warmth: bool = True
    day_kelvin: int = 4000
    evening_kelvin: int = 2700
    night_kelvin: int = 2200
    # A night light: set only in the night hours (and the naps).
    night_only: bool = False
    morning: int = 40
    morning_kelvin: int = 3000
    # Dimmer in the morning, until morning_end (bedrooms).
    quiet_morning: bool = False
    nap: int = 15
    nap_kelvin: int = 2200


@dataclass(frozen=True)
class Nap:
    """A nap slot of a room: its lights dimmed from start to end, on its days (every day when none)."""

    start: time
    end: time
    days: tuple[int, ...] = ()  # 0 = Monday.

    def active(self, local: datetime) -> bool:
        if self.days and local.weekday() not in self.days:
            return False
        return self.start != self.end and in_window(local.time(), self.start, self.end)


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
    noise: str | None = None
    openings: tuple[str, ...] = ()
    climate: ClimateDevice | None = None
    fans: tuple[FanDevice, ...] = ()
    purifiers: tuple[PurifierDevice, ...] = ()
    alerts: dict[str, AlertSettings] = field(default_factory=dict)
    lights: tuple[LightDevice, ...] = ()
    naps: tuple[Nap, ...] = ()

    def napping(self, local: datetime) -> bool:
        return any(nap.active(local) for nap in self.naps)

    @property
    def devices(self) -> list[str]:
        devices = [self.climate.entity_id] if self.climate else []
        return devices + [f.entity_id for f in self.fans] + [p.entity_id for p in self.purifiers]

    @property
    def sensors(self) -> list[str]:
        return [e for e in (self.temperature, self.co2, self.humidity, self.noise) if e] + list(self.openings)


@dataclass(frozen=True)
class Outdoor:
    """An outdoor place (garden, terrace…) and its sensors."""

    name: str
    area: str | None = None
    temperature: tuple[str, ...] = ()
    air_quality: tuple[str, ...] = ()
    noise: tuple[str, ...] = ()


@dataclass(frozen=True)
class Settings:
    notify: tuple[str, ...] = ()
    # Every outdoor sensor: the top-level ones and those of the outdoor places.
    outdoor: tuple[str, ...] = ()
    aggregate: str = "min"
    outdoor_noise: tuple[str, ...] = ()
    outdoor_air: tuple[str, ...] = ()
    outdoors: tuple[Outdoor, ...] = ()
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
    night_start: time | None = None
    night_end: time | None = None
    rooms: tuple[Room, ...] = ()
    lighting_enabled: bool = True
    # End of the quiet morning of the rooms that have it.
    morning_end: time | None = None
    # Seconds of the gradual brightness changes.
    transition: int = 120

    def night(self, local: time) -> bool:
        """Quiet night hours (none when either bound is unset)."""
        if self.night_start is None or self.night_end is None or self.night_start == self.night_end:
            return False
        return in_window(local, self.night_start, self.night_end)

    def morning(self, local: time) -> bool:
        """Quiet morning hours: from the end of the night (midnight without one) until morning_end."""
        if self.morning_end is None:
            return False
        start = self.night_end or time(0)
        return start != self.morning_end and in_window(local, start, self.morning_end)

    def room(self, room_id: str) -> Room | None:
        return next((r for r in self.rooms if r.id == room_id), None)


def _lights(raw: dict[str, Any], lighting: dict[str, Any]) -> tuple[LightDevice, ...]:
    """The lights of a room, each with the lighting settings merged (global < room < light)."""
    lights = []
    for entity_id, own in _device_items(raw.get(CONF_LIGHTS)):
        merged = _merge(lighting, raw.get(CONF_LIGHTING), own)
        lights.append(
            LightDevice(
                entity_id=entity_id,
                day=int(merged[CONF_DAY]),
                evening=int(merged[CONF_EVENING]),
                night=int(merged[CONF_NIGHT]),
                warmth=bool(merged[CONF_WARMTH]),
                day_kelvin=int(merged[CONF_DAY_KELVIN]),
                evening_kelvin=int(merged[CONF_EVENING_KELVIN]),
                night_kelvin=int(merged[CONF_NIGHT_KELVIN]),
                night_only=bool(own.get(CONF_NIGHT_ONLY, False)),
                morning=int(merged[CONF_MORNING]),
                morning_kelvin=int(merged[CONF_MORNING_KELVIN]),
                quiet_morning=bool(merged[CONF_QUIET_MORNING]),
                nap=int(merged[CONF_NAP]),
                nap_kelvin=int(merged[CONF_NAP_KELVIN]),
            )
        )
    return tuple(lights)


def _room(
    raw: dict[str, Any], alerts: dict[str, dict], control: dict[str, Any], used: set[str], lighting: dict[str, Any]
) -> Room:
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
            night_fan_mode=c[CONF_NIGHT_FAN_MODE] or None,
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
                night_percentage=_int(f[CONF_NIGHT_PERCENTAGE]),
                night_preset=f[CONF_NIGHT_PRESET] or None,
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
                night_percentage=_int(p[CONF_NIGHT_PERCENTAGE]),
                night_preset=p[CONF_NIGHT_PRESET] or None,
                night_mode=p[CONF_NIGHT_MODE] or None,
            )
        )
    openings = raw.get(CONF_OPENINGS) or []
    return Room(
        id=room_id,
        name=name,
        temperature=raw.get(CONF_TEMPERATURE) or None,
        co2=raw.get(CONF_CO2) or None,
        humidity=raw.get(CONF_HUMIDITY) or None,
        noise=raw.get(CONF_NOISE) or None,
        openings=tuple([openings] if isinstance(openings, str) else openings),
        climate=climate,
        fans=tuple(fans),
        purifiers=tuple(purifiers),
        lights=_lights(raw, lighting),
        naps=tuple(
            Nap(
                start=parse_time(n["start"]) or time(0),
                end=parse_time(n["end"]) or time(0),
                days=tuple(WEEKDAYS.index(d) for d in n.get(CONF_DAYS) or []),
            )
            for n in raw.get(CONF_NAPS) or []
        ),
        alerts={kind: AlertSettings.from_dict(_merge(alerts[kind], room_alerts.get(kind))) for kind in KINDS},
    )


def _ids(value: Any) -> tuple[str, ...]:
    """Entity ids of an option: one, a list, or none."""
    if not value:
        return ()
    return (value,) if isinstance(value, str) else tuple(value)


def build_settings(options: dict[str, Any]) -> Settings:
    """Settings from the options, every missing value taken from the defaults."""
    alerts = {kind: _merge(DEFAULT_ALERTS[kind], (options.get(CONF_ALERTS) or {}).get(kind)) for kind in KINDS}
    raw_control = options.get(CONF_CONTROL) or {}
    control = _merge(DEFAULT_CONTROL, raw_control)
    for section in (CONF_CLIMATE, CONF_FANS, CONF_PURIFIERS):
        control[section] = _merge(DEFAULT_CONTROL[section], raw_control.get(section))
    used: set[str] = set()
    lighting = _merge(DEFAULT_LIGHTING, options.get(CONF_LIGHTING))
    rooms = tuple(_room(r, alerts, control, used, lighting) for r in options.get(CONF_ROOMS) or [])
    notify = options.get(CONF_NOTIFY) or []
    outdoors = tuple(
        Outdoor(
            name=str(o[CONF_NAME]),
            area=o.get(CONF_AREA) or None,
            temperature=_ids(o.get(CONF_TEMPERATURE)),
            air_quality=_ids(o.get(CONF_AIR_QUALITY)),
            noise=_ids(o.get(CONF_NOISE)),
        )
        for o in options.get(CONF_OUTDOORS) or []
    )

    def every(key: str, sensors: Callable[[Outdoor], tuple[str, ...]]) -> tuple[str, ...]:
        found = list(_ids(options.get(key))) + [e for o in outdoors for e in sensors(o)]
        return tuple(dict.fromkeys(found))

    return Settings(
        notify=tuple(f"notify.{n.removeprefix('notify.')}" for n in ([notify] if isinstance(notify, str) else notify)),
        outdoor=every(CONF_OUTDOOR, lambda o: o.temperature),
        aggregate=str(options.get(CONF_OUTDOOR_AGGREGATE) or "min"),
        outdoor_noise=every(CONF_OUTDOOR_NOISE, lambda o: o.noise),
        outdoor_air=every(CONF_OUTDOOR_AIR, lambda o: o.air_quality),
        outdoors=outdoors,
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
        night_start=parse_time(control[CONF_NIGHT_START]),
        night_end=parse_time(control[CONF_NIGHT_END]),
        rooms=rooms,
        lighting_enabled=bool(lighting[CONF_ENABLED]),
        morning_end=parse_time(lighting[CONF_MORNING_END]),
        transition=int(lighting[CONF_TRANSITION]),
    )
