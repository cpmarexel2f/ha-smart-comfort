"""Config flow: a single entry; YAML import, and options for everything (rooms, alerts, control)."""

from __future__ import annotations

import copy
import logging
from collections.abc import Iterable
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)

from . import const as k
from .config import build_settings, slugify
from .schema import OPTIONS

_LOGGER = logging.getLogger(__name__)

# Room form: overrides of the room, stored in room.alerts / room.control.
ROOM_OVERRIDES = "overrides"
OV_TOO_HOT = "too_hot_threshold"
OV_TOO_COLD = "too_cold_threshold"
OV_FAN_PRESET = "fan_preset"
OV_FAN_OPEN_PRESET = "fan_open_preset"
OV_FAN_OFF_PRESET = "fan_off_preset"
OV_PUR_OPEN_PRESET = "purifier_open_preset"
OV_PUR_CLOSED_PRESET = "purifier_closed_preset"
OV_PUR_SELECT = "purifier_mode_select"
OV_PUR_OPEN_MODE = "purifier_open_mode"
OV_PUR_CLOSED_MODE = "purifier_closed_mode"
OV_PUR_KEEP_ON = "purifier_keep_on"


def _minutes(minimum: int = 0) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum, max=k.MAX_MINUTES, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min"
        )
    )


def _number(unit: str | None = None, step: float = 0.1, minimum: float = -50, maximum: float = 5000) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=NumberSelectorMode.BOX, unit_of_measurement=unit)
    )


PERCENT = NumberSelector(
    NumberSelectorConfig(min=0, max=100, step=1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%")
)
TEXT = TextSelector()


def _entity(domain: str | list[str], multiple: bool = False, device_class: str | None = None) -> EntitySelector:
    config: dict[str, Any] = {"domain": domain, "multiple": multiple}
    if device_class:
        config["device_class"] = device_class
    return EntitySelector(EntitySelectorConfig(**config))


def _select(options: list[str], key: str, multiple: bool = False, custom: bool = False) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            multiple=multiple,
            custom_value=custom,
            translation_key=key,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _opt(key: str, value: Any) -> vol.Optional:
    """Optional field pre-filled with value (left empty when None)."""
    return (
        vol.Optional(key, description={"suggested_value": value}) if value not in (None, "", []) else vol.Optional(key)
    )


def _clean(data: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Drop empty values: missing means default.

    A field emptied in the form whose default is a value is kept as None instead, so that it stays empty
    (a fan without temperature control, no boost hours…) rather than coming back to the default.
    """
    out = {key: value for key, value in data.items() if value not in (None, "", [])}
    for key in _nullable(defaults or {}):
        out.setdefault(key, None)
    return out


def _nullable(defaults: dict[str, Any]) -> Iterable[str]:
    return [key for key, value in defaults.items() if value is not None and not isinstance(value, (bool, dict))]


def _notify_options(hass: HomeAssistant, current: list[str]) -> list[str]:
    names = {f"notify.{n}" for n in hass.services.async_services_for_domain("notify")}
    return sorted((names - {"notify.send_message", "notify.persistent_notification"}) | set(current))


def _general_schema(hass: HomeAssistant, o: dict[str, Any], first: bool = False) -> vol.Schema:
    notify = list(o.get(k.CONF_NOTIFY, []))
    schema: dict[Any, Any] = {
        vol.Optional(k.CONF_NOTIFY, default=notify): SelectSelector(
            SelectSelectorConfig(
                options=_notify_options(hass, notify),
                multiple=True,
                custom_value=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(k.CONF_OUTDOOR, default=list(o.get(k.CONF_OUTDOOR, []))): _entity(
            ["sensor", "weather"], multiple=True
        ),
        vol.Required(k.CONF_OUTDOOR_AGGREGATE, default=o.get(k.CONF_OUTDOOR_AGGREGATE, "min")): _select(
            list(k.AGGREGATES), k.CONF_OUTDOOR_AGGREGATE
        ),
    }
    if first:
        return vol.Schema(schema)
    schema.update(
        {
            vol.Required(
                k.CONF_DIGEST_WINDOW, default=o.get(k.CONF_DIGEST_WINDOW, k.DEFAULT_DIGEST_WINDOW)
            ): _minutes(),
            vol.Required(k.CONF_REMINDER, default=o.get(k.CONF_REMINDER, k.DEFAULT_REMINDER)): _minutes(),
            vol.Required(k.CONF_SNOOZE_DURATION, default=o.get(k.CONF_SNOOZE_DURATION, k.DEFAULT_SNOOZE)): _minutes(1),
            vol.Required(
                k.CONF_STARTUP_GRACE, default=o.get(k.CONF_STARTUP_GRACE, k.DEFAULT_STARTUP_GRACE)
            ): _minutes(),
            _opt(k.CONF_QUIET_START, o.get(k.CONF_QUIET_START)): TimeSelector(),
            _opt(k.CONF_QUIET_END, o.get(k.CONF_QUIET_END)): TimeSelector(),
            _opt(k.CONF_PRESENCE, o.get(k.CONF_PRESENCE)): _entity(
                ["zone", "person", "group", "binary_sensor", "input_boolean", "device_tracker"]
            ),
            vol.Required(
                k.CONF_CLEAR_WHEN_RESOLVED, default=o.get(k.CONF_CLEAR_WHEN_RESOLVED, True)
            ): BooleanSelector(),
            vol.Required(
                k.CONF_CRITICAL_VOLUME, default=o.get(k.CONF_CRITICAL_VOLUME, k.DEFAULT_CRITICAL_VOLUME)
            ): NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05, mode=NumberSelectorMode.SLIDER)),
            _opt(k.CONF_URL, o.get(k.CONF_URL)): TEXT,
            vol.Required(k.CONF_TAG, default=o.get(k.CONF_TAG, k.DEFAULT_TAG)): TEXT,
        }
    )
    return vol.Schema(schema)


def _alert_schema(kind: str, current: dict[str, Any]) -> vol.Schema:
    d = {**k.DEFAULT_ALERTS[kind], **current}
    unit = {"co2_high": "ppm", "humidity_high": "%"}.get(kind, "°C")
    schema: dict[Any, Any] = {vol.Required(k.CONF_ENABLED, default=d[k.CONF_ENABLED]): BooleanSelector()}
    if k.CONF_THRESHOLD in k.DEFAULT_ALERTS[kind]:
        schema[vol.Required(k.CONF_THRESHOLD, default=d[k.CONF_THRESHOLD])] = _number(unit)
    for key in (k.CONF_MIN_INDOOR, k.CONF_MIN_OUTDOOR, k.CONF_MAX_OUTDOOR):
        if key in k.DEFAULT_ALERTS[kind]:
            schema[_opt(key, d[key])] = _number("°C")
    schema.update(
        {
            vol.Required(k.CONF_HYSTERESIS, default=d[k.CONF_HYSTERESIS]): _number(unit, minimum=0),
            vol.Required(k.CONF_DELAY, default=d[k.CONF_DELAY]): _minutes(),
            vol.Required(k.CONF_SEVERITY, default=d[k.CONF_SEVERITY]): _select(list(k.SEVERITIES), k.CONF_SEVERITY),
            vol.Required(k.CONF_ESCALATION, default=d[k.CONF_ESCALATION]): _number(unit, minimum=0),
        }
    )
    return vol.Schema(schema)


def _control_schema(c: dict[str, Any]) -> vol.Schema:
    d = {**k.DEFAULT_CONTROL, **c}
    cl = {**k.DEFAULT_CONTROL[k.CONF_CLIMATE], **(c.get(k.CONF_CLIMATE) or {})}
    fa = {**k.DEFAULT_CONTROL[k.CONF_FANS], **(c.get(k.CONF_FANS) or {})}
    pu = {**k.DEFAULT_CONTROL[k.CONF_PURIFIERS], **(c.get(k.CONF_PURIFIERS) or {})}
    return vol.Schema(
        {
            vol.Required(k.CONF_ENABLED, default=d[k.CONF_ENABLED]): BooleanSelector(),
            _opt(k.CONF_START, d[k.CONF_START]): TimeSelector(),
            _opt(k.CONF_END, d[k.CONF_END]): TimeSelector(),
            vol.Required(k.CONF_MANUAL_OVERRIDE, default=d[k.CONF_MANUAL_OVERRIDE]): _minutes(),
            vol.Required(k.CONF_SUPPRESS_HANDLED, default=d[k.CONF_SUPPRESS_HANDLED]): BooleanSelector(),
            vol.Required(k.CONF_CLIMATE): section(
                vol.Schema(
                    {
                        vol.Required(k.CONF_COOL_ABOVE, default=cl[k.CONF_COOL_ABOVE]): _number("°C"),
                        vol.Required(k.CONF_OFF_BELOW, default=cl[k.CONF_OFF_BELOW]): _number("°C"),
                        vol.Required(k.CONF_SETPOINT, default=cl[k.CONF_SETPOINT]): _number("°C", step=0.5),
                        _opt(k.CONF_FAN_MODE, cl[k.CONF_FAN_MODE]): TEXT,
                        vol.Required(k.CONF_CLOSED_FOR, default=cl[k.CONF_CLOSED_FOR]): _minutes(),
                        vol.Required(k.CONF_OFF_ON_OPEN, default=cl[k.CONF_OFF_ON_OPEN]): _minutes(),
                    }
                ),
                {"collapsed": True},
            ),
            vol.Required(k.CONF_FANS): section(
                vol.Schema(
                    {
                        _opt(k.CONF_ON_ABOVE, fa[k.CONF_ON_ABOVE]): _number("°C"),
                        _opt(k.CONF_OFF_BELOW, fa[k.CONF_OFF_BELOW]): _number("°C"),
                        _opt(k.CONF_PERCENTAGE, fa[k.CONF_PERCENTAGE]): PERCENT,
                        _opt(k.CONF_PRESET, fa[k.CONF_PRESET]): TEXT,
                        _opt(k.CONF_OPEN_PERCENTAGE, fa[k.CONF_OPEN_PERCENTAGE]): PERCENT,
                        _opt(k.CONF_OPEN_PRESET, fa[k.CONF_OPEN_PRESET]): TEXT,
                        _opt(k.CONF_OFF_PRESET, fa[k.CONF_OFF_PRESET]): TEXT,
                    }
                ),
                {"collapsed": True},
            ),
            vol.Required(k.CONF_PURIFIERS): section(
                vol.Schema(
                    {
                        _opt(k.CONF_OPEN_PERCENTAGE, pu[k.CONF_OPEN_PERCENTAGE]): PERCENT,
                        _opt(k.CONF_OPEN_PRESET, pu[k.CONF_OPEN_PRESET]): TEXT,
                        _opt(k.CONF_CLOSED_PRESET, pu[k.CONF_CLOSED_PRESET]): TEXT,
                        vol.Required(k.CONF_KEEP_ON, default=pu[k.CONF_KEEP_ON]): BooleanSelector(),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


def _room_schema(room: dict[str, Any]) -> vol.Schema:
    alerts = room.get(k.CONF_ALERTS) or {}
    control = room.get(k.CONF_CONTROL) or {}
    fans = control.get(k.CONF_FANS) or {}
    pur = control.get(k.CONF_PURIFIERS) or {}

    def ids(key: str) -> list[str]:
        raw = room.get(key) or []
        raw = [raw] if isinstance(raw, (str, dict)) else raw
        return [i if isinstance(i, str) else i[k.CONF_ENTITY_ID] for i in raw]

    climate = ids(k.CONF_CLIMATE)
    return vol.Schema(
        {
            vol.Required(k.CONF_NAME, default=room.get(k.CONF_NAME, "")): TEXT,
            _opt(k.CONF_TEMPERATURE, room.get(k.CONF_TEMPERATURE)): _entity("sensor", device_class="temperature"),
            _opt(k.CONF_CO2, room.get(k.CONF_CO2)): _entity("sensor", device_class="carbon_dioxide"),
            _opt(k.CONF_HUMIDITY, room.get(k.CONF_HUMIDITY)): _entity("sensor", device_class="humidity"),
            _opt(k.CONF_OPENINGS, list(room.get(k.CONF_OPENINGS) or [])): _entity("binary_sensor", multiple=True),
            _opt(k.CONF_CLIMATE, climate[0] if climate else None): _entity("climate"),
            _opt(k.CONF_FANS, ids(k.CONF_FANS)): _entity("fan", multiple=True),
            _opt(k.CONF_PURIFIERS, ids(k.CONF_PURIFIERS)): _entity("fan", multiple=True),
            vol.Required(ROOM_OVERRIDES): section(
                vol.Schema(
                    {
                        _opt(OV_TOO_HOT, (alerts.get(k.KIND_TOO_HOT) or {}).get(k.CONF_THRESHOLD)): _number("°C"),
                        _opt(OV_TOO_COLD, (alerts.get(k.KIND_TOO_COLD) or {}).get(k.CONF_THRESHOLD)): _number("°C"),
                        _opt(OV_FAN_PRESET, fans.get(k.CONF_PRESET)): TEXT,
                        _opt(OV_FAN_OPEN_PRESET, fans.get(k.CONF_OPEN_PRESET)): TEXT,
                        _opt(OV_FAN_OFF_PRESET, fans.get(k.CONF_OFF_PRESET)): TEXT,
                        _opt(OV_PUR_OPEN_PRESET, pur.get(k.CONF_OPEN_PRESET)): TEXT,
                        _opt(OV_PUR_CLOSED_PRESET, pur.get(k.CONF_CLOSED_PRESET)): TEXT,
                        _opt(OV_PUR_SELECT, pur.get(k.CONF_MODE_SELECT)): _entity("select"),
                        _opt(OV_PUR_OPEN_MODE, pur.get(k.CONF_OPEN_MODE)): TEXT,
                        _opt(OV_PUR_CLOSED_MODE, pur.get(k.CONF_CLOSED_MODE)): TEXT,
                        _opt(OV_PUR_KEEP_ON, pur.get(k.CONF_KEEP_ON)): BooleanSelector(),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


def _unique_id(base: str, used: list[str]) -> str:
    room_id, n = base, 2
    while room_id in used:
        room_id, n = f"{base}_{n}", n + 1
    return room_id


def _keep_items(old: Any, new_ids: list[str]) -> list[Any]:
    """Device list from the form, keeping the per-device overrides set in YAML."""
    old = [old] if isinstance(old, (str, dict)) else (old or [])
    by_id = {i[k.CONF_ENTITY_ID]: i for i in old if isinstance(i, dict)}
    return [by_id.get(e, e) for e in new_ids]


def _room_from_form(user_input: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    room = copy.deepcopy(old)
    room[k.CONF_NAME] = user_input[k.CONF_NAME].strip()
    for key in (k.CONF_TEMPERATURE, k.CONF_CO2, k.CONF_HUMIDITY):
        if user_input.get(key):
            room[key] = user_input[key]
        else:
            room.pop(key, None)
    room[k.CONF_OPENINGS] = list(user_input.get(k.CONF_OPENINGS) or [])
    climate = user_input.get(k.CONF_CLIMATE)
    old_climate = old.get(k.CONF_CLIMATE)
    if climate:
        room[k.CONF_CLIMATE] = (
            old_climate if isinstance(old_climate, dict) and old_climate.get(k.CONF_ENTITY_ID) == climate else climate
        )
    else:
        room.pop(k.CONF_CLIMATE, None)
    room[k.CONF_FANS] = _keep_items(old.get(k.CONF_FANS), list(user_input.get(k.CONF_FANS) or []))
    room[k.CONF_PURIFIERS] = _keep_items(old.get(k.CONF_PURIFIERS), list(user_input.get(k.CONF_PURIFIERS) or []))

    ov = user_input.get(ROOM_OVERRIDES) or {}
    alerts = room.setdefault(k.CONF_ALERTS, {})
    for kind, key in ((k.KIND_TOO_HOT, OV_TOO_HOT), (k.KIND_TOO_COLD, OV_TOO_COLD)):
        section_data = dict(alerts.get(kind) or {})
        if ov.get(key) is not None:
            section_data[k.CONF_THRESHOLD] = float(ov[key])
        else:
            section_data.pop(k.CONF_THRESHOLD, None)
        alerts[kind] = section_data
    control = room.setdefault(k.CONF_CONTROL, {})
    fans = dict(control.get(k.CONF_FANS) or {})
    pur = dict(control.get(k.CONF_PURIFIERS) or {})
    for target, key, form_key in (
        (fans, k.CONF_PRESET, OV_FAN_PRESET),
        (fans, k.CONF_OPEN_PRESET, OV_FAN_OPEN_PRESET),
        (fans, k.CONF_OFF_PRESET, OV_FAN_OFF_PRESET),
        (pur, k.CONF_OPEN_PRESET, OV_PUR_OPEN_PRESET),
        (pur, k.CONF_CLOSED_PRESET, OV_PUR_CLOSED_PRESET),
        (pur, k.CONF_MODE_SELECT, OV_PUR_SELECT),
        (pur, k.CONF_OPEN_MODE, OV_PUR_OPEN_MODE),
        (pur, k.CONF_CLOSED_MODE, OV_PUR_CLOSED_MODE),
        (pur, k.CONF_KEEP_ON, OV_PUR_KEEP_ON),
    ):
        if ov.get(form_key) not in (None, ""):
            target[key] = ov[form_key]
        else:
            target.pop(key, None)
    control[k.CONF_FANS], control[k.CONF_PURIFIERS] = fans, pur
    # Empty sections are dropped, the room stays minimal.
    room[k.CONF_ALERTS] = {key: value for key, value in alerts.items() if value}
    room[k.CONF_CONTROL] = {key: value for key, value in control.items() if value}
    return {key: value for key, value in room.items() if value not in (None, "", [], {})}


class SmartComfortConfigFlow(ConfigFlow, domain=k.DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(k.DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        schema = _general_schema(self.hass, {}, first=True)
        if user_input is not None:
            try:
                options = OPTIONS(_clean(user_input))
            except vol.Invalid as err:
                _LOGGER.debug("Invalid options: %s", err)
                errors["base"] = "invalid_options"
                schema = self.add_suggested_values_to_schema(schema, user_input)
            else:
                return self.async_create_entry(title=k.TITLE, data={}, options=options)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """First YAML import; later changes of the YAML are applied by async_import_yaml."""
        await self.async_set_unique_id(k.DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=k.TITLE, data={"yaml_hash": import_data["yaml_hash"]}, options=import_data["options"]
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SmartComfortOptionsFlow()


class SmartComfortOptionsFlow(OptionsFlow):
    """Menu: general, alerts, control, rooms."""

    def __init__(self) -> None:
        self._options: dict[str, Any] | None = None
        self._kind: str | None = None
        self._room: int | None = None

    @property
    def options(self) -> dict[str, Any]:
        if self._options is None:
            self._options = copy.deepcopy(dict(self.config_entry.options))
        return self._options

    def _save(self, options: dict[str, Any]) -> ConfigFlowResult | None:
        """Save the new options, None when they are invalid (the step shows its form again with an error)."""
        try:
            validated = OPTIONS(options)
        except vol.Invalid as err:
            _LOGGER.debug("Invalid options: %s", err)
            return None
        self._options = options
        return self.async_create_entry(data=validated)

    def _form(
        self, step_id: str, schema: vol.Schema, user_input: dict[str, Any] | None, **kwargs: Any
    ) -> ConfigFlowResult:
        """The form of a step, again with the values entered and an error when they could not be saved."""
        errors: dict[str, str] = kwargs.pop("errors", None) or {}
        if user_input is not None:
            errors = errors or {"base": "invalid_options"}
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors, **kwargs)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["general", "alerts", "control", "add_room"]
        if self.options.get(k.CONF_ROOMS):
            menu += ["edit_room", "remove_room"]
        return self.async_show_menu(
            step_id="init",
            menu_options=menu,
            description_placeholders={"rooms": str(len(self.options.get(k.CONF_ROOMS) or []))},
        )

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            keep = {
                key: copy.deepcopy(self.options[key])
                for key in (k.CONF_ALERTS, k.CONF_CONTROL, k.CONF_ROOMS)
                if key in self.options
            }
            if (result := self._save({**_clean(user_input), **keep})) is not None:
                return result
        return self._form("general", _general_schema(self.hass, self.options), user_input)

    async def async_step_alerts(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._kind = user_input["kind"]
            return await self.async_step_alert()
        return self.async_show_form(
            step_id="alerts", data_schema=vol.Schema({vol.Required("kind"): _select(list(k.KINDS), "kind")})
        )

    async def async_step_alert(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        kind = self._kind or k.KINDS[0]
        if user_input is not None:
            options = copy.deepcopy(self.options)
            options.setdefault(k.CONF_ALERTS, {})[kind] = _clean(user_input, k.DEFAULT_ALERTS[kind]) | {
                k.CONF_ENABLED: user_input[k.CONF_ENABLED]
            }
            if (result := self._save(options)) is not None:
                return result
        return self._form(
            "alert",
            _alert_schema(kind, (self.options.get(k.CONF_ALERTS) or {}).get(kind) or {}),
            user_input,
            description_placeholders={"kind": kind},
            last_step=True,
        )

    async def async_step_control(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            control = _clean(
                {key: value for key, value in user_input.items() if not isinstance(value, dict)}, k.DEFAULT_CONTROL
            )
            for key in (k.CONF_ENABLED, k.CONF_SUPPRESS_HANDLED):
                control[key] = user_input[key]
            for key in (k.CONF_CLIMATE, k.CONF_FANS, k.CONF_PURIFIERS):
                control[key] = _clean(user_input.get(key) or {}, k.DEFAULT_CONTROL[key])
            if (result := self._save({**copy.deepcopy(self.options), k.CONF_CONTROL: control})) is not None:
                return result
        return self._form("control", _control_schema(self.options.get(k.CONF_CONTROL) or {}), user_input)

    def _room_names(self) -> list[dict[str, str]]:
        return [{"value": str(i), "label": r[k.CONF_NAME]} for i, r in enumerate(self.options.get(k.CONF_ROOMS) or [])]

    async def async_step_add_room(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._room_form("add_room", user_input, None)

    async def async_step_edit_room(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._room = int(user_input["room"])
            return await self.async_step_room()
        return self.async_show_form(
            step_id="edit_room",
            data_schema=vol.Schema(
                {vol.Required("room"): SelectSelector(SelectSelectorConfig(options=self._room_names()))}
            ),
        )

    async def async_step_room(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._room_form("room", user_input, self._room)

    async def _room_form(self, step_id: str, user_input: dict[str, Any] | None, index: int | None) -> ConfigFlowResult:
        rooms = self.options.get(k.CONF_ROOMS) or []
        old = rooms[index] if index is not None else {}
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[k.CONF_NAME].strip()
            others = [slugify(r[k.CONF_NAME]) for i, r in enumerate(rooms) if i != index]
            if not name:
                errors[k.CONF_NAME] = "name_required"
            elif slugify(name) in others:
                errors[k.CONF_NAME] = "name_exists"
            else:
                options = copy.deepcopy(self.options)
                new_rooms = options.setdefault(k.CONF_ROOMS, [])
                room = _room_from_form(user_input, old)
                # A stable id: renaming the room keeps its sensor, its alerts and its snoozes.
                ids = [r.id for r in build_settings(self.options).rooms]
                if index is None:
                    room["id"] = _unique_id(slugify(name), ids)
                    new_rooms.append(room)
                else:
                    room.setdefault("id", ids[index])
                    new_rooms[index] = room
                if (result := self._save(options)) is not None:
                    return result
                errors["base"] = "invalid_options"
        return self._form(step_id, _room_schema(old), user_input, errors=errors, last_step=True)

    async def async_step_remove_room(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            remove = {int(i) for i in user_input.get("rooms") or []}
            options = copy.deepcopy(self.options)
            options[k.CONF_ROOMS] = [r for i, r in enumerate(options.get(k.CONF_ROOMS) or []) if i not in remove]
            if (result := self._save(options)) is not None:
                return result
        return self._form(
            "remove_room",
            vol.Schema(
                {
                    vol.Optional("rooms", default=[]): SelectSelector(
                        SelectSelectorConfig(options=self._room_names(), multiple=True)
                    )
                }
            ),
            user_input,
        )
