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
}
FAN = {
    vol.Optional(k.CONF_ON_ABOVE): vol.Any(None, NUMBER),
    vol.Optional(k.CONF_OFF_BELOW): vol.Any(None, NUMBER),
    vol.Optional(k.CONF_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_PRESET): OPT_STR,
    vol.Optional(k.CONF_OPEN_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_OPEN_PRESET): OPT_STR,
    vol.Optional(k.CONF_OFF_PRESET): OPT_STR,
}
PURIFIER = {
    vol.Optional(k.CONF_OPEN_PERCENTAGE): vol.Any(None, PERCENT),
    vol.Optional(k.CONF_OPEN_PRESET): OPT_STR,
    vol.Optional(k.CONF_CLOSED_PRESET): OPT_STR,
    vol.Optional(k.CONF_MODE_SELECT): vol.Any(None, cv.entity_domain("select")),
    vol.Optional(k.CONF_OPEN_MODE): OPT_STR,
    vol.Optional(k.CONF_CLOSED_MODE): OPT_STR,
    vol.Optional(k.CONF_KEEP_ON): cv.boolean,
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
    }
)


def _devices(domain: str, extra: dict) -> vol.All:
    item = vol.Any(
        cv.entity_domain(domain),
        vol.Schema({vol.Required(k.CONF_ENTITY_ID): cv.entity_domain(domain), **extra}),
    )
    return vol.All(cv.ensure_list, [item])


ROOM = vol.Schema(
    {
        vol.Required(k.CONF_NAME): cv.string,
        vol.Optional("id"): cv.slug,
        # Home Assistant area the room was discovered from (re-running the discovery updates it).
        vol.Optional(k.CONF_AREA): cv.string,
        vol.Optional(k.CONF_TEMPERATURE): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_CO2): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_HUMIDITY): vol.Any(None, cv.entity_id),
        vol.Optional(k.CONF_OPENINGS): cv.entity_ids,
        vol.Optional(k.CONF_CLIMATE): vol.Any(
            None,
            cv.entity_domain("climate"),
            vol.Schema({vol.Required(k.CONF_ENTITY_ID): cv.entity_domain("climate"), **CLIMATE}),
        ),
        vol.Optional(k.CONF_FANS): _devices("fan", FAN),
        vol.Optional(k.CONF_PURIFIERS): _devices("fan", PURIFIER),
        vol.Optional(k.CONF_ALERTS): ALERTS,
        vol.Optional(k.CONF_CONTROL): DEVICE_SECTIONS,
    }
)

OPTIONS = vol.Schema(
    {
        vol.Optional(k.CONF_NOTIFY): vol.All(cv.ensure_list, [notify_service]),
        vol.Optional(k.CONF_OUTDOOR): cv.entity_ids,
        vol.Optional(k.CONF_OUTDOOR_AGGREGATE): vol.In(k.AGGREGATES),
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
    }
)

CONFIG_SCHEMA = vol.Schema({vol.Optional(k.DOMAIN): OPTIONS}, extra=vol.ALLOW_EXTRA)
