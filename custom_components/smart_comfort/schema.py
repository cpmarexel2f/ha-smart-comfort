"""Validation of the YAML configuration and of the options. Defaults are applied by config.build_settings."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from . import const as k
from .config import parse_time

MINUTES = vol.All(vol.Coerce(int), vol.Range(min=0, max=k.MAX_MINUTES))
NUMBER = vol.Coerce(float)
PERCENT = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))
OPT_STR = vol.Any(None, cv.string)


def time_string(value: Any) -> str | None:
    """Validate "HH:MM[:SS]" and store it as a string (options must be JSON)."""
    if value in (None, ""):
        return None
    try:
        parsed = parse_time(value)
    except (TypeError, ValueError) as err:
        raise vol.Invalid(f"Invalid time: {value}") from err
    return parsed.strftime("%H:%M:%S") if parsed else None


def notify_service(value: Any) -> str:
    name = cv.string(value).strip().removeprefix("notify.")
    if not name:
        raise vol.Invalid("Empty notify action")
    return f"notify.{name}"


# Every device: its indicator light or display, and a time to go back to its normal state.
EQUIPMENT = {
    vol.Optional(k.CONF_DISPLAY): vol.Any(None, cv.entity_domain(list(k.DISPLAY_DOMAINS))),
    vol.Optional(k.CONF_RESET_AT): time_string,
}

ALERT = vol.Schema(
    {
        vol.Optional(k.CONF_ENABLED): cv.boolean,
        vol.Optional(k.CONF_THRESHOLD): NUMBER,
        vol.Optional(k.CONF_HYSTERESIS): vol.All(NUMBER, vol.Range(min=0)),
        vol.Optional(k.CONF_DELAY): MINUTES,
        vol.Optional(k.CONF_SEVERITY): vol.In(k.SEVERITIES),
        vol.Optional(k.CONF_ESCALATION): vol.All(NUMBER, vol.Range(min=0)),
        vol.Optional(k.CONF_MIN_OUTDOOR): vol.Any(None, NUMBER),
        vol.Optional(k.CONF_MAX_OUTDOOR): vol.Any(None, NUMBER),
        vol.Optional(k.CONF_MIN_INDOOR): vol.Any(None, NUMBER),
        vol.Optional(k.CONF_MAX_NOISE): vol.Any(None, NUMBER),
        vol.Optional(k.CONF_MAX_AIR): vol.Any(None, NUMBER),
    }
)
ALERTS = vol.Schema({vol.Optional(kind): ALERT for kind in k.KINDS})

CLIMATE = {
    vol.Optional(k.CONF_COOL_ABOVE): NUMBER,
    vol.Optional(k.CONF_OFF_BELOW): NUMBER,
    vol.Optional(k.CONF_SETPOINT): NUMBER,
    vol.Optional(k.CONF_FAN_MODE): OPT_STR,
    vol.Optional(k.CONF_CLOSED_FOR): MINUTES,
    vol.Optional(k.CONF_OFF_ON_OPEN): MINUTES,
    vol.Optional(k.CONF_NIGHT_FAN_MODE): OPT_STR,
    **EQUIPMENT,
}
FAN = {
    vol.Optional(k.CONF_ON_ABOVE): vol.Any(None, NUMBER),
    vol.Optional(k.CONF_OFF_BELOW): vol.Any(None, NUMBER),
    vol.Optional(k.CONF_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_PRESET): OPT_STR,
    vol.Optional(k.CONF_OPEN_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_OPEN_PRESET): OPT_STR,
    vol.Optional(k.CONF_OFF_PRESET): OPT_STR,
    vol.Optional(k.CONF_NIGHT_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_NIGHT_PRESET): OPT_STR,
    **EQUIPMENT,
}
PURIFIER = {
    vol.Optional(k.CONF_OPEN_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_OPEN_PRESET): OPT_STR,
    vol.Optional(k.CONF_CLOSED_PRESET): OPT_STR,
    vol.Optional(k.CONF_MODE_SELECT): vol.Any(None, cv.entity_domain("select")),
    vol.Optional(k.CONF_OPEN_MODE): OPT_STR,
    vol.Optional(k.CONF_CLOSED_MODE): OPT_STR,
    vol.Optional(k.CONF_KEEP_ON): cv.boolean,
    vol.Optional(k.CONF_NIGHT_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_NIGHT_PRESET): OPT_STR,
    vol.Optional(k.CONF_NIGHT_MODE): OPT_STR,
    **EQUIPMENT,
}
DEVICE_SECTIONS = vol.Schema(
    {
        vol.Optional(k.CONF_CLIMATE): vol.Schema(CLIMATE),
        vol.Optional(k.CONF_FANS): vol.Schema(FAN),
        vol.Optional(k.CONF_PURIFIERS): vol.Schema(PURIFIER),
    }
)
CONTROL = DEVICE_SECTIONS.extend(
    {
        vol.Optional(k.CONF_ENABLED): cv.boolean,
        vol.Optional(k.CONF_START): time_string,
        vol.Optional(k.CONF_END): time_string,
        vol.Optional(k.CONF_MANUAL_OVERRIDE): MINUTES,
        vol.Optional(k.CONF_SUPPRESS_HANDLED): cv.boolean,
        vol.Optional(k.CONF_NIGHT_START): time_string,
        vol.Optional(k.CONF_NIGHT_END): time_string,
        vol.Optional(k.CONF_DISPLAY_OFF): time_string,
        vol.Optional(k.CONF_DISPLAY_ON): time_string,
    }
)


def _devices(domain: str, extra: dict) -> vol.All:
    item = vol.Any(
        cv.entity_domain(domain),
        vol.Schema({vol.Required(k.CONF_ENTITY_ID): cv.entity_domain(domain), **extra}),
    )
    return vol.All(cv.ensure_list, [item])


LIGHTING_LEVELS = {
    vol.Optional(k.CONF_DAY): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(k.CONF_EVENING): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(k.CONF_NIGHT): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(k.CONF_WARMTH): cv.boolean,
    vol.Optional(k.CONF_DAY_KELVIN): vol.All(vol.Coerce(int), vol.Range(min=1500, max=10000)),
    vol.Optional(k.CONF_EVENING_KELVIN): vol.All(vol.Coerce(int), vol.Range(min=1500, max=10000)),
    vol.Optional(k.CONF_NIGHT_KELVIN): vol.All(vol.Coerce(int), vol.Range(min=1500, max=10000)),
    vol.Optional(k.CONF_MORNING): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(k.CONF_MORNING_KELVIN): vol.All(vol.Coerce(int), vol.Range(min=1500, max=10000)),
    vol.Optional(k.CONF_QUIET_MORNING): cv.boolean,
    vol.Optional(k.CONF_NAP): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(k.CONF_NAP_KELVIN): vol.All(vol.Coerce(int), vol.Range(min=1500, max=10000)),
}
TIME_SLOT = {
    vol.Required("start"): time_string,
    vol.Required("end"): time_string,
    vol.Optional(k.CONF_DAYS): vol.All(cv.ensure_list, [vol.In(k.WEEKDAYS)]),
}
NAP = vol.Schema(TIME_SLOT)
LIGHTING = vol.Schema(
    {
        vol.Optional(k.CONF_ENABLED): cv.boolean,
        vol.Optional(k.CONF_TRANSITION): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
        vol.Optional(k.CONF_MORNING_END): time_string,
        **LIGHTING_LEVELS,
    }
)
LIGHT = {vol.Optional(k.CONF_NIGHT_ONLY): cv.boolean, **LIGHTING_LEVELS}


def _off_key(value: Any) -> Any:
    """YAML 1.1 reads an unquoted `off:` key as False: back to "off"."""
    if isinstance(value, dict) and False in value:
        value = {(k.CONF_OFF if key is False else key): v for key, v in value.items()}
    return value


PRESENCE_SLOT = vol.All(
    _off_key,
    vol.Schema(
        {
            **TIME_SLOT,
            vol.Optional(k.CONF_LIGHTS): cv.entity_ids,
            vol.Optional(k.CONF_BRIGHTNESS): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=100))),
            vol.Optional(k.CONF_OFF): cv.boolean,
            vol.Optional(k.CONF_OFF_AFTER): vol.Any(None, vol.All(NUMBER, vol.Range(min=0, max=k.MAX_MINUTES))),
            vol.Optional(k.CONF_COLOR): vol.Any(
                None, vol.All(cv.ensure_list, vol.Length(min=3, max=3), [vol.All(vol.Coerce(int), vol.Range(0, 255))])
            ),
        }
    ),
)
PRESENCE = vol.Schema(
    {
        vol.Required(k.CONF_SENSORS): cv.entity_ids,
        vol.Optional(k.CONF_LIGHTS): cv.entity_ids,
        vol.Optional(k.CONF_LUX): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_MAX_LUX): vol.Any(None, NUMBER),
        vol.Optional(k.CONF_OFF_AFTER): vol.All(NUMBER, vol.Range(min=0, max=k.MAX_MINUTES)),
        vol.Optional(k.CONF_ON_AFTER): vol.All(NUMBER, vol.Range(min=0, max=600)),
        vol.Optional(k.CONF_TRANSITION): vol.Any(None, vol.All(NUMBER, vol.Range(min=0, max=300))),
        vol.Optional(k.CONF_NOT_DURING_NAPS): cv.entity_ids,
        vol.Optional(k.CONF_SLOTS): vol.All(cv.ensure_list, [PRESENCE_SLOT]),
    }
)

ROOM = vol.Schema(
    {
        vol.Required(k.CONF_NAME): cv.string,
        vol.Optional("id"): cv.slug,
        # Home Assistant area the room was discovered from (re-running the discovery updates it).
        vol.Optional(k.CONF_AREA): cv.string,
        vol.Optional(k.CONF_TEMPERATURE): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_CO2): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_HUMIDITY): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_NOISE): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_OPENINGS): cv.entity_ids,
        vol.Optional(k.CONF_CLIMATE): vol.Any(
            None,
            cv.entity_domain("climate"),
            vol.Schema({vol.Required(k.CONF_ENTITY_ID): cv.entity_domain("climate"), **CLIMATE}),
        ),
        vol.Optional(k.CONF_FANS): _devices("fan", FAN),
        vol.Optional(k.CONF_PURIFIERS): _devices("fan", PURIFIER),
        vol.Optional(k.CONF_LIGHTS): _devices("light", LIGHT),
        vol.Optional(k.CONF_LIGHTING): vol.Schema(LIGHTING_LEVELS),
        vol.Optional(k.CONF_NAPS): vol.All(cv.ensure_list, [NAP]),
        vol.Optional(k.CONF_PRESENCE_LIGHTS): PRESENCE,
        vol.Optional(k.CONF_ALERTS): ALERTS,
        vol.Optional(k.CONF_CONTROL): DEVICE_SECTIONS,
    }
)

OUTDOOR = vol.Schema(
    {
        vol.Required(k.CONF_NAME): cv.string,
        # Home Assistant area the place was discovered from (re-running the discovery updates it).
        vol.Optional(k.CONF_AREA): cv.string,
        vol.Optional(k.CONF_TEMPERATURE): cv.entity_ids,
        vol.Optional(k.CONF_AIR_QUALITY): cv.entity_ids,
        vol.Optional(k.CONF_NOISE): cv.entity_ids,
    }
)

OPTIONS = vol.Schema(
    {
        vol.Optional(k.CONF_NOTIFY): vol.All(cv.ensure_list, [notify_service]),
        vol.Optional(k.CONF_OUTDOOR): cv.entity_ids,
        vol.Optional(k.CONF_OUTDOOR_AGGREGATE): vol.In(k.AGGREGATES),
        vol.Optional(k.CONF_OUTDOOR_NOISE): cv.entity_ids,
        vol.Optional(k.CONF_OUTDOOR_AIR): cv.entity_ids,
        vol.Optional(k.CONF_DIGEST_WINDOW): MINUTES,
        vol.Optional(k.CONF_STARTUP_GRACE): MINUTES,
        vol.Optional(k.CONF_REMINDER): MINUTES,
        vol.Optional(k.CONF_SNOOZE_DURATION): vol.All(MINUTES, vol.Range(min=1)),
        vol.Optional(k.CONF_QUIET_START): time_string,
        vol.Optional(k.CONF_QUIET_END): time_string,
        vol.Optional(k.CONF_PRESENCE): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_CLEAR_WHEN_RESOLVED): cv.boolean,
        vol.Optional(k.CONF_CRITICAL_VOLUME): vol.All(NUMBER, vol.Range(min=0, max=1)),
        vol.Optional(k.CONF_URL): OPT_STR,
        vol.Optional(k.CONF_TAG): cv.string,
        vol.Optional(k.CONF_ALERTS): ALERTS,
        vol.Optional(k.CONF_CONTROL): CONTROL,
        vol.Optional(k.CONF_ROOMS): vol.All(cv.ensure_list, [ROOM]),
        vol.Optional(k.CONF_OUTDOORS): vol.All(cv.ensure_list, [OUTDOOR]),
        vol.Optional(k.CONF_LIGHTING): LIGHTING,
    }
)

CONFIG_SCHEMA = vol.Schema({vol.Optional(k.DOMAIN): OPTIONS}, extra=vol.ALLOW_EXTRA)
