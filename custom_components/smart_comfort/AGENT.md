# Smart Comfort — Agent Context

## Purpose
Home Assistant custom integration that replaces cooldown-based comfort automations: per-room alerts tracked as episodes and sent as grouped, replaceable notifications, plus control of air conditioners, fans and air purifiers.

## Architecture

```
custom_components/smart_comfort/
├── __init__.py      # YAML import (async_import_yaml), actions snooze/unsnooze/acknowledge/notify_now, entry setup
├── const.py         # Keys (same in YAML and options), kinds, DEFAULT_ALERTS, DEFAULT_CONTROL
├── schema.py        # voluptuous: CONFIG_SCHEMA (YAML) and OPTIONS (also validates what the options flow saves)
├── config.py        # Pure: build_settings(options) -> Settings/Room/AlertSettings/devices, defaults merged (global < room < device)
├── engine.py        # Pure: Episode, Engine.evaluate (readings -> episodes), Engine.step (gates -> Digest | Clear | None)
├── control.py       # Pure: Controller.evaluate (room context + device states -> Commands), targets, manual overrides, keep_on
├── message.py       # Pure: render(digest, texts) -> title, message; texts = translations common.*
├── manager.py       # HA glue: state tracking, debounce, interval, commands with own Context, notify, mobile_app actions, Store
├── config_flow.py   # Single entry; import step; options menu general / alerts (per kind) / control (sections) / rooms
├── sensor.py        # alerts, room (enum per room), last_notification
├── switch.py        # notifications, control (restored)
├── button.py        # notify_now, unsnooze
├── status.py        # episode_info / room_info / status: shared by the sensors and the panel
├── websocket.py     # smart_comfort/config, smart_comfort/config/save (OPTIONS + unique room names), smart_comfort/subscribe (SIGNAL_UPDATE)
├── discovery.py     # discover_rooms (areas -> rooms, outdoor areas -> outdoor sensors), merge (keeps what is set, matches on area then name)
├── panel.py         # Static path /smart_comfort_static (once per run) + custom panel "smart-comfort" (admin), removed with the entry
├── frontend/smart-comfort-panel.js  # Plain web component (no build): tabs overview/rooms/alerts/notifications/control, ha-form
├── entity.py / icons.json / services.yaml / translations/{en,fr,de,es}.json / brand/
```

## Rules
- Options dict is the single source of truth (entry.options), same shape as YAML. Missing keys mean defaults; keep it minimal. A field emptied in the options flow whose default is a value is stored as None (stays empty). Rooms created in the UI get a stable `id` (renaming keeps the sensor and the episodes).
- YAML: `async_import_yaml` creates the entry via the import flow, or, when the entry exists (a single-entry integration can't run a flow then), updates its options only if the sha256 of the YAML differs from `entry.data["yaml_hash"]`. Unchanged YAML keeps UI edits.
- Episode key `room|kind`. Pending until `delay`, active after; ends when the check is False (hysteresis applied once the episode exists). A check returning None (unknown sensor/opening) leaves the episode untouched, unless the sensor entity no longer exists (`RoomReading.missing`, once HA runs and the startup grace is over; `outdoor` when every outdoor entity is gone, for the kinds whose `SOURCES` list it). Episodes whose sensor was removed from the room go away in `update_settings`. An opening unavailable for `OPENING_UNAVAILABLE` min is left out of its room. Temperatures are °C (°F/K converted; weather entities: `temperature` attribute).
- Due = never notified, worse by `escalation` (not when acknowledged), `reminder` elapsed or episode snooze over since the last notification (not when acknowledged). Snoozed (episode, room or "*") and handled too_hot (room whose AC/fan target is running) are invisible.
- Digest = all visible episodes (only critical ones while `hold`), sent when the batch is older than `digest_window` or a due item is critical. Same `tag` every time: it replaces the previous notification. `Clear` (clear_notification, to `notify.mobile_app_*` and legacy notify groups only) once no visible episode was notified. `step()` doesn't mark a digest: the manager calls `engine.sent()` once at least one notifier got it.
- Gates: startup grace (only when HA was starting at setup), notifications switch, hold (quiet hours or presence away).
- Control: a target per device; commands only on a target change and when the device doesn't already satisfy it. Hysteresis band keeps the previous target. Climate in a mode other than cool/off is left alone, except by `off_open` (opening open for `off_on_open`). A purifier without closed preset/mode goes back to its pre-boost state (`before_boost`). A failed command forgets the target, retried after `COMMAND_RETRY` min doubled at each failure in a row (max `COMMAND_RETRY_MAX`, reset when all commands of the device succeed; another target is not held back); a failed pre-boost restore puts `before_boost` back. keep_on respects manual overrides. Manual change = device state/attribute change whose context isn't ours, outside 90 s after our last command → override `manual_override` min; when it ends the target is forgotten and applied again.
- State (episodes, snoozes, last notified keys, targets, overrides, pre-boost states, last notification, switches) in `Store` `smart_comfort`, and in `hass.data[DOMAIN]["state"]` across entry reloads; `async_stop` waits for the evaluation in progress first. `async_remove_entry` deletes both.
- Notification texts: translations `common.*` with `str.format`; a broken template falls back to English (message.FALLBACK).

## Panel
- Registered at entry setup when `frontend` is loaded, kept across entry reloads (saving reloads the entry; an open panel must not vanish), removed in `async_remove_entry`.
- Labels come from the translations through `frontend/get_translations` (category `options`: the options flow steps general / alert / control (+ sections) / room (+ section overrides); category `selector`: kinds, severities, aggregates). Panel-only strings are in `STRINGS` of the JS (en/fr/de/es).
- ha-form is lazy-loaded by Home Assistant: `loadHaForm()` loads it through the entities card editor.
- The draft stores only what differs from the defaults (`diff`, `prune`); times "HH:MM" and "HH:MM:SS" compare equal. Device items with no own setting are stored as a bare entity id. Unknown keys of a room (room-level `control`, `id`) are kept.
- Discover: `smart_comfort/discover` returns the draft options with the discovered rooms merged (not saved); the panel marks them new/completed until Save or Discard.
- The status subscription listens to `SIGNAL_UPDATE`, sent by `_update_listeners` and by setup/unload, so it survives reloads.

## Release
Bump `version` in manifest.json and add its CHANGELOG.md section; pushing to main publishes `vX.Y.Z` with `smart_comfort.zip` when that tag doesn't exist yet.

## Tests
`pip install -r requirements_test.txt && pytest` — engine/control/message tests are pure Python; `tests/test_init.py` runs the integration with mocked notify and fan services. CI runs the latest Home Assistant (Python 3.14) and 2024.12.0.
