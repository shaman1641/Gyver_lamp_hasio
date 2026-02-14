"""Light platform for Gyver Lamp MQTT."""
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, EFFECT_LIST

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gyver Lamp light."""
    device = GyverLampDevice(
        hass,
        entry.data["name"],
        entry.data["command_topic"],
        entry.data["state_topic"],
        entry.entry_id,
    )
    async_add_entities([device])


class GyverLampDevice(LightEntity):
    """Representation of Gyver Lamp."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST
    _attr_brightness = 255
    _attr_is_on = False
    _attr_effect = EFFECT_LIST[0]
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        command_topic: str,
        state_topic: str,
        entry_id: str,
    ) -> None:
        """Initialize the lamp."""
        self.hass = hass
        self._attr_name = name
        self._command_topic = command_topic
        self._state_topic = state_topic
        self._entry_id = entry_id
        self._chip_id = command_topic.split("/")[-2]
        self._attr_unique_id = f"gyver_lamp_{self._chip_id}"

        # Subscribe to state updates
        hass.components.mqtt.async_subscribe(state_topic, self._on_mqtt_message)

    @callback
    def _on_mqtt_message(self, msg: dict[str, Any]) -> None:
        """Handle incoming MQTT messages."""
        payload = msg.payload
        
        if not payload.startswith("CURR "):
            return

        parts = payload.split()
        if len(parts) < 10:
            _LOGGER.warning("Invalid state message: %s", payload)
            return

        try:
            effect_idx = int(parts[1])
            brightness = int(parts[2])
            is_on = parts[5] == "1"

            self._attr_effect = EFFECT_LIST[effect_idx] if effect_idx < len(EFFECT_LIST) else None
            self._attr_brightness = brightness
            self._attr_is_on = is_on

            self.async_write_ha_state()
        except (IndexError, ValueError) as err:
            _LOGGER.warning("Failed to parse state: %s", err)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lamp on."""
        if ATTR_EFFECT in kwargs:
            effect_name = kwargs[ATTR_EFFECT]
            if effect_name in EFFECT_LIST:
                effect_idx = EFFECT_LIST.index(effect_name)
                await self.hass.components.mqtt.async_publish(
                    self._command_topic, f"EFF{effect_idx}"
                )
                self._attr_effect = effect_name

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await self.hass.components.mqtt.async_publish(
                self._command_topic, f"BRI{brightness}"
            )
            self._attr_brightness = brightness

        # Turn on matrix if needed
        if not self._attr_is_on:
            await self.hass.components.mqtt.async_publish(
                self._command_topic, "P_ON"
            )
            self._attr_is_on = True

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lamp off."""
        await self.hass.components.mqtt.async_publish(
            self._command_topic, "P_OFF"
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="AlexGyver",
            model="LED Matrix Lamp",
            configuration_url="https://alexgyver.ru/led-matrix-lamp/",
        )