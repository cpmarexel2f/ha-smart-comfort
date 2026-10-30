"""Notification texts of a digest, from the translations `common.*` strings. Pure Python."""

from __future__ import annotations

import logging
from datetime import datetime

from .const import (
    KIND_BAD_AIR_OUTSIDE,
    KIND_CLOSE_WINDOWS,
    KIND_CO2,
    KIND_HUMIDITY,
    KIND_NOISE,
    KIND_NOISY_OUTSIDE,
    KIND_TOO_COLD,
    KIND_TOO_HOT,
    KIND_VENTILATE,
    KIND_WINDOW_OPEN_COLD,
)
from .engine import REASON_NEW, REASON_WORSE, Digest, _severity_rank

_LOGGER = logging.getLogger(__name__)

ICONS = {
    KIND_TOO_HOT: "🌡️",
    KIND_CLOSE_WINDOWS: "🔥",
    KIND_VENTILATE: "🪟",
    KIND_TOO_COLD: "❄️",
    KIND_WINDOW_OPEN_COLD: "🥶",
    KIND_CO2: "🌬️",
    KIND_HUMIDITY: "💧",
    KIND_NOISE: "🔊",
    KIND_NOISY_OUTSIDE: "🔇",
    KIND_BAD_AIR_OUTSIDE: "😷",
}

# English fallbacks, used when a translation is missing or broken.
FALLBACK = {
    "title_one": "{room}",
    "title_many": "{count} comfort alerts",
    "room_line": "{room}: {problem}",
    "decimal": ".",
    "duration_minutes": "{minutes} min",
    "duration_hours": "{hours} h {minutes:02d}",
    "since": "for {duration}",
    "worse": "getting worse",
    "line_too_hot": "{value} °C, above {threshold} °C",
    "line_too_cold": "{value} °C, below {threshold} °C",
    "line_ventilate": "{temperature} °C inside, {outdoor} °C outside — open the windows",
    "line_close_windows": "{outdoor} °C outside, {temperature} °C inside — close {openings}",
    "line_window_open_cold": "{openings} open, {outdoor} °C outside",
    "line_co2_high": "CO₂ {value} ppm — air the room",
    "line_humidity_high": "humidity {value} % — air the room",
    "line_noise_high": "noise {value} dB, above {threshold} dB",
    "line_noisy_outside": "{value} dB outside — close {openings}",
    "line_bad_air_outside": "outdoor air quality {value}/6 — close {openings}",
    "action_snooze": "Snooze {hours} h",
    "action_snooze_minutes": "Snooze {minutes} min",
    "action_ack": "Got it",
}

DIGITS = {KIND_CO2: 0, KIND_HUMIDITY: 0, KIND_NOISE: 0, KIND_NOISY_OUTSIDE: 0, KIND_BAD_AIR_OUTSIDE: 0}


def format_text(texts: dict[str, str], key: str, **values: object) -> str:
    template = texts.get(key) or FALLBACK[key]
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        _LOGGER.warning("Broken translation for %s: %s", key, template)
        return FALLBACK[key].format(**values)


def number(texts: dict[str, str], value: object, digits: int = 1) -> str:
    if not isinstance(value, (int, float)):
        return "?"
    text = f"{value:.{digits}f}"
    return text.replace(".", texts.get("decimal") or ".")


def duration(texts: dict[str, str], minutes: float) -> str:
    total = max(0, int(minutes))
    if total < 60:
        return format_text(texts, "duration_minutes", minutes=total)
    return format_text(texts, "duration_hours", hours=total // 60, minutes=total % 60)


def render(
    digest: Digest, texts: dict[str, str], now: datetime, names: dict[str, str] | None = None
) -> tuple[str, str, str]:
    """(title, message, icon) of a digest. `names`: friendly names of the openings."""
    names = names or {}
    lines: list[str] = []
    problems: list[str] = []
    for item in digest.items:
        ep = item.episode
        details = ep.details
        digits = DIGITS.get(ep.kind, 1)
        openings = ", ".join(names.get(o, o) for o in details.get("openings", []))
        problem = format_text(
            texts,
            f"line_{ep.kind}",
            value=number(texts, ep.value, digits),
            threshold=number(texts, details.get("threshold"), digits),
            outdoor=number(texts, details.get("outdoor")),
            temperature=number(texts, details.get("temperature")),
            openings=openings,
        )
        if item.reason == REASON_WORSE:
            problem += f" ({format_text(texts, 'worse')})"
        elif item.reason != REASON_NEW:
            problem += (
                f" ({format_text(texts, 'since', duration=duration(texts, (now - ep.since).total_seconds() / 60))})"
            )
        problems.append(problem)
        line = format_text(texts, "room_line", room=item.room_name, problem=problem)
        lines.append(f"{ICONS.get(ep.kind, '')} {line}".strip())
    top = max(digest.items, key=lambda i: (i.reason != "ongoing", _severity_rank(i.severity)))
    icon = ICONS.get(top.episode.kind, "")
    if len(digest.items) == 1:
        title = format_text(texts, "title_one", room=top.room_name)
        message = problems[0]
    else:
        title = format_text(texts, "title_many", count=len(digest.items))
        message = "\n".join(lines)
    return f"{icon} {title}".strip(), message, icon
