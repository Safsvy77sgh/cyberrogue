import pygame
import sys
import random
import math
from typing import List, Tuple, Optional, Dict
from systems.renderer import Renderer, Palette
from settings import *
from settings import SettingsManager
from sounds import SoundManager

from entities.player import Player
from entities.enemy_extended import ExtendedEnemyFinal, EnemyFactory, EnemyLootSystem
from entities.bullet import Bullet
from entities.obstacle import Obstacle
from entities.pickup import Pickup
from entities.particle import Particle, ParticleSystem, ParticleEmitter, create_explosion, create_sparks, create_smoke, create_trail
from entities.wall import EnergyWall
from entities.damage_number import DamageNumber

from systems.collision import CollisionSystem
from systems.wave_manager import RoomManager
from systems.achievement import AchievementManager
from systems.save_system import SaveSystem
from systems.shop import Shop
from systems.story import StoryManager
from systems.quest import QuestManager
from systems.dialogue import DialogueManager
from systems.ui import UI
from systems.portal import Portal
from systems.editor import Editor
from systems.synergy import SynergySystem
from systems.procedural_generation import ProceduralGenerator
from systems.building import BuildingSystem
from systems.weather import WeatherSystem
from systems.stealth import StealthSystem
from systems.allies import AllySystem
from systems.vehicles import VehicleSystem
from systems.economy import EconomySystem
from systems.mutations import MutationSystem
from systems.reputation import ReputationSystem
from systems.time_system import TimeSystem
from systems.events import EventSystem
from systems.legacy import LegacySystem
from systems.adaptive_enemies import AdaptiveEnemySystem
from systems.evolutionary_ai import EvolutionaryAIManager
from systems.coop import CoopSystem
from systems.weapons_extended import WeaponManager
from systems.protection import ProtectionManager
from systems.minions import MinionManager

# Опциональный патч мобильного управления. Если файла нет - игра просто
# работает как обычно, без сторонней зависимости.
try:
    import mobile_patch
except ImportError:
    mobile_patch = None
try:
    from mobile_controls import MobileControls
    MOBILE_CONTROLS_AVAILABLE = True
except ImportError:
    MOBILE_CONTROLS_AVAILABLE = False

# ============================================================================
# 10 ИДЕЙ ПО УЛУЧШЕНИЮ КОМНАТНОЙ СИСТЕМЫ (в духе The Binding of Isaac)
# ----------------------------------------------------------------------------
# 1. [РЕАЛИЗОВАНО] Комнаты-ловушки (trap) содержат пульсирующие зоны урона
#    (шипы/мины), которые наносят урон игроку раз в секунду, если он стоит
#    внутри зоны в момент "пульса". См. `_populate_hazards`, `update_hazards`.
# 2. [РЕАЛИЗОВАНО] Сокровищный гоблин: редкий враг с повышенной скоростью и
#    пониженным HP, убегающий от игрока; при убийстве даёт увеличенный лут.
#    См. `_maybe_spawn_treasure_goblin`, `on_enemy_killed`.
# 3. [РЕАЛИЗОВАНО] Кровавые комнаты (blood): убийство врагов в такой комнате
#    восстанавливает игроку небольшое количество HP (вампиризм на время
#    нахождения в комнате). См. `blood_room_active`.
# 4. [РЕАЛИЗОВАНО] Аркадные комнаты (arcade): при первом входе запускается
#    "игровой автомат", случайно выдающий один из нескольких призов (кредиты,
#    временный баф, лечение или мини-волна дополнительных врагов как риск).
#    См. `_trigger_arcade_event`.
# 5. [РЕАЛИЗОВАНО] Библиотечные комнаты (library): после зачистки игроку
#    предлагается выбрать один из 3 постоянных бафов клавишами 1/2/3.
#    См. `_offer_library_choice`, обработка в `handle_keydown`.
# 6. [ИДЕЯ] Разрушаемые стены-проходы: часть препятствий в секретных комнатах
#    можно уничтожить взрывом, открывая проход к дополнительной комнате,
#    не отображённой на графе дверей.
# 7. [ИДЕЯ] Модификаторы этажа: в начале каждого этажа случайно выбирается
#    глобальный модификатор ("Огненный пол", "Скоростные враги", "Двойной
#    лут"), меняющий баланс на всём этаже.
# 8. [ИДЕЯ] Комнаты-загадки: простая головоломка (нажать переключатели в
#    правильном порядке), за решение которой выдаётся уникальная награда.
# 9. [ИДЕЯ] Мини-карта комнат (сознательно НЕ реализована по требованию
#    заказчика, но структура RoomManager.rooms уже готова для неё).
# 10. [ИДЕЯ] Проклятие пола: в комнатах curse активен временный дебафф
#     (снижение обзора/урона), снимающийся при выходе из комнаты, а не
#     насовсем - более честный вариант жертвы-риска.
# ============================================================================


EFFECT_SYNERGIES = {
    frozenset({'fire', 'oil'}): {'name': 'explosion', 'damage': 60, 'radius': 90, 'color': ORANGE},
    frozenset({'fire', 'gas'}): {'name': 'explosion', 'damage': 90, 'radius': 120, 'color': RED},
    frozenset({'ice', 'shock'}): {'name': 'shatter', 'damage': 40, 'radius': 70, 'color': CYAN},
    frozenset({'poison', 'acid'}): {'name': 'corrosion', 'damage': 30, 'radius': 50, 'color': GREEN},
    frozenset({'oil', 'shock'}): {'name': 'chain_shock', 'damage': 35, 'radius': 100, 'color': YELLOW},
}

ROOM_TYPE_NAMES = {
    'start': 'Стартовая комната',
    'normal': 'Комната',
    'boss': 'КОМНАТА БОССА!',
    'treasure': 'Сокровищница!',
    'shop': 'Магазин',
    'trap': 'Ловушка!',
    'secret': 'Секретная комната!',
    'curse': 'Проклятая комната!',
    'sacrifice': 'Комната жертвоприношения!',
    'miniboss': 'Комната мини-босса!',
    'arcade': 'Аркада!',
    'library': 'Библиотека',
    'chest': 'Комната сундуков!',
    'blood': 'Кровавая комната!',
}

LIBRARY_BUFFS = [
    {'key': 'damage', 'name': 'Том ярости', 'desc': '+15% урона навсегда'},
    {'key': 'max_hp', 'name': 'Том стойкости', 'desc': '+25 максимального HP'},
    {'key': 'crit', 'name': 'Том точности', 'desc': '+8% шанс крита'},
]


class Game:

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.sound_manager = SoundManager()
        self.settings_manager = SettingsManager()
        self.settings_open = False

        # --- Локации и базовые контейнеры (до систем) ---
        self.location_data = self._load_locations()
        self.unlocked_locations = ['ruined_city']
        self.current_location = "ruined_city"
        self.portals: List[Portal] = []
        self.lightning_effects = []
        self._triggered_synergies = set()

        # --- Игровые структуры, не зависящие от систем ---
        self.particle_system = ParticleSystem()
        self.particle_emitters: List[ParticleEmitter] = []
        self.loot_system = EnemyLootSystem()
        self.debug_mode = False
        self.settings_button_rect = pygame.Rect(SCREEN_WIDTH - 100, 10, 90, 30)
        self.help_button_rect = pygame.Rect(SCREEN_WIDTH - 100, 50, 90, 30)

        # --- Комнаты (только словари!) ---
        self.current_rooms: List[Dict] = []
        self.current_room: Optional[Dict] = None
        self.room_hazards: List[Dict] = []
        self.blood_room_active = False
        self.library_choice_pending: Optional[List[Dict]] = None
        self._room_content_flags = {}

        self.session_stats = {
            'damage_dealt': 0,
            'enemies_killed': 0,
            'pickups_collected': 0,
            'waves_survived': 0,
            'bosses_killed': 0,
            'max_combo': 0,
            'time_played': 0
        }
        self.screen_shake = 0
        self.screen_shake_intensity = 5
        self.flash_alpha = 0
        self.flash_color = WHITE
        self.crafted_items = 0

        # --- Прогресс до load_game_data(), чтобы избежать атрибутов "снаружи __init__" ---
        self.best_score = 0
        self.total_kills = 0
        self.total_playtime = 0
        self.unlocked_weapons = ['pistol']
        self.achievements_data = {}
        self.player_data = None

        # --- Все системы ---
        self.collision_system = CollisionSystem(self)
        self.room_manager = RoomManager(self)
        self.wave_manager = self.room_manager  # обратная совместимость по имени
        self.achievement_manager = AchievementManager(self)
        self.save_system = SaveSystem()
        self.shop = Shop(self)
        self.ui = UI(self)
        self.story_manager = StoryManager(self)
        self.quest_manager = QuestManager(self)
        self.dialogue_manager = DialogueManager(self)
        self.crafting_system = None
        self.editor = Editor(self)
        self.synergy_system = SynergySystem()
        self.procedural_generator = ProceduralGenerator()
        self.building_system = BuildingSystem()
        self.weather_system = WeatherSystem()
        self.stealth_system = StealthSystem(self)
        self.ally_system = AllySystem(self)
        self.vehicle_system = VehicleSystem(self)
        self.economy_system = EconomySystem(self)
        self.mutation_system = MutationSystem(self)
        self.reputation_system = ReputationSystem()
        self.time_system = TimeSystem()
        self.event_system = EventSystem(self)
        self.legacy_system = LegacySystem()
        self.adaptive_enemy_system = AdaptiveEnemySystem(self)
        self.evolutionary_ai = EvolutionaryAIManager()
        self.coop_system = CoopSystem(self)

        # --- Менеджеры (используются игроком) ---
        self.weapon_manager = WeaponManager()
        self.protection_manager = ProtectionManager()
        self.minion_manager = MinionManager()

        # --- Состояния интерфейса ---
        self.editor_mode = False
        self.show_instructions = False
        self.crafting_open = False
        self.mutation_menu_open = False
        self.vehicle_menu_open = False
        self.building_mode = False
        self.coop_mode = False
        self.in_dialogue = False

        # --- Временные эффекты ---
        self.time_scale = 1.0
        self.time_scale_timer = 0.0
        self.exp_multiplier = 1.0
        self.gravity_multiplier = 1.0
        self.darkness_active = False
        self.meteor_shower_active = False
        self.meteor_timer = 0.0
        self.trader_active = False
        self.trader_position = (0, 0)

        # --- Загрузка сохранённых данных (перед reset_game) ---
        self.load_game_data()

        # --- Сброс мира и игрока ---
        self.reset_game()
        # После reset_game() добавьте:
        self.sound_manager.play_music('exploration')  # Начинаем с исследовательской музыки

        # --- Наследие (применяется после создания игрока) ---
        self.legacy_system.apply_legacy_to_new_character(self.player)

        # --- Запуск сюжета ---
        self.story_manager.start_chapter(1)

        # --- Финальная синхронизация ссылок на системы ---
        self.active_quests = self.quest_manager.active_quests
        self.completed_quests = self.quest_manager.completed_quests
        self.active_effects = self.player.effect_system.active_effects if self.player else []
        self.active_buildings = self.building_system.buildings
        self.active_allies = self.ally_system.allies
        self.active_vehicles = self.vehicle_system.vehicles
        self.active_mutations = self.mutation_system.active_mutations
        self.active_events = self.event_system.active_events
        self.coop_players = self.coop_system.players


        # --- Мобильный патч (если присутствует) ---
        

        # Мобильное управление будет активировано через mobile_patch
        self.mobile_controls = None
        self.mobile_mode = False
        self._needs_input_restore = False
        self._original_input_functions = {}

    def _load_locations(self) -> Dict:
        return {
            "ruined_city": {"name": "Разрушенный город", "enemy_types": ['basic', 'fast', 'shooter'], "obstacle_density": 15, "boss_chance": 0.05, "portals_to": ["lab_omega", "wasteland"], "biome": "city"},
            "lab_omega": {"name": "Лаборатория Омега", "enemy_types": ['basic', 'shooter', 'tank'], "obstacle_density": 20, "boss_chance": 0.1, "portals_to": ["ruined_city"], "biome": "lab"},
            "sector_7": {"name": "Сектор 7", "enemy_types": ['fast', 'shooter', 'elite', 'tank'], "obstacle_density": 25, "boss_chance": 0.2, "portals_to": ["underground_city"], "biome": "city"},
            "underground_city": {"name": "Подземный город", "enemy_types": ['basic', 'elite'], "obstacle_density": 10, "boss_chance": 0.0, "portals_to": ["sector_7", "orbital_station"], "biome": "lab"},
            "orbital_station": {"name": "Орбитальная станция Гнездо", "enemy_types": ['elite', 'hybrid', 'tank'], "obstacle_density": 30, "boss_chance": 0.5, "portals_to": ["genesis_core"], "biome": "lab"},
            "genesis_core": {"name": "Ядро ГЕНЕЗИСА", "enemy_types": ['avatar', 'hybrid', 'elite'], "obstacle_density": 35, "boss_chance": 1.0, "portals_to": [], "biome": "lab"},
            "wasteland": {"name": "Пустоши", "enemy_types": ['fast', 'tank', 'basic'], "obstacle_density": 8, "boss_chance": 0.08, "portals_to": ["ruined_city", "cyber_forest"], "biome": "wasteland"},
            "cyber_forest": {"name": "Кибернетический лес", "enemy_types": ['hybrid', 'fast', 'shooter'], "obstacle_density": 18, "boss_chance": 0.15, "portals_to": ["wasteland", "sector_7"], "biome": "forest"}
        }

    def load_game_data(self):
        data = self.save_system.load()
        if data:
            self.best_score = data.get('best_score', 0)
            self.total_kills = data.get('total_kills', 0)
            self.total_playtime = data.get('total_playtime', 0)
            self.unlocked_weapons = data.get('unlocked_weapons', ['pistol'])
            self.achievements_data = data.get('achievements', {})
            self.unlocked_locations = data.get('unlocked_locations', ['ruined_city'])
            self.player_data = data.get('player_data', None)
        else:
            self.best_score = 0
            self.total_kills = 0
            self.total_playtime = 0
            self.unlocked_weapons = ['pistol']
            self.achievements_data = {}
            self.unlocked_locations = ['ruined_city']
            self.player_data = None

    def save_game_data(self):
        data = {
            'best_score': self.best_score,
            'total_kills': self.total_kills + self.player.kills,
            'total_playtime': self.total_playtime + self.time_elapsed,
            'unlocked_weapons': self.player.weapons,
            'achievements': self.achievement_manager.achievements,
            'unlocked_locations': self.unlocked_locations,
            'player_data': self.player.save_player_data(),
            'story_flags': self.story_manager.flags,
            'reputation': getattr(self.reputation_system, 'factions', getattr(self.reputation_system, 'reputation', {})),
            'crafting_level': self.crafting_system.crafting_level if self.crafting_system else 1,
        }
        self.save_system.save(data)
        self.legacy_system.save_legacy()

    # ------------------------------------------------------------------
    # Инициализация / сброс игры
    # ------------------------------------------------------------------
    def reset_game(self):
        self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        if self.player_data:
            self.player.load_player_data(self.player_data)
        self.crafting_system = self.player.crafting_system
        for weapon in self.unlocked_weapons:
            if weapon not in self.player.weapons:
                self.player.add_weapon(weapon)
        self.player.weapon_manager = self.weapon_manager
        self.player.protection_manager = self.protection_manager
        self.player.minion_manager = self.minion_manager

        self.bullets: List[Bullet] = []
        self.enemy_bullets: List[Bullet] = []
        self.enemies: List[ExtendedEnemyFinal] = []
        self.obstacles: List[Obstacle] = []
        self.particles: List[Particle] = []
        self.pickups: List[Pickup] = []
        self.energy_walls: List[EnergyWall] = []
        self.damage_numbers: List[DamageNumber] = []
        self.portals: List[Portal] = []
        self.lightning_effects = []
        self.room_hazards = []
        self._triggered_synergies = set()
        self._room_content_flags = {}
        self.particle_system = ParticleSystem()
        self.particle_emitters.clear()

        self.score = 0
        self.wave = 1
        self.time_elapsed = 0.0
        self.game_over = False
        self.respawn_timer = 0.0
        self.auto_respawn_delay = 5.0
        self.paused = False
        self.shop_open = False
        self.in_dialogue = False
        self.editor_mode = False
        self.crafting_open = False
        self.show_instructions = False
        self.library_choice_pending = None

        # 1. Генерация нового этажа с комнатами (без дублирования - единственная точка входа)
        self.room_manager.reset()
        self.current_rooms = list(self.room_manager.rooms.values())
        self.current_room = self.room_manager.get_current_room()

        # 2. Игрок в центр стартовой комнаты
        if self.current_room:
            self.player.x, self.player.y = self.current_room['center']

        self.player_rect = pygame.Rect(
            self.player.x - self.player.radius,
            self.player.y - self.player.radius,
            self.player.radius * 2,
            self.player.radius * 2
        )

        # 3. Наполнение стартовой комнаты (без врагов)
        self._enter_room(self.current_room, initial=True)

        # 4. Транспорт (не привязан к конкретной комнате)


        self.ui.show_notification("Выживите как можно дольше!", CYAN, 3.0)

        # Синхронизация
        self.active_quests = self.quest_manager.active_quests
        self.completed_quests = self.quest_manager.completed_quests
        self.active_effects = self.player.effect_system.active_effects
        self.active_buildings = self.building_system.buildings
        self.active_allies = self.ally_system.allies
        self.active_vehicles = self.vehicle_system.vehicles
        self.active_mutations = self.mutation_system.active_mutations
        self.active_events = self.event_system.active_events
        self.coop_players = self.coop_system.players

    def spawn_portals(self):
        if self.current_location in self.location_data:
            location = self.location_data[self.current_location]
            for destination in location.get('portals_to', []):
                x = random.randint(100, SCREEN_WIDTH - 100)
                y = random.randint(100, SCREEN_HEIGHT - 100)
                self.portals.append(Portal(x, y, destination))

    def change_location(self, new_location: str):
        if new_location in self.location_data and new_location in self.unlocked_locations:
            self.current_location = new_location
            self.enemies.clear()
            self.obstacles.clear()
            self.pickups.clear()
            self.bullets.clear()
            self.enemy_bullets.clear()
            self.energy_walls.clear()
            self.portals.clear()
            self.room_hazards.clear()

            # Новая локация = новый этаж с новым графом комнат
            self.room_manager.reset()
            self.current_rooms = list(self.room_manager.rooms.values())
            self.current_room = self.room_manager.get_current_room()
            if self.current_room:
                self.player.x, self.player.y = self.current_room['center']
            self._enter_room(self.current_room, initial=True)

            self.spawn_portals()
            location = self.location_data[new_location]
            self.ui.show_notification(f"Локация: {location['name']}", CYAN, 3.0)
            self.story_manager.on_location_changed(new_location)

    # ------------------------------------------------------------------
    # Комнаты: заполнение содержимым, переходы через двери
    # ------------------------------------------------------------------
    def _room_enemy_count(self, room_type: str) -> int:
        counts = {
            'start': 3,
            'normal': random.randint(3, 5),
            'boss': 1,
            'treasure': random.randint(1, 2),
            'shop': 0,
            'trap': random.randint(5, 8),
            'secret': random.randint(1, 2),
            'curse': random.randint(3, 5),
            'sacrifice': random.randint(6, 10),
            'miniboss': 2,
            'arcade': random.randint(2, 4),
            'library': random.randint(2, 4),
            'chest': random.randint(2, 4),
            'blood': random.randint(3, 6),
        }
        return counts.get(room_type, random.randint(3, 5))

    def _random_point_in_room(self, room: Dict, margin: int = 50) -> Tuple[float, float]:
        x = random.randint(int(room['x'] + margin), int(max(room['x'] + margin + 1, room['x'] + room['width'] - margin)))
        y = random.randint(int(room['y'] + margin), int(max(room['y'] + margin + 1, room['y'] + room['height'] - margin)))
        return x, y

    def _enter_room(self, room: Optional[Dict], initial: bool = False):
        """Очищает динамическое содержимое и наполняет новую комнату."""
        if room is None:
            return

        self.update_music()

        self.bullets.clear()
        self.enemy_bullets.clear()
        self.enemies.clear()
        self.obstacles.clear()
        self.pickups.clear()
        self.energy_walls.clear()
        self.room_hazards.clear()
        self.blood_room_active = (room['type'] == 'blood')

        if not initial:
            x, y = self.room_manager.get_entry_position()
            self.player.x, self.player.y = x, y

        self._generate_room_obstacles(room)

        if not room['cleared']:
            self._generate_room_enemies(room)
        self._generate_room_pickups(room)
        self._populate_hazards(room)

        if room['type'] == 'arcade' and not room.get('populated'):
            self._trigger_arcade_event()

        room['populated'] = True

        self.ui.show_notification(ROOM_TYPE_NAMES.get(room['type'], 'Комната'), CYAN, 2.0)

        if not self.enemies:
            # Пустые/уже зачищенные комнаты сразу считаются пройденными
            self.room_manager.mark_current_cleared()

    def _generate_room_obstacles(self, room: Dict):
        count = random.randint(10, 15)
        door_rects = self.room_manager.get_door_rects()
        for _ in range(count):
            placed = False
            for _ in range(20):
                x, y = self._random_point_in_room(room, 50)
                w = random.randint(30, 70)
                h = random.randint(30, 70)
                candidate_rect = pygame.Rect(x - w / 2, y - h / 2, w, h)
                too_close_to_player = math.hypot(x - self.player.x, y - self.player.y) < 130
                blocks_door = any(candidate_rect.inflate(30, 30).colliderect(r) for r in door_rects.values())
                if not too_close_to_player and not blocks_door:
                    placed = True
                    break
            if not placed:
                continue

            type_roll = random.random()
            if type_roll < 0.3:
                type_ = 'box'
            elif type_roll < 0.5:
                type_ = 'crate'
            elif type_roll < 0.7:
                type_ = 'barrel'
            else:
                type_ = 'wall'
            hp = 50 + self.wave * 10
            self.obstacles.append(Obstacle(x, y, w, h, hp, type_))

            # Кучка - 1-3 дополнительных препятствия рядом с основным
            if random.random() < 0.6:
                for _ in range(random.randint(1, 3)):
                    cx = max(room['x'] + 20, min(x + random.randint(-70, 70), room['x'] + room['width'] - 70))
                    cy = max(room['y'] + 20, min(y + random.randint(-70, 70), room['y'] + room['height'] - 70))
                    cw = random.randint(20, 50)
                    ch = random.randint(20, 50)
                    c_type = random.choice(['box', 'crate', 'barrel'])
                    self.obstacles.append(Obstacle(cx, cy, cw, ch, 40 + self.wave * 8, c_type))

    def _generate_room_enemies(self, room: Dict):
        num_enemies = self._room_enemy_count(room['type'])
        if num_enemies <= 0:
            return

        enemy_types = self.location_data.get(self.current_location, {}).get(
            'enemy_types', ['basic', 'fast', 'shooter', 'tank']
        )
        effective_wave = self.room_manager.get_effective_wave()

        goblin_spawned = False
        for _ in range(num_enemies):
            x, y = None, None
            for _ in range(50):
                cx, cy = self._random_point_in_room(room, 50)
                if math.hypot(cx - self.player.x, cy - self.player.y) > 180:
                    x, y = cx, cy
                    break
            if x is None:
                x, y = room['x'] + room['width'] - 80, room['y'] + room['height'] - 80

            if room['type'] == 'boss':
                enemy = EnemyFactory.create_boss(x, y, effective_wave)
            elif room['type'] == 'miniboss':
                enemy = EnemyFactory.create_elite(x, y, effective_wave)
            else:
                enemy_type = random.choice(enemy_types)
                enemy = EnemyFactory.create_enemy(x, y, effective_wave, enemy_type)

            modifiers = self.time_system.get_modifiers()
            if modifiers.get('special_enemies') and hasattr(enemy, 'hp'):
                bonus_hp = int(enemy.max_hp * 0.2)
                enemy.max_hp += bonus_hp
                enemy.hp += bonus_hp

            # Идея №2: редкий "сокровищный гоблин" в комнатах normal/treasure
            if (not goblin_spawned and room['type'] in ('normal', 'treasure')
                    and random.random() < 0.04):
                enemy.is_treasure_goblin = True
                enemy.max_hp = max(1, int(enemy.max_hp * 0.5))
                enemy.hp = enemy.max_hp
                if hasattr(enemy, 'speed'):
                    enemy.speed *= 1.8
                goblin_spawned = True

            self.enemies.append(enemy)

    def update_music(self):
        """Обновляет фоновую музыку в зависимости от ситуации."""
        if self.game_over:
            self.sound_manager.stop_music()
            return
        if self.paused:
            return

        room_type = self.current_room.get('type', 'exploration') if self.current_room else 'exploration'
        has_enemies = len([e for e in self.enemies if e.alive]) > 0

        # Старая добрая музыка
        if room_type == 'boss':
            self.sound_manager.play_music('boss')
            # Добавляем жуткий смех при появлении босса
            if not hasattr(self, '_boss_laugh_played'):
                self._boss_laugh_played = True
                self.sound_manager.play('evil_laugh')
        elif has_enemies:
            self.sound_manager.play_music('combat')
        else:
            self.sound_manager.play_music('exploration')

    def spawn_enemy(self, enemy_type: str = None):
        """Запасной метод для спавна врага (используется событиями)."""
        enemy_types = self.location_data.get(self.current_location, {}).get('enemy_types', ['basic', 'fast', 'shooter'])
        if enemy_type is None:
            enemy_type = random.choice(enemy_types)

        # Спавним в текущей комнате или в центре экрана
        if self.current_room:
            x, y = self._random_point_in_room(self.current_room, 50)
        else:
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)

        enemy = EnemyFactory.create_enemy(x, y, self.room_manager.get_effective_wave(), enemy_type)
        self.enemies.append(enemy)

    def _generate_room_pickups(self, room: Dict):
        num_items = random.randint(1, 3)
        extra_types = ['scrap', 'energy', 'medkit', 'circuit', 'crystal']
        rare_types = ['weapon_pistol', 'weapon_shotgun', 'weapon_laser', 'scrap',
                      'energy_cell', 'medkit', 'ai_core', 'crystal']

        if room['type'] in ('treasure', 'chest'):
            num_items = random.randint(3, 6)
        elif room['type'] == 'library':
            num_items = random.randint(2, 3)
        elif room['type'] == 'secret':
            num_items = random.randint(2, 4)

        for _ in range(num_items):
            x, y = self._random_point_in_room(room, 30)
            if room['type'] in ('treasure', 'secret', 'chest'):
                item_type = random.choice(rare_types)
            else:
                item_type = random.choice(extra_types)
            self.pickups.append(Pickup(x, y, item_type))

    def _populate_hazards(self, room: Dict):
        """Идея №1: комнаты-ловушки получают пульсирующие зоны урона."""
        self.room_hazards = []
        if room['type'] != 'trap':
            return
        num_hazards = random.randint(3, 5)
        for _ in range(num_hazards):
            x, y = self._random_point_in_room(room, 60)
            self.room_hazards.append({
                'x': x, 'y': y, 'radius': random.randint(35, 55),
                'timer': random.uniform(0, 1.5), 'period': 1.5,
                'active_time': 0.5, 'damage': 8, 'cooldown': 0.0,
            })

    def _trigger_arcade_event(self):
        """Идея №4: игровой автомат в комнате arcade — случайная награда."""
        outcome = random.choice(['credits', 'heal', 'buff', 'risk'])
        if outcome == 'credits':
            bonus = random.randint(100, 300)
            self.score += bonus
            self.ui.show_notification(f"Автомат выдал {bonus} очков!", YELLOW, 3.0)
        elif outcome == 'heal':
            self.player.heal(30)
            self.ui.show_notification("Автомат восстановил здоровье!", GREEN, 3.0)
        elif outcome == 'buff':
            self.player.apply_temporary_buff('damage_boost', 20.0)
            self.ui.show_notification("Автомат усилил урон на время!", ORANGE, 3.0)
        else:
            self.ui.show_notification("Автомат сломался! Появились враги!", RED, 3.0)
            room = self.room_manager.get_current_room()
            if room:
                for _ in range(3):
                    x, y = self._random_point_in_room(room, 50)
                    enemy = EnemyFactory.create_enemy(x, y, self.room_manager.get_effective_wave())
                    self.enemies.append(enemy)

    def _offer_library_choice(self):
        """Идея №5: после зачистки библиотеки предложить выбор одного бафа."""
        options = random.sample(LIBRARY_BUFFS, k=min(3, len(LIBRARY_BUFFS)))
        self.library_choice_pending = options
        text = " | ".join(f"{i + 1}: {o['name']} ({o['desc']})" for i, o in enumerate(options))
        self.ui.show_notification("Выберите книгу (нажмите 1-3): " + text, PURPLE, 6.0)

    def apply_library_choice(self, index: int):
        if not self.library_choice_pending or not (0 <= index < len(self.library_choice_pending)):
            return
        buff = self.library_choice_pending[index]
        if buff['key'] == 'damage':
            self.player.damage_multiplier *= 1.15
        elif buff['key'] == 'max_hp':
            self.player.max_hp += 25
            self.player.hp += 25
        elif buff['key'] == 'crit':
            self.player.crit_chance += 0.08
        self.ui.show_notification(f"Получено: {buff['name']}", PURPLE, 2.5)
        self.library_choice_pending = None

    def check_door_interaction(self):
        door_rects = self.room_manager.get_door_rects()
        for direction, rect in door_rects.items():
            center = rect.center
            if math.hypot(self.player.x - center[0], self.player.y - center[1]) < 40:
                if self.room_manager.try_transition(direction):
                    new_room = self.room_manager.get_current_room()
                    self.current_room = new_room
                    self._enter_room(new_room)
                return

    def _check_floor_exit(self):
        """Если комната босса зачищена - предлагаем переход на новый этаж."""
        room = self.room_manager.get_current_room()
        if not room or room['type'] != 'boss' or not room['cleared']:
            return
        if math.hypot(self.player.x - room['center'][0], self.player.y - room['center'][1]) < 50:
            self.room_manager.advance_floor(self)
            self.current_rooms = list(self.room_manager.rooms.values())
            self.current_room = self.room_manager.get_current_room()
            if self.current_room:
                self.player.x, self.player.y = self.current_room['center']
            self._enter_room(self.current_room, initial=True)

    def spawn_boss(self):
        generation = 0
        if hasattr(self.evolutionary_ai, 'get_current_generation'):
            generation = self.evolutionary_ai.get_current_generation()
        room = self.room_manager.get_current_room()
        target_room = room if room else {'x': 100, 'y': 100, 'width': SCREEN_WIDTH - 200, 'height': SCREEN_HEIGHT - 200}
        x, y = self._random_point_in_room(target_room, 100)
        boss = EnemyFactory.create_boss(x, y, self.room_manager.get_effective_wave() + generation)
        self.enemies.append(boss)
        self.sound_manager.play('boss')
        self.ui.show_notification("БОСС ПОЯВИЛСЯ!", RED, 3.0)

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            # Обработка изменения размера окна
            for event in pygame.event.get(pygame.VIDEORESIZE):
                if event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.size)

            if self.time_scale_timer > 0:
                self.time_scale_timer -= dt
                if self.time_scale_timer <= 0:
                    self.time_scale = 1.0
            dt *= self.time_scale

            self.handle_events()
            self.update(dt)
            self.draw()

        self.save_game_data()
        pygame.quit()
        sys.exit()

    def handle_resize(self, new_size):
        """Обрабатывает изменение размера окна."""
        if self.mobile_controls:
            # Пересоздаём мобильные контролы с новым размером
            try:
                from mobile_controls import MobileControls
                self.mobile_controls = MobileControls(new_size[0], new_size[1])
            except:
                pass

    def handle_events(self):
        # Обработка мобильных кнопок (до обычных событий)
        if self.mobile_mode and self.mobile_controls:
            # Обработка кнопок мобильного интерфейса
            if self.mobile_controls.button_states.get('pause'):
                self.paused = not self.paused
                self.mobile_controls.button_states['pause'] = False

            if self.mobile_controls.button_states.get('dash'):
                if hasattr(self.player, 'dash'):
                    self.player.dash()
                self.mobile_controls.button_states['dash'] = False

            if self.mobile_controls.button_states.get('wall'):
                if hasattr(self.player, 'activate_wall'):
                    self.player.activate_wall()
                self.mobile_controls.button_states['wall'] = False

            if self.mobile_controls.button_states.get('interact'):
                self.check_door_interaction()
                self.mobile_controls.button_states['interact'] = False

            if self.mobile_controls.button_states.get('shop'):
                self.shop_open = not self.shop_open
                self.mobile_controls.button_states['shop'] = False

        # Обычная обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Обработка мобильных событий
            elif self.mobile_mode and self.mobile_controls:
                self.mobile_controls.handle_event(event)

            # Обычная обработка (только если не мобильный режим)
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            elif event.type == pygame.KEYUP:
                self.handle_keyup(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.handle_mouse_up(event)
            elif event.type == pygame.MOUSEWHEEL:
                if self.editor_mode:
                    self.editor.handle_event(event)

    def handle_keydown(self, event: pygame.event.Event):
        # Диалог обрабатывается первым, чтобы ESC/цифры не улетали в игру
        if self.in_dialogue:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                self.hide_dialogue()
            elif event.key == pygame.K_1:
                self.story_manager.select_dialogue_response(0)
            elif event.key == pygame.K_2:
                self.story_manager.select_dialogue_response(1)
            elif event.key == pygame.K_3:
                self.story_manager.select_dialogue_response(2)
            elif event.key == pygame.K_4:
                self.story_manager.select_dialogue_response(3)
            return

        if self.library_choice_pending:
            if event.key == pygame.K_1:
                self.apply_library_choice(0)
                return
            elif event.key == pygame.K_2:
                self.apply_library_choice(1)
                return
            elif event.key == pygame.K_3:
                self.apply_library_choice(2)
                return

        if event.key == pygame.K_ESCAPE:
            if self.shop_open:
                self.shop_open = False
            elif self.crafting_open:
                self.crafting_open = False
            elif self.editor_mode:
                self.editor_mode = False
            elif self.settings_open:
                self.settings_open = False
            elif self.show_instructions:
                self.show_instructions = False
            elif self.mutation_menu_open:
                self.mutation_menu_open = False
            elif self.building_mode:
                self.building_mode = False
            else:
                self.running = False

        elif event.key == pygame.K_r and self.game_over:
            self.reset_game()
        elif event.key == pygame.K_p and not self.game_over:
            self.paused = not self.paused
        elif event.key == pygame.K_b and not self.game_over:
            self.shop_open = not self.shop_open
        elif event.key == pygame.K_c and not self.game_over and not self.shop_open:
            self.crafting_open = not self.crafting_open
        elif event.key == pygame.K_m and not self.game_over:
            self.mutation_menu_open = not self.mutation_menu_open
        elif event.key == pygame.K_n and not self.game_over:
            self.building_mode = not self.building_mode
        elif event.key == pygame.K_k and not self.game_over:
            self.economy_system.toggle_stock_market()
            if self.economy_system.stock_market_open:
                self.shop_open = False
                self.crafting_open = False
        elif event.key == pygame.K_F1:
            self.show_instructions = not self.show_instructions
        elif event.key == pygame.K_F2:
            self.editor_mode = not self.editor_mode
        elif event.key == pygame.K_F3:
            self.settings_open = not self.settings_open
        elif event.key == pygame.K_F4:
            if self.portals:
                portal = random.choice(self.portals)
                self.player.x = portal.x
                self.player.y = portal.y
        elif event.key == pygame.K_F5:
            # Стоимость призыва дрона
            drone_cost = 50
            if self.player.scrap >= drone_cost:
                if self.ally_system.summon_ally('drone'):
                    self.player.scrap -= drone_cost
                    self.ui.show_notification(f"Дрон призван! (-{drone_cost} скрапа)", CYAN, 2.0)
                else:
                    self.ui.show_notification("Не удалось призвать дрона!", RED, 2.0)
            else:
                self.ui.show_notification(f"Нужно {drone_cost} скрапа для дрона!", RED, 2.0)
        elif event.key == pygame.K_F6:
            vehicle = self.vehicle_system.get_vehicle_at(self.player.x, self.player.y)
            if vehicle and vehicle.enter(self.player):
                self.ui.show_notification(f"Вы сели в {vehicle.type}", GREEN, 2.0)
        elif event.key == pygame.K_F7:
            if self.player.in_vehicle:
                self.player.vehicle.exit(self.player)
                self.ui.show_notification("Вы вышли из транспорта", WHITE, 2.0)
        elif event.key == pygame.K_F8:
            self.debug_mode = not self.debug_mode
            self.ui.show_notification(f"Отладка: {'Вкл' if self.debug_mode else 'Выкл'}", CYAN, 2.0)
        elif event.key == pygame.K_F9:
            if self.coop_system.add_player(self.player.x + 50, self.player.y):
                self.ui.show_notification("Второй игрок добавлен!", GREEN, 2.0)
        elif self.shop_open:
            if event.key == pygame.K_1: self.shop.buy_item(0)
            elif event.key == pygame.K_2: self.shop.buy_item(1)
            elif event.key == pygame.K_3: self.shop.buy_item(2)
            elif event.key == pygame.K_4: self.shop.buy_item(3)
            elif event.key == pygame.K_5: self.shop.buy_item(4)
            elif event.key == pygame.K_6: self.shop.buy_item(5)
            elif event.key == pygame.K_7: self.shop.buy_item(6)
        elif self.crafting_open:
            if event.key == pygame.K_1: self.craft_item(0)
            elif event.key == pygame.K_2: self.craft_item(1)
            elif event.key == pygame.K_3: self.craft_item(2)
            elif event.key == pygame.K_4: self.craft_item(3)
            elif event.key == pygame.K_5: self.craft_item(4)
        elif self.mutation_menu_open:
            if event.key == pygame.K_1:
                self.apply_random_mutation()
        elif self.building_mode:
            if event.key == pygame.K_1: self.building_system.selected_type = 'turret'
            elif event.key == pygame.K_2: self.building_system.selected_type = 'wall'
            elif event.key == pygame.K_3: self.building_system.selected_type = 'generator'
            elif event.key == pygame.K_4: self.building_system.selected_type = 'medstation'
            elif event.key == pygame.K_SPACE: self.place_building()
        elif not self.game_over and not self.paused:
            if event.key == pygame.K_v:
                if self.player.upgrade_skill('survival', 'max_hp'):
                    self.ui.show_notification("HP улучшено!", GREEN, 1.5)
            elif event.key == pygame.K_x:
                if self.player.upgrade_skill('tech', 'energy_efficiency'):
                    self.ui.show_notification("Энергия улучшена!", CYAN, 1.5)
            elif event.key == pygame.K_j:
                self.quest_manager.debug_print_quests()

    def summon_drone(self):
        """Призыв дрона за скрап."""
        drone_cost = 50

        if self.player.scrap < drone_cost:
            self.ui.show_notification(f"Нужно {drone_cost} скрапа для дрона!", RED, 2.0)
            return False

        if self.ally_system.summon_ally('drone'):
            self.player.scrap -= drone_cost
            self.ui.show_notification(f"Дрон призван! (-{drone_cost} скрапа)", CYAN, 2.0)
            return True

        return False

    def show_dialogue(self, dialogue_data=None):
        self.in_dialogue = True
        if hasattr(self.ui, 'show_dialogue'):
            self.ui.show_dialogue(dialogue_data)

    def hide_dialogue(self):
        self.in_dialogue = False
        if hasattr(self.ui, 'hide_dialogue'):
            self.ui.hide_dialogue()
        if hasattr(self.story_manager, 'pending_dialogue'):
            self.story_manager.pending_dialogue = None
        if hasattr(self.story_manager, 'pending_choice'):
            self.story_manager.pending_choice = None

    def craft_item(self, index: int):
        recipes = self.crafting_system.get_available_recipes()
        if 0 <= index < len(recipes):
            recipe = recipes[index]
            if self.crafting_system.craft(recipe.id):
                self.crafted_items += 1
                result = recipe.result
                if result.get('type') == 'repair':
                    self.player.heal(result.get('amount', 25))
                elif result.get('type') == 'energy':
                    self.player.energy = min(self.player.max_energy, self.player.energy + result.get('amount', 25))
                elif result.get('type') == 'weapon':
                    self.player.add_weapon(result.get('weapon_id', 'pistol'))
                elif result.get('type') == 'protection':
                    self.player.add_protection(result.get('protection_id', ''))
                elif result.get('type') == 'minion':
                    self.player.add_minion(result.get('minion_id', ''))
                elif result.get('type') == 'consumable':
                    self.apply_consumable_effect(result.get('effect', ''), result.get('value', 0))
                self.sound_manager.play('pickup')
                self.ui.show_notification(f"Создано: {recipe.name}", GREEN, 2.0)

    def apply_consumable_effect(self, effect: str, value: int):
        if effect == 'heal':
            self.player.heal(value)
        elif effect == 'energy':
            self.player.energy = min(self.player.max_energy, self.player.energy + value)
        elif effect == 'emp':
            self.player._activate_emp(self)
        elif effect == 'shield':
            self.player.shield_timer = max(self.player.shield_timer, float(value))
        elif effect == 'damage_boost':
            self.player.apply_temporary_buff('damage_boost', float(value))
        elif effect == 'speed_boost':
            self.player.apply_temporary_buff('speed_boost', float(value))

    def apply_random_mutation(self):
        # Проверяем, можно ли получить мутацию
        if not self.mutation_system.can_get_mutation():
            reason = self.mutation_system.get_cannot_reason()
            self.ui.show_notification(reason, RED, 2.0)
            return

        mutation = self.mutation_system.get_random_mutation()
        if mutation:
            cost = getattr(mutation, 'cost', 1)
            if not self.mutation_system.pay_mutation_cost(cost):
                self.ui.show_notification("Недостаточно ресурсов для мутации!", RED, 2.0)
                return
            self.mutation_system.apply_mutation(mutation.id)
            self.ui.show_notification(f"Мутация: {mutation.name} (стоимость: {cost})", PURPLE, 3.0)

    def place_building(self):
        selected = self.building_system.selected_type
        if self.building_system.add_building(self.player.x, self.player.y, selected, self.player):
            self.ui.show_notification(f"Построено: {selected}", GREEN, 2.0)
        else:
            self.ui.show_notification("Недостаточно ресурсов для постройки", RED, 2.0)

    def handle_keyup(self, event: pygame.event.Event):
        pass

    def handle_mouse_down(self, event: pygame.event.Event):
        if hasattr(self, 'settings_button_rect') and self.settings_button_rect.collidepoint(event.pos):
            self.settings_open = True
            return
        if hasattr(self, 'help_button_rect') and self.help_button_rect.collidepoint(event.pos):
            self.show_instructions = True
            return

        if self.editor_mode:
            self.editor.handle_event(event)
            return
        if self.economy_system.stock_market_open:
            self.economy_system.handle_stock_market_click(event.pos)
            return
        if self.shop_open:
            self.handle_shop_click(event.pos)
        elif self.crafting_open:
            self.handle_crafting_click(event.pos)
        elif self.in_dialogue:
            self.handle_dialogue_click(event.pos)
        elif self.settings_open:
            self.handle_settings_click(event.pos)
        elif self.game_over:
            self.reset_game()
        else:
            self.check_portal_interaction(event.pos)
            if not self.player.in_vehicle:
                vehicle = self.vehicle_system.get_vehicle_at(event.pos[0], event.pos[1])
                if vehicle and vehicle.enter(self.player):
                    self.ui.show_notification(f"Вы сели в {vehicle.type}", GREEN, 2.0)

    def handle_mouse_up(self, event: pygame.event.Event):
        pass

    def handle_shop_click(self, pos: Tuple[int, int]):
        y_start = 150
        for i in range(len(self.shop.items)):
            y = y_start + i * 40
            if y <= pos[1] <= y + 30 and SCREEN_WIDTH // 2 - 400 <= pos[0] <= SCREEN_WIDTH // 2 + 400:
                self.shop.buy_item(i)
                break

    def handle_crafting_click(self, pos: Tuple[int, int]):
        y_start = 150
        recipes = self.crafting_system.get_available_recipes()
        for i, recipe in enumerate(recipes):
            y = y_start + i * 40
            if y <= pos[1] <= y + 30 and SCREEN_WIDTH // 2 - 400 <= pos[0] <= SCREEN_WIDTH // 2 + 400:
                self.craft_item(i)
                break

    def handle_dialogue_click(self, pos: Tuple[int, int]):
        close_button = pygame.Rect(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 250, 30, 30)
        if close_button.collidepoint(pos):
            self.hide_dialogue()
            return
        pending = getattr(self.story_manager, 'pending_choice', None)
        if pending:
            responses = pending.get('responses', [])
            y_start = SCREEN_HEIGHT - 200
            for i in range(len(responses)):
                y = y_start + i * 40
                if y <= pos[1] <= y + 30:
                    self.story_manager.select_dialogue_response(i)
                    break

    def handle_settings_click(self, pos: Tuple[int, int]):
        y = 200
        if y <= pos[1] <= y + 40 and SCREEN_WIDTH // 2 - 100 <= pos[0] <= SCREEN_WIDTH // 2 + 100:
            current = self.settings_manager.get('sound_volume')
            new_volume = 0.0 if current > 0.5 else 1.0
            self.settings_manager.set('sound_volume', new_volume)
            self.sound_manager.set_volume(new_volume)

    def check_portal_interaction(self, pos: Tuple[int, int]):
        for portal in self.portals:
            if portal.contains(self.player.x, self.player.y, self.player.radius):
                self.change_location(portal.destination)
                break

    def check_effect_synergies(self):
        active_ids = {getattr(effect, 'effect_id', None) for effect in self.active_effects}
        active_ids.discard(None)
        still_active = set()
        for combo, reaction in EFFECT_SYNERGIES.items():
            if combo.issubset(active_ids):
                still_active.add(combo)
                if combo not in self._triggered_synergies:
                    self.on_synergy_triggered(combo, reaction)
        self._triggered_synergies = still_active

    def on_synergy_triggered(self, combo: frozenset, reaction: Dict):
        x, y = self.player.x, self.player.y
        self.collision_system._handle_explosion(x, y, reaction['radius'])
        self.spawn_particles(x, y, 25, reaction['color'])
        self.screen_shake = max(self.screen_shake, 0.25)
        self.ui.show_notification(f"Синергия: {reaction['name'].upper()}!", reaction['color'], 2.0)
        if hasattr(self.synergy_system, 'record_synergy'):
            self.synergy_system.record_synergy(reaction['name'])

    def update(self, dt: float):
        if hasattr(self, 'renderer') and self.renderer:
            self.renderer.update(dt)
        self.update_effects(dt)
        self.ui.update(dt)

        # Обновляем музыку
        self.update_music()

        if self.game_over or self.paused:
            return
        if self.editor_mode:
            self.editor.update(dt)
            return
        if self.shop_open or self.in_dialogue or self.crafting_open or self.settings_open or self.show_instructions or self.mutation_menu_open or self.economy_system.stock_market_open:
            return

        self.time_elapsed += dt
        self.session_stats['time_played'] += dt
        self.time_system.update(dt)
        self.weather_system.update(dt, self)
        self.event_system.update(dt)
        self.score += int(dt * 10)
        self.room_manager.update(dt, self)
        self.wave = self.room_manager.get_effective_wave()

        # Получаем ввод
        if self.mobile_mode and self.mobile_controls:
            # Мобильное управление
            move_x, move_y = self.mobile_controls.get_movement()
            aim_x, aim_y = self.mobile_controls.get_aim()

            # Создаём виртуальные клавиши
            virtual_keys = {
                pygame.K_w: move_y < -0.3,
                pygame.K_s: move_y > 0.3,
                pygame.K_a: move_x < -0.3,
                pygame.K_d: move_x > 0.3,
                pygame.K_UP: move_y < -0.3,
                pygame.K_DOWN: move_y > 0.3,
                pygame.K_LEFT: move_x < -0.3,
                pygame.K_RIGHT: move_x > 0.3,
            }

            # Сохраняем оригинальные функции
            if not self._original_input_functions:
                self._original_input_functions = {
                    'key_get_pressed': pygame.key.get_pressed,
                    'mouse_get_pressed': pygame.mouse.get_pressed,
                    'mouse_get_pos': pygame.mouse.get_pos,
                }

            # Виртуальная мышь для прицеливания
            if abs(aim_x) > 0.3 or abs(aim_y) > 0.3:
                mouse_pos = (
                    self.player.x + aim_x * 200,
                    self.player.y + aim_y * 200
                )
            else:
                mouse_pos = (self.player.x + 100, self.player.y)

            # Виртуальные кнопки мыши
            is_shooting = self.mobile_controls.is_attacking()
            mouse_buttons = (is_shooting, False, False)

            # Подменяем функции
            def fake_key_get_pressed():
                class KeyState:
                    def __getitem__(self, key):
                        return virtual_keys.get(key, False)

                return KeyState()

            def fake_mouse_get_pressed():
                return mouse_buttons

            def fake_mouse_get_pos():
                return mouse_pos

            pygame.key.get_pressed = fake_key_get_pressed
            pygame.mouse.get_pressed = fake_mouse_get_pressed
            pygame.mouse.get_pos = fake_mouse_get_pos

            try:
                # Обновляем игрока с мобильным вводом
                if not self.player.in_vehicle:
                    self.player.update(dt, virtual_keys, mouse_pos, mouse_buttons, self)

                # Остальные обновления
                self.vehicle_system.update(dt, virtual_keys)
                if hasattr(self.coop_system, 'update'):
                    self.coop_system.update(dt, virtual_keys)
            finally:
                # Восстанавливаем оригинальные функции
                pygame.key.get_pressed = self._original_input_functions['key_get_pressed']
                pygame.mouse.get_pressed = self._original_input_functions['mouse_get_pressed']
                pygame.mouse.get_pos = self._original_input_functions['mouse_get_pos']
        else:
            # Обычное управление
            keys = pygame.key.get_pressed()
            mouse_pos = pygame.mouse.get_pos()
            mouse_buttons = pygame.mouse.get_pressed()

            if not self.player.in_vehicle:
                self.player.update(dt, keys, mouse_pos, mouse_buttons, self)
            self.vehicle_system.update(dt, keys)
            if hasattr(self.coop_system, 'update'):
                self.coop_system.update(dt, keys)

        # ===== ПРОВЕРКА СМЕРТИ СРАЗУ ПОСЛЕ ОБНОВЛЕНИЯ ИГРОКА =====
        if self.player.hp <= 0:
            self.player.hp = 0
            self.player.alive = False
            self.game_over = True
            self.session_stats['waves_survived'] = self.wave
            self.save_game_data()
            self.legacy_system.record_death({
                'kills': self.player.kills,
                'score': self.score,
                'wave': self.wave,
                'time': self.time_elapsed
            })
            self.ui.show_notification("Вы погибли! Нажмите R для перезапуска", RED, 3.0)
            return  # ВАЖНО: выходим сразу
        # ==========================================================

        self.player_rect.x = self.player.x - self.player.radius
        self.player_rect.y = self.player.y - self.player.radius

        self.update_bullets(dt)
        self.update_enemies(dt)
        self.collision_system.check_bullet_collisions()
        self.collision_system.check_entity_collisions()
        self.update_obstacles(dt)
        self.particle_system.update(dt)
        self.update_particles(dt)
        self.update_pickups(dt)
        self.update_walls(dt)
        self.update_damage_numbers(dt)
        self.update_portals(dt)
        self.update_hazards(dt)
        self.player.effect_system.update(dt, self)
        self.check_effect_synergies()
        self.ally_system.update(dt)
        self.building_system.update(dt, self)
        self.stealth_system.update(dt)
        self.mutation_system.update(dt)
        self.adaptive_enemy_system.update(dt, self)
        self.update_lightning(dt)
        if self.meteor_shower_active:
            self.update_meteor_shower(dt)
        self.quest_manager.update(dt)
        self.story_manager.update(dt)
        self.achievement_manager.check_achievements()
        self.economy_system.update(dt)
        self.reputation_system.update(dt) if hasattr(self.reputation_system, 'update') else None
        self.update_coop(dt)

        self.check_door_interaction()
        self.check_trader_interaction()
        self._check_floor_exit()

    def check_trader_interaction(self):
        """Проверка взаимодействия с торговцем."""
        if not self.trader_active:
            return
        dist = math.hypot(self.player.x - self.trader_position[0],
                          self.player.y - self.trader_position[1])
        if dist < 50:
            self.shop_open = True
            self.trader_active = False
            self.ui.show_notification("Торговец открыл магазин!", GREEN, 2.0)

    def update_coop(self, dt: float):
        if hasattr(self.coop_system, 'players'):
            for coop_player in self.coop_system.players:
                if not coop_player.alive:
                    self.coop_system.revive_player(coop_player)

    def update_effects(self, dt: float):
        if self.screen_shake > 0:
            self.screen_shake = max(0, self.screen_shake - dt)
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - dt * 3)

    def update_bullets(self, dt: float):
        for bullet in self.bullets[:]:
            if not bullet.update(dt):
                self.bullets.remove(bullet)
        for bullet in self.enemy_bullets[:]:
            if not bullet.update(dt):
                self.enemy_bullets.remove(bullet)

    def update_enemies(self, dt: float):
        for enemy in self.enemies[:]:
            class_name = enemy.__class__.__name__

            if class_name == 'ExtendedEnemyFinal':
                enemy.update(dt, self.player, self)
            elif class_name == 'Minion':
                # Миньон - у него другой метод update
                enemy.update(dt, self)
            else:
                # Старый враг - передаём кортеж координат
                enemy.update(dt, (self.player.x, self.player.y), self)

            if class_name != 'Minion':
                if not enemy.alive and getattr(enemy, 'death_animation', 0) <= 0:
                    if not getattr(enemy, 'kill_processed', False):
                        enemy.kill_processed = True
                        self.on_enemy_killed(enemy)
    def _update_minion(self, minion, dt: float):
        """Обновление миньона: движение к игроку + атака вблизи."""
        player = self.player
        if not player or not player.alive:
            return

        # Дистанция до игрока
        dx = player.x - minion.x
        dy = player.y - minion.y
        dist = math.hypot(dx, dy)

        # Параметры миньона
        attack_range = getattr(minion, 'attack_range', 30)
        speed = getattr(minion, 'speed', 100)
        attack_cooldown = getattr(minion, 'attack_cooldown', 0.7)
        base_damage = getattr(minion, 'damage', 10)

        # Таймер атаки
        if not hasattr(minion, 'attack_timer'):
            minion.attack_timer = 0.0
        minion.attack_timer -= dt

        if dist > attack_range:
            # Движение к игроку
            if dist > 0:
                move_x = dx / dist * speed * dt
                move_y = dy / dist * speed * dt
                minion.x += move_x
                minion.y += move_y

                # Поворот к игроку
                if hasattr(minion, 'angle'):
                    minion.angle = math.atan2(dy, dx)
        else:
            # Атака игрока
            if minion.attack_timer <= 0:
                minion.attack_timer = attack_cooldown

                # Урон зависит от уровня игрока
                level_bonus = player.level * 0.5
                damage = int(base_damage + level_bonus)

                # Критический шанс миньона
                crit_chance = getattr(minion, 'crit_chance', 0.05)
                is_crit = random.random() < crit_chance
                if is_crit:
                    damage = int(damage * 1.5)

                # Наносим урон
                player.take_damage(damage)

                # Визуальные эффекты
                self.spawn_sparks(player.x, player.y, 5)
                self.add_damage_number(player.x, player.y - player.radius, damage,
                                       YELLOW if not is_crit else ORANGE, is_crit)

                # Звук удара
                if hasattr(self, 'sound_manager') and self.sound_manager:
                    self.sound_manager.play('hit')

        # Ограничение в пределах комнаты
        self._clamp_enemy_to_room(minion)

    def update_pickups(self, dt: float):
        for pickup in self.pickups[:]:
            if not pickup.update(dt, (self.player.x, self.player.y)):
                # Проверяем, был ли пикап уничтожен
                if pickup.is_destroyed():
                    explosion = pickup.get_explosion_data()
                    if explosion:
                        # Взрыв наносит урон врагам и игроку
                        self.collision_system._handle_explosion(
                            explosion['x'], explosion['y'], explosion['radius']
                        )
                        self.spawn_particles(explosion['x'], explosion['y'], 20, ORANGE)
                self.pickups.remove(pickup)
                pickup.apply_effect(self)
                self.player.pickups_collected += 1
                self.session_stats['pickups_collected'] += 1
                self.sound_manager.play('pickup')
                self.story_manager.on_item_collected(pickup)

    def _clamp_enemy_to_room(self, enemy):
        """Ограничивает позицию врага текущей комнатой."""
        if not self.current_room:
            return

        room = self.current_room
        margin = 20
        enemy.x = max(room['x'] + margin, min(enemy.x, room['x'] + room['width'] - margin))
        enemy.y = max(room['y'] + margin, min(enemy.y, room['y'] + room['height'] - margin))

    def update_obstacles(self, dt: float):
        for obstacle in self.obstacles:
            obstacle.update(dt)

    def update_particles(self, dt: float):
        for particle in self.particles[:]:
            if not particle.update(dt):
                self.particles.remove(particle)
        for emitter in self.particle_emitters[:]:
            emitter.update(dt)
            if emitter.is_finished():
                self.particle_emitters.remove(emitter)

    def update_pickups(self, dt: float):
        for pickup in self.pickups[:]:
            if not pickup.update(dt, (self.player.x, self.player.y)):
                self.pickups.remove(pickup)
                pickup.apply_effect(self)
                self.player.pickups_collected += 1
                self.session_stats['pickups_collected'] += 1
                self.sound_manager.play('pickup')
                self.story_manager.on_item_collected(pickup)

    def update_walls(self, dt: float):
        for wall in self.energy_walls[:]:
            if not wall.update(dt, self.enemies):
                self.energy_walls.remove(wall)

    def update_damage_numbers(self, dt: float):
        for damage_number in self.damage_numbers[:]:
            if not damage_number.update(dt):
                self.damage_numbers.remove(damage_number)

    def update_portals(self, dt: float):
        for portal in self.portals:
            portal.update(dt)

    def update_hazards(self, dt: float):
        """Идея №1: пульсирующие ловушки в комнатах типа trap."""
        for hazard in self.room_hazards:
            hazard['timer'] += dt
            if hazard['cooldown'] > 0:
                hazard['cooldown'] -= dt
            cycle_pos = hazard['timer'] % hazard['period']
            is_active = cycle_pos < hazard['active_time']
            if is_active and hazard['cooldown'] <= 0 and self.player.alive:
                dist = math.hypot(self.player.x - hazard['x'], self.player.y - hazard['y'])
                if dist < hazard['radius']:
                    self.player.take_damage(hazard['damage'])
                    hazard['cooldown'] = 1.0

    def update_lightning(self, dt: float):
        for lightning in self.lightning_effects[:]:
            lightning['life'] -= dt
            if lightning['life'] <= 0:
                self.lightning_effects.remove(lightning)

    def update_meteor_shower(self, dt: float):
        self.meteor_timer += dt
        if self.meteor_timer >= 1.0:
            self.meteor_timer = 0
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT // 2)
            self.particles.extend(create_trail(x, y - 120, ORANGE, 8))
            self.collision_system._handle_explosion(x, y, 100)
            self.spawn_particles(x, y, 20, ORANGE)

    def spawn_particles(self, x: float, y: float, count: int, color: Tuple[int, int, int] = GRAY):
        particles = create_explosion(x, y, color, count)
        self.particles.extend(particles)
        self.particle_system.spawn_explosion(x, y, 50, count // 2)

    def spawn_sparks(self, x: float, y: float, count: int = 10):
        sparks = create_sparks(x, y, YELLOW, count)
        self.particles.extend(sparks)
        self.particle_system.spawn_sparks(x, y, count)

    def spawn_smoke(self, x: float, y: float, count: int = 5):
        smoke = create_smoke(x, y, count)
        self.particles.extend(smoke)
        self.particle_system.spawn_smoke(x, y, count)

    def add_damage_number(self, x: float, y: float, damage: int,
                          color: Tuple[int, int, int] = YELLOW,
                          is_crit: bool = False, is_heal: bool = False):
        self.damage_numbers.append(DamageNumber(x, y, damage, color, is_crit, is_heal))

    def on_enemy_killed(self, enemy: ExtendedEnemyFinal):
        self.player.kills += 1
        self.session_stats['enemies_killed'] += 1
        self.total_kills += 1
        self.player.add_combo(1)
        self.session_stats['max_combo'] = max(self.session_stats['max_combo'], self.player.combo)
        self.player.energy = min(PLAYER_MAX_ENERGY, self.player.energy + 5)
        combo_multiplier = self.player.get_combo_multiplier()
        stealth_multiplier = self.stealth_system.get_stealth_damage_multiplier()
        score_gain = int(100 * self.wave * combo_multiplier * stealth_multiplier * self.exp_multiplier)
        self.score += score_gain
        self.player.add_exp(int((20 + self.wave * 5) * self.exp_multiplier))
        self.spawn_particles(enemy.x, enemy.y, 15, RED)
        self.spawn_sparks(enemy.x, enemy.y, 5)
        self.add_damage_number(enemy.x, enemy.y - enemy.radius, score_gain, WHITE)
        self.player.effect_system.trigger_all(target=enemy, game=self, damage=score_gain, is_kill=True)
        self.adaptive_enemy_system.update_adaptation(self.player.current_weapon, score_gain)
        self.story_manager.on_enemy_killed(enemy)
        self.quest_manager.handle_game_event('kill', 1, enemy.type)

        # Идея №3: кровавые комнаты лечат при убийстве
        if self.blood_room_active:
            self.player.heal(4)

        if hasattr(enemy, 'loot_dropped'):
            loot = self.loot_system.generate_loot(enemy, self)
        else:
            loot = []
            if random.random() < 0.5:
                loot.append({'type': random.choice(['scrap', 'energy']), 'amount': random.randint(1, 3)})

        # Идея №2: сокровищный гоблин даёт увеличенный лут
        if getattr(enemy, 'is_treasure_goblin', False):
            for _ in range(random.randint(3, 5)):
                loot.append({'type': random.choice(['scrap', 'circuit', 'crystal']), 'amount': random.randint(2, 5)})
            self.ui.show_notification("Сокровищный гоблин повержен!", YELLOW, 3.0)

        for item in loot:
            if item['type'] == 'weapon':
                self.pickups.append(Pickup(enemy.x, enemy.y, f"weapon_{item['weapon_id']}"))
            elif item['type'] == 'protection':
                self.pickups.append(Pickup(enemy.x, enemy.y, f"protection_{item['protection_id']}"))
            elif item['type'] == 'minion':
                self.pickups.append(Pickup(enemy.x, enemy.y, f"minion_{item['minion_id']}"))
            else:
                self.pickups.append(Pickup(enemy.x + random.randint(-20, 20), enemy.y + random.randint(-20, 20), item['type'], item.get('amount', 1)))

        if getattr(enemy, 'is_boss', False):
            self.session_stats['bosses_killed'] += 1
            self.score += 500
            if hasattr(self.evolutionary_ai, 'record_boss_defeat'):
                self.evolutionary_ai.record_boss_defeat(self.wave, self.time_elapsed)
            elif hasattr(self.evolutionary_ai, 'evolve'):
                self.evolutionary_ai.evolve()
        elif getattr(enemy, 'is_elite', False):
            self.spawn_particles(enemy.x, enemy.y, 10, YELLOW)

        if enemy in self.enemies:
            self.enemies.remove(enemy)
        self.sound_manager.play('explosion')
        if getattr(enemy, 'is_boss', False):
            self.screen_shake = 0.5
            self.flash_alpha = 0.3
            self.flash_color = WHITE

        # Проверка зачистки текущей комнаты
        remaining = [e for e in self.enemies if e.__class__.__name__ != 'Minion' and e.alive]
        if not remaining:
            room = self.room_manager.get_current_room()
            was_cleared = room['cleared'] if room else True
            self.room_manager.mark_current_cleared()
            if room and not was_cleared:
                self._grant_room_clear_reward(room)

    def _grant_room_clear_reward(self, room: Dict):
        room_type = room['type']
        if room_type == 'normal':
            self.player.add_exp(20)
            self.score += 100
        elif room_type == 'boss':
            self.player.add_exp(50)
            self.score += 200
            self.trader_active = False
        elif room_type == 'curse':
            self.player.scrap += 0
            for _ in range(2):
                self.pickups.append(Pickup(*self._random_point_in_room(room, 40), 'crystal'))
        elif room_type == 'sacrifice':
            self.player.scrap += 30
        elif room_type == 'miniboss':
            self.pickups.append(Pickup(*self._random_point_in_room(room, 40), 'crystal'))
            self.score += 50
        elif room_type == 'library':
            self._offer_library_choice()
        self.ui.show_notification("Комната зачищена!", GREEN, 1.5)

    def activate_phoenix(self):
        """Активирует протокол «Феникс»: самоуничтожение лаборатории."""
        explosion_x, explosion_y = self.player.x, self.player.y
        radius = 400

        if self.player.alive:
            dist = math.hypot(self.player.x - explosion_x, self.player.y - explosion_y)
            if dist < radius:
                self.player.take_damage(int(40 * (1 - dist / radius)) + 10)

        for enemy in self.enemies[:]:
            if enemy.alive:
                dist = math.hypot(enemy.x - explosion_x, enemy.y - explosion_y)
                if dist < radius:
                    damage = int(150 * (1 - dist / radius))
                    enemy.take_damage(damage)
                    if not enemy.alive:
                        self.on_enemy_killed(enemy)

        self.spawn_particles(explosion_x, explosion_y, 60, ORANGE)
        self.spawn_sparks(explosion_x, explosion_y, 30)
        self.screen_shake = 1.0
        self.flash_alpha = 0.8
        self.flash_color = WHITE
        if self.sound_manager:
            self.sound_manager.play('explosion')

    def unlock_random_location(self):
        locked = [loc for loc in self.location_data if loc not in self.unlocked_locations]
        if locked:
            new_location = random.choice(locked)
            self.unlocked_locations.append(new_location)
            self.ui.show_notification(f"Открыта новая локация: {self.location_data[new_location]['name']}", GREEN, 3.0)

    # ------------------------------------------------------------------
    # Отрисовка (улучшенная, с рендерером и fallback)
    # ------------------------------------------------------------------
    def draw(self):
        self.screen.fill(BLACK)

        # Тряска экрана
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-self.screen_shake_intensity, self.screen_shake_intensity)
            shake_y = random.randint(-self.screen_shake_intensity, self.screen_shake_intensity)

        game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Фон (рендерер или fallback)
        self.draw_background(game_surface)

        # Комнаты и объекты
        self.draw_room_bounds(game_surface)
        self.draw_hazards(game_surface)
        self.draw_doors(game_surface)
        self.draw_obstacles(game_surface)
        self.building_system.draw(game_surface)
        self.draw_walls(game_surface)
        self.draw_portals(game_surface)
        self.draw_pickups(game_surface)
        self.draw_story_objects(game_surface)
        self.draw_enemies(game_surface)
        self.ally_system.draw(game_surface)
        self.vehicle_system.draw(game_surface)
        self.draw_player(game_surface)
        self.draw_bullets(game_surface)
        self.draw_particles(game_surface)
        self.particle_system.draw(game_surface)
        self.draw_lightning(game_surface)
        self.draw_damage_numbers(game_surface)

        # Торговец
        if self.trader_active:
            self._draw_trader(game_surface)

        # Перенос game_surface на экран с учётом тряски
        self.screen.blit(game_surface, (shake_x, shake_y))

        # Оверлеи
        self.time_system.draw_overlay(self.screen)
        self.weather_system.draw_overlay(self.screen)

        # UI и HUD
        self.ui.draw_hud(self.screen)
        self.ui.draw(self.screen)
        self.draw_hud_buttons(self.screen)
        self.draw_room_progress(self.screen)
        self.achievement_manager.draw_achievements(self.screen)
        self.event_system.draw_active_events(self.screen)
        self.economy_system.draw_market_events(self.screen)

        # HOOK: протокол «Феникс» — активируется автоматически, если у Game
        # появится флаг self.phoenix_active / self.phoenix_time_left.
        if hasattr(self, 'renderer') and self.renderer and getattr(self, 'phoenix_active', False):
            renderer = self.renderer
            renderer.draw_phoenix_warning(self.screen, alpha=getattr(self, 'phoenix_warning_alpha', 0.5))
            time_left = getattr(self, 'phoenix_time_left', None)
            if time_left is not None:
                renderer.draw_phoenix_countdown(self.screen, SCREEN_WIDTH // 2 - 20, 40, time_left)

        # Экраны (пауза, магазин, меню и т.д.)
        if self.editor_mode:
            self.editor.draw(self.screen)
        elif self.economy_system.stock_market_open:
            self.economy_system.draw_stock_market(self.screen)
        elif self.game_over:
            self.draw_game_over()
        elif self.paused:
            self.draw_pause()
        elif self.shop_open:
            self.shop.draw(self.screen)
        elif self.crafting_open:
            self.draw_crafting()
        elif self.mutation_menu_open:
            self.draw_mutation_menu()
        elif self.in_dialogue:
            self.draw_dialogue()
        elif self.settings_open:
            self.draw_settings()
        elif self.show_instructions:
            self.draw_instructions()
        elif self.building_mode:
            self.draw_building_menu()

        # Вспышки и затемнение
        if self.flash_alpha > 0:
            if hasattr(self, 'renderer') and self.renderer:
                self.renderer.add_flash(self.flash_color, self.flash_alpha, 0.1)
            else:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                flash_surf.fill(self.flash_color)
                flash_surf.set_alpha(int(self.flash_alpha * 255))
                self.screen.blit(flash_surf, (0, 0))

        if self.darkness_active:
            darkness = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            darkness.fill((0, 0, 0, 200))
            self.screen.blit(darkness, (0, 0))

        if self.mobile_controls and self.mobile_mode:
            self.mobile_controls.draw(self.screen)

        pygame.display.flip()


    def _draw_trader(self, surface):
        """Отрисовка торговца (с рендерером и fallback)."""
        x, y = self.trader_position
        if hasattr(self, 'renderer') and self.renderer:
            renderer = self.renderer
            # Свечение и тело
            renderer.draw_glow(surface, x, y, 30, (255, 200, 80), 100)
            pygame.draw.circle(surface, (80, 80, 100), (int(x), int(y)), 20)
            pygame.draw.circle(surface, (200, 200, 220), (int(x), int(y)), 20, 2)
            # Глаза
            for ex, ey in ((-7, -5), (7, -5)):
                pygame.draw.circle(surface, (255, 255, 255), (int(x + ex), int(y + ey)), 4)
                pygame.draw.circle(surface, (0, 0, 0), (int(x + ex), int(y + ey)), 2)
            # Рот
            pygame.draw.arc(surface, (200, 200, 220), (x - 8, y - 2, 16, 10), 0, math.pi, 2)
            # Подпись
            renderer.draw_text(surface, "Торговец", int(x - 30), int(y - 45), 22, (255, 200, 80), shadow=True)
        else:
            pygame.draw.circle(surface, YELLOW, (int(x), int(y)), 20)
            pygame.draw.circle(surface, WHITE, (int(x), int(y)), 20, 2)
            font = pygame.font.Font(None, 24)
            text = font.render("Торговец", True, WHITE)
            surface.blit(text, (x - 30, y - 40))

    def draw_background(self, surface: pygame.Surface):
        if hasattr(self, 'renderer') and self.renderer:
            self.renderer.draw_background(surface)
            return
        # Fallback
        grid_size = 50
        for x in range(0, SCREEN_WIDTH, grid_size):
            pygame.draw.line(surface, (30, 30, 30), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, grid_size):
            pygame.draw.line(surface, (30, 30, 30), (0, y), (SCREEN_WIDTH, y))
        for _ in range(20):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            pygame.draw.circle(surface, (20, 20, 25), (x, y), 1)

    # ------------------------------------------------------------------
    # (ИСПРАВЛЕНИЕ #1) Единственные версии этих методов — с рендерером.
    # Старые "простые" дубликаты, которые раньше шли ниже и перетирали
    # эти определения, удалены.
    # ------------------------------------------------------------------
    def draw_room_bounds(self, surface: pygame.Surface):
        room = self.room_manager.get_current_room()
        if not room:
            return
        rect = pygame.Rect(room['x'], room['y'], room['width'], room['height'])
        if hasattr(self, 'renderer') and self.renderer:
            renderer = self.renderer
            pulse = 0.5 + 0.5 * math.sin(self.time_elapsed * 2)
            color = (80, 200, 255)
            renderer.draw_rect_glow(surface, rect, color, alpha=30 + int(20 * pulse))
            pygame.draw.rect(surface, color, rect, 2)
            corner_len = 30
            for cx, cy in [(rect.left, rect.top), (rect.right, rect.top),
                           (rect.left, rect.bottom), (rect.right, rect.bottom)]:
                dx = -1 if cx == rect.left else 1
                dy = -1 if cy == rect.top else 1
                pygame.draw.line(surface, color, (cx, cy), (cx + dx * corner_len, cy), 4)
                pygame.draw.line(surface, color, (cx, cy), (cx, cy + dy * corner_len), 4)
        else:
            pygame.draw.rect(surface, (60, 60, 70), rect, 3)

    def draw_doors(self, surface: pygame.Surface):
        room = self.room_manager.get_current_room()
        if not room:
            return
        for direction, rect in self.room_manager.get_door_rects().items():
            color = GREEN if room['cleared'] else RED
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                renderer.draw_rect_glow(surface, rect, color, alpha=80)
                door_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(door_surf, (*color, 200), door_surf.get_rect(), border_radius=4)
                surface.blit(door_surf, rect.topleft)
                pygame.draw.rect(surface, WHITE, rect, 2, border_radius=4)
                if room['cleared']:
                    arrow = "→" if direction in ('left', 'right') else "↓"
                    renderer.draw_text(surface, arrow, rect.centerx - 8, rect.centery - 10, 20, WHITE, shadow=True)
            else:
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, WHITE, rect, 2)

    def draw_hazards(self, surface: pygame.Surface):
        for hazard in self.room_hazards:
            cycle_pos = hazard['timer'] % hazard['period']
            is_active = cycle_pos < hazard['active_time']
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                if is_active:
                    renderer.draw_glow(surface, hazard['x'], hazard['y'], hazard['radius'], (255, 60, 60), 180)
                    pygame.draw.circle(surface, (255, 80, 80), (int(hazard['x']), int(hazard['y'])), hazard['radius'])
                    for i in range(8):
                        angle = i * math.pi / 4
                        sx = hazard['x'] + math.cos(angle) * hazard['radius'] * 0.6
                        sy = hazard['y'] + math.sin(angle) * hazard['radius'] * 0.6
                        ex = hazard['x'] + math.cos(angle) * hazard['radius']
                        ey = hazard['y'] + math.sin(angle) * hazard['radius']
                        pygame.draw.line(surface, (255, 150, 150), (sx, sy), (ex, ey), 3)
                else:
                    pygame.draw.circle(surface, (120, 40, 40), (int(hazard['x']), int(hazard['y'])), hazard['radius'],
                                       2)
            else:
                color = (255, 60, 60) if is_active else (120, 40, 40)
                pygame.draw.circle(surface, color, (int(hazard['x']), int(hazard['y'])), hazard['radius'],
                                   0 if is_active else 2)

    def draw_room_progress(self, surface: pygame.Surface):
        text = f"Этаж {self.room_manager.floor}  |  Комнат зачищено: {self.room_manager.cleared_rooms}/{self.room_manager.total_rooms}"
        if hasattr(self, 'renderer') and self.renderer:
            renderer = self.renderer
            # (ИСПРАВЛЕНИЕ #5) Голографическая панель под текстом прогресса.
            font = pygame.font.Font(None, 22)
            text_w, text_h = font.size(text)
            panel_rect = pygame.Rect(12, SCREEN_HEIGHT - 30 - 6, text_w + 16, text_h + 12)
            renderer.draw_panel(surface, panel_rect, border_color=(80, 200, 255))
            renderer.draw_text(surface, text, 20, SCREEN_HEIGHT - 30, 22, (200, 220, 240), shadow=True, glow=True)
        else:
            font = pygame.font.Font(None, 22)
            rendered = font.render(text, True, WHITE)
            surface.blit(rendered, (20, SCREEN_HEIGHT - 30))

    def draw_obstacles(self, surface: pygame.Surface):
        for obstacle in self.obstacles:
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                obs_type = getattr(obstacle, 'type', 'box')

                # Получаем координаты разными способами
                ox = getattr(obstacle, 'x', getattr(obstacle, 'rect', pygame.Rect(0, 0, 50, 50)).x)
                oy = getattr(obstacle, 'y', getattr(obstacle, 'rect', pygame.Rect(0, 0, 50, 50)).y)
                ow = getattr(obstacle, 'w',
                             getattr(obstacle, 'width', getattr(obstacle, 'rect', pygame.Rect(0, 0, 50, 50)).width))
                oh = getattr(obstacle, 'h',
                             getattr(obstacle, 'height', getattr(obstacle, 'rect', pygame.Rect(0, 0, 50, 50)).height))

                cx = ox + ow // 2
                cy = oy + oh // 2

                if obs_type == 'barrel':
                    renderer.draw_obstacle_barrel(surface, cx, cy, ow, oh)
                elif obs_type in ('crate', 'box'):
                    renderer.draw_obstacle_crate(surface, cx, cy, max(ow, oh))
                elif obs_type == 'wall':
                    renderer.draw_obstacle_wall(surface, pygame.Rect(ox, oy, ow, oh))
                else:
                    renderer.draw_obstacle_crate(surface, cx, cy, max(ow, oh))

                # (ИСПРАВЛЕНИЕ #2) Трещины на повреждённых препятствиях.
                hp = getattr(obstacle, 'hp', None)
                max_hp = getattr(obstacle, 'max_hp', None)
                if hp is not None and max_hp:
                    hp_ratio = max(0.0, min(1.0, hp / max_hp))
                    if hp_ratio < 0.7:
                        crack_rect = pygame.Rect(ox, oy, ow, oh)
                        renderer.draw_crack_overlay(surface, crack_rect, intensity=1 - hp_ratio,
                                                    seed=id(obstacle) % 100000)
            else:
                obstacle.draw(surface)

    def draw_walls(self, surface: pygame.Surface):
        for wall in self.energy_walls:
            wall.draw(surface)

    def draw_portals(self, surface: pygame.Surface):
        for portal in self.portals:
            if hasattr(self, 'renderer') and self.renderer:
                self.renderer.draw_portal(surface, portal.x, portal.y)
            else:
                portal.draw(surface)

    def draw_pickups(self, surface: pygame.Surface):
        for pickup in self.pickups:
            # Используем собственный draw пикапа (детализированная отрисовка)
            pickup.draw(surface)

    def draw_story_objects(self, surface: pygame.Surface):
        """(ИСПРАВЛЕНИЕ #6) Сюжетные объекты мира — терминалы, аудиологи,
        голопроекторы, квантовые ядра, артефакты, памятные фрагменты.

        HOOK: активируется автоматически, если у Game появится список
        self.story_objects, где у каждого объекта есть .x, .y и .type,
        принимающий одно из значений: 'terminal', 'audio_log', 'holo_projector',
        'quantum_core', 'memory_fragment', либо .type == 'artifact' вместе с
        .artifact_type. Пока такого списка нет — метод ничего не делает и
        безопасен для вызова.
        """
        if not (hasattr(self, 'renderer') and self.renderer):
            return
        story_objects = getattr(self, 'story_objects', None)
        if not story_objects:
            return
        renderer = self.renderer
        for obj in story_objects:
            obj_type = getattr(obj, 'type', None)
            x, y = getattr(obj, 'x', 0), getattr(obj, 'y', 0)
            if obj_type == 'terminal':
                renderer.draw_terminal_screen(surface, x, y)
            elif obj_type == 'audio_log':
                renderer.draw_audio_log_device(surface, x, y)
            elif obj_type == 'holo_projector':
                renderer.draw_holo_projector(surface, x, y)
            elif obj_type == 'quantum_core':
                renderer.draw_quantum_core(surface, x, y)
            elif obj_type == 'memory_fragment':
                renderer.draw_memory_fragment(surface, x, y)
            elif obj_type == 'artifact':
                renderer.draw_story_artifact(surface, x, y, getattr(obj, 'artifact_type', 'default'))

    def draw_enemies(self, surface: pygame.Surface):
        for enemy in self.enemies:
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                enemy_type = getattr(enemy, 'type', 'basic')
                if getattr(enemy, 'is_boss', False):
                    enemy_type = 'boss'
                elif getattr(enemy, 'is_elite', False):
                    enemy_type = 'elite'
                hp = getattr(enemy, 'hp', 1)
                max_hp = getattr(enemy, 'max_hp', 1)
                hp_ratio = hp / max_hp if max_hp > 0 else 0
                ex, ey = enemy.x, enemy.y
                angle = getattr(enemy, 'angle', 0)
                radius = getattr(enemy, 'radius', 18)

                # (ИСПРАВЛЕНИЕ #6) Дополнительные эффекты по типу врага.
                base_type = getattr(enemy, 'type', 'basic')
                if getattr(enemy, 'is_elite', False):
                    renderer.draw_enemy_elite_aura(surface, ex, ey, radius=int(radius * 1.3))
                if getattr(enemy, 'is_boss', False):
                    renderer.draw_enemy_boss_rings(surface, ex, ey, radius=int(radius * 1.8),
                                                   phase=getattr(enemy, 'phase', 0))
                if base_type == 'drone':
                    renderer.draw_drone_patrol_path(surface, ex, ey, radius=radius)
                elif base_type == 'tank':
                    renderer.draw_tank_tread_marks(surface, ex, ey, angle)
                elif base_type == 'shooter' and getattr(enemy, 'has_line_of_sight', True):
                    renderer.draw_shooter_laser_sight(surface, ex, ey, (self.player.x, self.player.y))

                renderer.draw_enemy(surface, enemy_type, ex, ey, angle, hp_ratio, None, radius,
                                    phase=getattr(enemy, 'phase', 0))
            else:
                enemy.draw(surface)

    def draw_cyborg_sphere(self, surface, x, y, angle, radius=20, color=None, eye_color=None):
        """Киборг-шар с шестиугольным глазом."""
        color = color or Palette.NEON_CYAN
        eye_color = eye_color or (255, 255, 255)
        pulse = 0.5 + 0.5 * math.sin(self._time * 5.0)

        # Свечение
        self.draw_glow(surface, x, y, radius * 2, color, 100)

        # Корпус
        pygame.draw.circle(surface, (30, 40, 50), (int(x), int(y)), radius)
        pygame.draw.circle(surface, color, (int(x), int(y)), radius, 3)

        # Энергетический слой
        pygame.draw.circle(surface, (60, 180, 220), (int(x), int(y)), radius - 4, 1)

        # Узлы
        for i in range(6):
            a = self._time * 0.8 + i * math.tau / 6
            dot_x = x + math.cos(a) * radius * 0.7
            dot_y = y + math.sin(a) * radius * 0.7
            pygame.draw.circle(surface, color, (int(dot_x), int(dot_y)), 2)

        # Шестиугольный глаз
        eye_x = x + math.cos(angle) * radius * 0.3
        eye_y = y + math.sin(angle) * radius * 0.3
        eye_size = radius * 0.35

        # Свечение глаза
        self.draw_glow(surface, eye_x, eye_y, int(eye_size * 1.5), eye_color, 120)

        # Шестиугольник
        points = []
        for i in range(6):
            a = i * math.pi / 3 - math.pi / 6
            points.append((eye_x + math.cos(a) * eye_size, eye_y + math.sin(a) * eye_size))
        pygame.draw.polygon(surface, color, points, 2)

        inner_points = []
        for i in range(6):
            a = i * math.pi / 3 - math.pi / 6
            inner_points.append((eye_x + math.cos(a) * eye_size * 0.6, eye_y + math.sin(a) * eye_size * 0.6))
        pygame.draw.polygon(surface, eye_color, inner_points)

        core_r = max(2, int(eye_size * 0.25 * (0.8 + 0.2 * pulse)))
        pygame.draw.circle(surface, color, (int(eye_x), int(eye_y)), core_r)

    def draw_player(self, surface: pygame.Surface):
        if not self.player.in_vehicle:
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                angle = getattr(self.player, 'angle', 0)
                radius = getattr(self.player, 'radius', 20)
                is_shielded = getattr(self.player, 'shield_timer', 0) > 0

                # Получаем угол на мышь
                mouse_x, mouse_y = pygame.mouse.get_pos()
                eye_angle = math.atan2(mouse_y - self.player.y, mouse_x - self.player.x)

                # Эффект размытия при рывке — призрачные шары
                if getattr(self.player, 'dash_timer', 0) > 0:
                    self._draw_dash_ghosts(surface, self.player.x, self.player.y, eye_angle, radius)

                # Шар с шестиугольным глазом
                # Получаем угол на мышь
                mouse_x, mouse_y = pygame.mouse.get_pos()
                eye_angle = math.atan2(mouse_y - self.player.y, mouse_x - self.player.x)

                # Шар с шестиугольным глазом (глаз смотрит на мышь)
                self._draw_cyborg_sphere(surface, self.player.x, self.player.y, eye_angle, radius, is_shielded)

                # Щит
                if is_shielded:
                    renderer.draw_energy_shield(surface, self.player.x, self.player.y, radius=radius, active=True)

                # HP бар
                hp_ratio = self.player.hp / self.player.max_hp if self.player.max_hp > 0 else 0
                hp_color = GREEN if hp_ratio > 0.5 else (YELLOW if hp_ratio > 0.25 else RED)
                renderer.draw_health_bar(surface, int(self.player.x - 20), int(self.player.y - radius - 20), 40, 6,
                                         hp_ratio, hp_color)
            else:
                self.player.draw(surface)
        for minion in self.player.minions:
            if minion.alive:
                if hasattr(self, 'renderer') and self.renderer:
                    self.renderer.draw_enemy(surface, 'basic', minion.x, minion.y, 0, 1.0, None,
                                             getattr(minion, 'radius', 12))
                else:
                    minion.draw(surface)

    def _draw_cyborg_sphere(self, surface, x, y, angle, radius, shielded):
        """Отрисовка киборга-шара с шестиугольным глазом."""
        if not (hasattr(self, 'renderer') and self.renderer):
            # Fallback: простой шар с глазом
            pygame.draw.circle(surface, (80, 240, 255), (int(x), int(y)), radius)
            pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), radius, 2)
            eye_x = x + math.cos(angle) * radius * 0.3
            eye_y = y + math.sin(angle) * radius * 0.3
            for i in range(6):
                a = i * math.pi / 3 - math.pi / 6
                points = [(eye_x + math.cos(a) * radius * 0.35, eye_y + math.sin(a) * radius * 0.35) for a in
                          [i * math.pi / 3 - math.pi / 6 for i in range(6)]]
                pygame.draw.polygon(surface, (255, 255, 255), points)
            return

        renderer = self.renderer
        pulse = 0.5 + 0.5 * math.sin(renderer._time * 5.0)

        # Внешнее свечение
        renderer.draw_glow(surface, x, y, radius * 2, (80, 240, 255), 100)

        # Основной шар — металлический корпус
        body_color = (30, 40, 50) if not shielded else (40, 50, 60)
        pygame.draw.circle(surface, body_color, (int(x), int(y)), radius)

        # Контур с неоновой обводкой
        pygame.draw.circle(surface, (80, 240, 255), (int(x), int(y)), radius, 3)

        # Внутренний энергетический слой
        pygame.draw.circle(surface, (60, 180, 220), (int(x), int(y)), radius - 4, 1)

        # Светящиеся точки по окружности
        for i in range(6):
            a = renderer._time * 0.8 + i * math.tau / 6
            dot_x = x + math.cos(a) * radius * 0.7
            dot_y = y + math.sin(a) * radius * 0.7
            pygame.draw.circle(surface, (80, 240, 255), (int(dot_x), int(dot_y)), 2)

        # Шестиугольный глаз
        eye_x = x + math.cos(angle) * radius * 0.3
        eye_y = y + math.sin(angle) * radius * 0.3
        eye_size = radius * 0.35

        # Свечение глаза
        renderer.draw_glow(surface, eye_x, eye_y, int(eye_size * 1.5), (255, 255, 255), 120)

        # Шестиугольник — внешний контур
        outer_points = []
        for i in range(6):
            a = i * math.pi / 3 - math.pi / 6
            outer_points.append((eye_x + math.cos(a) * eye_size, eye_y + math.sin(a) * eye_size))
        pygame.draw.polygon(surface, (80, 240, 255), outer_points, 2)

        # Шестиугольник — внутренняя заливка
        inner_points = []
        for i in range(6):
            a = i * math.pi / 3 - math.pi / 6
            inner_points.append((eye_x + math.cos(a) * eye_size * 0.6, eye_y + math.sin(a) * eye_size * 0.6))
        pygame.draw.polygon(surface, (255, 255, 255), inner_points)

        # Ядро глаза
        core_r = max(2, int(eye_size * 0.25 * (0.8 + 0.2 * pulse)))
        pygame.draw.circle(surface, (80, 240, 255), (int(eye_x), int(eye_y)), core_r)

    def draw_bullets(self, surface: pygame.Surface):
        for bullet in self.bullets:
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                if getattr(bullet, 'from_player', True):
                    angle = math.atan2(getattr(bullet, 'vy', 0), getattr(bullet, 'vx', 1))
                    renderer.draw_projectile_player(surface, bullet.x, bullet.y, angle)
                else:
                    renderer.draw_projectile_enemy(surface, bullet.x, bullet.y, getattr(bullet, 'radius', 6))
            else:
                bullet.draw(surface)
        for bullet in self.enemy_bullets:
            if hasattr(self, 'renderer') and self.renderer:
                self.renderer.draw_projectile_enemy(surface, bullet.x, bullet.y, getattr(bullet, 'radius', 6))
            else:
                bullet.draw(surface)

    def draw_particles(self, surface: pygame.Surface):
        for particle in self.particles:
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                # (ИСПРАВЛЕНИЕ #6) Если у частицы указан конкретный "kind",
                # используем специализированный метод отрисовки renderer'а
                # вместо обычного кружка. Если kind не задан или неизвестен —
                # прежнее поведение (draw_particle) сохраняется как fallback.
                kind = getattr(particle, 'kind', None)
                px, py = getattr(particle, 'x', 0), getattr(particle, 'y', 0)
                color = getattr(particle, 'color', None)
                angle = getattr(particle, 'angle', 0)
                size = getattr(particle, 'size', 8)

                if kind == 'fire':
                    renderer.draw_fire_trail(surface, px, py, angle)
                elif kind == 'ice':
                    renderer.draw_ice_spike(surface, px, py, size=size)
                elif kind == 'poison':
                    renderer.draw_poison_bubble(surface, px, py, size=size)
                elif kind == 'blood':
                    renderer.draw_blood_splatter(surface, px, py)
                elif kind == 'spark':
                    renderer.draw_spark_burst(surface, px, py)
                elif kind == 'smoke':
                    renderer.draw_smoke_puff(surface, px, py, radius=size)
                elif kind == 'star':
                    renderer.draw_star_particle(surface, px, py, size=size)
                elif kind == 'explosion':
                    renderer.draw_explosion_shockwave(surface, px, py, radius=size)
                elif kind == 'heal':
                    renderer.draw_healing_cross(surface, px, py, size=size)
                elif kind == 'portal':
                    renderer.draw_portal_particles(surface, px, py, radius=size)
                else:
                    renderer.draw_particle(surface, particle)
            else:
                particle.draw(surface)

    def draw_lightning(self, surface: pygame.Surface):
        for lightning in self.lightning_effects:
            start = lightning['start']
            end = lightning['end']
            color = lightning.get('color', CYAN)
            if hasattr(self, 'renderer') and self.renderer:
                renderer = self.renderer
                points = [start]
                segments = 8
                for i in range(1, segments):
                    t = i / segments
                    x = start[0] + (end[0] - start[0]) * t + random.randint(-15, 15)
                    y = start[1] + (end[1] - start[1]) * t + random.randint(-15, 15)
                    points.append((x, y))
                points.append(end)
                for i in range(len(points) - 1):
                    renderer.draw_line_glow(surface, points[i], points[i + 1], color, 3)
                for i in range(len(points) - 1):
                    pygame.draw.line(surface, (255, 255, 255), points[i], points[i + 1], 1)
            else:
                points = [start]
                segments = 5
                for i in range(1, segments):
                    t = i / segments
                    x = start[0] + (end[0] - start[0]) * t + random.randint(-10, 10)
                    y = start[1] + (end[1] - start[1]) * t + random.randint(-10, 10)
                    points.append((x, y))
                points.append(end)
                pygame.draw.lines(surface, color, False, points, 2)

    def draw_damage_numbers(self, surface: pygame.Surface):
        for damage_number in self.damage_numbers:
            if hasattr(self, 'renderer') and self.renderer and hasattr(damage_number, 'x'):
                renderer = self.renderer
                value = getattr(damage_number, 'value', getattr(damage_number, 'damage', None))
                if value is not None:
                    renderer.draw_damage_numbers_improved(
                        surface, damage_number.x, damage_number.y, int(value),
                        color=getattr(damage_number, 'color', None),
                        is_crit=getattr(damage_number, 'is_crit', False),
                    )
                else:
                    damage_number.draw(surface)
            else:
                damage_number.draw(surface)

    def draw_hud_buttons(self, screen):
        """Отрисовка кнопок настроек и инструкций (адаптировано для мобильных)."""
        if self.mobile_mode:
            # На мобильных кнопки меньше и расположены иначе
            settings_rect = pygame.Rect(10, 10, 50, 30)
            help_rect = pygame.Rect(70, 10, 50, 30)
        else:
            settings_rect = pygame.Rect(SCREEN_WIDTH - 100, 10, 90, 30)
            help_rect = pygame.Rect(SCREEN_WIDTH - 100, 50, 90, 30)

        if hasattr(self, 'renderer') and self.renderer:
            renderer = self.renderer
            mouse_pos = pygame.mouse.get_pos()
            renderer.draw_button(screen, settings_rect, "⚙", hovered=settings_rect.collidepoint(mouse_pos),
                                 color=(80, 240, 255))
            renderer.draw_button(screen, help_rect, "?", hovered=help_rect.collidepoint(mouse_pos),
                                 color=(255, 70, 200))
        else:
            font = pygame.font.Font(None, 24)
            pygame.draw.rect(screen, (60, 60, 60), settings_rect)
            pygame.draw.rect(screen, WHITE, settings_rect, 2)
            settings_text = font.render("⚙", True, WHITE)
            screen.blit(settings_text, (settings_rect.x + 15, settings_rect.y + 5))

            pygame.draw.rect(screen, (60, 60, 60), help_rect)
            pygame.draw.rect(screen, WHITE, help_rect, 2)
            help_text = font.render("?", True, WHITE)
            screen.blit(help_text, (help_rect.x + 20, help_rect.y + 5))

        self.settings_button_rect = settings_rect
        self.help_button_rect = help_rect

    def draw_dialogue(self):
        """Отрисовка диалогового окна."""
        pending = getattr(self.story_manager, 'pending_choice', None)
        current_dialogue = getattr(self.ui, 'current_dialogue', None)
        dialogue_data = pending or current_dialogue

        if not dialogue_data:
            return

        dialogue_box = pygame.Rect(50, SCREEN_HEIGHT - 250, SCREEN_WIDTH - 100, 200)
        pygame.draw.rect(self.screen, (20, 20, 30), dialogue_box)
        pygame.draw.rect(self.screen, WHITE, dialogue_box, 2)

        # Кнопка закрытия
        close_button = pygame.Rect(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 250, 30, 30)
        pygame.draw.rect(self.screen, (60, 60, 60), close_button)
        pygame.draw.rect(self.screen, WHITE, close_button, 2)
        close_font = pygame.font.Font(None, 24)
        close_text = close_font.render("X", True, WHITE)
        self.screen.blit(close_text, (close_button.x + 10, close_button.y + 5))

        # Имя говорящего
        font_name = pygame.font.Font(None, 30)
        speaker = dialogue_data.get('speaker', '')
        name_text = font_name.render(speaker, True, CYAN)
        self.screen.blit(name_text, (dialogue_box.x + 20, dialogue_box.y + 20))

        # Текст диалога
        font_text = pygame.font.Font(None, 24)
        text = dialogue_data.get('text', '')
        text_surf = font_text.render(text, True, WHITE)
        self.screen.blit(text_surf, (dialogue_box.x + 20, dialogue_box.y + 60))

        # Ответы
        responses = dialogue_data.get('responses', [])
        y = dialogue_box.y + 120
        for i, response in enumerate(responses):
            response_text = f"{i + 1}. {response.get('text', '')}"
            response_surf = font_text.render(response_text, True, YELLOW)
            self.screen.blit(response_surf, (dialogue_box.x + 40, y))
            y += 30

        # Подсказка
        hint_font = pygame.font.Font(None, 20)
        hint_text = hint_font.render("ESC/X - закрыть | 1-4 - выбрать ответ", True, LIGHT_GRAY)
        self.screen.blit(hint_text, (dialogue_box.x + 20, dialogue_box.y + dialogue_box.height - 30))

    def draw_crafting(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        font_large = pygame.font.Font(None, 60)
        title = font_large.render("КРАФТИНГ", True, ORANGE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        font = pygame.font.Font(None, 30)
        resources = self.player.get_resource_dict()
        resources_text = " | ".join([f"{k}: {v}" for k, v in resources.items() if v > 0])
        if not resources_text:
            resources_text = "Нет ресурсов"
        resources_surf = font.render(resources_text, True, WHITE)
        self.screen.blit(resources_surf, (SCREEN_WIDTH // 2 - resources_surf.get_width() // 2, 110))
        y = 170
        recipes = self.crafting_system.get_available_recipes()
        for i, recipe in enumerate(recipes):
            materials = ", ".join([f"{mat}: {amount}" for mat, amount in recipe.materials.items()])
            text = f"{i + 1}. {recipe.name} - [{materials}] - {recipe.description}"
            color = WHITE if self.crafting_system.can_craft(recipe.id) else GRAY
            rendered = font.render(text, True, color)
            self.screen.blit(rendered, (SCREEN_WIDTH // 2 - 400, y))
            y += 30

    def draw_mutation_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        font_large = pygame.font.Font(None, 60)
        title = font_large.render("МУТАЦИИ", True, PURPLE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        font = pygame.font.Font(None, 25)
        y = 150
        active_text = font.render("Активные мутации:", True, GREEN)
        self.screen.blit(active_text, (SCREEN_WIDTH // 2 - 200, y))
        y += 30
        for mutation in self.mutation_system.active_mutations:
            text = font.render(f"- {mutation.name}: {mutation.description}", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - 200, y))
            y += 25
        y += 20
        available_text = font.render("Доступные мутации:", True, YELLOW)
        self.screen.blit(available_text, (SCREEN_WIDTH // 2 - 200, y))
        y += 30
        for mutation in self.mutation_system.available_mutations:
            if not mutation.active:
                text = font.render(f"- {mutation.name}: {mutation.description}", True, LIGHT_GRAY)
                self.screen.blit(text, (SCREEN_WIDTH // 2 - 200, y))
                y += 25
        hint = font.render("Нажмите 1 для случайной мутации", True, CYAN)
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def draw_building_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        font = pygame.font.Font(None, 30)
        title = font.render("СТРОИТЕЛЬСТВО", True, YELLOW)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        building_types = [
            ("1. Турель", "10 металлолома, 2 схемы"),
            ("2. Стена", "5 металлолома"),
            ("3. Генератор", "15 металлолома, 5 схем"),
            ("4. Медстанция", "12 металлолома, 3 схемы")
        ]
        y = 120
        for building_text, cost_text in building_types:
            text = font.render(f"{building_text} - {cost_text}", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - 200, y))
            y += 40
        hint = font.render("Пробел - разместить | N - выйти", True, CYAN)
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))

    def draw_settings(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        font_large = pygame.font.Font(None, 60)
        title = font_large.render("НАСТРОЙКИ", True, CYAN)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))
        font = pygame.font.Font(None, 30)
        y = 200
        settings_items = [
            f"Громкость звука: {self.settings_manager.get('sound_volume')}",
            f"Сложность: {self.settings_manager.get('difficulty')}",
            f"Тряска экрана: {'Вкл' if self.settings_manager.get('screen_shake') else 'Выкл'}"
        ]
        for item in settings_items:
            rendered = font.render(item, True, WHITE)
            self.screen.blit(rendered, (SCREEN_WIDTH // 2 - 200, y))
            y += 40

    def draw_instructions(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        font_large = pygame.font.Font(None, 50)
        title = font_large.render("ИНСТРУКЦИЯ", True, GREEN)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        font = pygame.font.Font(None, 25)
        instructions = [
            "WASD / Стрелки - движение",
            "Мышь - прицеливание",
            "ЛКМ - стрельба",
            "ПКМ / Shift - рывок",
            "Пробел - энергетическая стена",
            "Подойдите к зелёной двери - переход в комнату",
            "1-0 - переключение оружия",
            "B - магазин",
            "K - биржа",
            "C - крафтинг",
            "M - мутации",
            "N - строительство",
            "F4 - телепорт к порталу",
            "F5 - призыв дрона",
            "F6 - сесть в транспорт",
            "F7 - выйти из транспорта",
            "F8 - отладка",
            "F9 - кооператив",
            "P - пауза",
            "F1 - инструкция",
            "F2 - редактор",
            "F3 - настройки",
            "ESC - выход"
        ]
        y = 130
        for instruction in instructions:
            rendered = font.render(instruction, True, WHITE)
            self.screen.blit(rendered, (SCREEN_WIDTH // 2 - 300, y))
            y += 25

    def draw_game_over(self):
        if hasattr(self, 'renderer') and self.renderer:
            renderer = self.renderer
            panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 320, SCREEN_HEIGHT // 2 - 200, 640, 420)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))
            renderer.draw_panel(self.screen, panel_rect, border_color=(255, 70, 90))
        else:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))
        font_large = pygame.font.Font(None, 72)
        title = font_large.render("ИГРА ОКОНЧЕНА", True, RED)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 2 - 150))
        font = pygame.font.Font(None, 36)
        stats = [
            f"Счёт: {self.score}",
            f"Этаж: {self.room_manager.floor}",
            f"Рекорд: {self.best_score}",
            f"Убийств: {self.player.kills}",
            f"Максимальное комбо: {self.session_stats['max_combo']}",
            f"Время: {int(self.time_elapsed)} сек",
            f"День: {self.time_system.day}",
            f"Период: {self.time_system.get_period()}"
        ]
        y = SCREEN_HEIGHT // 2 - 50
        for stat in stats:
            text = font.render(stat, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, y))
            y += 40
        legacy_stats = self.legacy_system.get_total_stats()
        legacy_text = font.render(
            f"Всего убийств: {legacy_stats['total_kills']} | Всего смертей: {legacy_stats['total_deaths']}", True, CYAN)
        self.screen.blit(legacy_text, (SCREEN_WIDTH // 2 - legacy_text.get_width() // 2, y + 20))
        hint = font.render("Нажмите R или кликните для перезапуска", True, CYAN)
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, y + 60))

    def draw_pause(self):
        if hasattr(self, 'renderer') and self.renderer:
            renderer = self.renderer
            panel_rect = pygame.Rect(SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT // 2 - 90, 440, 180)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
            renderer.draw_panel(self.screen, panel_rect, border_color=(80, 240, 255))
        else:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
        font = pygame.font.Font(None, 60)
        text = font.render("ПАУЗА", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        font_small = pygame.font.Font(None, 30)
        hint = font_small.render("Нажмите P для продолжения", True, LIGHT_GRAY)
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def _draw_dash_ghosts(self, surface, x, y, angle, radius):
        """Призрачные копии шара позади игрока при рывке."""
        if not (hasattr(self, 'renderer') and self.renderer):
            return

        renderer = self.renderer
        # Направление рывка — назад от угла взгляда
        back_angle = angle + math.pi

        # 5 призрачных копий
        for i in range(1, 6):
            offset = i * 10  # Расстояние между копиями
            ghost_x = x + math.cos(back_angle) * offset
            ghost_y = y + math.sin(back_angle) * offset

            # Прозрачность уменьшается с расстоянием
            alpha = 255 // (i + 1)
            ghost_color = (80, 240, 255, alpha)

            # Шар-призрак
            ghost_radius = int(radius * (1 - i * 0.1))  # Немного уменьшается
            if ghost_radius < 5:
                continue

            # Полупрозрачный круг
            ghost_surf = pygame.Surface((ghost_radius * 2, ghost_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surf, ghost_color, (ghost_radius, ghost_radius), ghost_radius)
            surface.blit(ghost_surf, (int(ghost_x - ghost_radius), int(ghost_y - ghost_radius)))

            # Лёгкое свечение
            renderer.draw_glow(surface, ghost_x, ghost_y, ghost_radius, (80, 240, 255), alpha // 3)

