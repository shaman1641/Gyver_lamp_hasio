"""Number platform for Gyver Lamp MQTT."""
import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gyver Lamp numbers."""
    base_name = entry.data["name"]
    cmd_topic = entry.data["command_topic"]
    state_topic = entry.data["state_topic"]
    entry_id = entry.entry_id

    async_add_entities([
        GyverLampSpeed(hass, base_name, cmd_topic, state_topic, entry_id),
        GyverLampScale(hass, base_name, cmd_topic, state_topic, entry_id),
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

    def __init__(self, hass, base_name, cmd_topic, state_topic, entry_id):
        self.hass = hass
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._entry_id = entry_id
        self._chip_id = cmd_topic.split("/")[-2]
        self._attr_unique_id = f"gyver_lamp_{self._chip_id}_speed"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"gyver_lamp_{self._chip_id}")},
        )
        hass.components.mqtt.async_subscribe(state_topic, self._on_mqtt_message)

    @callback
    def _on_mqtt_message(self, msg: dict[str, Any]) -> None:
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
        await self.hass.components.mqtt.async_publish(
            self._cmd_topic, f"SPD{int(value)}"
        )
        self.async_write_ha_state()


class GyverLampScale(NumberEntity):
    """Scale control for Gyver Lamp."""

    _attr_has_entity_name = True
    _attr_name = "Масштаб"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_value = 50
    _attr_icon = "mdi:magnify"
    _attr_should_poll = False

    def __init__(self, hass, base_name, cmd_topic, state_topic, entry_id):
        self.hass = hass
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._entry_id = entry_id
        self._chip_id = cmd_topic.split("/")[-2]
        self._attr_unique_id = f"gyver_lamp_{self._chip_id}_scale"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"gyver_lamp_{self._chip_id}")},
        )
        hass.components.mqtt.async_subscribe(state_topic, self._on_mqtt_message)

    @callback
    def _on_mqtt_message(self, msg: dict[str, Any]) -> None:
        """Update scale from state."""
        if msg.payload.startswith("CURR "):
            try:
                parts = msg.payload.split()
                self._attr_native_value = int(parts[4])
                self.async_write_ha_state()
            except (IndexError, ValueError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        """Set new scale value."""
        self._attr_native_value = value
        await self.hass.components.mqtt.async_publish(
            self._cmd_topic, f"SCA{int(value)}"
        )
        self.async_write_ha_state()