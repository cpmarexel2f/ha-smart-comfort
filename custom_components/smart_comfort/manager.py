"""Home Assistant side: reads states, runs the engine and the controller, sends notifications and commands."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.core import CALLBACK_TYPE, Context, CoreState, Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .config import Room, Settings, in_window
from .const import (
    ACTION_ACK,
    ACTION_SNOOZE,
    DEBOUNCE,
    DOMAIN,
    EVALUATE_INTERVAL,
    EVENT_CONTROL,
    EVENT_NOTIFIED,
    NOTIFY_TIMEOUT,
    OPENING_UNAVAILABLE,
    SERVICE_TIMEOUT,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .control import Command, Controller, DeviceState, RoomContext
from .engine import Clear, Digest, Engine, Gates, RoomReading
from .message import format_text, render

_LOGGER = logging.getLogger(__name__)

BAD_STATES = (STATE_UNAVAILABLE, STATE_UNKNOWN, None, "")
# A device change right after a command of ours is its answer, not a manual change (polled integrations).
COMMAND_GRACE = timedelta(seconds=90)
INTERRUPTION = {SEVERITY_INFO: "passive", SEVERITY_WARNING: "time-sensitive", SEVERITY_CRITICAL: "critical"}


def _float(state: State | None) -> float | None:
    if state is None or state.state in BAD_STATES:
        return None
    try:
        return float(state.state)
    except ValueError:
        return None


def _temperature(state: State | None) -> float | None:
    """Temperature in °C of a sensor or a weather entity (its temperature attribute), converted from its unit."""
    if state is None or state.state in BAD_STATES:
        return None
    if state.domain == "weather":
        raw, unit = state.attributes.get("temperature"), state.attributes.get("temperature_unit")
    else:
        raw, unit = state.state, state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if unit in TemperatureConverter.VALID_UNITS and unit != UnitOfTemperature.CELSIUS:
        value = round(TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS), 2)
    return value


def present(state: State | None) -> bool:
    """Someone is home according to a zone, person, tracker, group or boolean entity. Unknown: yes."""
    if state is None or state.state in BAD_STATES:
        return True
    if state.domain == "zone":
        try:
            return int(state.state) > 0
        except ValueError:
            return True
    return state.state in ("home", "on", "true")


class SmartComfort:
    """One instance per config entry (there is only one)."""

    def __init__(self, hass: HomeAssistant, settings: Settings) -> None:
        self.hass = hass
        self.settings = settings
        self.engine = Engine(settings)
        self.controller = Controller(settings)
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.notifications_enabled = True
        self.control_enabled = True
        self.started_at: datetime | None = None
        self.last_notification: dict[str, Any] | None = None
        self.handled: set[str] = set()
        self._texts: dict[str, str] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._debounce: CALLBACK_TYPE | None = None
        self._lock = asyncio.Lock()
        self._contexts: deque[str] = deque(maxlen=200)
        self._commanded: dict[str, datetime] = {}
        self._stopped = False

    # Lifecycle.

    async def async_start(self, starting: bool) -> None:
        # After a reload, the state left by the previous instance (its delayed save may not be written yet).
        data = self.hass.data.get(DOMAIN, {}).pop("state", None) or await self.store.async_load() or {}
        self.engine.restore(data.get("engine") or {})
        self.controller.restore(data.get("control") or {})
        if (last := data.get("last_notification")) is not None:
            self.last_notification = last
        # Switches: known before the first evaluation, not only once the switch entities are restored.
        self.notifications_enabled = bool(data.get("notifications_enabled", True))
        self.control_enabled = bool(data.get("control_enabled", True))
        await self._load_texts()
        # The startup grace period counts from now when Home Assistant is starting, not on a reload.
        self.started_at = dt_util.utcnow() if starting else None
        self._track()
        self._unsubs.append(async_track_time_interval(self.hass, self._interval, timedelta(seconds=EVALUATE_INTERVAL)))
        self._unsubs.append(self.hass.bus.async_listen("mobile_app_notification_action", self._action))

    async def async_stop(self) -> None:
        """Stop, once the evaluation in progress (if any) is over, and hand the state to the next instance."""
        if self._stopped:
            return
        self._stopped = True
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._debounce:
            self._debounce()
            self._debounce = None
        async with self._lock:
            data = self._data()
            self.hass.data.setdefault(DOMAIN, {})["state"] = data
            await self.store.async_save(data)

    def _track(self) -> None:
        s = self.settings
        sensors = {e for r in s.rooms for e in r.sensors} | set(s.outdoor)
        if s.presence:
            sensors.add(s.presence)
        devices = {e for r in s.rooms for e in r.devices}
        selects = {p.mode_select for r in s.rooms for p in r.purifiers if p.mode_select}
        if entities := sorted(sensors | devices | selects):
            self._unsubs.append(async_track_state_change_event(self.hass, entities, self._state_changed))

    async def _load_texts(self) -> None:
        prefix = f"component.{DOMAIN}.common."
        try:
            raw = await async_get_translations(self.hass, self.hass.config.language, "common", [DOMAIN])
        except Exception:  # noqa: BLE001 - texts fall back to English
            _LOGGER.warning("Could not load the notification texts")
            raw = {}
        self._texts = {k.removeprefix(prefix): v for k, v in raw.items() if k.startswith(prefix)}

    # Listeners (entities).

    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def remove() -> None:
            self._listeners.remove(update)

        return remove

    @callback
    def _update_listeners(self) -> None:
        for update in list(self._listeners):
            update()

    @callback
    def save(self) -> None:
        if not self._stopped:
            self.store.async_delay_save(self._data, 5)

    def _data(self) -> dict[str, Any]:
        return {
            "engine": self.engine.as_dict(),
            "control": self.controller.as_dict(),
            "last_notification": self.last_notification,
            "notifications_enabled": self.notifications_enabled,
            "control_enabled": self.control_enabled,
        }

    # Triggers.

    @callback
    def _state_changed(self, event: Event) -> None:
        entity_id: str = event.data["entity_id"]
        if any(entity_id in r.devices for r in self.settings.rooms):
            self._device_changed(entity_id, event.data.get("old_state"), event.data.get("new_state"))
        if self._debounce is None and not self._stopped:
            self._debounce = async_call_later(self.hass, DEBOUNCE, self._debounced)

    async def _debounced(self, _now: datetime) -> None:
        self._debounce = None
        await self.async_evaluate()

    async def _interval(self, _now: datetime) -> None:
        await self.async_evaluate()

    @callback
    def _device_changed(self, entity_id: str, old: State | None, new: State | None) -> None:
        """A change that Smart Comfort didn't make pauses the control of the device."""
        if old is None or new is None or old.state in BAD_STATES or new.state in BAD_STATES:
            return
        if new.context.id in self._contexts:
            return
        now = dt_util.utcnow()
        if (sent := self._commanded.get(entity_id)) is not None and now - sent < COMMAND_GRACE:
            return
        keys = ("preset_mode", "percentage", "hvac_mode", "temperature", "fan_mode")
        changed = old.state != new.state or any(old.attributes.get(k) != new.attributes.get(k) for k in keys)
        if changed and entity_id in self.controller.targets:
            _LOGGER.debug("Manual change of %s, control paused", entity_id)
            self.controller.manual_change(entity_id, now)

    # Readings.

    def outdoor(self) -> float | None:
        values = [v for e in self.settings.outdoor if (v := _temperature(self.hass.states.get(e))) is not None]
        if not values:
            return None
        if self.settings.aggregate == "max":
            return max(values)
        if self.settings.aggregate == "mean":
            return round(sum(values) / len(values), 2)
        return min(values)

    def _outdoor_gone(self, settled: bool) -> bool:
        """Every outdoor temperature entity no longer exists (not just unavailable)."""
        outdoor = self.settings.outdoor
        return settled and bool(outdoor) and all(self.hass.states.get(e) is None for e in outdoor)

    def _settled(self, now: datetime) -> bool:
        """Home Assistant runs and the startup grace is over: an entity still missing is gone."""
        if self.hass.state is not CoreState.running:
            return False
        return self.started_at is None or now - self.started_at >= timedelta(minutes=self.settings.startup_grace)

    def ignored_openings(self, room: Room, now: datetime) -> list[str]:
        """Openings unavailable for a while (dead battery…) or gone: left out instead of blocking the room."""
        out = []
        grace = timedelta(minutes=OPENING_UNAVAILABLE)
        for entity_id in room.openings:
            state = self.hass.states.get(entity_id)
            if state is None:
                if self._settled(now):
                    out.append(entity_id)
            elif state.state not in ("on", "off") and now - state.last_changed >= grace:
                out.append(entity_id)
        return out

    def _openings(self, room: Room, now: datetime) -> tuple[list[str] | None, datetime | None, datetime | None]:
        """(open entity ids or None if one is unknown, open since, all closed since)."""
        ignored = set(self.ignored_openings(room, now))
        states = [self.hass.states.get(e) for e in room.openings if e not in ignored]
        if any(s is None or s.state not in ("on", "off") for s in states):
            return None, None, None
        opened = [s for s in states if s.state == "on"]
        if opened:
            return [s.entity_id for s in opened], min(s.last_changed for s in opened), None
        changed = [s.last_changed for s in states] + [
            s.last_changed for e in ignored if (s := self.hass.states.get(e)) is not None
        ]
        return [], None, max(changed, default=None)

    def reading(self, room: Room, now: datetime | None = None) -> tuple[RoomReading, RoomContext]:
        now = now or dt_util.utcnow()
        opened, open_since, closed_since = self._openings(room, now)
        temperature = _temperature(self.hass.states.get(room.temperature)) if room.temperature else None
        settled = self._settled(now)
        sources = (("temperature", room.temperature), ("co2", room.co2), ("humidity", room.humidity))
        missing = {n for n, entity_id in sources if entity_id and settled and self.hass.states.get(entity_id) is None}
        if self._outdoor_gone(settled):
            missing.add("outdoor")
        reading = RoomReading(
            temperature=temperature,
            co2=_float(self.hass.states.get(room.co2)) if room.co2 else None,
            humidity=_float(self.hass.states.get(room.humidity)) if room.humidity else None,
            open=opened,
            has_openings=bool(room.openings),
            missing=frozenset(missing),
        )
        ctx = RoomContext(
            temperature=temperature,
            any_open=None if opened is None else bool(opened),
            closed_since=closed_since,
            open_since=open_since,
            has_openings=bool(room.openings),
        )
        return reading, ctx

    def device_states(self, room: Room) -> dict[str, DeviceState]:
        out: dict[str, DeviceState] = {}
        selects = {p.entity_id: p.mode_select for p in room.purifiers}
        for entity_id in room.devices:
            state = self.hass.states.get(entity_id)
            if state is None or state.state in BAD_STATES:
                out[entity_id] = DeviceState(available=False)
                continue
            is_climate = state.domain == "climate"
            on = state.state != "off" if is_climate else state.state == "on"
            option = None
            if (select := selects.get(entity_id)) and (sel := self.hass.states.get(select)) is not None:
                option = sel.state
            out[entity_id] = DeviceState(
                on=on,
                hvac_mode=state.state if is_climate else None,
                preset=state.attributes.get("preset_mode"),
                percentage=state.attributes.get("percentage"),
                option=option,
                off_since=state.last_changed if not on else None,
            )
        return out

    # Evaluation.

    def gates(self, now: datetime) -> Gates:
        s = self.settings
        starting = self.started_at is not None and now - self.started_at < timedelta(minutes=s.startup_grace)
        local = dt_util.as_local(now).time()
        quiet = s.quiet_start is not None and s.quiet_end is not None and in_window(local, s.quiet_start, s.quiet_end)
        away = s.presence is not None and not present(self.hass.states.get(s.presence))
        return Gates(enabled=self.notifications_enabled, starting=starting, hold=quiet or away)

    async def async_evaluate(self) -> None:
        if self._stopped:
            return
        async with self._lock:
            if self._stopped:
                return
            now = dt_util.utcnow()
            local = dt_util.as_local(now).time()
            readings: dict[str, RoomReading] = {}
            commands: list[Command] = []
            handled: set[str] = set()
            for room in self.settings.rooms:
                reading, ctx = self.reading(room, now)
                states = self.device_states(room)
                if self.control_enabled:
                    commands += self.controller.evaluate(now, local, room, ctx, states)
                if self.controller.handled(room, states):
                    handled.add(room.id)
                reading.handled = room.id in handled
                readings[room.id] = reading
            self.engine.evaluate(now, readings, self.outdoor())
            self.handled = handled
            failed = {c.device for c in commands if not await self._command(c, now)}
            for device in {c.device for c in commands if c.device} - failed:
                self.controller.command_succeeded(device)
            result = self.engine.step(now, self.gates(now), handled)
            if isinstance(result, Digest):
                await self._send(result, now)
            elif isinstance(result, Clear):
                await self._clear()
            self.save()
        if not self._stopped:
            self._update_listeners()

    async def _command(self, cmd: Command, now: datetime) -> bool:
        context = Context()
        self._contexts.append(context.id)
        self._commanded[cmd.entity_id] = now
        data = {"entity_id": cmd.entity_id, **cmd.data}
        try:
            async with asyncio.timeout(SERVICE_TIMEOUT):
                await self.hass.services.async_call(cmd.domain, cmd.service, data, blocking=True, context=context)
        except Exception as err:  # noqa: BLE001 - one failing device doesn't stop the others
            _LOGGER.warning("%s.%s on %s failed: %s", cmd.domain, cmd.service, cmd.entity_id, err)
            self.controller.command_failed(cmd, now)
            return False
        self.hass.bus.async_fire(
            EVENT_CONTROL,
            {
                "entity_id": cmd.entity_id,
                "action": f"{cmd.domain}.{cmd.service}",
                "data": cmd.data,
                "target": cmd.target,
            },
            context=context,
        )
        return True

    # Notifications.

    def _payload(self, digest: Digest) -> dict[str, Any]:
        s = self.settings
        push: dict[str, Any] = {"interruption-level": INTERRUPTION.get(digest.severity, "active")}
        if digest.severity == SEVERITY_CRITICAL:
            push["sound"] = {"name": "default", "critical": 1, "volume": s.critical_volume}
        elif digest.severity == SEVERITY_WARNING:
            push["sound"] = "default"
        snooze = s.snooze
        snooze_title = (
            self._text("action_snooze", hours=snooze // 60)
            if snooze % 60 == 0
            else self._text("action_snooze_minutes", minutes=snooze)
        )
        data: dict[str, Any] = {
            "tag": s.tag,
            "group": s.tag,
            "push": push,
            "actions": [
                {"action": ACTION_SNOOZE, "title": snooze_title},
                {"action": ACTION_ACK, "title": self._text("action_ack")},
            ],
        }
        if digest.severity == SEVERITY_CRITICAL:
            data.update({"priority": "high", "ttl": 0})
        if s.url:
            data["url"] = s.url
            data["clickAction"] = s.url
        return data

    def _text(self, key: str, **values: Any) -> str:
        return format_text(self._texts, key, **values)

    async def _notify(self, payload: dict[str, Any], services: list[str] | None = None) -> bool:
        """Send with every notifier; False when all of them failed (True without any notifier)."""
        services = list(self.settings.notify) if services is None else services
        sent = not services
        for service in services:
            domain, name = service.split(".", 1)
            try:
                async with asyncio.timeout(NOTIFY_TIMEOUT):
                    await self.hass.services.async_call(domain, name, payload, blocking=True)
            except Exception as err:  # noqa: BLE001 - one failing notifier doesn't stop the others
                _LOGGER.warning("Notification with %s failed: %s", service, err)
            else:
                sent = True
        return sent

    async def _send(self, digest: Digest, now: datetime) -> bool:
        """Send the digest; its problems are marked notified only when at least one notifier got it."""
        names = {}
        for item in digest.items:
            for o in item.episode.details.get("openings", []):
                state = self.hass.states.get(o)
                names[o] = state.name if state else o
        title, message, _icon = render(digest, self._texts, now, names)
        if not await self._notify({"title": title, "message": message, "data": self._payload(digest)}):
            _LOGGER.warning("No notifier could send the alerts, trying again at the next evaluation")
            return False
        self.engine.sent(digest, now)
        self.last_notification = {
            "at": now.isoformat(),
            "title": title,
            "message": message,
            "severity": digest.severity,
            "alerts": digest.keys,
        }
        self.hass.bus.async_fire(EVENT_NOTIFIED, {**self.last_notification})
        return True

    async def _clear(self) -> None:
        # Only the Companion app understands it: other notifiers would show the text "clear_notification".
        if mobile := [s for s in self.settings.notify if self._companion(s)]:
            await self._notify({"message": "clear_notification", "data": {"tag": self.settings.tag}}, mobile)

    def _companion(self, service: str) -> bool:
        """A Companion app notifier, or a notify group (usually of phones, which forwards to them)."""
        name = service.removeprefix("notify.")
        if name.startswith("mobile_app_"):
            return True
        groups = self.hass.data.get("notify_services", {}).get("group", [])  # Legacy notify groups.
        return any(getattr(group, "_service_name", None) == name for group in groups)

    # User actions.

    async def _action(self, event: Event) -> None:
        action = event.data.get("action")
        if action not in (ACTION_SNOOZE, ACTION_ACK):
            return
        if self._stopped:
            return
        keys = self.engine.last_keys
        if action == ACTION_SNOOZE:
            self.engine.snooze(dt_util.utcnow(), self.settings.snooze, keys=keys)
        else:
            self.engine.acknowledge(keys=keys)
        self.save()
        self._update_listeners()

    async def async_snooze(self, minutes: int | None, rooms: list[str] | None, kinds: list[str] | None) -> None:
        self.engine.snooze(dt_util.utcnow(), minutes or self.settings.snooze, rooms=rooms, kinds=kinds)
        self.save()
        self._update_listeners()

    async def async_unsnooze(self, rooms: list[str] | None) -> None:
        self.engine.unsnooze(dt_util.utcnow(), rooms)
        self.save()
        await self.async_evaluate()

    async def async_acknowledge(self, rooms: list[str] | None, kinds: list[str] | None) -> None:
        self.engine.acknowledge(rooms=rooms, kinds=kinds)
        self.save()
        self._update_listeners()

    async def async_notify_now(self) -> bool:
        async with self._lock:
            now = dt_util.utcnow()
            digest = self.engine.summary(now, self.handled)
            if digest is None:
                return False
            sent = await self._send(digest, now)
            self.save()
        self._update_listeners()
        return sent

    @callback
    def set_notifications(self, enabled: bool) -> None:
        self.notifications_enabled = enabled
        self.save()
        self._update_listeners()

    @callback
    def set_control(self, enabled: bool) -> None:
        self.control_enabled = enabled
        self.save()
        self._update_listeners()
