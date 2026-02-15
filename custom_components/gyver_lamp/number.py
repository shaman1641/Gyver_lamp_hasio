"""Number platform for Gyver Lamp MQTT — Speed control only."""
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gyver Lamp speed control."""
    cmd_topic = entry.data["command_topic"]
    state_topic = entry.data["state_topic"]
    chip_id = cmd_topic.split("/")[-2]

    async_add_entities([
        GyverLampSpeed(hass, cmd_topic, state_topic, chip_id),
    ])


class GyverLampSpeed(NumberEntity):
    """Speed control for Gyver Lamp."""

    _attr_has_entity_name = True
    _attr_name = "Скорость"
    _attr_native_min_value = 1
    _attr_native_max_value = 255
    _attr_native_step = 1
    _attr_native_value = 4
    _attr_icon = "mdi:speedometer"
    _attr_should_poll = False

    def __init__(self, hass, cmd_topic, state_topic, chip_id):
        self.hass = hass
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._chip_id = chip_id
        self._attr_unique_id = f"gyver_lamp_{chip_id}_speed"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await mqtt.async_subscribe(
            self.hass, self._state_topic, self._on_mqtt_message
        )

    @callback
    def _on_mqtt_message(self, msg: mqtt.models.ReceiveMessage) -> None:
        """Update speed from state."""
        if msg.payload.startswith("CURR "):
            try:
                parts = msg.payload.split()
                self._attr_native_value = int(parts[3])
                self.async_write_ha_state()
            except (IndexError, ValueError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        """Set new speed value."""
        self._attr_native_value = value
        await mqtt.async_publish(
            self.hass, self._cmd_topic, f"SPD{int(value)}"
        )
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"gyver_lamp_{self._chip_id}")},
            name=f"Gyver Lamp {self._chip_id}",
            manufacturer="AlexGyver",
            model="LED Matrix Lamp",
        )