"""Constants for Gyver Lamp MQTT integration."""
from typing import Final

DOMAIN: Final = "gyver_lamp"

DEFAULT_NAME: Final = "Gyver Lamp"
DEFAULT_COMMAND_TOPIC: Final = "LedLamp/LedLamp_xxxxxxxx/cmnd"
DEFAULT_STATE_TOPIC: Final = "LedLamp/LedLamp_xxxxxxxx/state"

# Effect names in Russian (точно как в прошивке)
EFFECT_LIST: Final = [
    "Конфетти", "Огонь", "Белый огонь", "Радуга верт.", "Радуга гориз.",
    "Радуга диаг.", "Смена цвета", "Безумие 3D", "Облака 3D", "Лава 3D",
    "Плазма 3D", "Радуга 3D", "Павлин 3D", "Зебра 3D", "Лес 3D",
    "Океан 3D", "Цвет", "Снегопад", "Метель", "Звездопад", "Матрица",
    "Светлячки", "Светлячки шлейф", "Пейнтбол", "Кубик", "Белый свет",
]