"""Discovery: rooms from the Home Assistant areas, with their sensors and devices.

Every area that is not outdoors becomes a room, with what it has: sensors, openings, devices.
Sensors and openings that belong to an air conditioner, fan or purifier are left out (internal
temperatures, filter states…), and so are the heating thermostats (a climate without cooling).
Temperature sensors of the outdoor areas become the outdoor temperature.

The result is merged into the options without replacing what is already set: missing sensors are
filled in, missing devices added, rooms of new areas appended. Nothing is saved here.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from . import const as k
from .config import slugify

# Words of outdoor areas and sensors, in slug form (several languages).
OUTDOOR_WORDS = (
    "exterieur",
    "exterior",
    "outdoor",
    "outside",
    "dehors",
    "terrasse",
    "terrace",
    "terraza",
    "jardin",
    "garden",
    "garten",
    "balcon",
    "balcony",
    "balkon",
    "patio",
    "yard",
    "piscine",
    "pool",
    "aussen",
)
PURIFIER_WORDS = ("purif", "luftreinig", "air_clean")
NATURAL_WORDS = ("natur",)
DIRECT_WORDS = ("direct", "straight", "standard", "normal")
AUTO_WORDS = ("auto",)
MANUAL_WORDS = ("manual", "manuel", "favorite", "favori", "manuell")
# Domains of the devices whose own sensors are not room sensors.
BUSY_DOMAINS = {"climate", "fan", "humidifier", "water_heater", "vacuum"}
OPENING_CLASSES = {"window", "door", "opening"}


def _has(text: str, words: tuple[str, ...]) -> bool:
    slug = slugify(text)
    return any(w in slug for w in words)


def _pick(values: list[str], words: tuple[str, ...]) -> str | None:
    return next((v for v in values if _has(v, words)), None)


@dataclass
class _Entity:
    entity_id: str
    domain: str
    name: str
    device_id: str | None
    device_class: str | None
    attributes: dict[str, Any]


@dataclass
class _Area:
    area_id: str
    name: str
    entities: list[_Entity] = field(default_factory=list)


@dataclass
class Report:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    outdoor: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {"added": self.added, "updated": self.updated, "outdoor": self.outdoor}


def _collect(hass: HomeAssistant) -> tuple[list[_Area], dict[str, set[str]], dict[str, list[_Entity]]]:
    """Areas with their entities, the domains of each device, and the entities of each device."""
    areas = {a.id: _Area(a.id, a.name) for a in ar.async_get(hass).async_list_areas()}
    devices = dr.async_get(hass)
    device_domains: dict[str, set[str]] = {}
    by_device: dict[str, list[_Entity]] = {}
    for entry in er.async_get(hass).entities.values():
        if entry.disabled_by or entry.hidden_by or entry.entity_category is not None:
            continue
        device = devices.async_get(entry.device_id) if entry.device_id else None
        state = hass.states.get(entry.entity_id)
        attributes = dict(state.attributes) if state else {}
        name = (state.name if state else None) or entry.name or entry.original_name or entry.entity_id
        if device is not None:
            name = f"{name} {device.name_by_user or device.name or ''} {device.model or ''}"
        ent = _Entity(
            entry.entity_id,
            entry.domain,
            name,
            entry.device_id,
            attributes.get("device_class") or entry.device_class or entry.original_device_class,
            attributes,
        )
        if entry.device_id:
            device_domains.setdefault(entry.device_id, set()).add(entry.domain)
            by_device.setdefault(entry.device_id, []).append(ent)
        area_id = entry.area_id or (device.area_id if device else None)
        if area_id in areas:
            areas[area_id].entities.append(ent)
    return list(areas.values()), device_domains, by_device


def _best(candidates: list[_Entity], by_device: dict[str, list[_Entity]]) -> str | None:
    """The sensor of a room: from a device that also measures other things (a weather station…)."""

    def score(e: _Entity) -> tuple[int, int, str]:
        siblings = {s.device_class for s in by_device.get(e.device_id or "", [])}
        related = len(siblings & {"temperature", "humidity", "carbon_dioxide"})
        return (related, 1 if e.attributes.get("state_class") == "measurement" else 0, e.entity_id)

    if not candidates:
        return None
    best = max(candidates, key=score)
    return best.entity_id


def _fan(entity: _Entity) -> str | dict[str, Any]:
    presets = list(entity.attributes.get("preset_modes") or [])
    item: dict[str, Any] = {k.CONF_ENTITY_ID: entity.entity_id}
    if natural := _pick(presets, NATURAL_WORDS):
        item[k.CONF_PRESET] = natural
        item[k.CONF_OFF_PRESET] = natural
    if direct := _pick(presets, DIRECT_WORDS):
        item[k.CONF_OPEN_PRESET] = direct
    return item if len(item) > 1 else entity.entity_id


def _purifier(entity: _Entity, by_device: dict[str, list[_Entity]]) -> str | dict[str, Any]:
    item: dict[str, Any] = {k.CONF_ENTITY_ID: entity.entity_id}
    for sibling in by_device.get(entity.device_id or "", []):
        if sibling.domain != "select":
            continue
        options = list(sibling.attributes.get("options") or [])
        auto, manual = _pick(options, AUTO_WORDS), _pick(options, MANUAL_WORDS)
        if auto and manual:
            item.update({k.CONF_MODE_SELECT: sibling.entity_id, k.CONF_OPEN_MODE: manual, k.CONF_CLOSED_MODE: auto})
            break
    else:
        presets = list(entity.attributes.get("preset_modes") or [])
        if (auto := _pick(presets, AUTO_WORDS)) and (manual := _pick(presets, MANUAL_WORDS)):
            item.update({k.CONF_OPEN_PRESET: manual, k.CONF_CLOSED_PRESET: auto})
    return item if len(item) > 1 else entity.entity_id


def _is_purifier(entity: _Entity, by_device: dict[str, list[_Entity]]) -> bool:
    if _has(entity.name, PURIFIER_WORDS) or _has(entity.entity_id, PURIFIER_WORDS):
        return True
    siblings = by_device.get(entity.device_id or "", [])
    return any(s.device_class in ("pm25", "aqi", "pm10") for s in siblings)


def discover_rooms(hass: HomeAssistant) -> tuple[list[dict[str, Any]], list[str]]:
    """Rooms found in the areas, and the outdoor temperature sensors."""
    areas, device_domains, by_device = _collect(hass)

    def busy(e: _Entity) -> bool:
        return bool(e.device_id) and bool(device_domains.get(e.device_id, set()) & BUSY_DOMAINS)

    rooms: list[dict[str, Any]] = []
    outdoor: list[str] = []
    for area in sorted(areas, key=lambda a: a.name.casefold()):
        sensors = [e for e in area.entities if e.domain == "sensor" and not busy(e)]
        temps = [e for e in sensors if e.device_class == "temperature"]
        if _has(area.name, OUTDOOR_WORDS) or _has(area.area_id, OUTDOOR_WORDS):
            outdoor += sorted(e.entity_id for e in temps)
            continue
        indoor = [e for e in temps if not _has(e.name, OUTDOOR_WORDS) and not _has(e.entity_id, OUTDOOR_WORDS)]
        room: dict[str, Any] = {k.CONF_NAME: area.name, k.CONF_AREA: area.area_id}
        for key, device_class, pool in (
            (k.CONF_TEMPERATURE, "temperature", indoor),
            (k.CONF_CO2, "carbon_dioxide", sensors),
            (k.CONF_HUMIDITY, "humidity", sensors),
        ):
            candidates = [e for e in pool if e.device_class == device_class and not _has(e.name, OUTDOOR_WORDS)]
            if (best := _best(candidates, by_device)) is not None:
                room[key] = best
        openings = sorted(
            e.entity_id
            for e in area.entities
            if e.domain == "binary_sensor" and e.device_class in OPENING_CLASSES and not busy(e)
        )
        if openings:
            room[k.CONF_OPENINGS] = openings
        coolers = [
            e for e in area.entities if e.domain == "climate" and "cool" in (e.attributes.get("hvac_modes") or [])
        ]
        if coolers:
            room[k.CONF_CLIMATE] = min(coolers, key=lambda e: e.entity_id).entity_id
        fans, purifiers = [], []
        for e in sorted((e for e in area.entities if e.domain == "fan"), key=lambda e: e.entity_id):
            if "climate" in device_domains.get(e.device_id or "", set()):
                continue  # The fan of an air conditioner.
            if _is_purifier(e, by_device):
                purifiers.append(_purifier(e, by_device))
            else:
                fans.append(_fan(e))
        if fans:
            room[k.CONF_FANS] = fans
        if purifiers:
            room[k.CONF_PURIFIERS] = purifiers
        rooms.append(room)
    return rooms, outdoor


def _item_id(item: Any) -> str:
    return item if isinstance(item, str) else str(item.get(k.CONF_ENTITY_ID))


def merge(options: dict[str, Any], found: list[dict[str, Any]], outdoor: list[str]) -> tuple[dict[str, Any], Report]:
    """Options with the discovered rooms: existing values kept, missing ones filled in, new rooms appended."""
    out = copy.deepcopy(options)
    report = Report()
    rooms = out.setdefault(k.CONF_ROOMS, [])
    for new in found:
        match = next((r for r in rooms if r.get(k.CONF_AREA) == new[k.CONF_AREA]), None) or next(
            (r for r in rooms if k.CONF_AREA not in r and slugify(r[k.CONF_NAME]) == slugify(new[k.CONF_NAME])),
            None,
        )
        if match is None:
            rooms.append(new)
            report.added.append(new[k.CONF_NAME])
            continue
        changed = False
        if match.get(k.CONF_AREA) != new[k.CONF_AREA]:
            match[k.CONF_AREA] = new[k.CONF_AREA]
        for key in (k.CONF_TEMPERATURE, k.CONF_CO2, k.CONF_HUMIDITY, k.CONF_CLIMATE):
            if key in new and not match.get(key):
                match[key] = new[key]
                changed = True
        for key in (k.CONF_OPENINGS, k.CONF_FANS, k.CONF_PURIFIERS):
            current = match.get(key) or []
            current = [current] if isinstance(current, (str, dict)) else list(current)
            known = {_item_id(i) for i in current}
            added = [i for i in new.get(key, []) if _item_id(i) not in known]
            if added:
                match[key] = current + added
                changed = True
        if changed:
            report.updated.append(match[k.CONF_NAME])
    if not rooms:
        out.pop(k.CONF_ROOMS)
    if outdoor and not out.get(k.CONF_OUTDOOR):
        out[k.CONF_OUTDOOR] = outdoor
        report.outdoor = outdoor
    return out, report
