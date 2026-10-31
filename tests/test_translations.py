"""Every translation has exactly the keys and placeholders of the English one."""

from __future__ import annotations

import json
import string
from pathlib import Path

import pytest

TRANSLATIONS = Path(__file__).parent.parent / "custom_components" / "smart_comfort" / "translations"
LANGUAGES = ["de", "es", "fr"]


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def _load(language: str) -> dict[str, str]:
    return _flatten(json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8")))


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def test_all_languages_are_tested():
    """A new translations/*.json file is added to LANGUAGES."""
    assert sorted(p.stem for p in TRANSLATIONS.glob("*.json")) == sorted(["en", *LANGUAGES])


@pytest.mark.parametrize("language", LANGUAGES)
def test_translation_parity(language: str):
    """Same keys as en.json, same placeholders in each string, nothing empty."""
    english, other = _load("en"), _load(language)
    assert sorted(other) == sorted(english)
    for key, text in english.items():
        assert other[key].strip(), key
        assert _placeholders(other[key]) == _placeholders(text), key


@pytest.mark.parametrize("service", ["snooze", "acknowledge"])
def test_service_kinds_selector(service: str):
    """The kinds of the snooze and acknowledge actions: every kind of alert, each one translated."""
    import yaml

    from custom_components.smart_comfort.const import KINDS

    services = yaml.safe_load((TRANSLATIONS.parent / "services.yaml").read_text(encoding="utf-8"))
    options = services[service]["fields"]["kinds"]["selector"]["select"]["options"]
    assert options == list(KINDS)
    translated = json.loads((TRANSLATIONS / "en.json").read_text(encoding="utf-8"))["selector"]["kind"]["options"]
    assert sorted(translated) == sorted(KINDS)
