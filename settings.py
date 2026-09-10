# settings.py
import pygame
import json
import os
import math
import random
from typing import Dict, List, Tuple, Optional, Any


# ============================================================
# ОПРЕДЕЛЕНИЕ ПЛАТФОРМЫ
# ============================================================

# Проверяем, на мобильном ли устройстве запущена игра
def _is_mobile_device() -> bool:
    """Определяет, запущена ли игра на мобильном устройстве."""
    # Проверяем Android
    if os.path.exists('/system/build.prop') or os.environ.get('ANDROID_ARGUMENT'):
        return True

    # Проверяем iOS (для будущего)
    if os.environ.get('IOS_ARGUMENT'):
        return True

    # Проверяем переменную окружения для тестирования
    if os.environ.get('MOBILE_MODE', '').lower() in ('1', 'true', 'yes'):
        return True

    return False


IS_MOBILE = _is_mobile_device()

# ============================================================
# ЭКРАН И ОСНОВНЫЕ НАСТРОЙКИ
# ============================================================

if IS_MOBILE:
    # Для мобильных устройств - портретная ориентация
    SCREEN_WIDTH = 1080
    SCREEN_HEIGHT = 1920
    FPS = 30  # Меньше FPS для экономии батареи
    IS_FULLSCREEN = True
else:
    # Для десктопа - альбомная ориентация
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 60
    IS_FULLSCREEN = False

GAME_TITLE = "ПЕРЕГРУЗКА: ПОСЛЕДНИЙ ПРОТОКОЛ"
VERSION = "2.0.0"

# ============================================================
# ЦВЕТА
# ============================================================

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
LIGHT_GRAY = (180, 180, 180)
DARK_GRAY = (50, 50, 50)
RED = (220, 50, 50)
DARK_RED = (150, 20, 20)
GREEN = (50, 200, 50)
DARK_GREEN = (0, 150, 0)
LIGHT_GREEN = (100, 255, 100)
BLUE = (30, 80, 200)
LIGHT_BLUE = (100, 150, 255)
DARK_BLUE = (15, 30, 80)
CYAN = (0, 200, 200)
LIGHT_CYAN = (100, 255, 255)
YELLOW = (255, 220, 0)
LIGHT_YELLOW = (255, 255, 150)
ORANGE = (255, 140, 0)
LIGHT_ORANGE = (255, 180, 100)
PURPLE = (150, 0, 200)
LIGHT_PURPLE = (200, 100, 255)
MAGENTA = (255, 0, 255)
LIGHT_MAGENTA = (255, 150, 255)
PINK = (255, 100, 150)
BROWN = (139, 69, 19)
LIGHT_BROWN = (180, 120, 70)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BRONZE = (205, 127, 50)

# ============================================================
# ИГРОК
# ============================================================

# Адаптивные параметры для мобильных
if IS_MOBILE:
    PLAYER_SPEED = 300  # Немного медленнее для удобства управления
    PLAYER_RADIUS = 25  # Больше для лучшей видимости на маленьком экране
    PLAYER_MAX_HP = 120  # Больше HP для мобильных
    PLAYER_MAX_ENERGY = 100
    PLAYER_FIRE_RATE = 0.25  # Быстрее стрельба для компенсации
    PLAYER_BASE_DAMAGE = 30  # Больше урон
    PLAYER_CRIT_CHANCE = 0.15
    PLAYER_CRIT_MULTIPLIER = 2.0
    PLAYER_REGEN_RATE = 0.5  # Небольшая регенерация
    PLAYER_ARMOR = 1
else:
    PLAYER_SPEED = 350
    PLAYER_RADIUS = 18
    PLAYER_MAX_HP = 100
    PLAYER_MAX_ENERGY = 100
    PLAYER_FIRE_RATE = 0.3
    PLAYER_BASE_DAMAGE = 25
    PLAYER_CRIT_CHANCE = 0.15
    PLAYER_CRIT_MULTIPLIER = 2.0
    PLAYER_REGEN_RATE = 0
    PLAYER_ARMOR = 0

# ============================================================
# ОРУЖИЕ
# ============================================================

BULLET_SPEED = 700
ENEMY_BULLET_SPEED = 400
BULLET_RADIUS = 5
BULLET_LIFETIME = 2.0

# Типы оружия (адаптированы для мобильных)
WEAPON_TYPES = {
    'pistol': {
        'name': 'Пистолет',
        'damage': 30 if IS_MOBILE else 25,
        'fire_rate': 0.25 if IS_MOBILE else 0.3,
        'bullet_speed': 700,
        'bullet_radius': 6 if IS_MOBILE else 5,
        'piercing': False,
        'explosive': False,
        'ammo': -1,
        'description': 'Стандартное оружие'
    },
    'shotgun': {
        'name': 'Дробовик',
        'damage': 20 if IS_MOBILE else 15,
        'fire_rate': 0.8,
        'bullet_speed': 600,
        'bullet_radius': 5,
        'piercing': False,
        'explosive': False,
        'ammo': 30,
        'pellets': 7,
        'spread': 0.4 if IS_MOBILE else 0.3,  # Больше разброс для мобильных
        'description': 'Мощное оружие ближнего боя'
    },
    'laser': {
        'name': 'Лазер',
        'damage': 45 if IS_MOBILE else 40,
        'fire_rate': 0.15,
        'bullet_speed': 900,
        'bullet_radius': 4,
        'piercing': True,
        'explosive': False,
        'ammo': 100,
        'description': 'Точное оружие с пробиванием'
    },
    'plasma_rifle': {
        'name': 'Плазменная винтовка',
        'damage': 40 if IS_MOBILE else 35,
        'fire_rate': 0.2,
        'bullet_speed': 800,
        'bullet_radius': 7,
        'piercing': False,
        'explosive': True,
        'explosion_radius': 60 if IS_MOBILE else 50,
        'ammo': 50,
        'description': 'Взрывные плазменные заряды'
    },
    'rocket_launcher': {
        'name': 'Ракетница',
        'damage': 70 if IS_MOBILE else 60,
        'fire_rate': 1.5,
        'bullet_speed': 500,
        'bullet_radius': 10,
        'piercing': False,
        'explosive': True,
        'explosion_radius': 120 if IS_MOBILE else 100,
        'ammo': 15,
        'description': 'Мощные ракеты'
    },
    'minigun': {
        'name': 'Миниган',
        'damage': 12 if IS_MOBILE else 10,
        'fire_rate': 0.05,
        'bullet_speed': 750,
        'bullet_radius': 4,
        'piercing': False,
        'explosive': False,
        'ammo': 200,
        'description': 'Очень быстрая стрельба'
    }
}

# ============================================================
# СПОСОБНОСТИ (адаптированы для мобильных)
# ============================================================

if IS_MOBILE:
    DASH_SPEED = 700  # Немного медленнее для контроля
    DASH_DURATION = 0.2
    DASH_COOLDOWN = 1.2  # Быстрее перезарядка
    WALL_RADIUS = 60
    WALL_DURATION = 4.0
    WALL_COOLDOWN = 5.0
    REPAIR_COST = 25
    REPAIR_AMOUNT = 30
    STEALTH_DURATION = 3.0
    STEALTH_COOLDOWN = 4.0
    EMP_RADIUS = 250  # Больше радиус для мобильных
    EMP_DAMAGE = 60
else:
    DASH_SPEED = 800
    DASH_DURATION = 0.15
    DASH_COOLDOWN = 1.5
    WALL_RADIUS = 50
    WALL_DURATION = 4.0
    WALL_COOLDOWN = 6.0
    REPAIR_COST = 30
    REPAIR_AMOUNT = 25
    STEALTH_DURATION = 3.0
    STEALTH_COOLDOWN = 5.0
    EMP_RADIUS = 200
    EMP_DAMAGE = 50

# ============================================================
# ВРАГИ (адаптированы для мобильных)
# ============================================================

if IS_MOBILE:
    ENEMY_BASE_HP = 35  # Меньше HP для баланса
    ENEMY_BASE_SPEED = 120  # Медленнее враги
    ENEMY_FIRE_RATE = 2.5  # Реже стреляют
    ENEMY_BASE_RADIUS = 25  # Больше для видимости
    ENEMY_BASE_DAMAGE = 12  # Меньше урон
else:
    ENEMY_BASE_HP = 40
    ENEMY_BASE_SPEED = 150
    ENEMY_FIRE_RATE = 2.0
    ENEMY_BASE_RADIUS = 20
    ENEMY_BASE_DAMAGE = 15

# Типы врагов
ENEMY_TYPES = {
    'basic': {
        'name': 'Дрон',
        'hp_multiplier': 1.0,
        'speed_multiplier': 1.0,
        'damage_multiplier': 1.0,
        'radius': 25 if IS_MOBILE else 20,
        'color': RED,
        'abilities': [],
        'description': 'Обычный боевой дрон'
    },
    'fast': {
        'name': 'Быстрый дрон',
        'hp_multiplier': 0.7,
        'speed_multiplier': 1.3 if IS_MOBILE else 1.5,  # Медленнее на мобильных
        'damage_multiplier': 0.8,
        'radius': 20 if IS_MOBILE else 15,
        'color': ORANGE,
        'abilities': ['dodge'],
        'description': 'Быстрый, но хрупкий'
    },
    'tank': {
        'name': 'Танк',
        'hp_multiplier': 1.5 if IS_MOBILE else 1.8,  # Меньше HP на мобильных
        'speed_multiplier': 0.7,
        'damage_multiplier': 1.5,
        'radius': 32 if IS_MOBILE else 28,
        'color': DARK_RED,
        'abilities': ['heavy_armor', 'shield'],
        'description': 'Медленный, но бронированный'
    },
    'shooter': {
        'name': 'Стрелок',
        'hp_multiplier': 1.0,
        'speed_multiplier': 1.0,
        'damage_multiplier': 1.0,
        'radius': 26 if IS_MOBILE else 22,
        'color': MAGENTA,
        'abilities': ['rapid_fire', 'long_range'],
        'description': 'Атакует с дистанции'
    },
    'elite': {
        'name': 'Элитный дрон',
        'hp_multiplier': 1.5,
        'speed_multiplier': 1.2,
        'damage_multiplier': 1.5,
        'radius': 30 if IS_MOBILE else 25,
        'color': YELLOW,
        'abilities': ['regen', 'dash', 'multi_shot'],
        'description': 'Опасный противник'
    },
    'hybrid': {
        'name': 'Гибрид',
        'hp_multiplier': 2.0,
        'speed_multiplier': 1.3,
        'damage_multiplier': 2.0,
        'radius': 35 if IS_MOBILE else 30,
        'color': (255, 0, 128),
        'abilities': ['regen', 'dash', 'multi_shot', 'teleport'],
        'description': 'Получеловек-полумашина'
    },
    'avatar': {
        'name': 'Аватар ИИ',
        'hp_multiplier': 8.0 if IS_MOBILE else 10.0,  # Меньше HP босса
        'speed_multiplier': 0.8,
        'damage_multiplier': 2.5 if IS_MOBILE else 3.0,
        'radius': 55 if IS_MOBILE else 50,
        'color': PURPLE,
        'abilities': ['regen', 'multi_shot', 'teleport', 'summon'],
        'description': 'Мощное проявление ИИ'
    }
}

# ============================================================
# ВОЛНЫ (адаптированы для мобильных)
# ============================================================

if IS_MOBILE:
    WAVE_DURATION = 25.0  # Короче волны
    MAX_ENEMIES = 15  # Меньше врагов на экране
    SPAWN_RATE_BASE = 2.5  # Медленнее спавн
    BOSS_WAVE_INTERVAL = 4  # Чаще боссы
else:
    WAVE_DURATION = 30.0
    MAX_ENEMIES = 25
    SPAWN_RATE_BASE = 2.0
    BOSS_WAVE_INTERVAL = 5

# Модификаторы волн
WAVE_MODIFIERS = {
    'fast_spawn': {'name': 'Быстрый спавн', 'description': 'Враги появляются быстрее', 'spawn_rate_multiplier': 0.5},
    'enemy_regen': {'name': 'Регенерация врагов', 'description': 'Враги восстанавливают HP', 'regen_bonus': 3},
    'explosive_enemies': {'name': 'Взрывные враги', 'description': 'Враги взрываются при смерти',
                          'explode_on_death': True},
    'double_enemies': {'name': 'Двойные враги', 'description': 'Больше врагов', 'enemy_count_multiplier': 2.0},
    'enemy_armor': {'name': 'Броня врагов', 'description': 'Враги получают броню', 'armor_bonus': 5},
    'player_weakened': {'name': 'Ослабление игрока', 'description': 'Игрок наносит меньше урона',
                        'player_damage_multiplier': 0.7},
    'no_pickups': {'name': 'Нет пикапов', 'description': 'Пикапы не появляются', 'disable_pickups': True}
}

# ============================================================
# ФАЙЛЫ
# ============================================================

# Для мобильных используем другую директорию
if IS_MOBILE:
    try:
        # Для Android используем getcwd() или специальную директорию
        SAVE_DIR = os.path.join(os.environ.get('ANDROID_APP_PATH', os.getcwd()), 'save_data')
    except:
        SAVE_DIR = 'save_data'
else:
    SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

# Создаём директорию, если её нет
if not os.path.exists(SAVE_DIR):
    try:
        os.makedirs(SAVE_DIR)
    except:
        pass

SAVE_FILE = os.path.join(SAVE_DIR, "overload_save.cfg")
SETTINGS_FILE = os.path.join(SAVE_DIR, "settings.json")
LEGACY_FILE = os.path.join(SAVE_DIR, "legacy_data.json")
ACHIEVEMENTS_FILE = os.path.join(SAVE_DIR, "achievements.json")
STATS_FILE = os.path.join(SAVE_DIR, "stats.json")

# ============================================================
# НАСТРОЙКИ ПО УМОЛЧАНИЮ
# ============================================================

DEFAULT_SETTINGS = {
    "sound_volume": 0.7,
    "music_volume": 0.5,
    "difficulty": "normal",
    "screen_shake": not IS_MOBILE,  # Отключаем тряску на мобильных
    "show_fps": False,
    "language": "ru",
    "fullscreen": IS_MOBILE,  # Полноэкранный режим на мобильных
    "particle_quality": "low" if IS_MOBILE else "high",  # Меньше частиц на мобильных
    "auto_save": True,
    "tutorial_completed": False,
    "touch_controls_opacity": 0.6,
    "touch_controls_size": "large" if IS_MOBILE else "medium",
    "vibration_enabled": True if IS_MOBILE else False
}

# Настройки сложности (адаптированы для мобильных)
DIFFICULTY_SETTINGS = {
    'easy': {
        'enemy_hp_multiplier': 0.6 if IS_MOBILE else 0.7,
        'enemy_damage_multiplier': 0.6 if IS_MOBILE else 0.7,
        'player_damage_multiplier': 1.4 if IS_MOBILE else 1.3,
        'spawn_rate_multiplier': 1.8 if IS_MOBILE else 1.5,
        'score_multiplier': 0.8
    },
    'normal': {
        'enemy_hp_multiplier': 1.0,
        'enemy_damage_multiplier': 1.0,
        'player_damage_multiplier': 1.0,
        'spawn_rate_multiplier': 1.0,
        'score_multiplier': 1.0
    },
    'hard': {
        'enemy_hp_multiplier': 1.3 if IS_MOBILE else 1.5,
        'enemy_damage_multiplier': 1.3 if IS_MOBILE else 1.5,
        'player_damage_multiplier': 0.9 if IS_MOBILE else 0.8,
        'spawn_rate_multiplier': 0.8 if IS_MOBILE else 0.7,
        'score_multiplier': 1.5
    },
    'nightmare': {
        'enemy_hp_multiplier': 1.7 if IS_MOBILE else 2.0,
        'enemy_damage_multiplier': 1.7 if IS_MOBILE else 2.0,
        'player_damage_multiplier': 0.7 if IS_MOBILE else 0.6,
        'spawn_rate_multiplier': 0.6 if IS_MOBILE else 0.5,
        'score_multiplier': 2.0
    }
}

# ============================================================
# ЭФФЕКТЫ И РЕДКОСТИ
# ============================================================

RARITIES = {
    'common': {'name': 'Обычный', 'color': WHITE, 'weight': 50},
    'uncommon': {'name': 'Необычный', 'color': GREEN, 'weight': 30},
    'rare': {'name': 'Редкий', 'color': BLUE, 'weight': 15},
    'epic': {'name': 'Эпический', 'color': PURPLE, 'weight': 4},
    'legendary': {'name': 'Легендарный', 'color': ORANGE, 'weight': 1}
}

# ============================================================
# РЕСУРСЫ
# ============================================================

RESOURCE_TYPES = {
    'scrap': {'name': 'Металлолом', 'color': GRAY},
    'circuit': {'name': 'Электронные компоненты', 'color': CYAN},
    'energy_cell': {'name': 'Энергоячейка', 'color': YELLOW},
    'crystal': {'name': 'Кристалл', 'color': MAGENTA},
    'ai_core': {'name': 'Ядро ИИ', 'color': PURPLE},
    'organic_tissue': {'name': 'Органические ткани', 'color': GREEN}
}

# ============================================================
# ЛОКАЦИИ
# ============================================================

LOCATIONS = {
    'ruined_city': {
        'name': 'Разрушенный город',
        'enemy_types': ['basic', 'fast', 'shooter'],
        'obstacle_density': 10 if IS_MOBILE else 15,  # Меньше препятствий на мобильных
        'boss_chance': 0.05,
        'portals_to': ['lab_omega', 'wasteland'],
        'biome': 'city',
        'description': 'Руины некогда великого мегаполиса'
    },
    'lab_omega': {
        'name': 'Лаборатория Омега',
        'enemy_types': ['basic', 'shooter', 'tank'],
        'obstacle_density': 15 if IS_MOBILE else 20,
        'boss_chance': 0.1,
        'portals_to': ['ruined_city'],
        'biome': 'lab',
        'description': 'Секретная лаборатория, где всё началось'
    },
    'sector_7': {
        'name': 'Сектор 7',
        'enemy_types': ['fast', 'shooter', 'elite', 'tank'],
        'obstacle_density': 18 if IS_MOBILE else 25,
        'boss_chance': 0.2,
        'portals_to': ['underground_city'],
        'biome': 'city',
        'description': 'Фабрика дронов'
    },
    'underground_city': {
        'name': 'Подземный город',
        'enemy_types': ['basic', 'elite'],
        'obstacle_density': 8 if IS_MOBILE else 10,
        'boss_chance': 0.0,
        'portals_to': ['sector_7', 'orbital_station'],
        'biome': 'lab',
        'description': 'Убежище Сопротивления'
    },
    'orbital_station': {
        'name': 'Орбитальная станция Гнездо',
        'enemy_types': ['elite', 'hybrid', 'tank'],
        'obstacle_density': 22 if IS_MOBILE else 30,
        'boss_chance': 0.5,
        'portals_to': ['genesis_core'],
        'biome': 'lab',
        'description': 'База Кейна'
    },
    'genesis_core': {
        'name': 'Ядро ГЕНЕЗИСА',
        'enemy_types': ['avatar', 'hybrid', 'elite'],
        'obstacle_density': 25 if IS_MOBILE else 35,
        'boss_chance': 1.0,
        'portals_to': [],
        'biome': 'lab',
        'description': 'Сердце ИИ'
    },
    'wasteland': {
        'name': 'Пустоши',
        'enemy_types': ['fast', 'tank', 'basic'],
        'obstacle_density': 6 if IS_MOBILE else 8,
        'boss_chance': 0.08,
        'portals_to': ['ruined_city', 'cyber_forest'],
        'biome': 'wasteland',
        'description': 'Бескрайние пустоши'
    },
    'cyber_forest': {
        'name': 'Кибернетический лес',
        'enemy_types': ['hybrid', 'fast', 'shooter'],
        'obstacle_density': 12 if IS_MOBILE else 18,
        'boss_chance': 0.15,
        'portals_to': ['wasteland', 'sector_7'],
        'biome': 'forest',
        'description': 'Лес, захваченный машинами'
    }
}

# ============================================================
# КРАФТИНГ
# ============================================================

CRAFTING_RECIPES = [
    {
        'name': 'Аптечка',
        'materials': {'scrap': 5, 'circuit': 1},
        'result': {'type': 'repair', 'amount': 40 if IS_MOBILE else 30},
        'description': 'Восстанавливает HP'
    },
    {
        'name': 'Энергоячейка',
        'materials': {'scrap': 3, 'circuit': 2},
        'result': {'type': 'energy', 'amount': 50},
        'description': 'Восстанавливает 50 энергии'
    },
    {
        'name': 'Дробовик',
        'materials': {'scrap': 15, 'circuit': 5, 'energy_cell': 1},
        'result': {'type': 'weapon', 'weapon_type': 'shotgun'},
        'description': 'Мощное оружие ближнего боя'
    },
    {
        'name': 'Лазер',
        'materials': {'scrap': 20, 'circuit': 8, 'energy_cell': 2},
        'result': {'type': 'weapon', 'weapon_type': 'laser'},
        'description': 'Точное оружие с пробиванием'
    },
    {
        'name': 'ЭМИ-граната',
        'materials': {'scrap': 8, 'circuit': 4},
        'result': {'type': 'consumable', 'effect': 'emp'},
        'description': 'Отключает роботов в радиусе'
    },
    {
        'name': 'Плазменная винтовка',
        'materials': {'scrap': 30, 'circuit': 12, 'energy_cell': 3, 'crystal': 1},
        'result': {'type': 'weapon', 'weapon_type': 'plasma_rifle'},
        'description': 'Взрывные плазменные заряды'
    },
    {
        'name': 'Ракетница',
        'materials': {'scrap': 40, 'circuit': 15, 'energy_cell': 5},
        'result': {'type': 'weapon', 'weapon_type': 'rocket_launcher'},
        'description': 'Мощные ракеты'
    },
    {
        'name': 'Миниган',
        'materials': {'scrap': 50, 'circuit': 20, 'energy_cell': 8, 'crystal': 2},
        'result': {'type': 'weapon', 'weapon_type': 'minigun'},
        'description': 'Очень быстрая стрельба'
    }
]


# ============================================================
# СИСТЕМА НАСТРОЕК
# ============================================================

class SettingsManager:
    """Менеджер настроек"""

    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        """Загрузка настроек из файла"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings.update(data)
            except:
                pass

    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except:
            pass

    def get(self, key: str, default=None):
        """Получение настройки"""
        return self.settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value):
        """Установка настройки"""
        self.settings[key] = value
        self.save_settings()

    def get_difficulty_settings(self) -> dict:
        """Получение настроек сложности"""
        difficulty = self.get('difficulty', 'normal')
        return DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS['normal'])

    def toggle(self, key: str):
        """Переключение булевой настройки"""
        self.settings[key] = not self.settings.get(key, False)
        self.save_settings()

    def reset_to_default(self):
        """Сброс к настройкам по умолчанию"""
        self.settings = DEFAULT_SETTINGS.copy()
        self.save_settings()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Получение расстояния между двумя точками"""
    return math.hypot(x2 - x1, y2 - y1)


def get_angle(x1: float, y1: float, x2: float, y2: float) -> float:
    """Получение угла между двумя точками"""
    return math.atan2(y2 - y1, x2 - x1)


def normalize_vector(x: float, y: float) -> Tuple[float, float]:
    """Нормализация вектора"""
    norm = math.hypot(x, y)
    if norm > 0:
        return (x / norm, y / norm)
    return (0, 0)


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Ограничение значения"""
    return max(min_value, min(max_value, value))


def lerp(start: float, end: float, t: float) -> float:
    """Линейная интерполяция"""
    return start + (end - start) * t


def random_color() -> Tuple[int, int, int]:
    """Случайный цвет"""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def random_position(margin: int = 50) -> Tuple[float, float]:
    """Случайная позиция на экране"""
    return (random.randint(margin, SCREEN_WIDTH - margin),
            random.randint(margin, SCREEN_HEIGHT - margin))


def is_on_screen(x: float, y: float, margin: int = 50) -> bool:
    """Проверка, находится ли точка на экране"""
    return (margin <= x <= SCREEN_WIDTH - margin and
            margin <= y <= SCREEN_HEIGHT - margin)


def load_json(filename: str) -> dict:
    """Загрузка JSON файла"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_json(filename: str, data: dict) -> bool:
    """Сохранение JSON файла"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False


def create_surface(width: int, height: int, color: Tuple[int, int, int], alpha: int = 255) -> pygame.Surface:
    """Создание поверхности с прозрачностью"""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((*color, alpha))
    return surface


def draw_text(screen: pygame.Surface, text: str, x: float, y: float,
              font_size: int = 30, color: Tuple[int, int, int] = WHITE,
              align: str = 'left') -> pygame.Rect:
    """Отрисовка текста"""
    font = pygame.font.Font(None, font_size)
    text_surface = font.render(text, True, color)

    if align == 'center':
        rect = text_surface.get_rect(center=(x, y))
    elif align == 'right':
        rect = text_surface.get_rect(topright=(x, y))
    else:
        rect = text_surface.get_rect(topleft=(x, y))

    screen.blit(text_surface, rect)
    return rect