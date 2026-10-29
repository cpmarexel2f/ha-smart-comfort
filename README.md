# ha-smart-comfort

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![HACS Validation](https://github.com/juju35/ha-smart-comfort/actions/workflows/hacs.yml/badge.svg)](https://github.com/juju35/ha-smart-comfort/actions/workflows/hacs.yml)
[![Validate](https://github.com/juju35/ha-smart-comfort/actions/workflows/validate.yml/badge.svg)](https://github.com/juju35/ha-smart-comfort/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/juju35/ha-smart-comfort)](https://github.com/juju35/ha-smart-comfort/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center"><img src="custom_components/smart_comfort/brand/icon.png" alt="Smart Comfort" width="120"></p>

Home Assistant integration for **fewer, smarter comfort alerts** — temperature, CO₂, humidity, windows to open or close — and **automatic control of air conditioners, fans and air purifiers**, room by room.

Comfort automations built with a cooldown keep notifying every couple of hours as long as a room stays warm, flap around a threshold, and pile up one notification per sensor. Smart Comfort tracks each problem as an **episode**: notified once when it starts, again only if it gets worse (or after a reminder delay, if you want one), grouped with the others into a single notification that replaces the previous one, held during quiet hours, and cleared from the phones when everything is back to normal.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=juju35&repository=ha-smart-comfort&category=integration)

## Features

- **Seven alerts per room**: too hot, too cold, open the windows (warmer inside than outside), close the windows (hotter outside), window open in the cold, high CO₂, high humidity — each with its threshold, hysteresis, delay, severity and escalation step, globally and per room
- **Episodes, not cooldowns**: one notification when a problem starts, none while it lasts; again when it gets worse by the escalation step, or after the reminder delay (off by default)
- **Hysteresis and delay**: a problem starts once its condition has held for the delay, and ends only once the value is back past the threshold by the hysteresis — no flapping. An unavailable sensor changes nothing
- **Digest**: what comes up within the digest window (5 minutes by default) goes out in **one** notification listing every current problem, replacing the previous one on the phone (notification `tag`) instead of piling up
- **Quiet hours** and **presence**: during quiet hours, or while nobody is home, only critical alerts are sent; the others go out at the end if they are still relevant, and those over meanwhile are never sent
- **Severities** mapped to the iOS / Android interruption levels: info (silent), warning (time-sensitive, sound), critical (bypasses silent mode and Focus, configurable volume)
- **Actionable notifications**: **Snooze 4 h** and **Got it** (no more reminders for these problems) buttons, right from the phone
- **Cleared when resolved**: the notification is removed from the phones once every notified problem is over
- **Device control** per room:
  - **air conditioner**: cools above a temperature once the openings have been closed for a while, turns off below another one, or when an opening stays open (whatever its mode, heating included)
  - **fans**: on above a temperature, off below another one (hysteresis band in between), full speed while a window is open during the day
  - **air purifiers**: boost while a window is open during the day (preset, speed, or a mode select such as `manual`/`automatic`), back to normal when closed (the closed preset / mode, or else the state it had before the boost), and optionally **kept on** (turned back on after a power cut)
  - commands are sent only when the target changes and the device isn't already in that state; a device changed **by hand** is left alone for an hour (configurable)
  - a room whose air conditioner or fan Smart Comfort has turned on gets no "too hot" alert (a device turned on by hand doesn't count)
- **No re-notification after a restart**: episodes, snoozes and device targets are stored; nothing is sent during the startup grace period
- **YAML or UI**: configure everything in YAML (imported at startup) or in the integration options — rooms, alerts, control
- Sensors for the active alerts and the comfort of each room, switches to pause the notifications or the device control, buttons, actions and events
- English, French, German and Spanish

## Prerequisites

- Home Assistant 2024.12 or newer
- A notify action: the [Companion app](https://companion.home-assistant.io/) (`notify.mobile_app_…`) or a notify group of several phones. The snooze buttons, replacement and clearing of notifications need the Companion app; other notifiers get the title and message (and no clearing message)
- Temperature (and optionally CO₂ / humidity) sensors per room, door/window `binary_sensor`s, and outdoor temperature sensors for the window alerts

## Installation

### Via HACS (recommended)

Click the button below to add the repository directly:

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=juju35&repository=ha-smart-comfort&category=integration)

Then click **Download** and restart Home Assistant.

Or manually:

1. Open HACS → **⋮** (top right) → **Custom repositories**
2. Add `https://github.com/juju35/ha-smart-comfort` — Type: **Integration**
3. Search for **Smart Comfort** and click **Download**
4. Restart Home Assistant

### Manual

Copy `custom_components/smart_comfort/` to `/config/custom_components/smart_comfort/`, then restart Home Assistant.

## Configuration

Both ways can be used together:

- **YAML**: add a `smart_comfort:` section (below). At startup it creates the integration, or replaces its options **if the YAML changed** since the last import. While the YAML stays the same, changes made in the UI are kept
- **UI**: [![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smart_comfort) — **Settings → Devices & services → Add integration → Smart Comfort**, then **Configure** for the notifications, the alerts, the device control and the rooms

Per-device settings (a preset for one fan only) are YAML only; editing a room in the UI keeps them.

### Example

```yaml
smart_comfort:
  notify:
    - notify.family            # a notify group, or notify.mobile_app_…
  outdoor_temperature:
    - sensor.outdoor_north_temperature
    - sensor.outdoor_south_temperature
  outdoor_aggregate: min       # min avoids a sensor in the sun
  quiet_start: "22:30"
  quiet_end: "08:00"
  presence: zone.home
  url: homeassistant://navigate/lovelace/comfort

  alerts:
    too_hot: { threshold: 27, delay: 15, escalation: 1 }
    close_windows: { min_outdoor: 27, severity: critical }
    co2_high: { threshold: 1300 }

  control:
    start: "09:00"             # window boost hours
    end: "21:00"
    fans: { on_above: 23, off_below: 22, percentage: 50, open_percentage: 100 }
    purifiers: { open_percentage: 100, keep_on: true }

  rooms:
    - name: Living room
      temperature: sensor.living_room_temperature
      co2: sensor.living_room_co2
      openings:
        - binary_sensor.living_room_window
        - binary_sensor.living_room_french_door
      climate: climate.living_room_ac
      fans:
        - entity_id: fan.living_room_fan
          preset: Natural
          open_preset: Standard
      purifiers:
        - entity_id: fan.living_room_purifier
          mode_select: select.living_room_purifier_mode
          open_mode: manual
          closed_mode: automatic

    - name: Bedroom
      temperature: sensor.bedroom_temperature
      openings: [binary_sensor.bedroom_window]
      alerts:
        too_hot: { threshold: 25 }   # overrides for this room only
      purifiers:
        - entity_id: fan.bedroom_purifier
          open_preset: Favorite
          closed_preset: Auto

    - name: Bathroom
      humidity: sensor.bathroom_humidity
```

### General options

| Option | Default | Description |
|---|---|---|
| `notify` | none | Notify actions the alerts go to |
| `outdoor_temperature` | none | Outdoor sensors (or `weather` entities, their `temperature` attribute); unavailable ones are ignored |
| `outdoor_aggregate` | `min` | `min`, `max` or `mean` of the outdoor sensors |
| `digest_window` | 5 min | Wait for other alerts before sending one grouped notification. Critical alerts don't wait |
| `reminder` | 0 | Minutes after which a problem still going on is notified again. 0: never (only when it gets worse) |
| `snooze_duration` | 240 min | Duration of the **Snooze** button and of the `snooze` action by default |
| `startup_grace` | 10 min | Nothing is sent during this time after Home Assistant starts |
| `quiet_start` / `quiet_end` | none | Quiet hours (may cross midnight): only critical alerts are sent |
| `presence` | none | Zone (`zone.home`: number of people), person, group, tracker or boolean: while nobody is home, only critical alerts are sent |
| `clear_when_resolved` | `true` | Remove the notification once every notified problem is over |
| `critical_volume` | 0.5 | Volume of the iOS critical sound, 0 to 1 |
| `url` | none | Opened when the notification is tapped |
| `tag` | `smart_comfort` | Notification tag: each notification replaces the previous one |

### Alerts

Set under `alerts:` for every room, and under `rooms[].alerts:` for one room.

| Alert | Condition | Default |
|---|---|---|
| `too_hot` | temperature > `threshold` | 27 °C, warning |
| `too_cold` | temperature < `threshold` | 17 °C, warning |
| `ventilate` | openings closed, temperature ≥ `min_indoor` and ≥ outdoor + `threshold` | 24 °C, +2 °C, info |
| `close_windows` | an opening open, outdoor ≥ `min_outdoor` and ≥ temperature + `threshold` | 25 °C, +0.5 °C, warning |
| `window_open_cold` | an opening open for the delay, outdoor ≤ `max_outdoor` | 12 °C, 20 min, **disabled** |
| `co2_high` | CO₂ > `threshold` | 1200 ppm, info |
| `humidity_high` | humidity > `threshold` | 70 %, info |

Each alert also takes `enabled`, `hysteresis` (how far back past the threshold the value must go for the problem to end), `delay` (minutes the condition must hold), `severity` (`info`, `warning`, `critical`) and `escalation` (notify again when the value gets this much worse; 0: never).

### Device control

Set under `control:` for every room, under `rooms[].control:` for one room, and on the device item itself for one device.

| Option | Default | Description |
|---|---|---|
| `enabled` | `true` | Control the devices (also the **Device control** switch) |
| `start` / `end` | 09:00 / 21:00 | Window boost hours of the fans and purifiers. Both empty (or equal): all day |
| `manual_override` | 60 min | A device changed by hand is left alone this long, then its target is applied again. 0: never paused |
| `suppress_when_handled` | `true` | No "too hot" alert for a room whose air conditioner or fan is running on Smart Comfort's command |
| `climate.cool_above` / `off_below` | 23 / 21 °C | Cool above, turn off below |
| `climate.setpoint` / `fan_mode` | 22 °C / none | Setpoint and fan mode when cooling |
| `climate.closed_for` / `off_on_open` | 2 / 1 min | Openings closed for this long before cooling; off when one stays open this long |
| `fans.on_above` / `off_below` | 23 / 22 °C | On above, off below. Leave both empty for fans driven by the windows only |
| `fans.percentage` / `preset` | 50 % / none | When on |
| `fans.open_percentage` / `open_preset` | 100 % / none | While a window is open in the boost hours |
| `fans.off_preset` | none | Preset set before turning off (the fan restarts in it) |
| `purifiers.open_percentage` / `open_preset` | 100 % / none | While a window is open in the boost hours |
| `purifiers.closed_preset` | none | When the windows are closed. Without it (nor `closed_mode`), the purifier goes back to the state it had before the boost |
| `purifiers.mode_select` / `open_mode` / `closed_mode` | none | A `select` entity and its options for the two states (e.g. `manual` / `automatic`) |
| `purifiers.keep_on` | `false` | Turn the purifier back on when it has been off for 10 seconds |

An air conditioner in another mode than `cool` or `off` (heat, dry…) is left alone by the temperature control, but turned off when an opening stays open.

Thresholds and messages are in °C; sensors in °F or K are converted. An opening unavailable for 10 minutes (dead battery…) is left out of its room instead of blocking its alerts and devices (`ignored_openings` attribute of the room sensor). The problems of a sensor removed from a room end.

### Entities

| Entity | Description |
|---|---|
| `sensor.smart_comfort_active_alerts` | Number of current problems. Attributes: `alerts` (room, kind, value, since, notified_at, snoozed, acknowledged, handled…), `snoozes`, `outdoor_temperature` |
| `sensor.smart_comfort_<room>_comfort` | `ok` or the main problem of the room. Attributes: readings, open and ignored openings, alerts, device targets and manual overrides |
| `sensor.smart_comfort_last_notification` | Time of the last notification. Attributes: `title`, `message`, `severity`, `alerts` |
| `switch.smart_comfort_notifications` | Send notifications (problems are still tracked when off) |
| `switch.smart_comfort_device_control` | Control the devices |
| `button.smart_comfort_notify_now` | Send every current problem now, ignoring quiet hours and the digest window |
| `button.smart_comfort_cancel_snoozes` | Cancel every snooze |

### Actions

| Action | Fields | Description |
|---|---|---|
| `smart_comfort.snooze` | `duration` (min), `rooms`, `kinds` | Don't notify for a while. Without `kinds`, problems that come up meanwhile in these rooms are snoozed too |
| `smart_comfort.unsnooze` | `rooms` | Cancel the snoozes |
| `smart_comfort.acknowledge` | `rooms`, `kinds` | No reminder nor escalation for the current problems until they end |
| `smart_comfort.notify_now` | | Send a summary now; returns `sent` |

Rooms are given by name or id (`Living room` or `living_room`).

```yaml
action: smart_comfort.snooze
data:
  rooms: [Bedroom]
  duration: 480
```

### Events

- `smart_comfort_notified`: `at`, `title`, `message`, `severity`, `alerts`
- `smart_comfort_control`: `entity_id`, `action`, `data`, `target`, for each command sent to a device

## How it works

Every 30 seconds, and a few seconds after a watched sensor or device changes, Smart Comfort reads the rooms, decides the device targets and sends their commands, updates the episodes, then decides whether a notification is due:

1. A problem is **pending** while its condition holds for less than the delay, **active** after that, and over once the value is back past the threshold by the hysteresis
2. An active problem is **due** when it has never been notified, when it got worse by the escalation step, or after the reminder delay. Snoozed problems are skipped; acknowledged ones are only notified once
3. The first due problem starts the digest window; at its end, one notification lists **every** current problem (new, worse, still going on), since it replaces the previous one. A critical problem is sent right away
4. During quiet hours or while nobody is home, only critical problems are sent; the others are still due at the end
5. When no notified problem is left, the notification is cleared

To debug:

```yaml
logger:
  logs:
    custom_components.smart_comfort: debug
```

## Development

```bash
pip install -r requirements_test.txt && pytest
```

The engine (`engine.py`), the device decisions (`control.py`) and the texts (`message.py`) are plain Python, tested without Home Assistant.

### Releasing

1. Bump the version in `custom_components/smart_comfort/manifest.json`
2. Add a `## <version>` section at the top of [CHANGELOG.md](CHANGELOG.md)
3. Push to `main`: the **Release** workflow creates the tag and the GitHub release with the changelog section as notes

## Translations

The integration and its notifications follow the language of Home Assistant. Currently supported:

| Language | Code |
|---|---|
| English | `en` |
| Français | `fr` |
| Deutsch | `de` |
| Español | `es` |

Contributions for additional languages are welcome!

## License

[MIT](LICENSE)
