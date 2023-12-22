"""Interface to NEC M-Series and ME-Series video displays.

This component implements the external control protocol for NEC M-Series and
ME-Series video displays, connecting over TCP/IP on the local network.

It provides a "remote" implementation which can turn the display on and off,
and various sensors for parameters describing the current state of the display.
"""

import asyncio
from contextlib import asynccontextmanager

import necme
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import CONF_CONTROLLER, CONF_MONITOR_ID, DOMAIN, LOGGER

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.REMOTE]

STANDARD_SOURCES: list[necme.InputTerminal] = [
    necme.InputTerminal(0x11),
    necme.InputTerminal(0x12),
    necme.InputTerminal(0x88),
    necme.InputTerminal(0x0F),
]
STANDARD_SOURCE_NAMES = {
    t.builtin_name: t for t in STANDARD_SOURCES if t.builtin_name is not None
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize a single controller entry."""
    hass.data.setdefault(DOMAIN, {})
    host = entry.data.get(CONF_CONTROLLER)
    monitor_id = entry.data.get(CONF_MONITOR_ID)

    hass.data[DOMAIN][entry.entry_id] = NECDisplayController(
        hass,
        host=host,
        monitor_id=monitor_id,
    )
    await hass.data[DOMAIN][entry.entry_id]._async_init()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Shut down a single controller entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        del hass.data[DOMAIN]
    return unload_ok


class NECDisplayController:
    """A connection to a specific display controller."""

    hass: HomeAssistant
    host: str
    monitor_id: int
    _lock: asyncio.Lock
    _input_names = dict[necme.InputTerminal, str]

    def __init__(self, hass: HomeAssistant, host: str, monitor_id=int):
        """Initialize."""
        self.hass = hass
        self.host = host
        self.monitor_id = monitor_id
        self._monitor = None
        self._user_count = 0
        self._lock = asyncio.Lock()
        self._input_names = {}

    async def _async_init(self):
        LOGGER.info("async_init")
        pass

    async def async_turn_on(self) -> necme.PowerMode:
        """Command the monitor to turn on."""
        async with self._monitor_instance() as monitor:
            LOGGER.debug("turning on monitor %d", self.monitor_id)
            new_mode = await monitor.set_power_on()
        LOGGER.debug("monitor %d is now %r", self.monitor_id, new_mode)
        return new_mode

    async def async_turn_off(self) -> necme.PowerMode:
        """Command the monitor to turn on."""
        async with self._monitor_instance() as monitor:
            LOGGER.debug("turning off monitor %d", self.monitor_id)
            new_mode = await monitor.set_power_off()
        LOGGER.debug("monitor %d is now %r", self.monitor_id, new_mode)
        return new_mode

    async def async_get_power_mode(self) -> necme.PowerMode:
        """Return the current power mode of the monitor."""
        async with self._monitor_instance() as monitor:
            LOGGER.debug("requesting power status for monitor %d", self.monitor_id)
            async with asyncio.timeout(3.0):
                mode = await monitor.read_power_status()
        LOGGER.debug("monitor %d has status %r", self.monitor_id, mode)
        return mode

    async def async_get_active_input_name(self) -> str:
        """Return the name of the currently-selected input terminal."""
        async with self._monitor_instance() as monitor, asyncio.timeout(3.0):
            LOGGER.debug(
                "requesting active input terminal for monitor %d", self.monitor_id
            )
            input = await monitor.read_active_input()
            LOGGER.debug("monitor %d has active input %r", self.monitor_id, input)
            name = self._input_names.get(input, None)
            if name is not None:
                LOGGER.debug(
                    "monitor %d input %r has cached name: %s",
                    self.monitor_id,
                    input,
                    name,
                )
                return name
            LOGGER.debug(
                "requesting name of input terminal %r from monitor %d",
                input,
                self.monitor_id,
            )
            name = (await monitor.read_input_name(input)).strip()
            LOGGER.debug("monitor %d %r has name %s", self.monitor_id, input, name)
            self._input_names[input] = name
            return name

    @property
    def known_input_names(self) -> list:
        """List of currently-known source names, often incomplete."""
        return list(self._input_names.values())

    def _input_terminal_by_name(self, name: str) -> necme.InputTerminal | None:
        for k, v in self._input_names.items():
            if v == name:
                return k
        return STANDARD_SOURCE_NAMES.get(name, None)

    @asynccontextmanager
    async def _monitor_instance(self):
        async with self._lock:
            LOGGER.debug("connecting to monitor %d at %s", self.monitor_id, self.host)
            controller = await necme.Controller.connect_tcpip(self.host)
            monitor = controller.open_monitor(self.monitor_id)
            yield monitor
            LOGGER.debug(
                "disconnecting from monitor %d at %s", self.monitor_id, self.host
            )
            await controller.close()
