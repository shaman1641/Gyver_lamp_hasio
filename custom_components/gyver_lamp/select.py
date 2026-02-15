"""Select platform for Gyver Lamp MQTT — Alarms and dawn settings."""
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Временные опции (каждые 5 минут)
TIME_OPTIONS = ["Выключен"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 5)]

# Опции рассвета (соответствуют командам DAWN0-DAWN9)
DAWN_OPTIONS = [
    "Выключен",
    "5 минут",
    "10 минут",
    "15 минут",
    "20 минут",
    "25 минут",
    "30 минут",
    "40 минут",
    "50 минут",
    "60 минут",
]

# Маппинг дня недели → номер в команде (понедельник = 1)
DAY_TO_INDEX = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
}

DAY_NAMES = {
    "monday": "Понедельник",
    "tuesday": "Вторник",
    "wednesday": "Среда",
    "thursday": "Четверг",
    "friday": "Пятница",
    "saturday": "Суббота",
    "sunday": "Воскресенье",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gyver Lamp alarm selects."""
    cmd_topic = entry.data["command_topic"]
    state_topic = entry.data["state_topic"]
    chip_id = cmd_topic.split("/")[-2]
    base_name = entry.data["name"]

    entities = []

    # Создаём 7 будильников (по одному на день недели)
    for day_key, day_index in DAY_TO_INDEX.items():
        entities.append(
            GyverLampAlarmSelect(
                hass,
                base_name,
                cmd_topic,
                state_topic,
                chip_id,
                day_key,
                day_index,
            )
        )

    # Добавляем настройку рассвета
    entities.append(
        GyverLampDawnSelect(
            hass,
            base_name,
            cmd_topic,
            state_topic,
            chip_id,
        )
    )

    async_add_entities(entities)


class GyverLampAlarmSelect(SelectEntity):
    """Alarm control for a specific day of week."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:alarm"

    def __init__(
        self,
        hass: HomeAssistant,
        base_name: str,
        cmd_topic: str,
        state_topic: str,
        chip_id: str,
        day_key: str,
        day_index: int,
    ) -> None:
        """Initialize the alarm select."""
        self.hass = hass
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._chip_id = chip_id
        self._day_key = day_key
        self._day_index = day_index
        self._attr_name = f"Будильник {DAY_NAMES[day_key]}"
        self._attr_unique_id = f"gyver_lamp_{chip_id}_alarm_{day_key}"
        self._attr_options = TIME_OPTIONS
        self._attr_current_option = "Выключен"
        self._alarm_minutes = 0
        self._is_enabled = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await mqtt.async_subscribe(
            self.hass, self._state_topic, self._on_mqtt_message
        )

    @callback
    def _on_mqtt_message(self, msg: mqtt.models.ReceiveMessage) -> None:
        """Handle incoming MQTT messages."""
        if not msg.payload.startswith("ALMS "):
            return

        try:
            parts = msg.payload.split()
            if len(parts) < 16:
                return

            # Первые 7 значений — статусы будильников (1 = вкл, 0 = выкл)
            enabled_status = int(parts[self._day_index])  # parts[1] = пн, parts[2] = вт...
            self._is_enabled = enabled_status == 1

            # Следующие 7 значений — время в минутах
            time_index = 7 + self._day_index  # parts[8] = время пн, parts[9] = время вт...
            self._alarm_minutes = int(parts[time_index])

            # Обновляем текущую опцию
            if self._is_enabled:
                hours = self._alarm_minutes // 60
                minutes = self._alarm_minutes % 60
                self._attr_current_option = f"{hours:02d}:{minutes:02d}"
            else:
                self._attr_current_option = "Выключен"

            self.async_write_ha_state()
        except (IndexError, ValueError) as err:
            _LOGGER.debug("Failed to parse ALMS message: %s", err)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "Выключен":
            # Выключаем будильник
            await mqtt.async_publish(
                self.hass,
                self._cmd_topic,
                f"ALM_SET{self._day_index} OFF",
            )
            self._attr_current_option = "Выключен"
            self._is_enabled = False
        else:
            # Включаем будильник с указанным временем
            hours, minutes = map(int, option.split(":"))
            total_minutes = hours * 60 + minutes
            await mqtt.async_publish(
                self.hass,
                self._cmd_topic,
                f"ALM_SET{self._day_index} {total_minutes}",
            )
            self._attr_current_option = option
            self._is_enabled = True
            self._alarm_minutes = total_minutes

        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"gyver_lamp_{self._chip_id}")},
            name=f"{self._attr_name} ({self._chip_id})",
            manufacturer="AlexGyver",
            model="LED Matrix Lamp",
            via_device=(DOMAIN, f"gyver_lamp_{self._chip_id}"),
        )


class GyverLampDawnSelect(SelectEntity):
    """Dawn (sunrise) time before alarm."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:weather-sunset-up"
    _attr_name = "Рассвет перед будильником"
    _attr_options = DAWN_OPTIONS

    def __init__(
        self,
        hass: HomeAssistant,
        base_name: str,
        cmd_topic: str,
        state_topic: str,
        chip_id: str,
    ) -> None:
        """Initialize the dawn select."""
        self.hass = hass
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._chip_id = chip_id
        self._attr_unique_id = f"gyver_lamp_{chip_id}_dawn"
        self._attr_current_option = "Выключен"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await mqtt.async_subscribe(
            self.hass, self._state_topic, self._on_mqtt_message
        )

    @callback
    def _on_mqtt_message(self, msg: mqtt.models.ReceiveMessage) -> None:
        """Handle incoming MQTT messages."""
        if not msg.payload.startswith("ALMS "):
            return

        try:
            parts = msg.payload.split()
            if len(parts) < 16:
                return

            # Последнее значение — опция рассвета (0-9)
            dawn_option = int(parts[-1])
            if 0 <= dawn_option < len(DAWN_OPTIONS):
                self._attr_current_option = DAWN_OPTIONS[dawn_option]
                self.async_write_ha_state()
        except (IndexError, ValueError) as err:
            _LOGGER.debug("Failed to parse ALMS dawn message: %s", err)

    async def async_select_option(self, option: str) -> None:
        """Change the selected dawn option."""
        try:
            index = DAWN_OPTIONS.index(option)
            await mqtt.async_publish(
                self.hass,
                self._cmd_topic,
                f"DAWN{index}",
            )
            self._attr_current_option = option
            self.async_write_ha_state()
        except ValueError:
            _LOGGER.error("Invalid dawn option: %s", option)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"gyver_lamp_{self._chip_id}")},
            name=f"Рассвет ({self._chip_id})",
            manufacturer="AlexGyver",
            model="LED Matrix Lamp",
            via_device=(DOMAIN, f"gyver_lamp_{self._chip_id}"),
        )