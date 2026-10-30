# Changelog

## 1.0.0

### What's new
- **Outdoors**: outdoor places (`outdoors:` — garden, terrace…), each with its `temperature`, `air_quality` and `noise` sensors, shown in an **Outdoors** category below the rooms in the panel. Their sensors add up with the top-level outdoor options.
- **Outdoor air quality**: `outdoor_air_quality` sensors and those of the outdoor places, read as a level from 1 (good) to 6 (extremely poor) — European indexes (Atmo France, EAQI) as is, US AQI by its bands, text states — the worst one counts. A **close the windows (poor air outside)** alert (`bad_air_outside`, above level 3), and no suggestion to open the windows while the air is poor (`ventilate.max_outdoor_air`, 3). Shown in the overview and in the attributes of the active alerts sensor, with the outdoor noise.
- While nothing is set up (no room nor outdoor place), the overview of the panel offers **Discover**, which opens its result in the Rooms tab.
- Discover puts the outdoor areas in the Outdoors category instead of leaving them out, with their temperature, air quality and noise sensors (an outdoor module counts by the area of its device); their sensors leave the top-level options, where they would count twice. Outdoor sensors in no area are added to the top-level options: a sensor named outdoor, a city air quality index (Atmo France, WAQI, AirVisual…, not its forecast nor pollen), and the weather entity when there is no outdoor temperature sensor at all.

### Fixes
- Discover completes the outdoor sensors that are already set instead of skipping them as soon as one is there.
- Options flow: the noise alerts and the maximum outdoor noise show dB instead of °C.

## 0.4.0

### What's new
- **Noise alerts**: a room `noise` sensor (sound level, dB) and a **noisy room** alert (60 dB by default); outdoor noise sensors (`outdoor_noise`) with a **close the windows (noisy outside)** alert when an opening is open in the noise (65 dB), and no suggestion to open the windows while it is noisy outside (`ventilate.max_outdoor_noise`, 65 dB).
- **Quiet night**: between `night_start` and `night_end` (22:00–07:00 by default), devices with night settings run quieter — fans at `night_percentage` / `night_preset`, purifiers at `night_preset` / `night_percentage` / `night_mode` (mode select), air conditioners with `night_fan_mode` — and get no window boost. The day settings, or the state before the night, come back in the morning. An off purifier stays off at night.
- Discover fills in the room noise sensors, the outdoor noise sensors of the outdoor areas, and the night settings from the quiet presets and fan modes (sleep, silent…); devices already configured get the settings they don't have yet.
- Panel: noise in the overview (outdoor noise, quiet night, room noise) and in the forms.

### Fixes
- A purifier driven by a mode select gets its mode option back too when the state it had before a window boost is restored.

### Maintenance
- The panel subscription test no longer depends on the order of the unload and setup messages, which differs on Home Assistant 2024.12 (the minimum version job failed since 0.3.1).

## 0.3.1

### Fixes
- Panel: the overview no longer shows "Smart Comfort is not loaded" for up to 30 s after a reload (options saved, restart, integration reloaded): the status sent at the end of the setup is now taken into account, and the overview follows the live status instead of the state read when the panel opened.

## 0.3.0

### What's new
- **Discover** button in the Rooms tab of the panel: adds a room for every Home Assistant area except the outdoor ones and sets it up (sensors, windows and doors, air conditioner, fans and purifiers with their presets and modes); the outdoor areas give the outdoor temperature. What is already set is kept; the result is shown collapsed with a summary of each room and is saved with **Save**. WebSocket command `smart_comfort/discover`.
- Rooms remember the area they come from (`area`), so that discovering again completes them instead of adding them twice.

## 0.2.0

### What's new
- **Configuration panel** in the sidebar (administrators): overview of the active alerts, rooms and devices with snooze / acknowledge buttons and the notification and control switches; editing of the rooms (sensors, openings, air conditioner, fans and purifiers with their own settings, alert overrides), the alerts, the notifications and the device control, saved in one go. Each tab has its own address (`/smart-comfort/rooms`…).
- WebSocket commands `smart_comfort/config`, `smart_comfort/config/save` and `smart_comfort/subscribe`, used by the panel.

### Fixes
- Air conditioners are now switched to cooling with `climate.set_hvac_mode` followed by `climate.set_temperature`: some integrations (`generic_thermostat`…) ignored the mode given with the temperature and never started cooling.
- Device changes while Home Assistant starts (entities settling on their first state) no longer count as manual changes pausing their control.
- The `handled` flag of an alert in the attributes is now only set on the alerts a running device actually hides ("too hot"), not on every alert of its room.

## 0.1.4

### Fixes
- An air purifier driven by its mode select only (for example `closed_mode: auto` when the windows close) no longer pauses its own control for the manual override time when it answers the mode change by updating its preset or speed: the next window boost and "keep on" work again. Changing the purifier by hand still pauses its control.

## 0.1.3

### Fixes
- A device that ends up in the wanted state although its command failed (cloud air conditioner answering too slowly…) is now considered controlled right away instead of only after the retry delay (up to one hour): its room's "too hot" alert stays hidden while it cools, turning it off by hand pauses its control instead of having it turned back on, and the retry delay starts over from 5 minutes.

## 0.1.2

### Fixes
- Air purifiers go back to the speed or preset they had before the window boost even when the first try fails (device offline for a moment…), instead of staying at full speed.
- A device command that keeps failing (unsupported preset or mode…) is no longer sent again and logged every 30 seconds: it is tried again after 5 minutes, then 10, 20… up to one hour, and right away when the device needs something else.
- The ventilate, close windows and window open in the cold alerts end when every outdoor temperature entity is deleted, instead of staying active with reminders forever.

## 0.1.1

### Fixes
- A snoozed problem that is still going on is notified again when the snooze ends (or is cancelled), instead of staying silent: Snooze no longer behaves like Got it.
- Options: a field emptied in the form now stays empty instead of coming back to its default — fans driven by the windows only (no "On from" / "Off below"), purifiers boosted with a preset only (no speed), window boost all day (no hours), alerts without minimum / maximum temperature.
- Air purifiers go back to the preset or speed they had before the window boost when the windows close (unless a "windows closed" preset or mode is set), instead of staying at full speed.
- The problems of a sensor removed from a room, or of a deleted sensor entity, now end instead of staying active forever.
- `weather` entities used as outdoor temperature work: their temperature attribute is read. Temperatures in °F or K are converted to °C.
- A device command that fails is tried again at the next evaluation.
- Alerts are no longer lost when every notifier fails: they are sent again at the next evaluation.
- The "clear notification" message is sent to the Companion app notifiers and notify groups only: other notifiers (Telegram, e-mail…) no longer receive the text "clear_notification".
- The Snooze and Got it buttons of a notification only cover the alerts it showed, also after a restart.
- No duplicate notification when the options are changed while a notification is being sent.
- "Keep on" no longer turns a purifier back on right after it was turned off by hand: the manual override applies.
- An air conditioner is turned off when an opening stays open whatever its mode (heating included), not only when cooling.
- A window or door sensor unavailable for 10 minutes (dead battery…) is left out of its room instead of blocking its alerts and devices; listed in the `ignored_openings` attribute of the room sensor.
- Renaming a room created in the options keeps its sensor, its alerts and its snoozes; the sensor of a removed room is removed.
- The Notifications and Device control switches apply from the start, before their entities are restored.
- Window open in the cold: the escalation now triggers when it gets colder outside, not warmer.
- Quiet hours or window boost hours with the same start and end now mean all day instead of never.
- An invalid value in the options shows an error instead of failing.
- Removing the integration also forgets its alerts, snoozes and device targets.
- The release zip installed by HACS includes the integration icon.
- Texts: clearer descriptions (room overrides, "this cold or colder", snooze kinds, "no too hot alert" only for devices Smart Comfort turned on), German and Spanish wording fixes.

### Maintenance
- The readings, alerts and device attributes of the sensors are no longer stored in the recorder database at every evaluation.

## 0.1.0

### What's new
- First release.
- Seven comfort alerts per room — too hot, too cold, open the windows, close the windows, window open in the cold, high CO₂, high humidity — with threshold, hysteresis, delay, severity and escalation step, globally and per room.
- Problems tracked as episodes: notified once, again only when they get worse (or after an optional reminder delay).
- One grouped notification per digest window, replacing the previous one (notification tag), cleared when everything is back to normal.
- Quiet hours and presence: only critical alerts while they apply, the others sent at the end if still relevant.
- Snooze and Got it buttons in the notification; `snooze`, `unsnooze`, `acknowledge` and `notify_now` actions.
- Control of air conditioners, fans and air purifiers per room: temperature with hysteresis, window boost during the day, mode selects, keep on, pause after a manual change.
- Configuration in YAML (imported at startup, applied again only when it changes) or in the integration options.
- Sensors for the active alerts, the comfort of each room and the last notification; switches for the notifications and the device control; buttons.
- State kept across restarts: no notification sent again after a restart.
- English, French, German and Spanish.
