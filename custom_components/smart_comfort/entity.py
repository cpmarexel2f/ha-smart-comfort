"""Base entity: one service device, refreshed after every evaluation."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, TITLE
from .manager import SmartComfort


class SmartComfortEntity(Entity):
    """Shared device and listener."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: SmartComfort, entry_id: str, key: str, unique: str | None = None) -> None:
        self.manager = manager
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{unique or key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=TITLE,
            manufacturer="juju35",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://github.com/juju35/ha-smart-comfort",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.async_add_listener(self.async_write_ha_state))
