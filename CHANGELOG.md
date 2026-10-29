# Changelog

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
