"""Light platform for Gyver Lamp MQTT with 3 sliders: brightness, color/scale, speed."""
import logging
from typing import Any, Tuple

from homeassistant.components import mqtt
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

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
    """Representation of Gyver Lamp with 3 sliders."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS, ColorMode.HS, ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST
    _attr_brightness = 255
    _attr_is_on = False
    _attr_effect = EFFECT_LIST[0]
    _attr_should_poll = False
    _attr_hs_color: Tuple[float, float] | None = None
    _attr_color_temp_kelvin: int | None = None
    _scale_value = 50
    _speed_value = 4

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

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await mqtt.async_subscribe(
            self.hass, self._state_topic, self._on_mqtt_message
        )

    @callback
    def _on_mqtt_message(self, msg: mqtt.models.ReceiveMessage) -> None:
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
            speed = int(parts[3])
            scale = int(parts[4])
            is_on = parts[5] == "1"

            self._scale_value = scale
            self._speed_value = speed

            # Скорость → цветовая температура (2000K-6500K)
            self._attr_color_temp_kelvin = int((speed - 1) / 254 * 4500 + 2000)

            # Цвет/Масштаб → оттенок (0-360°)
            # Для всех эффектов используем один параметр: масштаб 1-100 → оттенок 0-360°
            hue = (scale - 1) / 99 * 360
            self._attr_hs_color = (hue, 100.0)  # Насыщенность фиксирована 100%

            # Режим цвета: всегда включаем оба режима для отображения двух слайдеров
            # (ограничение HA: можно указать несколько режимов, но активен будет один)
            # Мы динамически переключаем в методе _determine_color_mode()
            self._determine_color_mode(effect_idx)

            self._attr_effect = EFFECT_LIST[effect_idx] if effect_idx < len(EFFECT_LIST) else None
            self._attr_brightness = brightness
            self._attr_is_on = is_on

            self.async_write_ha_state()
        except (IndexError, ValueError) as err:
            _LOGGER.warning("Failed to parse state: %s", err)

    def _determine_color_mode(self, effect_idx: int) -> None:
        """Determine active color mode based on effect."""
        # Для эффектов #1 (Огонь) и #16 (Цвет) активируем режим цвета
        if effect_idx in (1, 16):
            self._attr_color_mode = ColorMode.HS
        # Для всех остальных — режим цветовой температуры (скорость)
        # Но мы хотим видеть ОБА слайдера! Поэтому хак:
        # Указываем оба режима в supported_color_modes, а активный переключаем динамически
        else:
            # Приоритет: скорость важнее для большинства эффектов
            self._attr_color_mode = ColorMode.COLOR_TEMP

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lamp on."""
        # Установка эффекта
        if ATTR_EFFECT in kwargs:
            effect_name = kwargs[ATTR_EFFECT]
            if effect_name in EFFECT_LIST:
                effect_idx = EFFECT_LIST.index(effect_name)
                await mqtt.async_publish(
                    self.hass, self._command_topic, f"EFF{effect_idx}"
                )
                self._attr_effect = effect_name
                self._determine_color_mode(effect_idx)

        # Установка цвета/масштаба через оттенок (для ВСЕХ эффектов)
        if ATTR_HS_COLOR in kwargs:
            hue, saturation = kwargs[ATTR_HS_COLOR]
            # Оттенок 0-360° → масштаб 1-100
            scale = int(hue / 360 * 99) + 1
            scale = max(1, min(100, scale))
            await mqtt.async_publish(
                self.hass, self._command_topic, f"SCA{scale}"
            )
            self._scale_value = scale
            self._attr_hs_color = (hue, saturation)

        # Установка скорости через цветовую температуру (для ВСЕХ эффектов)
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            # Цветовая температура 2000-6500K → скорость 1-255
            speed = int((temp - 2000) / 4500 * 254) + 1
            speed = max(1, min(255, speed))
            await mqtt.async_publish(
                self.hass, self._command_topic, f"SPD{speed}"
            )
            self._speed_value = speed
            self._attr_color_temp_kelvin = temp

        # Установка яркости
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await mqtt.async_publish(
                self.hass, self._command_topic, f"BRI{brightness}"
            )
            self._attr_brightness = brightness

        # Включение матрицы
        if not self._attr_is_on:
            await mqtt.async_publish(
                self.hass, self._command_topic, "P_ON"
            )
            self._attr_is_on = True

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lamp off."""
        await mqtt.async_publish(
            self.hass, self._command_topic, "P_OFF"
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return minimum color temperature."""
        return 2000

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return maximum color temperature."""
        return 6500

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"gyver_lamp_{self._chip_id}")},
            name=self._attr_name,
            manufacturer="AlexGyver",
            model="LED Matrix Lamp",
        )