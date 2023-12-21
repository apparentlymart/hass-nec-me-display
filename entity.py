"""Base entity for all concrete entity types in this component."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CONF_MODEL, CONF_SERIAL, DOMAIN, LOGGER


class NECDisplayEntity(Entity):
    """Base entity for all concrete entity types in this component."""

    def __init__(self, controller, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self._controller = controller
        self._attr_unique_id = config_entry.unique_id or config_entry.entry_id
        LOGGER.info(
            "setting up device for %s %s",
            config_entry.data.get(CONF_MODEL),
            config_entry.data.get(CONF_SERIAL),
        )
        self._attr_device_info = DeviceInfo(
            name=f"NEC {config_entry.data.get(CONF_MODEL)}",
            manufacturer="NEC",
            model=config_entry.data.get(CONF_MODEL),
            serial_number=config_entry.data.get(CONF_SERIAL),
        )
        if self.unique_id:
            self._attr_device_info[ATTR_IDENTIFIERS] = {(DOMAIN, self.unique_id)}
