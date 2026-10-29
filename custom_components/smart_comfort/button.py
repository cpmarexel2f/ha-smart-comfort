"""Buttons: send a summary now, cancel the snoozes."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartComfortConfigEntry
from .entity import SmartComfortEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartComfortConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    m = entry.runtime_data
    async_add_entities(
        [NotifyNowButton(m, entry.entry_id, "notify_now"), UnsnoozeButton(m, entry.entry_id, "unsnooze")]
    )


class NotifyNowButton(SmartComfortEntity, ButtonEntity):
    """Send every current problem in one notification, ignoring quiet hours and the digest window."""

    async def async_press(self) -> None:
        await self.manager.async_notify_now()


class UnsnoozeButton(SmartComfortEntity, ButtonEntity):
    """Cancel every snooze."""

    async def async_press(self) -> None:
        await self.manager.async_unsnooze(None)
