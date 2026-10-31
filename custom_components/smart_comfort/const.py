"""Constants for Smart Comfort."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "smart_comfort"
TITLE: Final = "Smart Comfort"

# Top-level options (same keys in YAML and in the config entry options).
CONF_NOTIFY: Final = "notify"
CONF_OUTDOOR: Final = "outdoor_temperature"
CONF_OUTDOOR_AGGREGATE: Final = "outdoor_aggregate"
CONF_OUTDOOR_NOISE: Final = "outdoor_noise"
CONF_OUTDOOR_AIR: Final = "outdoor_air_quality"
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
# Outdoor places (garden, terrace…): their sensors give the outdoor temperature, air quality and noise.
CONF_OUTDOORS: Final = "outdoors"
# Adaptive lighting: brightness (and warmth) of the lights that are on, by time of day.
CONF_LIGHTING: Final = "lighting"

# Rooms.
CONF_NAME: Final = "name"
CONF_AREA: Final = "area"
CONF_TEMPERATURE: Final = "temperature"
CONF_CO2: Final = "co2"
CONF_HUMIDITY: Final = "humidity"
CONF_NOISE: Final = "noise"
CONF_OPENINGS: Final = "openings"
CONF_CLIMATE: Final = "climate"
CONF_FANS: Final = "fans"
CONF_PURIFIERS: Final = "purifiers"
CONF_ENTITY_ID: Final = "entity_id"
CONF_AIR_QUALITY: Final = "air_quality"
CONF_LIGHTS: Final = "lights"

# Lighting settings.
CONF_DAY: Final = "day"
CONF_EVENING: Final = "evening"
CONF_NIGHT: Final = "night"
CONF_WARMTH: Final = "warmth"
CONF_DAY_KELVIN: Final = "day_kelvin"
CONF_EVENING_KELVIN: Final = "evening_kelvin"
CONF_NIGHT_KELVIN: Final = "night_kelvin"
CONF_TRANSITION: Final = "transition"
CONF_NIGHT_ONLY: Final = "night_only"
CONF_MORNING: Final = "morning"
CONF_MORNING_KELVIN: Final = "morning_kelvin"
CONF_MORNING_END: Final = "morning_end"
CONF_QUIET_MORNING: Final = "quiet_morning"
CONF_NAP: Final = "nap"
CONF_NAP_KELVIN: Final = "nap_kelvin"
# Nap slots of a room: start, end and optionally the days (mon … sun).
CONF_NAPS: Final = "naps"
CONF_DAYS: Final = "days"
WEEKDAYS: Final = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# Lights on presence, per room: its sensors, the lights (all those of the room when none), a light level sensor
# and the level above which no light is turned on, the minutes without presence before turning them off, the
# lights left off during the naps of the house, and slots that set the brightness of some lights, or keep them off.
CONF_PRESENCE_LIGHTS: Final = "presence"
CONF_SENSORS: Final = "sensors"
CONF_LUX: Final = "lux"
CONF_MAX_LUX: Final = "max_lux"
CONF_OFF_AFTER: Final = "off_after"
CONF_NOT_DURING_NAPS: Final = "not_during_naps"
CONF_SLOTS: Final = "slots"
CONF_BRIGHTNESS: Final = "brightness"
CONF_OFF: Final = "off"
DEFAULT_OFF_AFTER: Final = 2

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
CONF_MAX_NOISE: Final = "max_outdoor_noise"
CONF_MAX_AIR: Final = "max_outdoor_air"

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
# Quiet night: devices quieter between night_start and night_end.
CONF_NIGHT_START: Final = "night_start"
CONF_NIGHT_END: Final = "night_end"
CONF_NIGHT_FAN_MODE: Final = "night_fan_mode"
CONF_NIGHT_PERCENTAGE: Final = "night_percentage"
CONF_NIGHT_PRESET: Final = "night_preset"
CONF_NIGHT_MODE: Final = "night_mode"
# Indicator light or display of a device, off in its hours; time a device goes back to its normal state.
CONF_DISPLAY: Final = "display"
CONF_DISPLAY_OFF: Final = "display_off"
CONF_DISPLAY_ON: Final = "display_on"
CONF_RESET_AT: Final = "reset_at"
# Presence lights: the color of a slot, the seconds a presence must last before they turn on.
CONF_COLOR: Final = "color"
CONF_ON_AFTER: Final = "on_after"
DISPLAY_DOMAINS: Final = ("light", "switch", "number", "select")

# Alert kinds, in display order.
KIND_TOO_HOT: Final = "too_hot"
KIND_TOO_COLD: Final = "too_cold"
KIND_VENTILATE: Final = "ventilate"
KIND_CLOSE_WINDOWS: Final = "close_windows"
KIND_WINDOW_OPEN_COLD: Final = "window_open_cold"
KIND_CO2: Final = "co2_high"
KIND_HUMIDITY: Final = "humidity_high"
KIND_NOISE: Final = "noise_high"
KIND_NOISY_OUTSIDE: Final = "noisy_outside"
KIND_BAD_AIR_OUTSIDE: Final = "bad_air_outside"
KINDS: Final = (
    KIND_TOO_HOT,
    KIND_CLOSE_WINDOWS,
    KIND_VENTILATE,
    KIND_TOO_COLD,
    KIND_WINDOW_OPEN_COLD,
    KIND_CO2,
    KIND_HUMIDITY,
    KIND_NOISE,
    KIND_NOISY_OUTSIDE,
    KIND_BAD_AIR_OUTSIDE,
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
        # Not suggested while the outdoor noise is above this (with an outdoor noise sensor).
        CONF_MAX_NOISE: 65.0,
        # Nor while the outdoor air quality is worse than this level (1 good … 6 extremely poor).
        CONF_MAX_AIR: 3.0,
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
    # Room noise level above the threshold (sound pressure sensor, dB).
    KIND_NOISE: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 60.0,
        CONF_HYSTERESIS: 5.0,
        CONF_DELAY: 10,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 10.0,
    },
    # Opening open while the outdoor noise is above the threshold: close it.
    KIND_NOISY_OUTSIDE: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 65.0,
        CONF_HYSTERESIS: 5.0,
        CONF_DELAY: 5,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 10.0,
    },
    # Opening open while the outdoor air quality is worse than the threshold level (1 good … 6 extremely poor).
    KIND_BAD_AIR_OUTSIDE: {
        CONF_ENABLED: True,
        CONF_THRESHOLD: 3.0,
        CONF_HYSTERESIS: 0.5,
        CONF_DELAY: 5,
        CONF_SEVERITY: SEVERITY_INFO,
        CONF_ESCALATION: 1.0,
    },
}

DEFAULT_CONTROL: Final[dict] = {
    CONF_ENABLED: True,
    # Window boosts (fans and purifiers at full speed when an opening is open) only in these hours.
    CONF_START: "09:00",
    CONF_END: "21:00",
    CONF_MANUAL_OVERRIDE: DEFAULT_MANUAL_OVERRIDE,
    CONF_SUPPRESS_HANDLED: True,
    # Quiet night: the night settings of each device apply in these hours, and no window boost.
    CONF_NIGHT_START: "22:00",
    CONF_NIGHT_END: "07:00",
    # Indicator lights and displays of the devices: off in these hours (the quiet night when unset).
    CONF_DISPLAY_OFF: None,
    CONF_DISPLAY_ON: None,
    CONF_CLIMATE: {
        CONF_COOL_ABOVE: 23.0,
        CONF_OFF_BELOW: 21.0,
        CONF_SETPOINT: 22.0,
        CONF_FAN_MODE: None,
        CONF_CLOSED_FOR: 2,
        CONF_OFF_ON_OPEN: 1,
        CONF_NIGHT_FAN_MODE: None,
        CONF_DISPLAY: None,
        CONF_RESET_AT: None,
    },
    CONF_FANS: {
        CONF_ON_ABOVE: 23.0,
        CONF_OFF_BELOW: 22.0,
        CONF_PERCENTAGE: 50,
        CONF_PRESET: None,
        CONF_OPEN_PERCENTAGE: 100,
        CONF_OPEN_PRESET: None,
        CONF_OFF_PRESET: None,
        CONF_NIGHT_PERCENTAGE: None,
        CONF_NIGHT_PRESET: None,
        CONF_DISPLAY: None,
        CONF_RESET_AT: None,
    },
    CONF_PURIFIERS: {
        CONF_OPEN_PERCENTAGE: 100,
        CONF_OPEN_PRESET: None,
        CONF_CLOSED_PRESET: None,
        CONF_MODE_SELECT: None,
        CONF_OPEN_MODE: None,
        CONF_CLOSED_MODE: None,
        CONF_KEEP_ON: False,
        CONF_NIGHT_PERCENTAGE: None,
        CONF_NIGHT_PRESET: None,
        CONF_NIGHT_MODE: None,
        CONF_DISPLAY: None,
        CONF_RESET_AT: None,
    },
}

# Brightness (%) by time of day: day (sun up), evening (sun down), night (quiet night hours, control
# night_start/night_end); warmth in kelvin with the same steps, for the lights that support it.
DEFAULT_LIGHTING: Final[dict] = {
    CONF_ENABLED: True,
    CONF_DAY: 100,
    CONF_EVENING: 60,
    CONF_NIGHT: 15,
    CONF_WARMTH: True,
    CONF_DAY_KELVIN: 4000,
    CONF_EVENING_KELVIN: 2700,
    CONF_NIGHT_KELVIN: 2200,
    # Quiet morning of the rooms that have it (bedrooms): from the end of the night until morning_end.
    CONF_MORNING: 40,
    CONF_MORNING_KELVIN: 3000,
    CONF_MORNING_END: "09:30",
    CONF_QUIET_MORNING: False,
    # During the nap slots of a room.
    CONF_NAP: 15,
    CONF_NAP_KELVIN: 2200,
    # Seconds of the gradual changes (a light just turned on gets its brightness at once).
    CONF_TRANSITION: 120,
}
# Sun elevation (degrees) from which it is day, and under which it is evening; in between, a blend.
SUN_DAY: Final = 6.0
SUN_EVENING: Final = -6.0
# Smallest gap worth a command: brightness points, kelvin.
LIGHT_STEP: Final = 3
KELVIN_STEP: Final = 100

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
