"""Config flow for NEC M-Series and ME-Series displays."""

import necme
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import AbortFlow

from .const import CONF_CONTROLLER, CONF_MODEL, CONF_MONITOR_ID, CONF_SERIAL, DOMAIN


class NECMEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configuration for for NEC M/ME-Series displays."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._host: str = ""
        self._monitor_id: int = 0
        self._model: str | None = None
        self._serial: str | None = None

    async def async_step_user(self, input):
        """Handle manually adding the integration."""
        if input is not None:
            controller_host = input[CONF_CONTROLLER]
            discovered = await self._async_discover(controller_host=controller_host)
            self._host = discovered.host
            self._monitor_id = discovered.monitor_id
            self._model = discovered.model
            self._serial = discovered.serial
            await self.async_set_unique_id(discovered.config_entry_unique_id)
            return self.async_create_entry(
                title=f"NEC {discovered.model}",
                data={
                    CONF_CONTROLLER: discovered.host,
                    CONF_MONITOR_ID: discovered.monitor_id,
                    CONF_MODEL: discovered.model,
                    CONF_SERIAL: discovered.serial,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONTROLLER, description="Controller hostname or IP address"
                    ): str
                }
            ),
        )

    async def _async_discover(self, controller_host):
        try:
            ctrl = await necme.Controller.connect_tcpip(controller_host)
        except ConnectionError as err:
            raise AbortFlow("cannot_connect") from err
        try:
            monitor = await ctrl.probe_open_one_monitor()
        except ValueError as err:
            raise AbortFlow("bad_protocol") from err
        except necme.UnsupportedPropertyError as err:
            raise AbortFlow("bad_protocol") from err

        try:
            model = await monitor.read_model_name()
        except ValueError as err:
            raise AbortFlow("bad_protocol") from err
        try:
            serial = await monitor.read_serial_no()
        except ValueError as err:
            raise AbortFlow("bad_protocol") from err

        return ControllerMeta(
            host=controller_host,
            monitor_id=monitor.endpoint.raw,
            model=model,
            serial=serial,
        )


class ControllerMeta:
    """Discovered metadata about a particular connected monitor."""

    def __init__(self, host, monitor_id, model, serial):
        """Initialize."""
        if len(monitor_id) != 1:
            raise ValueError("monitor_id must be exactly one byte")
        monitor_id_raw = monitor_id[0]
        if monitor_id_raw < 0x41 or monitor_id_raw > 0xA4:
            raise ValueError("invalid monitor_id")
        monitor_id = monitor_id_raw - 0x40

        self.host = host
        self.monitor_id = monitor_id
        self.model = model
        self.serial = serial

    @property
    def config_entry_unique_id(self):
        """A unique ID to use to track this controller and monitor as a config entry."""
        return f"{self.model}:{self.serial}"
