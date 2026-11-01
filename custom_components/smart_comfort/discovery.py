"""Discovery: rooms from the Home Assistant areas, with their sensors and devices.

Every area that is not outdoors and has something to follow (a comfort sensor, an air conditioner, a fan, a
purifier or a dimmable light) becomes a room, with what it has: sensors, openings, devices, lights (not the
indicators of devices nor the floodlights of cameras; night lights set at night only). The others (a hallway
with only its door, a room with nothing) are left out, and so are the outdoor areas without a sensor.
Sensors and openings that belong to an air conditioner, fan or purifier are left out (internal
temperatures, filter states…), and so are the heating thermostats (a climate without cooling).
The outdoor areas become outdoor places, with their temperature, air quality and noise sensors. Outdoor
sensors in no area (a module named outdoor, a city air quality index like Atmo France) go to the top-level
outdoor options; without any outdoor temperature, the weather entity gives it.
Devices get their night settings when they have a quiet preset or fan mode (sleep, silent…).

The result is merged into the options without replacing what is already set: missing sensors are
filled in, missing devices added, devices already there get the settings they don't have yet, rooms
of new areas appended. Nothing is saved here.
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
from .displays import off_option

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
# Air quality index sensors (an index, not a pollutant), and what is not the current outdoor air.
AIR_WORDS = (
    "air_quality",
    "qualite_de_l_air",
    "qualite_air",
    "qualite_globale",
    "luftqualitat",
    "calidad_del_aire",
    "aqi",
)
NOT_AIR_WORDS = ("pollen", "j_1", "tomorrow", "demain", "forecast")
AIR_PLATFORMS = ("atmofrance", "waqi", "airvisual", "airly", "airnow", "google_air_quality")
PURIFIER_WORDS = ("purif", "luftreinig", "air_clean")
NATURAL_WORDS = ("natur",)
DIRECT_WORDS = ("direct", "straight", "standard", "normal")
AUTO_WORDS = ("auto",)
MANUAL_WORDS = ("manual", "manuel", "favorite", "favori", "manuell")
# Quiet presets and fan modes, for the night (most silent first).
QUIET_WORDS = ("sleep", "silent", "quiet", "night", "nuit", "nacht", "noche", "schlaf", "sommeil", "leise")
LOW_WORDS = ("low", "bas", "faible", "niedrig", "bajo", "min")
# Domains of the devices whose own sensors are not room sensors.
# What makes a room worth following: a comfort sensor or a device (openings alone are not enough).
TRACKED = (
    k.CONF_TEMPERATURE,
    k.CONF_CO2,
    k.CONF_HUMIDITY,
    k.CONF_NOISE,
    k.CONF_CLIMATE,
    k.CONF_FANS,
    k.CONF_PURIFIERS,
    k.CONF_LIGHTS,
)
# Indicator lights and displays of the devices (slug form).
DISPLAY_WORDS = (
    "indicator",
    "voyant",
    "display",
    "ecran",
    "screen",
    "brightness",
    "luminosite",
    "helligkeit",
    "anzeige",
    "pantalla",
    "brillo",
)
# Bedrooms: a quiet morning for their lights.
BEDROOM_WORDS = ("chambre", "bedroom", "schlafzimmer", "kinderzimmer", "dormitorio", "habitacion", "nursery")
# Night lights: only set in the night hours.
NIGHT_LIGHT_WORDS = ("veilleuse", "night_light", "nightlight", "nachtlicht", "luz_nocturna", "luz_de_noche")
# Lights that are not lamps: the indicator of a device, the floodlight of a camera.
NOT_LAMP_WORDS = ("indicator", "voyant", "floodlight", "projecteur", "status_light", "led_indicator")
# Integrations of machines whose temperatures are not the room's (NAS, boxes, servers, UPS, printers…).
EQUIPMENT_PLATFORMS = frozenset(
    {
        "ugreen",
        "synology_dsm",
        "qnap",
        "qnap_qsw",
        "truenas",
        "unraid",
        "freebox",
        "livebox",
        "bbox",
        "sfr_box",
        "fritz",
        "fritzbox_callmonitor",
        "netgear",
        "unifi",
        "tplink_omada",
        "systemmonitor",
        "glances",
        "proxmoxve",
        "hddtemp",
        "nut",
        "apcupsd",
        "octoprint",
        "ipp",
        "hpprinter",
        "brother",
        "snmp",
        "esxi_stats",
    }
)
# Words (whole words of the entity id or name) of machine and appliance temperatures.
EQUIPMENT_WORDS = frozenset(
    {
        "cpu",
        "gpu",
        "soc",
        "chipset",
        "motherboard",
        "processor",
        "processeur",
        "disk",
        "disque",
        "hdd",
        "ssd",
        "nvme",
        "nas",
        "server",
        "serveur",
        "router",
        "routeur",
        "freebox",
        "livebox",
        "bbox",
        "modem",
        "switch",
        "printer",
        "imprimante",
        "ups",
        "onduleur",
        "inverter",
        "battery",
        "batterie",
        "coil",
        "pipe",
        "discharge",
        "compressor",
        "compresseur",
        "boiler",
        "chaudiere",
        "fridge",
        "refrigerator",
        "refrigerateur",
        "frigo",
        "freezer",
        "congelateur",
        "oven",
        "four",
        "aquarium",
        "probe",
        "nvr",
        "camera",
    }
)
BUSY_DOMAINS = {"climate", "fan", "humidifier", "water_heater", "vacuum"}
OPENING_CLASSES = {"window", "door", "opening"}


def _equipment(e: _Entity) -> bool:
    """A sensor of a machine (NAS, box, server, printer, fridge…), not of the air around it."""
    if e.platform in EQUIPMENT_PLATFORMS:
        return True
    tokens = set(slugify(f"{e.entity_id} {e.name}").split("_"))
    return bool(tokens & EQUIPMENT_WORDS)


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
    platform: str = ""


@dataclass
class _Area:
    area_id: str
    name: str
    entities: list[_Entity] = field(default_factory=list)


@dataclass
class Found:
    """What the discovery found: rooms, outdoor places, and outdoor sensors in no area."""

    rooms: list[dict[str, Any]] = field(default_factory=list)
    outdoors: list[dict[str, Any]] = field(default_factory=list)
    outdoor: list[str] = field(default_factory=list)
    outdoor_noise: list[str] = field(default_factory=list)
    outdoor_air: list[str] = field(default_factory=list)


@dataclass
class Report:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    outdoors_added: list[str] = field(default_factory=list)
    outdoors_updated: list[str] = field(default_factory=list)
    # Outdoor sensors in no area added to the top-level options.
    outdoor: list[str] = field(default_factory=list)
    outdoor_noise: list[str] = field(default_factory=list)
    outdoor_air: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "added": self.added,
            "updated": self.updated,
            "outdoors_added": self.outdoors_added,
            "outdoors_updated": self.outdoors_updated,
            "outdoor": self.outdoor,
            "outdoor_noise": self.outdoor_noise,
            "outdoor_air": self.outdoor_air,
        }


def _collect(
    hass: HomeAssistant,
) -> tuple[list[_Area], list[_Entity], dict[str, set[str]], dict[str, list[_Entity]]]:
    """Areas with their entities, the entities in no area, the domains and the entities of each device."""
    areas = {a.id: _Area(a.id, a.name) for a in ar.async_get(hass).async_list_areas()}
    devices = dr.async_get(hass)
    device_domains: dict[str, set[str]] = {}
    by_device: dict[str, list[_Entity]] = {}
    unassigned: list[_Entity] = []
    for entry in er.async_get(hass).entities.values():
        if entry.disabled_by or entry.hidden_by:
            continue
        # Settings of a device (its display…): only among its entities, not in the room.
        setting = entry.entity_category is not None
        if setting and not (entry.device_id and entry.domain in k.DISPLAY_DOMAINS):
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
            entry.platform,
        )
        if entry.device_id:
            by_device.setdefault(entry.device_id, []).append(ent)
            if setting:
                continue
            device_domains.setdefault(entry.device_id, set()).add(entry.domain)
        area_id = entry.area_id or (device.area_id if device else None)
        if area_id in areas:
            areas[area_id].entities.append(ent)
        elif area_id is None:
            unassigned.append(ent)
    return list(areas.values()), unassigned, device_domains, by_device


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


def _display(entity: _Entity, by_device: dict[str, list[_Entity]], used: set[str]) -> str | None:
    """The indicator light or display of a device: an on/off light, a switch, a brightness or a select."""
    for sibling in sorted(by_device.get(entity.device_id or "", []), key=lambda e: e.entity_id):
        if sibling.domain not in k.DISPLAY_DOMAINS or sibling.entity_id in used:
            continue
        if not (_has(sibling.entity_id, DISPLAY_WORDS) or _has(sibling.name, DISPLAY_WORDS)):
            continue
        attributes = sibling.attributes
        if sibling.domain == "light" and set(attributes.get("supported_color_modes") or ["onoff"]) != {"onoff"}:
            continue
        if sibling.domain == "select" and off_option(list(attributes.get("options") or [])) is None:
            continue
        return sibling.entity_id
    return None


def _with_display(
    item: str | dict[str, Any], entity: _Entity, by_device: dict[str, list[_Entity]]
) -> str | dict[str, Any]:
    used = {item.get(k.CONF_MODE_SELECT)} if isinstance(item, dict) else set()
    if (display := _display(entity, by_device, {u for u in used if u})) is None:
        return item
    found = item if isinstance(item, dict) else {k.CONF_ENTITY_ID: item}
    return {**found, k.CONF_DISPLAY: display}


def _fan(entity: _Entity) -> str | dict[str, Any]:
    presets = list(entity.attributes.get("preset_modes") or [])
    item: dict[str, Any] = {k.CONF_ENTITY_ID: entity.entity_id}
    if natural := _pick(presets, NATURAL_WORDS):
        item[k.CONF_PRESET] = natural
        item[k.CONF_OFF_PRESET] = natural
    if direct := _pick(presets, DIRECT_WORDS):
        item[k.CONF_OPEN_PRESET] = direct
    if quiet := _pick(presets, QUIET_WORDS):
        item[k.CONF_NIGHT_PRESET] = quiet
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
    if quiet := _pick(list(entity.attributes.get("preset_modes") or []), QUIET_WORDS):
        item[k.CONF_NIGHT_PRESET] = quiet
    return item if len(item) > 1 else entity.entity_id


def _climate(entity: _Entity) -> str | dict[str, Any]:
    """An air conditioner, with its quietest fan mode for the night."""
    modes = list(entity.attributes.get("fan_modes") or [])
    quiet = _pick(modes, QUIET_WORDS) or _pick(modes, LOW_WORDS)
    return {k.CONF_ENTITY_ID: entity.entity_id, k.CONF_NIGHT_FAN_MODE: quiet} if quiet else entity.entity_id


def _is_purifier(entity: _Entity, by_device: dict[str, list[_Entity]]) -> bool:
    if _has(entity.name, PURIFIER_WORDS) or _has(entity.entity_id, PURIFIER_WORDS):
        return True
    siblings = by_device.get(entity.device_id or "", [])
    return any(s.device_class in ("pm25", "aqi", "pm10") for s in siblings)


def _is_lamp(e: _Entity, device_domains: dict[str, set[str]]) -> bool:
    """A dimmable lamp: not on/off only, not a device's indicator or a camera's floodlight."""
    if "camera" in device_domains.get(e.device_id or "", set()) or e.platform in EQUIPMENT_PLATFORMS:
        return False
    if _has(e.entity_id, NOT_LAMP_WORDS) or _has(e.name, NOT_LAMP_WORDS):
        return False
    modes = set(e.attributes.get("supported_color_modes") or [])
    return bool(modes - {"onoff"})


def _light(e: _Entity) -> str | dict[str, Any]:
    if _has(e.entity_id, NIGHT_LIGHT_WORDS) or _has(e.name, NIGHT_LIGHT_WORDS):
        return {k.CONF_ENTITY_ID: e.entity_id, k.CONF_NIGHT_ONLY: True}
    return e.entity_id


def _is_air(e: _Entity, outdoor: bool = False) -> bool:
    """An air quality index sensor (in no area: a city one, like Atmo France, not a forecast nor pollen)."""
    if e.device_class == "aqi" and (not outdoor or e.platform in AIR_PLATFORMS):
        return True
    if not _has(e.name, AIR_WORDS) and not _has(e.entity_id, AIR_WORDS):
        return False
    if _has(e.entity_id, NOT_AIR_WORDS):
        return False
    # In no area: only the integrations of outdoor air quality (a city index), not any "air quality".
    return not outdoor or e.platform in AIR_PLATFORMS


def discover_rooms(hass: HomeAssistant) -> Found:
    """Rooms and outdoor places found in the areas, and the outdoor sensors in no area."""
    areas, unassigned, device_domains, by_device = _collect(hass)

    def busy(e: _Entity) -> bool:
        return bool(e.device_id) and bool(device_domains.get(e.device_id, set()) & BUSY_DOMAINS)

    found = Found()
    rooms = found.rooms
    # Sensors in no area: an outdoor module named so, a city air quality index.
    for e in sorted(unassigned, key=lambda e: e.entity_id):
        if e.domain != "sensor" or busy(e) or _equipment(e):
            continue
        if _is_air(e, outdoor=True):
            found.outdoor_air.append(e.entity_id)
        elif _has(e.name, OUTDOOR_WORDS) or _has(e.entity_id, OUTDOOR_WORDS):
            if e.device_class == "temperature":
                found.outdoor.append(e.entity_id)
            elif e.device_class == "sound_pressure":
                found.outdoor_noise.append(e.entity_id)
    for area in sorted(areas, key=lambda a: a.name.casefold()):
        sensors = [e for e in area.entities if e.domain == "sensor" and not busy(e) and not _equipment(e)]
        temps = [e for e in sensors if e.device_class == "temperature"]
        if _has(area.name, OUTDOOR_WORDS) or _has(area.area_id, OUTDOOR_WORDS):
            place: dict[str, Any] = {k.CONF_NAME: area.name, k.CONF_AREA: area.area_id}
            for key, items in (
                (k.CONF_TEMPERATURE, temps),
                (k.CONF_AIR_QUALITY, [e for e in sensors if _is_air(e)]),
                (k.CONF_NOISE, [e for e in sensors if e.device_class == "sound_pressure"]),
            ):
                if items:
                    place[key] = sorted(e.entity_id for e in items)
            if len(place) > 2:  # Not without a sensor.
                found.outdoors.append(place)
            continue
        indoor = [e for e in temps if not _has(e.name, OUTDOOR_WORDS) and not _has(e.entity_id, OUTDOOR_WORDS)]
        room: dict[str, Any] = {k.CONF_NAME: area.name, k.CONF_AREA: area.area_id}
        for key, device_class, pool in (
            (k.CONF_TEMPERATURE, "temperature", indoor),
            (k.CONF_CO2, "carbon_dioxide", sensors),
            (k.CONF_HUMIDITY, "humidity", sensors),
            (k.CONF_NOISE, "sound_pressure", sensors),
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
            cooler = min(coolers, key=lambda e: e.entity_id)
            room[k.CONF_CLIMATE] = _with_display(_climate(cooler), cooler, by_device)
        fans, purifiers = [], []
        for e in sorted((e for e in area.entities if e.domain == "fan"), key=lambda e: e.entity_id):
            if "climate" in device_domains.get(e.device_id or "", set()):
                continue  # The fan of an air conditioner.
            if _is_purifier(e, by_device):
                purifiers.append(_with_display(_purifier(e, by_device), e, by_device))
            else:
                fans.append(_with_display(_fan(e), e, by_device))
        if fans:
            room[k.CONF_FANS] = fans
        if purifiers:
            room[k.CONF_PURIFIERS] = purifiers
        lights = [e for e in area.entities if e.domain == "light" and not busy(e) and _is_lamp(e, device_domains)]
        # A light group in the room stands for its members.
        members = {m for e in lights for m in (e.attributes.get("entity_id") or [])}
        if found_lights := [_light(e) for e in sorted(lights, key=lambda e: e.entity_id) if e.entity_id not in members]:
            room[k.CONF_LIGHTS] = found_lights
            if _has(area.name, BEDROOM_WORDS) or _has(area.area_id, BEDROOM_WORDS):
                # Bedrooms: dimmer lights in the morning (their naps are set by hand).
                room[k.CONF_LIGHTING] = {k.CONF_QUIET_MORNING: True}
        if any(key in room for key in TRACKED):
            rooms.append(room)
    if not found.outdoor and not any(p.get(k.CONF_TEMPERATURE) for p in found.outdoors):
        # No outdoor temperature sensor: the weather entity's.
        found.outdoor = sorted(s.entity_id for s in hass.states.async_all("weather"))[:1]
    return found


def _item_id(item: Any) -> str:
    return item if isinstance(item, str) else str(item.get(k.CONF_ENTITY_ID))


def _complete(current: Any, new: Any) -> tuple[Any, bool]:
    """A device item completed with the settings found that it doesn't have yet (its own ones kept)."""
    if not isinstance(new, dict):
        return current, False
    item = {k.CONF_ENTITY_ID: current} if isinstance(current, str) else dict(current)
    missing = {key: value for key, value in new.items() if key not in item}
    if not missing:
        return current, False
    return {**item, **missing}, True


def merge(options: dict[str, Any], found: Found) -> tuple[dict[str, Any], Report]:
    """Options with what was discovered: existing values kept, missing ones filled in, new rooms and places appended."""
    out = copy.deepcopy(options)
    report = Report()
    rooms = out.setdefault(k.CONF_ROOMS, [])
    for new in found.rooms:
        match = _match(rooms, new)
        if match is None:
            rooms.append(new)
            report.added.append(new[k.CONF_NAME])
            continue
        changed = False
        if match.get(k.CONF_AREA) != new[k.CONF_AREA]:
            match[k.CONF_AREA] = new[k.CONF_AREA]
        for key in (k.CONF_TEMPERATURE, k.CONF_CO2, k.CONF_HUMIDITY, k.CONF_NOISE, k.CONF_CLIMATE):
            if key in new and not match.get(key):
                match[key] = new[key]
                changed = True
        if lighting := new.get(k.CONF_LIGHTING):
            own = match.setdefault(k.CONF_LIGHTING, {})
            for key, value in lighting.items():
                if key not in own:
                    own[key] = value
                    changed = True
        if match.get(k.CONF_CLIMATE) and _item_id(match[k.CONF_CLIMATE]) == _item_id(new.get(k.CONF_CLIMATE, "")):
            match[k.CONF_CLIMATE], completed = _complete(match[k.CONF_CLIMATE], new[k.CONF_CLIMATE])
            changed = changed or completed
        for key in (k.CONF_OPENINGS, k.CONF_FANS, k.CONF_PURIFIERS, k.CONF_LIGHTS):
            current = _list(match.get(key))
            found_items = {_item_id(i): i for i in new.get(key, [])}
            completed_items = []
            for item in current:
                done, completed = _complete(item, found_items.get(_item_id(item)))
                completed_items.append(done)
                changed = changed or completed
            known = {_item_id(i) for i in current}
            added = [i for i in new.get(key, []) if _item_id(i) not in known]
            if added or completed_items != current:
                match[key] = completed_items + added
                changed = True
        if changed:
            report.updated.append(match[k.CONF_NAME])
    if not rooms:
        out.pop(k.CONF_ROOMS)
    _merge_outdoors(out, found.outdoors, report)
    report.outdoor = _add_sensors(out, k.CONF_OUTDOOR, found.outdoor)
    report.outdoor_noise = _add_sensors(out, k.CONF_OUTDOOR_NOISE, found.outdoor_noise)
    report.outdoor_air = _add_sensors(out, k.CONF_OUTDOOR_AIR, found.outdoor_air)
    return out, report


OUTDOOR_KEYS = (
    (k.CONF_TEMPERATURE, k.CONF_OUTDOOR),
    (k.CONF_AIR_QUALITY, k.CONF_OUTDOOR_AIR),
    (k.CONF_NOISE, k.CONF_OUTDOOR_NOISE),
)


def _merge_outdoors(out: dict[str, Any], found: list[dict[str, Any]], report: Report) -> None:
    """The outdoor places found merged in; their sensors leave the top-level lists (they count once)."""
    places = out.setdefault(k.CONF_OUTDOORS, [])
    for new in found:
        match = _match(places, new)
        if match is None:
            places.append(new)
            report.outdoors_added.append(new[k.CONF_NAME])
        else:
            match[k.CONF_AREA] = new[k.CONF_AREA]
            changed = False
            for key, _ in OUTDOOR_KEYS:
                current = _list(match.get(key))
                added = [e for e in new.get(key, []) if e not in current]
                if added:
                    match[key] = current + added
                    changed = True
            if changed:
                report.outdoors_updated.append(match[k.CONF_NAME])
    for key, top in OUTDOOR_KEYS:
        in_places = {e for p in places for e in _list(p.get(key))}
        current = _list(out.get(top))
        if in_places & set(current):
            if kept := [e for e in current if e not in in_places]:
                out[top] = kept
            else:
                out.pop(top)
    if not places:
        out.pop(k.CONF_OUTDOORS)


def _match(items: list[dict[str, Any]], new: dict[str, Any]) -> dict[str, Any] | None:
    """The room or place of the same area, or of the same name without an area."""
    return next((r for r in items if r.get(k.CONF_AREA) == new[k.CONF_AREA]), None) or next(
        (r for r in items if k.CONF_AREA not in r and slugify(r[k.CONF_NAME]) == slugify(new[k.CONF_NAME])),
        None,
    )


def _list(value: Any) -> list[Any]:
    if not value:
        return []
    return [value] if isinstance(value, (str, dict)) else list(value)


def _add_sensors(options: dict[str, Any], key: str, found: list[str]) -> list[str]:
    """The outdoor sensors in no area found added to the ones set (kept), the ones added returned.

    A weather entity, found for want of a sensor, only when there is no outdoor temperature at all."""
    current = _list(options.get(key))
    if found and all(e.startswith("weather.") for e in found):
        places = options.get(k.CONF_OUTDOORS) or []
        if current or any(p.get(k.CONF_TEMPERATURE) for p in places):
            return []
    added = [e for e in found if e not in current]
    if added:
        options[key] = current + added
    return added
