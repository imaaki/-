import sqlite3
import uuid
from datetime import date
from itertools import product
from pathlib import Path

import streamlit  as st

# ---------- Настройки проекта ----------
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "wardrobe.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

CATEGORIES = [
    "Верх",
    "Низ",
    "Платье / комбинезон",
    "Обувь",
    "Верхняя одежда",
    "Аксессуар",
    "Другое",
]
SEASONS = ["Всесезонная", "Весна", "Лето", "Осень", "Зима"]
OCCASIONS = ["Повседневный", "Учёба / работа", "Праздник", "Спорт", "Прогулка"]

# Сливовая палитра с контрастным тёмным текстом и светлыми полями
CREAM = "#F7F3F7"       # фон приложения
PLUM = "#4B3152"        # основные сливовые элементы
CHERRY = "#963B55"      # кнопки при наведении и акцент
BUTTER = "#F2DE93"      # небольшие выделения
INK = "#2D2430"         # основной текст — тёмный
SIDEBAR = "#E9E1EB"     # фон бокового меню
SURFACE = "#FFFFFF"     # фон
