"""A media player entity for an NEC M/ME-series display."""

from __future__ import annotations

import functools
from typing import Any

import necme

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import NECDisplayEntity

SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Samsung TV from a config entry."""
    controller = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NECDisplayPlayer(controller, entry)], update_before_add=True)


class NECDisplayPlayer(NECDisplayEntity, MediaPlayerEntity):
    """Media player entity type for NEC M/ME-series displays."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = SUPPORTED_FEATURES

    async def async_update(self) -> None:
        """Update the device properties."""
        if self.hass.is_stopping:
            return

        await self._async_update_state()
        await self._async_update_source()
        self._attr_source_list = self._controller.known_input_names

    async def _async_update_state(self) -> None:
        tries = 0
        while tries < 3:
            try:
                self._attr_state = _player_state(
                    await self._controller.async_get_power_mode()
                )
                return
            except TimeoutError:
                tries = tries + 1

        raise TimeoutError(
            "failed to retrieve current power status after %d attempts" % tries
        )

    async def _async_update_source(self) -> None:
        tries = 0
        while tries < 3:
            try:
                self._attr_source = await self._controller.async_get_active_input_name()
                return
            except TimeoutError:
                tries = tries + 1

        raise TimeoutError(
            "failed to retrieve current input terminal after %d attempts" % tries
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Command the display to turn off."""
        new_mode = await self._controller.async_turn_off()
        self._attr_state = _player_state(new_mode)
        self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Command the display to turn off."""
        new_mode = await self._controller.async_turn_on()
        self._attr_state = _player_state(new_mode)
        self.async_schedule_update_ha_state()


def _player_state(mode: necme.PowerMode) -> MediaPlayerState:
    if mode is necme.PowerMode.ON:
        return MediaPlayerState.ON
    return MediaPlayerState.OFF
