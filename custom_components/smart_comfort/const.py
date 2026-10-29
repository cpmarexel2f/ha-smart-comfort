"""Constants for Smart Comfort."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "smart_comfort"
TITLE: Final = "Smart Comfort"

# Top-level options (same keys in YAML and in the config entry options).
CONF_NOTIFY: Final = "notify"
CONF_OUTDOOR: Final = "outdoor_temperature"
CONF_OUTDOOR_AGGREGATE: Final = "outdoor_aggregate"
CONF_DIGEST_WINDOW: Final = "digest_window"
CONF_STARTUP_GRACE: Final = "startup_grace"
CONF_REMINDER: Final = "reminder"
CONF_SNOOZE_DURATION: Final = "snooze_duration"
CONF_QUIET_START: Final = "quiet_start"
CONF_QUIET_END: Final = "quiet_end"
CONF_PRESENCE: Final = "presence"
CONF_CLEAR_WHEN_RESOLVED: Final = "clear_when_resolved"
CONF_CRITICAL_VOLUME: Final = "critical_volume"
CONF_URL: Final = "url"
CONF_TAG: Final = "tag"
CONF_ALERTS: Final = "alerts"
CONF_CONTROL: Final = "control"
CONF_ROOMS: Final = "rooms"

# Rooms.
CONF_NAME: Final = "name"
CONF_TEMPERATURE: Final = "temperature"
CONF_CO2: Final = "co2"
CONF_HUMIDITY: Final = "humidity"
CONF_OPENINGS: Final = "openings"
CONF_CLIMATE: Final = "climate"
CONF_FANS: Final = "fans"
CONF_PURIFIERS: Final = "purifiers"
CONF_ENTITY_ID: Final = "entity_id"

# Alert settings.
CONF_ENABLED: Final = "enabled"
CONF_THRESHOLD: Final = "threshold"
CONF_HYSTERESIS: Final = "hysteresis"
CONF_DELAY: Final = "delay"
CONF_SEVERITY: Final = "severity"
CONF_ESCALATION: Final = "escalation"
CONF_MIN_OUTDOOR: Final = "min_outdoor"
CONF_MAX_OUTDOOR: Final = "max_outdoor"
CONF_MIN_INDOOR: Final = "min_indoor"

# Control settings.
CONF_START: Final = "start"
CONF_END: Final = "end"
CONF_MANUAL_OVERRIDE: Final = "manual_override"
CONF_SUPPRESS_HANDLED: Final = "suppress_when_handled"
CONF_COOL_ABOVE: Final = "cool_above"
CONF_OFF_BELOW: Final = "off_below"
CONF_ON_ABOVE: Final = "on_above"
CONF_SETPOINT: Final = "setpoint"
CONF_FAN_MODE: Final = "fan_mode"
CONF_CLOSED_FOR: Final = "closed_for"
CONF_OFF_ON_OPEN: Final = "off_on_open"
CONF_PERCENTAGE: Final = "percentage"
CONF_PRESET: Final = "preset"
CONF_OPEN_PERCENTAGE: Final = "open_percentage"
CONF_OPEN_PRESET: Final = "open_preset"
CONF_OFF_PRESET: Final = "off_preset"
CONF_CLOSED_PRESET: Final = "closed_preset"
CONF_MODE_SELECT: Final = "mode_select"
CONF_OPEN_MODE: Final = "open_mode"
CONF_CLOSED_MODE: Final = "closed_mode"
CONF_KEEP_ON: Final = "keep_on"

# Alert kinds, in display order.
KIND_TOO_HOT: Final = "too_hot"
KIND_TOO_COLD: Final = "too_cold"
KIND_VENTILATE: Final = "ventilate"
KIND_CLOSE_WINDOWS: Final = "close_windows"
KIND_WINDOW_OPEN_COLD: Final = "window_open_cold"
KIND_CO2: Final = "co2_high"
KIND_HUMIDITY: Final = "humidity_high"
KINDS: Final = (
    KIND_TOO_HOT,
    KIND_CLOSE_WINDOWS,
    KIND_VENTILATE,
    KIND_TOO_COLD,
    KIND_WINDOW_OPEN_COLD,
    KIND_CO2,
    KIND_HUMIDITY,
)

SEVERITY_INFO: Final = "info"
SEVERITY_WARNING: Final = "warning"
SEVERITY_CRITICAL: Final = "critical"
SEVERITIES: Final = (SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_CRITICAL)

AGGREGATES: Final = ("min", "max", "mean")

# Defaults. Durations are minutes.
DEFAULT_DIGEST_WINDOW: Final = 5
DEFAULT_STARTUP_GRACE: Final = 10
DEFAULT_REMINDER: Final = 0
DEFAULT_SNOOZE: Final = 240
DEFAULT_MANUAL_OVERRIDE: Final = 60
DEFAULT_CRITICAL_VOLUME: Final = 0.5
DEFAULT_TAG: Final = "smart_comfort"
MAX_MINUTES: Final = 1440

DEFAULT_ALERTS: Final[dict[str, dict]] = {
    # Room above the threshold.
    KIND_TOO_HOT: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 27.0,
        CONF_HYSTERESIS: 0.5,
        CONF_DELAY: 15,
        CONF_SEVERITY: SEVERITY_WARNING,
        CONF_ESCALATION: 1.0,
    },
    # Room below the threshold.
    KIND_TOO_COLD: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 17.0,
        CONF_HYSTERESIS: 0.5,
        CONF_DELAY: 15,
        CONF_SEVERITY: SEVERITY_WARNING,
        CONF_ESCALATION: 1.0,
    },
    # Room warm (threshold) and warmer than outside by the margin, openings closed: open them.
    KIND_VENTILATE: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 2.0,
        CONF_MIN_INDOOR: 24.0,
        CONF_HYSTERESIS: 0.5,
        CONF_DELAY: 15,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 2.0,
    },
    # Opening open while outside is warmer than the room by the margin, and at least min_outdoor.
    KIND_CLOSE_WINDOWS: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 0.5,
        CONF_MIN_OUTDOOR: 25.0,
        CONF_HYSTERESIS: 0.3,
        CONF_DELAY: 5,
        CONF_SEVERITY: SEVERITY_WARNING,
        CONF_ESCALATION: 2.0,
    },
    # Opening open for the delay while outside is at most max_outdoor.
    KIND_WINDOW_OPEN_COLD: {
        CONF_ENABLED: False,
        CONF_MAX_OUTDOOR: 12.0,
        CONF_HYSTERESIS: 0.5,
        CONF_DELAY: 20,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 0,
    },
    KIND_CO2: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 1200.0,
        CONF_HYSTERESIS: 150.0,
        CONF_DELAY: 10,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 400.0,
    },
    KIND_HUMIDITY: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 70.0,
        CONF_HYSTERESIS: 5.0,
        CONF_DELAY: 15,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 10.0,
    },
}

DEFAULT_CONTROL: Final[dict] = {
    CONF_ENABLED: True,
    # Window boosts (fans and purifiers at full speed when an opening is open) only in these hours.
    CONF_START: "09:00",
    CONF_END: "21:00",
    CONF_MANUAL_OVERRIDE: DEFAULT_MANUAL_OVERRIDE,
    CONF_SUPPRESS_HANDLED: True,
    CONF_CLIMATE: {
        CONF_COOL_ABOVE: 23.0,
        CONF_OFF_BELOW: 21.0,
        CONF_SETPOINT: 22.0,
        CONF_FAN_MODE: None,
        CONF_CLOSED_FOR: 2,
        CONF_OFF_ON_OPEN: 1,
    },
    CONF_FANS: {
        CONF_ON_ABOVE: 23.0,
        CONF_OFF_BELOW: 22.0,
        CONF_PERCENTAGE: 50,
        CONF_PRESET: None,
        CONF_OPEN_PERCENTAGE: 100,
        CONF_OPEN_PRESET: None,
        CONF_OFF_PRESET: None,
    },
    CONF_PURIFIERS: {
        CONF_OPEN_PERCENTAGE: 100,
        CONF_OPEN_PRESET: None,
        CONF_CLOSED_PRESET: None,
        CONF_MODE_SELECT: None,
        CONF_OPEN_MODE: None,
        CONF_CLOSED_MODE: None,
        CONF_KEEP_ON: False,
    },
}

# Seconds.
EVALUATE_INTERVAL: Final = 30
DEBOUNCE: Final = 3
NOTIFY_TIMEOUT: Final = 20
SERVICE_TIMEOUT: Final = 15
KEEP_ON_DELAY: Final = 10
# Minutes after which an unavailable opening is left out of its room instead of blocking it.
OPENING_UNAVAILABLE: Final = 10
# Minutes before a failed device command is tried again, doubled at each new failure up to the maximum.
COMMAND_RETRY: Final = 5
COMMAND_RETRY_MAX: Final = 60

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = DOMAIN

ACTION_SNOOZE: Final = "SMART_COMFORT_SNOOZE"
ACTION_ACK: Final = "SMART_COMFORT_ACK"

SERVICE_SNOOZE: Final = "snooze"
SERVICE_UNSNOOZE: Final = "unsnooze"
SERVICE_ACKNOWLEDGE: Final = "acknowledge"
SERVICE_NOTIFY_NOW: Final = "notify_now"

EVENT_NOTIFIED: Final = f"{DOMAIN}_notified"
EVENT_CONTROL: Final = f"{DOMAIN}_control"

PANEL_URL: Final = "smart-comfort"
PANEL_ICON: Final = "mdi:home-thermometer"
# Dispatched after every evaluation and setup/unload of the entry (configuration panel status).
SIGNAL_UPDATE: Final = f"{DOMAIN}_update"
