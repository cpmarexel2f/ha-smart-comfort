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

- **Ten alerts per room**: too hot, too cold, open the windows (warmer inside than outside), close the windows (hotter outside), window open in the cold, high CO₂, high humidity, noisy room, close the windows (noisy outside), close the windows (poor air outside) — each with its threshold, hysteresis, delay, severity and escalation step, globally and per room
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
  - **indicator lights and displays** of the devices (an on/off indicator light or switch, a display brightness, a brightness select such as bright / dim / off) turned off in their hours (the quiet night by default) and during the naps of their room, and back on after at the brightness or option they had; found by Discover
  - **back to normal at a set time**, per device (`reset_at`): the purifier back to its automatic mode at 20:40, even after a change by hand
  - **quiet night**: in the night hours (22:00–07:00 by default), devices with night settings run quieter — a fan at a lower speed or a sleep preset, a purifier in its sleep preset or mode, an air conditioner in its silent fan mode — and get no window boost; the day settings (or the state before the night) come back in the morning
- **Adaptive lighting**: the dimmable lights of each room that are on get the brightness of the moment — day with the sun up, evening once it is down, night in the quiet night hours — at once when turned on, then gradually; optionally the warmth too (color temperature, can be turned off). Smart Comfort never turns a light on or off, night lights are only set at night, and a light changed by hand is left alone until it is turned off
- **Lights on presence**, per room: lights turned on when someone comes in (only when the room is dark enough, with a light level sensor) at the brightness of the moment, and off once nobody is left for a while; slots keep some lights off (weekday mornings…) or set their brightness (a dim entrance at night), lights chosen to stay off during the naps of the house, night lights only at night, a color per slot (a blue night light), a presence that must last a few seconds (someone passing by doesn't count), and a light turned off by hand stays off until the room is empty
- **Outdoors**: outdoor places (garden, terrace…) with their temperature, air quality and noise sensors, plus sensors in no area (weather entity, a city air quality index such as Atmo France)
- **Noise**: a sound level sensor per room (noisy room alert), and outdoor noise sensors: no suggestion to open the windows while it is noisy outside, and an alert to close them when they are open in the noise
- **Outdoor air quality**: an index from 1 (good) to 6 (extremely poor) — European indexes (Atmo, EAQI) as is, US AQI by its bands, text states (good, poor…) — the worst sensor counts: no suggestion to open the windows while the air is poor, and an alert to close them when they are open then
- **No re-notification after a restart**: episodes, snoozes and device targets are stored; nothing is sent during the startup grace period
- **YAML or UI**: configure everything in YAML (imported at startup), in the **Smart Comfort panel** of the sidebar, or in the integration options — rooms, alerts, control
- Sensors for the active alerts and the comfort of each room, switches to pause the notifications or the device control, buttons, actions and events
- English, French, German and Spanish

## Prerequisites

- Home Assistant 2024.12 or newer
- A notify action: the [Companion app](https://companion.home-assistant.io/) (`notify.mobile_app_…`) or a notify group of several phones. The snooze buttons, replacement and clearing of notifications need the Companion app; other notifiers get the title and message (and no clearing message)
- Temperature (and optionally CO₂ / humidity / noise) sensors per room, door/window `binary_sensor`s, and outdoor temperature sensors (or a weather entity) for the window alerts; optionally outdoor air quality and noise sensors

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
- **UI**: [![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smart_comfort) — **Settings → Devices & services → Add integration → Smart Comfort**, then the **Smart Comfort** panel in the sidebar (below), or **Configure** for the same settings as forms

### Configuration panel

Once set up, Smart Comfort adds a **Smart Comfort** page to the sidebar, for administrators:

- **Overview**: while nothing is set up (no room nor outdoor place), a **Discover** button that runs the discovery and opens its result in the Rooms tab; the active alerts with their state (notified, snoozed, acknowledged, handled by a running device) and **Snooze** / **Got it** buttons, the readings and devices of each room with their targets and manual overrides, the last notification, and switches for the notifications and the device control
- **Activity**: what Smart Comfort did and why, live and by day — devices (cooling, window boost, night mode, back to normal…), lights (brightness of the moment, on with presence, off with nobody), indicator lights, notifications sent and cleared, changes by hand that pause a device or a light, reset times, commands that failed — with filters (devices, lights, notifications, by hand); a line opens its entity
- **Rooms**: **Discover** adds a room for every Home Assistant area with something to follow (a comfort sensor, an air conditioner, a fan, a purifier or a dimmable light — not a hallway with only its door) and sets it up: temperature, CO₂, humidity and noise sensors (a weather station preferred over a device's own sensor; never the temperatures of machines — NAS, internet box, server, UPS, printer, fridge…), windows and doors, air conditioner (only one that can cool), fans with their natural / direct presets, purifiers with their auto / manual mode select or presets, dimmable lights (not the indicators of devices nor the floodlights of cameras; night lights flagged as such), the quiet morning of the bedrooms, and the night settings from their quiet presets and fan modes. The outdoor areas (garden, terrace, balcony…) with a sensor become outdoor places (an outdoor module counts by its device's area); outdoor sensors in no area — a sensor named outdoor, a city air quality index (Atmo France, WAQI…), and the weather entity when there is no outdoor temperature sensor — go to the other outdoor sensors. What is already set is kept, and running it again only adds what is new. Nothing is saved until **Save**. Each room shows the icon of its area (or one from its name) and folds into sections — **Sensors**, **Windows and doors**, **Devices**, **Lighting** (lights, quiet morning, naps), **Alerts** — each with a one-line summary; only what the room has is shown, and **+** buttons add the rest (a CO₂ sensor, a fan, a light, a nap, a customized alert…). Device settings stay folded under each device
- **Outdoors**: the outdoor places (garden, terrace…) with their temperature, air quality and noise sensors, and the other outdoor sensors (weather entity, city air quality index) with how the temperatures are combined
- **Alerts**: one line per alert with its state, threshold and severity; open it to change them (hysteresis, delay and escalation under **Advanced**)
- **Schedule**: every time window on one 24-hour line with the time now — quiet hours (notifications), quiet night (devices and lights), quiet morning (bedroom lights) and window boost — and their times, all in one place
- **Settings**: notifications (where, presence, grouping, reminder; the rest under **Advanced**), device control (with the air conditioner, fan and purifier defaults folded) and adaptive lighting (the brightness of each moment on one row, the warmth only when it is on)
- **YAML**: the configuration of Smart Comfort only, as it goes under `smart_comfort:` in `configuration.yaml` (the defaults are not repeated), with a **Copy** button — to move to YAML or keep a copy. Unsaved changes are included

Changes are checked and saved with **Save** (or dropped with **Discard**); the integration reloads with them, and the page keeps following its status. Only the settings that differ from the defaults are stored. When the configuration comes from YAML, the page says so: what is saved there stays until the YAML changes.

Each tab has its own address, e.g. `/smart-comfort/rooms` (the addresses of earlier versions, `/notifications` and `/control`, open **Settings**).

| Overview of the Smart Comfort panel | Dark mode |
|---|---|
| ![Overview of the Smart Comfort panel](screenshots/panel-overview.png) | ![Overview of the Smart Comfort panel, dark mode](screenshots/panel-overview-dark.png) |

<details>
<summary>More screenshots</summary>

| Discover offered in the overview while nothing is set up | Dark mode |
|---|---|
| ![Discover offered in the overview while nothing is set up](screenshots/panel-start.png) | ![Discover offered in the overview while nothing is set up, dark mode](screenshots/panel-start-dark.png) |

| Rooms found by Discover, before saving | Dark mode |
|---|---|
| ![Rooms found by Discover, before saving](screenshots/panel-discover.png) | ![Rooms found by Discover, before saving, dark mode](screenshots/panel-discover-dark.png) |

| The Activity tab: what Smart Comfort did and why, by day | Dark mode |
|---|---|
| ![The Activity tab: what Smart Comfort did and why, by day](screenshots/panel-activity.png) | ![The Activity tab, dark mode](screenshots/panel-activity-dark.png) |

| A room in the Smart Comfort panel | Dark mode |
|---|---|
| ![A room in the Smart Comfort panel](screenshots/panel-room.png) | ![A room in the Smart Comfort panel, dark mode](screenshots/panel-room-dark.png) |

| The Outdoors tab | Dark mode |
|---|---|
| ![The outdoor places and the other outdoor sensors](screenshots/panel-outdoors.png) | ![The outdoor places and the other outdoor sensors, dark mode](screenshots/panel-outdoors-dark.png) |

| Alert settings in the Smart Comfort panel | Dark mode |
|---|---|
| ![Alert settings in the Smart Comfort panel](screenshots/panel-alerts.png) | ![Alert settings in the Smart Comfort panel, dark mode](screenshots/panel-alerts-dark.png) |

| The day on one line: quiet hours, quiet night, quiet morning, window boost | Dark mode |
|---|---|
| ![The Schedule tab](screenshots/panel-schedule.png) | ![The Schedule tab, dark mode](screenshots/panel-schedule-dark.png) |

| Adaptive lighting settings | Dark mode |
|---|---|
| ![Adaptive lighting settings in the Settings tab](screenshots/panel-lighting.png) | ![Adaptive lighting settings in the Settings tab, dark mode](screenshots/panel-lighting-dark.png) |

| Quiet morning and naps of a bedroom | Dark mode |
|---|---|
| ![Quiet morning and nap slots of a bedroom](screenshots/panel-naps.png) | ![Quiet morning and nap slots of a bedroom, dark mode](screenshots/panel-naps-dark.png) |

| Lights on presence of the entrance | Dark mode |
|---|---|
| ![Lights on presence: sensors, lights, light level, naps and slots](screenshots/panel-presence.png) | ![Lights on presence, dark mode](screenshots/panel-presence-dark.png) |

| The YAML tab: the configuration as it goes in `configuration.yaml` | Dark mode |
|---|---|
| ![The YAML tab](screenshots/panel-yaml.png) | ![The YAML tab, dark mode](screenshots/panel-yaml-dark.png) |

</details>

### Example

```yaml
smart_comfort:
  notify:
    - notify.family            # a notify group, or notify.mobile_app_…
  outdoor_temperature: [weather.home]       # outdoor sensors in no outdoor place
  outdoor_aggregate: min       # min avoids a sensor in the sun
  outdoor_air_quality: [sensor.atmo_france_qualite_globale_rennes]
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
    night_start: "22:00"       # quiet night
    night_end: "07:00"
    climate: { night_fan_mode: silent }
    fans: { on_above: 23, off_below: 22, percentage: 50, open_percentage: 100, night_percentage: 20 }
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
      noise: sensor.bedroom_sound_level
      openings: [binary_sensor.bedroom_window]
      alerts:
        too_hot: { threshold: 25 }   # overrides for this room only
      purifiers:
        - entity_id: fan.bedroom_purifier
          open_preset: Favorite
          closed_preset: Auto
          night_preset: Sleep        # quieter at night
      lights:
        - light.bedroom
        - entity_id: light.bedroom_night_light
          night_only: true           # set only at night

    - name: Bathroom
      humidity: sensor.bathroom_humidity

  outdoors:
    - name: Terrace
      temperature:
        - sensor.outdoor_north_temperature
        - sensor.outdoor_south_temperature
      noise: [sensor.street_sound_level]
    - name: Garden
      air_quality: [sensor.garden_aqi]
```

### General options

| Option | Default | Description |
|---|---|---|
| `notify` | none | Notify actions the alerts go to |
| `outdoor_temperature` | none | Outdoor sensors (or `weather` entities, their `temperature` attribute), with those of the outdoor places; unavailable ones are ignored |
| `outdoor_aggregate` | `min` | `min`, `max` or `mean` of the outdoor temperature sensors |
| `outdoor_noise` | none | Outdoor sound level sensors (dB, mean of the available ones, with those of the outdoor places) for the noise alerts |
| `outdoor_air_quality` | none | Outdoor air quality index sensors (the worst of the available ones, with those of the outdoor places) for the air alerts |
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
| `noise_high` | room noise > `threshold` (room `noise` sensor) | 60 dB, info |
| `noisy_outside` | an opening open, outdoor noise > `threshold` (outdoor noise sensors) | 65 dB, info |
| `bad_air_outside` | an opening open, outdoor air quality level > `threshold` (outdoor air quality sensors) | 3 (degraded), info |

`ventilate` also takes `max_outdoor_noise` (65 dB) and `max_outdoor_air` (3): no suggestion to open while the outdoor noise or air quality level is above them. Without an outdoor noise or air quality sensor (or while it is unavailable) it doesn't hold anything back.

### Outdoor places

Under `outdoors:`, one entry per place: `name`, and lists of entities `temperature` (sensors or `weather` entities), `air_quality` and `noise`. Their sensors add up with the top-level `outdoor_temperature`, `outdoor_air_quality` and `outdoor_noise`.

Air quality is read as a level from 1 (good) to 6 (extremely poor): a European index (Atmo France, EAQI) as is, a US AQI (device class `aqi`, or a value above 6) by its bands (≤ 50: 1, ≤ 100: 2, ≤ 150: 3, ≤ 200: 4, ≤ 300: 5, above: 6), a text state (`good`, `fair`, `moderate`, `poor`, `very_poor`, `extremely_poor`, `bon`, `mauvais`…) by its name. 0 means no data (Atmo).

Each alert also takes `enabled`, `hysteresis` (how far back past the threshold the value must go for the problem to end), `delay` (minutes the condition must hold), `severity` (`info`, `warning`, `critical`) and `escalation` (notify again when the value gets this much worse; 0: never).

### Device control

The first six rows (`enabled`, `start` / `end`, `manual_override`, `suppress_when_handled`, `night_start` / `night_end`, `display_off` / `display_on`) are global: set them under `control:` only. The `climate.*`, `fans.*` and `purifiers.*` options are set under `control:` for every room, under `rooms[].control:` for one room, and on the device item itself for one device (without the `climate.` / `fans.` / `purifiers.` prefix).

| Option | Default | Description |
|---|---|---|
| `enabled` | `true` | Control the devices (also the **Device control** switch) |
| `start` / `end` | 09:00 / 21:00 | Window boost hours of the fans and purifiers. Both empty (or equal): all day |
| `manual_override` | 60 min | A device changed by hand is left alone this long, then its target is applied again. 0: never paused |
| `suppress_when_handled` | `true` | No "too hot" alert for a room whose air conditioner or fan is running on Smart Comfort's command |
| `night_start` / `night_end` | 22:00 / 07:00 | Quiet night hours: devices with night settings use them, and get no window boost |
| `display_off` / `display_on` | the quiet night | Hours the indicator lights and displays of the devices are off (e.g. 20:00 / 10:00) |
| `display` | none | On a device item: its indicator light or display — a `light` or `switch` (on/off), a `number` (off: its minimum), a `select` (off: its off option, such as `Off` or `Fermer`). Off in the display hours and during the naps of the room; Smart Comfort acts only when these start or end, so one turned back on by hand stays on until the next change |
| `reset_at` | none | On a device item: a time it goes back to its normal state (closed preset / mode, temperature control), its manual pause ended |
| `climate.cool_above` / `off_below` | 23 / 21 °C | Cool above, turn off below |
| `climate.setpoint` / `fan_mode` | 22 °C / none | Setpoint and fan mode when cooling |
| `climate.closed_for` / `off_on_open` | 2 / 1 min | Openings closed for this long before cooling; off when one stays open this long |
| `climate.night_fan_mode` | none | Fan mode when cooling at night (e.g. `silent`) |
| `fans.on_above` / `off_below` | 23 / 22 °C | On above, off below. Leave both empty for fans driven by the windows only |
| `fans.percentage` / `preset` | 50 % / none | When on |
| `fans.open_percentage` / `open_preset` | 100 % / none | While a window is open in the boost hours |
| `fans.off_preset` | none | Preset set before turning off (the fan restarts in it) |
| `fans.night_percentage` / `night_preset` | none | Speed and preset when on at night (unset: the day ones) |
| `purifiers.open_percentage` / `open_preset` | 100 % / none | While a window is open in the boost hours |
| `purifiers.closed_preset` | none | When the windows are closed. Without it (nor `closed_mode`), the purifier goes back to the state it had before the boost |
| `purifiers.mode_select` / `open_mode` / `closed_mode` | none | A `select` entity and its options for the two states (e.g. `manual` / `automatic`) |
| `purifiers.keep_on` | `false` | Turn the purifier back on when it has been off for 10 seconds |
| `purifiers.night_percentage` / `night_preset` / `night_mode` | none | At night: speed, preset, mode select option (e.g. `Sleep`). An off purifier stays off; the state before the night comes back in the morning (or the closed preset / mode) |

An air conditioner in another mode than `cool` or `off` (heat, dry…) is left alone by the temperature control, but turned off when an opening stays open.

Presets and modes depend on each device: set them on the device item (Discover picks them from the device's own list), not under `control:`. The panel offers them per device only.

```yaml
      fans:
        - entity_id: fan.living_fan
          preset: Naturel
          open_preset: Standard
          display: number.living_fan_screen_brightness
      purifiers:
        - entity_id: fan.bedroom_purifier
          open_preset: Favorite
          closed_preset: Auto
          night_preset: Sleep
          display: light.bedroom_purifier_indicator_light
          reset_at: "20:40"          # back to Auto, even after a change by hand
```

Thresholds and messages are in °C; sensors in °F or K are converted. An opening unavailable for 10 minutes (dead battery…) is left out of its room instead of blocking its alerts and devices (`ignored_openings` attribute of the room sensor). The problems of a sensor removed from a room end.

### Adaptive lighting

Set under `lighting:` for every light, under `rooms[].lighting:` for the lights of one room, and on the light item itself (`rooms[].lights:`) for one light. `enabled` and `transition` are global.

| Option | Default | Description |
|---|---|---|
| `enabled` | `true` | Adapt the lights (also the **Adaptive lighting** switch) |
| `day` | 100 % | Brightness with the sun up (elevation above 6°) |
| `evening` | 60 % | Brightness once the sun is down (below −6°); in between, a blend of the two |
| `night` | 15 % | Brightness in the quiet night hours (`control.night_start` / `night_end`) |
| `warmth` | `true` | Also set the color temperature, for the lights that support it. `false`: brightness only |
| `day_kelvin` / `evening_kelvin` / `night_kelvin` | 4000 / 2700 / 2200 K | Color temperature by time of day (within what each light can do) |
| `transition` | 120 s | Duration of the gradual changes; a light just turned on gets its brightness at once |
| `morning` | 40 % | Brightness of the quiet morning (rooms with `quiet_morning`), from the end of the night until `morning_end` |
| `morning_end` | 09:30 | End of the quiet morning (global) |
| `quiet_morning` | `false` | Dimmer lights in the morning for this room or light (Discover sets it on bedrooms) |
| `nap` | 15 % | Brightness during the nap slots of the room (`rooms[].naps`) |
| `morning_kelvin` / `nap_kelvin` | 3000 / 2200 K | Color temperature of the quiet morning and of the naps |
| `night_only` | `false` | On a light item: a night light, set only in the night hours and the naps, left alone by day |

Naps are set per room under `rooms[].naps:` — `start`, `end` and optionally `days` (`mon` … `sun`, every day when none). Discover never adds any. Order of precedence: night, nap, quiet morning, then day / evening.

Only the lights that are on are set: Smart Comfort never turns a light on or off. A brightness or warmth changed by hand pauses the light until it is turned off, or for `control.manual_override` minutes. On/off-only lights are left alone.

```yaml
smart_comfort:
  lighting:
    evening: 50
    night: 10
    warmth: false              # brightness only
  rooms:
    - name: Living room
      lights: [light.living_room, light.sofa]
      lighting: { evening: 70 }  # this room only
    - name: Kids' bedroom
      lights: [light.kids, { entity_id: light.kids_night_light, night_only: true }]
      lighting: { quiet_morning: true }   # dimmer until morning_end (09:30)
      naps:
        - { start: "13:30", end: "15:30", days: [sat, sun] }
```

### Lights on presence

Set per room under `rooms[].presence:` (in the panel: room → Lighting → Lights on presence). Discover never adds it: an existing presence automation would do the same.

| Option | Default | Description |
|---|---|---|
| `sensors` | required | Presence, occupancy or motion `binary_sensor`s: someone is there while one of them is on |
| `lights` | the room's | The lights turned on and off; any light can be added (the hallway's from the entrance) |
| `lux` / `max_lux` | none | A light level sensor, and the level above which no light is turned on |
| `on_after` | 0 s | Seconds a presence must last before the lights are turned on |
| `off_after` | 2 min | Minutes with nobody before the lights are turned off (decimals allowed) |
| `transition` | none | Seconds of the fade when the lights are turned on and off |
| `not_during_naps` | none | Lights not turned on while a room of the house has its nap (`rooms[].naps`) |
| `slots` | none | `start`, `end`, optional `days` and `lights` (all when none), then `off: true` (not turned on) or `brightness` (in %) and `color` (RGB, for the color lights), and optionally `off_after` (minutes with nobody before off while the slot applies: longer in the evening for a bathroom). The first slot that applies to a light decides |

A light is turned on only when none of the presence lights is already on, at the brightness of the moment (adaptive lighting) unless a slot sets one; a night light only at night and during the naps. Every presence light that is on is turned off once nobody is left. A presence light turned off by hand while someone is there is not turned back on until the room is empty. A light that is a presence light of two rooms (the hallway's, from the entrance and the hallway) stays on while someone is in either of them, and a light on because of the other room doesn't stop this room from turning its own on.

```yaml
    - name: Entrance
      lights: [light.entrance]
      presence:
        sensors: [binary_sensor.entrance_occupancy]
        lights: [light.entrance, light.hallway]
        lux: sensor.entrance_illuminance
        max_lux: 10
        off_after: 2
        not_during_naps: [light.hallway]
        slots:
          - { start: "06:30", end: "08:00", days: [mon, tue, wed, thu, fri], off: true }
          - { start: "20:00", end: "09:00", lights: [light.entrance], brightness: 20 }
          - { start: "20:00", end: "09:00", lights: [light.hallway], off: true }
    - name: Hallway
      lights: [light.hallway, { entity_id: light.hallway_night_light, night_only: true }]
      presence:
        sensors: [binary_sensor.hallway_occupancy]
        on_after: 5                  # someone passing by doesn't count
        off_after: 0.2
        slots:
          - { start: "20:00", end: "10:00", lights: [light.hallway_night_light], brightness: 30, color: [0, 0, 255] }
          - { start: "20:00", end: "10:00", lights: [light.hallway], off: true }
          - { start: "10:00", end: "20:00", lights: [light.hallway_night_light], off: true }
          - { start: "13:30", end: "17:00", off: true }
```

A slot color, like a slot brightness, is kept until the light is turned off (the adaptive lighting leaves it alone).

### Activity card

The integration also adds a Lovelace card (no resource to add): the latest activity of Smart Comfort, live, for any user.

```yaml
type: custom:smart-comfort-activity-card
title: Smart Comfort        # optional
limit: 10                   # entries shown (10 by default)
kinds: [device, presence]   # optional: device, lighting, presence, display, notified, manual, reset, failed
room: Living room           # optional: one room only
```

The activity (the last 300 entries) is kept across restarts. It is also available to any user with the WebSocket command `smart_comfort/activity` (`limit`), which sends the latest entries, then each new one.

### Entities

| Entity | Description |
|---|---|
| `sensor.smart_comfort_active_alerts` | Number of current problems. Attributes: `alerts` (room, kind, value, since, notified_at, snoozed, acknowledged, handled…), `snoozes`, `outdoor_temperature`, `outdoor_noise`, `outdoor_air_quality` |
| `sensor.smart_comfort_<room>_comfort` | `ok` or the main problem of the room. Attributes: readings, open and ignored openings, alerts, device targets and manual overrides |
| `sensor.smart_comfort_last_notification` | Time of the last notification. Attributes: `title`, `message`, `severity`, `alerts` |
| `switch.smart_comfort_notifications` | Send notifications (problems are still tracked when off) |
| `switch.smart_comfort_device_control` | Control the devices |
| `switch.smart_comfort_adaptive_lighting` | Adapt the brightness of the lights |
| `button.smart_comfort_notify_now` | Send every current problem now, ignoring quiet hours and the digest window |
| `button.smart_comfort_cancel_snoozes` | Cancel every snooze |

### Actions

| Action | Fields | Description |
|---|---|---|
| `smart_comfort.snooze` | `duration` (min), `rooms`, `kinds` | Don't notify for a while. Without `kinds`, problems that come up meanwhile in these rooms are snoozed too |
| `smart_comfort.unsnooze` | `rooms` | Cancel the snoozes |
| `smart_comfort.acknowledge` | `rooms`, `kinds` | No reminder nor escalation for the current problems until they end |
| `smart_comfort.notify_now` | | Send a summary now; returns `sent` |
| `smart_comfort.get_config` | | Returns the options in use (response only), to copy into the YAML or check what is set |

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

The screenshots are rendered by `python scripts/screenshots.py` (Playwright and Chromium: the panel with mock data, in the light and the dark theme). On a pull request that changes the panel or the script, the **Screenshots** workflow renders them and commits them to the branch.

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
