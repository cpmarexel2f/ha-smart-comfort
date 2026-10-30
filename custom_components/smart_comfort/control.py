"""Device control: air conditioners, fans and air purifiers of each room.

Pure Python. Each device has a target (cool/off, on/boost/off, boost/normal) derived from the room
reading, with a hysteresis band in which the previous target holds. Commands are sent only when
the target changes and the device isn't already in that state, so a user who changes a device by
hand is not fought: a manual change pauses the device for `manual_override` minutes, after which the
target is applied again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .config import ClimateDevice, FanDevice, PurifierDevice, Room, Settings, in_window
from .const import COMMAND_RETRY, COMMAND_RETRY_MAX, KEEP_ON_DELAY

TARGET_COOL = "cool"
TARGET_OFF = "off"
# Air conditioner turned off because an opening stays open: applies whatever its mode (heating too).
TARGET_OFF_OPEN = "off_open"
TARGET_ON = "on"
TARGET_BOOST = "boost"
TARGET_NORMAL = "normal"
# Quiet night variants: the device's night settings.
TARGET_COOL_NIGHT = "cool_night"
TARGET_ON_NIGHT = "on_night"
TARGET_NIGHT = "night"
COOLING = frozenset({TARGET_COOL, TARGET_COOL_NIGHT})
BLOWING = frozenset({TARGET_ON, TARGET_ON_NIGHT, TARGET_BOOST})


@dataclass
class DeviceState:
    """State of a device entity, None fields when unknown."""

    available: bool = True
    on: bool | None = None
    hvac_mode: str | None = None
    preset: str | None = None
    percentage: int | None = None
    option: str | None = None  # Current option of the purifier's mode select.
    fan_mode: str | None = None  # Air conditioner.
    off_since: datetime | None = None


@dataclass
class RoomContext:
    temperature: float | None
    any_open: bool | None
    # Since when every opening is closed / at least one is open (None when unknown or not the case).
    closed_since: datetime | None
    open_since: datetime | None
    has_openings: bool


@dataclass
class Command:
    """One action call: domain.service with data, on entity_id."""

    entity_id: str
    domain: str
    service: str
    data: dict[str, Any] = field(default_factory=dict)
    target: str | None = None
    # Controlled device the command is for (entity_id is the mode select for a purifier's option).
    device: str | None = None
    # State before the boost that this command restores: kept for a retry when the command fails.
    restores: dict[str, Any] | None = None


def _fan_commands(entity_id: str, percentage: int | None, preset: str | None) -> list[Command]:
    cmds = [Command(entity_id, "fan", "turn_on")]
    if preset:
        cmds.append(Command(entity_id, "fan", "set_preset_mode", {"preset_mode": preset}))
    if percentage is not None:
        cmds.append(Command(entity_id, "fan", "set_percentage", {"percentage": percentage}))
    return cmds


class Controller:
    """Targets and manual overrides of every controlled device."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.targets: dict[str, str] = {}
        self.overrides: dict[str, datetime] = {}
        self.keep_on_sent: dict[str, datetime] = {}
        # State of a purifier before its window boost, restored when the boost ends.
        self.before_boost: dict[str, dict[str, Any]] = {}
        # Failed commands: (target, not retried before) and number of failures in a row, by device.
        self.retry: dict[str, tuple[str, datetime]] = {}
        self.failures: dict[str, int] = {}

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        devices = {d for r in settings.rooms for d in r.devices}
        self.targets = {k: v for k, v in self.targets.items() if k in devices}
        self.overrides = {k: v for k, v in self.overrides.items() if k in devices}
        self.keep_on_sent = {k: v for k, v in self.keep_on_sent.items() if k in devices}
        self.before_boost = {k: v for k, v in self.before_boost.items() if k in devices}
        self.retry = {k: v for k, v in self.retry.items() if k in devices}
        self.failures = {k: v for k, v in self.failures.items() if k in devices}

    def as_dict(self) -> dict[str, Any]:
        return {
            "targets": self.targets,
            "overrides": {k: v.isoformat() for k, v in self.overrides.items()},
            "before_boost": self.before_boost,
        }

    def restore(self, data: dict[str, Any]) -> None:
        self.targets = {str(k): str(v) for k, v in (data.get("targets") or {}).items()}
        for k, v in (data.get("overrides") or {}).items():
            try:
                self.overrides[str(k)] = datetime.fromisoformat(v)
            except (TypeError, ValueError):
                continue
        saved = data.get("before_boost") or {}
        self.before_boost = {str(k): dict(v) for k, v in saved.items() if isinstance(v, dict)}
        self.update_settings(self.settings)

    def command_failed(self, cmd: Command, now: datetime) -> None:
        """A command could not be sent: forget the target so that it is tried again, after a delay.

        The delay doubles at each failure in a row, so that a lasting error (unsupported preset…) is
        not sent and logged again at every evaluation.
        """
        if cmd.target == "keep_on" or cmd.target is None:
            return
        device = cmd.device or cmd.entity_id
        if self.targets.get(device) == cmd.target:
            # First failed command of the device in this evaluation (it may have sent several).
            self.targets.pop(device, None)
            failures = self.failures[device] = self.failures.get(device, 0) + 1
            delay = min(COMMAND_RETRY * 2 ** (failures - 1), COMMAND_RETRY_MAX)
            self.retry[device] = (cmd.target, now + timedelta(minutes=delay))
        if cmd.restores is not None:
            self.before_boost.setdefault(device, cmd.restores)

    def command_succeeded(self, device: str) -> None:
        """Every command of the device was sent: failures in a row start over."""
        self.failures.pop(device, None)
        self.retry.pop(device, None)

    def manual_change(self, entity_id: str, now: datetime) -> None:
        """A device was changed by someone else than Smart Comfort."""
        if self.settings.manual_override > 0:
            self.overrides[entity_id] = now + timedelta(minutes=self.settings.manual_override)

    def overridden(self, entity_id: str, now: datetime) -> bool:
        until = self.overrides.get(entity_id)
        if until is None:
            return False
        if until > now:
            return True
        # Override over: forget the target so that it is applied again.
        del self.overrides[entity_id]
        self.targets.pop(entity_id, None)
        return False

    def handled(self, room: Room, states: dict[str, DeviceState]) -> bool:
        """An air conditioner cools or a fan blows in the room, on Smart Comfort's command."""
        for entity_id in room.devices:
            target, state = self.targets.get(entity_id), states.get(entity_id)
            if state is None or not state.available:
                continue
            if target in COOLING and state.hvac_mode == "cool":
                return True
            if target in BLOWING and state.on and any(f.entity_id == entity_id for f in room.fans):
                return True
        return False

    # Decisions.

    def evaluate(
        self, now: datetime, local: Any, room: Room, ctx: RoomContext, states: dict[str, DeviceState]
    ) -> list[Command]:
        """Commands for the devices of a room. `local` is the local time of day."""
        if not self.settings.control_enabled:
            return []
        boost_hours = in_window(local, self.settings.control_start, self.settings.control_end)
        night = self.settings.night(local)
        cmds: list[Command] = []
        if room.climate:
            cmds += self._device(now, room.climate.entity_id, states, self._climate(room.climate, ctx, now, night))
        for fan in room.fans:
            # No window boost at night for a device that has night settings: it would be loud.
            boost = boost_hours and not (night and fan.quiet)
            cmds += self._device(now, fan.entity_id, states, self._fan(fan, ctx, boost, night))
        for purifier in room.purifiers:
            state = states.get(purifier.entity_id)
            boost = boost_hours and not (night and purifier.quiet)
            cmds += self._keep_on(now, purifier, state)
            cmds += self._device(now, purifier.entity_id, states, self._purifier(purifier, ctx, boost, night))
        return cmds

    def _device(self, now: datetime, entity_id: str, states: dict[str, DeviceState], decision: Any) -> list[Command]:
        state = states.get(entity_id)
        if decision is None or state is None or not state.available or self.overridden(entity_id, now):
            return []
        target, commands_for, satisfied = decision
        if target is None or self.targets.get(entity_id) == target:
            return []
        retry = self.retry.get(entity_id)
        if retry is not None and retry[0] != target:
            del self.retry[entity_id]  # Another target goes now, and holding the failed one is over.
            retry = None
        if satisfied(state):
            self.targets[entity_id] = target
            if retry is not None:
                # The failed command was applied after all (slow cloud device timing out…): done.
                self.command_succeeded(entity_id)
            return []
        if retry is not None and now < retry[1]:
            return []  # Failed a moment ago: tried again once the delay is over.
        self.targets[entity_id] = target
        cmds = commands_for(state)
        for c in cmds:
            c.target, c.device = target, entity_id
        return cmds

    # Air conditioner: cool / off.

    def _climate(self, dev: ClimateDevice, ctx: RoomContext, now: datetime, night: bool = False) -> Any:
        temp, current = ctx.temperature, self.targets.get(dev.entity_id)
        target = current
        open_for = now - ctx.open_since if ctx.open_since else None
        closed_for = now - ctx.closed_since if ctx.closed_since else None
        if ctx.has_openings and ctx.any_open is None:
            return None
        if ctx.any_open and open_for is not None and open_for >= timedelta(minutes=dev.off_on_open):
            target = TARGET_OFF_OPEN
        elif temp is None:
            return None
        elif temp >= dev.cool_above and (
            not ctx.has_openings or (closed_for is not None and closed_for >= timedelta(minutes=dev.closed_for))
        ):
            target = TARGET_COOL
        elif temp <= dev.off_below:
            target = TARGET_OFF
        elif ctx.any_open:
            return None  # Opening just opened: wait for off_on_open.
        if target in COOLING:
            # Cooling, with the night fan mode in the night hours.
            target = TARGET_COOL_NIGHT if night and dev.night_fan_mode else TARGET_COOL
        fan_mode = dev.night_fan_mode if target == TARGET_COOL_NIGHT else dev.fan_mode

        def commands(state: DeviceState) -> list[Command]:
            if target in (TARGET_OFF, TARGET_OFF_OPEN):
                return [Command(dev.entity_id, "climate", "turn_off")]
            if state.hvac_mode == "cool":
                # Already cooling (day <-> night): only the fan mode changes.
                return [Command(dev.entity_id, "climate", "set_fan_mode", {"fan_mode": fan_mode})] if fan_mode else []
            cmds = [
                # Two actions: some integrations (generic_thermostat…) ignore hvac_mode in set_temperature.
                Command(dev.entity_id, "climate", "set_hvac_mode", {"hvac_mode": "cool"}),
                Command(dev.entity_id, "climate", "set_temperature", {"temperature": dev.setpoint}),
            ]
            if fan_mode:
                cmds.append(Command(dev.entity_id, "climate", "set_fan_mode", {"fan_mode": fan_mode}))
            return cmds

        def satisfied(state: DeviceState) -> bool:
            if target == TARGET_OFF_OPEN:
                return state.hvac_mode == "off"  # Any mode, heating included, while an opening stays open.
            if state.hvac_mode not in (None, "off", "cool"):
                return True  # Heating, drying…: left alone by the temperature control.
            if target not in COOLING:
                return state.hvac_mode != "cool"
            return state.hvac_mode == "cool" and (not fan_mode or state.fan_mode is None or state.fan_mode == fan_mode)

        return target, commands, satisfied

    # Fan: boost (opening open, in the hours) / on (warm) / off.

    def _fan(self, dev: FanDevice, ctx: RoomContext, boost_hours: bool, night: bool = False) -> Any:
        current = self.targets.get(dev.entity_id)
        temp = ctx.temperature
        boost = bool(ctx.any_open) and boost_hours and (dev.open_percentage is not None or dev.open_preset)
        if ctx.has_openings and ctx.any_open is None:
            return None
        temperature_control = dev.on_above is not None and dev.off_below is not None
        if boost:
            target = TARGET_BOOST
        elif not temperature_control:
            target = TARGET_OFF if current == TARGET_BOOST else None
        elif temp is None:
            return None
        elif temp >= dev.on_above:
            target = TARGET_ON
        elif temp <= dev.off_below or current == TARGET_BOOST:
            target = TARGET_OFF
        else:
            target = current
        if target in (TARGET_ON, TARGET_ON_NIGHT):
            target = TARGET_ON_NIGHT if night and dev.quiet else TARGET_ON
        night_pct = dev.night_percentage if dev.night_percentage is not None else dev.percentage
        night_preset = dev.night_preset or dev.preset

        def wanted() -> tuple[int | None, str | None]:
            if target == TARGET_BOOST:
                return dev.open_percentage, dev.open_preset
            if target == TARGET_ON_NIGHT:
                return night_pct, night_preset
            return dev.percentage, dev.preset

        def commands(state: DeviceState) -> list[Command]:
            if target in (TARGET_BOOST, TARGET_ON, TARGET_ON_NIGHT):
                return _fan_commands(dev.entity_id, *wanted())
            cmds = []
            if dev.off_preset:
                cmds.append(Command(dev.entity_id, "fan", "set_preset_mode", {"preset_mode": dev.off_preset}))
            return [*cmds, Command(dev.entity_id, "fan", "turn_off")]

        def satisfied(state: DeviceState) -> bool:
            if target == TARGET_OFF:
                return state.on is False
            pct, preset = wanted()
            return (
                bool(state.on) and (pct is None or state.percentage == pct) and (not preset or state.preset == preset)
            )

        return target, commands, satisfied

    # Air purifier: boost (opening open, in the hours) / normal.

    def _purifier(self, dev: PurifierDevice, ctx: RoomContext, boost_hours: bool, night: bool = False) -> Any:
        if ctx.has_openings and ctx.any_open is None:
            return None
        if ctx.any_open and boost_hours:
            target = TARGET_BOOST
        elif night and dev.quiet:
            target = TARGET_NIGHT
        else:
            target = TARGET_NORMAL
        # Without a "windows closed" preset or mode, normal is the state the purifier had before the boost.
        restore = None if dev.closed_preset or (dev.mode_select and dev.closed_mode) else self.before_boost
        saved = (restore or {}).get(dev.entity_id) if target == TARGET_NORMAL else None
        if saved is not None and dev.keep_on:
            saved = {**saved, "on": True}  # Kept on: never turned off by the restore.

        def restored(state: DeviceState) -> bool:
            if saved is None:
                return True
            if saved.get("on") is False:
                return state.on is False
            if dev.mode_select and saved.get("option") and state.option != saved["option"]:
                return False
            if saved.get("preset"):
                return bool(state.on) and state.preset == saved["preset"]
            return bool(state.on) and (saved.get("percentage") is None or state.percentage == saved["percentage"])

        def commands(state: DeviceState) -> list[Command]:
            cmds = []
            if target == TARGET_NIGHT:
                # Like the boost, the state before the night is restored when it ends (no closed preset/mode).
                if restore is not None and dev.entity_id not in restore:
                    restore[dev.entity_id] = self._snapshot(dev, state)
                if not state.on:
                    return cmds  # Off stays off at night (keep_on turns it back on, quietly next time).
                if dev.mode_select and dev.night_mode:
                    cmds.append(Command(dev.mode_select, "select", "select_option", {"option": dev.night_mode}))
                if dev.night_preset:
                    cmds.append(Command(dev.entity_id, "fan", "set_preset_mode", {"preset_mode": dev.night_preset}))
                if dev.night_percentage is not None:
                    cmds.append(Command(dev.entity_id, "fan", "set_percentage", {"percentage": dev.night_percentage}))
            elif target == TARGET_BOOST:
                if restore is not None and dev.entity_id not in restore:
                    restore[dev.entity_id] = self._snapshot(dev, state)
                if not state.on:
                    cmds.append(Command(dev.entity_id, "fan", "turn_on"))
                if dev.mode_select and dev.open_mode:
                    cmds.append(Command(dev.mode_select, "select", "select_option", {"option": dev.open_mode}))
                if dev.open_preset:
                    cmds.append(Command(dev.entity_id, "fan", "set_preset_mode", {"preset_mode": dev.open_preset}))
                if dev.open_percentage is not None:
                    cmds.append(Command(dev.entity_id, "fan", "set_percentage", {"percentage": dev.open_percentage}))
            else:
                if dev.mode_select and dev.closed_mode:
                    cmds.append(Command(dev.mode_select, "select", "select_option", {"option": dev.closed_mode}))
                if dev.closed_preset:
                    cmds.append(Command(dev.entity_id, "fan", "set_preset_mode", {"preset_mode": dev.closed_preset}))
                if saved is not None:
                    # Forgotten now, put back by command_failed() if the restore can't be sent.
                    self.before_boost.pop(dev.entity_id, None)
                    if dev.mode_select and saved.get("option") and saved.get("on") is not False:
                        cmds.append(
                            Command(
                                dev.mode_select,
                                "select",
                                "select_option",
                                {"option": saved["option"]},
                                restores=saved,
                            )
                        )
                    if saved.get("on") is False:
                        cmds.append(Command(dev.entity_id, "fan", "turn_off", restores=saved))
                    elif saved.get("preset"):
                        cmds.append(
                            Command(
                                dev.entity_id,
                                "fan",
                                "set_preset_mode",
                                {"preset_mode": saved["preset"]},
                                restores=saved,
                            )
                        )
                    elif saved.get("percentage") is not None:
                        cmds.append(
                            Command(
                                dev.entity_id,
                                "fan",
                                "set_percentage",
                                {"percentage": saved["percentage"]},
                                restores=saved,
                            )
                        )
            return cmds

        def satisfied(state: DeviceState) -> bool:
            if target == TARGET_NIGHT:
                return state.on is False or (
                    (not (dev.mode_select and dev.night_mode) or state.option == dev.night_mode)
                    and (not dev.night_preset or state.preset == dev.night_preset)
                    and (dev.night_percentage is None or state.percentage == dev.night_percentage)
                )
            if target == TARGET_BOOST:
                return (
                    bool(state.on)
                    and (not (dev.mode_select and dev.open_mode) or state.option == dev.open_mode)
                    and (not dev.open_preset or state.preset == dev.open_preset)
                    and (dev.open_percentage is None or state.percentage == dev.open_percentage)
                )
            if saved is not None and restored(state):
                self.before_boost.pop(dev.entity_id, None)
            return (
                (not (dev.mode_select and dev.closed_mode) or state.option == dev.closed_mode)
                and (not dev.closed_preset or state.preset == dev.closed_preset)
                and restored(state)
            )

        return target, commands, satisfied

    @staticmethod
    def _snapshot(dev: PurifierDevice, state: DeviceState) -> dict[str, Any]:
        """State of a purifier to put back after its boost or the night."""
        snapshot = {"on": state.on, "preset": state.preset, "percentage": state.percentage}
        if dev.mode_select and state.option:
            snapshot["option"] = state.option
        return snapshot

    def _keep_on(self, now: datetime, dev: PurifierDevice, state: DeviceState | None) -> list[Command]:
        """Turn a purifier back on when it has been off for a few seconds (power cut, glitch…)."""
        if not dev.keep_on or state is None or not state.available or state.on is not False:
            return []
        if self.overridden(dev.entity_id, now):
            return []  # Turned off by hand: left alone for the manual override.
        if state.off_since is None or now - state.off_since < timedelta(seconds=KEEP_ON_DELAY):
            return []
        last = self.keep_on_sent.get(dev.entity_id)
        if last is not None and now - last < timedelta(minutes=1):
            return []
        self.keep_on_sent[dev.entity_id] = now
        return [Command(dev.entity_id, "fan", "turn_on", target="keep_on")]
