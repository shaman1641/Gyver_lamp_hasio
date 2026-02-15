"""Config flow for Gyver Lamp MQTT."""
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import DOMAIN, DEFAULT_NAME, DEFAULT_COMMAND_TOPIC, DEFAULT_STATE_TOPIC

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gyver Lamp."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Extract chip ID from topic for unique ID
            command_topic = user_input["command_topic"]
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
                    vol.Required("command_topic", default=DEFAULT_COMMAND_TOPIC): str,
                    vol.Required("state_topic", default=DEFAULT_STATE_TOPIC): str,
                }
            ),
            errors=errors,
        )