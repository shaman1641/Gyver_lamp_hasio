"""Config flow for Gyver Lamp MQTT."""
import logging
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_COMMAND_TOPIC,
    DEFAULT_STATE_TOPIC,
)

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gyver Lamp."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate topics
            command_topic = user_input["command_topic"]
            state_topic = user_input["state_topic"]

            # Try to extract chip ID from topic
            chip_id_match = re.search(r'LedLamp_(\w+)', command_topic)
            if chip_id_match:
                chip_id = chip_id_match.group(1)
                await self.async_set_unique_id(f"gyver_lamp_{chip_id}")
                self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(
                        "command_topic", default=DEFAULT_COMMAND_TOPIC
                    ): str,
                    vol.Required(
                        "state_topic", default=DEFAULT_STATE_TOPIC
                    ): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Gyver Lamp."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=self.config_entry.data.get(CONF_NAME, DEFAULT_NAME),
                    ): str,
                    vol.Required(
                        "command_topic",
                        default=self.config_entry.data.get(
                            "command_topic", DEFAULT_COMMAND_TOPIC
                        ),
                    ): str,
                    vol.Required(
                        "state_topic",
                        default=self.config_entry.data.get(
                            "state_topic", DEFAULT_STATE_TOPIC
                        ),
                    ): str,
                }
            ),
        )