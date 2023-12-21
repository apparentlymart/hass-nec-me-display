"""Support for controlling some functionality of a display as a virtual remote control."""

from __future__ import annotations

from typing import Any

import necme

from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .entity import NECDisplayEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the remote from a config entry."""
    controller = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NECDisplayRemote(controller, entry)], update_before_add=True)


class NECDisplayRemote(NECDisplayEntity, RemoteEntity):
    """Device that sends commands to a monitor."""

    _attr_has_entity_name = True
    _attr_name = None

    async def async_update(self) -> None:
        """Update the device properties."""
        tries = 0
        while tries < 3:
            try:
                self._attr_is_on = _power_is_on(
                    await self._controller.async_get_power_mode()
                )
                return
            except TimeoutError:
                tries = tries + 1

        raise TimeoutError(
            "failed to retrieve current power status after %d attempts" % tries
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Command the display to turn off."""
        new_mode = await self._controller.async_turn_off()
        self._attr_is_on = _power_is_on(new_mode)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Command the display to turn off."""
        new_mode = await self._controller.async_turn_on()
        self._attr_is_on = _power_is_on(new_mode)


def _power_is_on(mode: necme.PowerMode) -> bool:
    return mode is necme.PowerMode.ON
