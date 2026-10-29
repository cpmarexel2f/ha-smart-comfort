# Changelog

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
