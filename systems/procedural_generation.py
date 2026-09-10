# systems/procedural_generation.py
import random
import math
import json
import os
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from settings import *
from entities.obstacle import Obstacle
from entities.enemy import Enemy
from entities.pickup import Pickup


# ============================================================
# КОМНАТЫ И СТРУКТУРЫ
# ============================================================

@dataclass
class Room:
    """Комната для процедурной генерации"""
    id: int = 0
    x: int = 0
    y: int = 0
    w: int = 200
    h: int = 200
    room_type: str = 'normal'  # start, normal, boss, treasure, shop, trap, secret
    biome: str = 'city'
    enemies: List[Dict] = field(default_factory=list)
    items: List[Dict] = field(default_factory=list)
    obstacles: List[Dict] = field(default_factory=list)
    connected_rooms: List[int] = field(default_factory=list)
    cleared: bool = False
    explored: bool = False
    locked: bool = False
    door_positions: Dict[str, Tuple[int, int]] = field(default_factory=dict)

    def get_center(self) -> Tuple[int, int]:
        """Получение центра комнаты"""
        return (self.x + self.w // 2, self.y + self.h // 2)

    def get_rect(self) -> pygame.Rect:
        """Получение прямоугольника комнаты"""
        return pygame.Rect(self.x, self.y, self.w, self.h)

    def contains_point(self, x: int, y: int) -> bool:
        """Проверка, содержит ли комната точку"""
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def intersects(self, other: 'Room', padding: int = 20) -> bool:
        """Проверка пересечения с другой комнатой"""
        return (self.x - padding < other.x + other.w + padding and
                self.x + self.w + padding > other.x - padding and
                self.y - padding < other.y + other.h + padding and
                self.y + self.h + padding > other.y - padding)

    def to_dict(self) -> dict:
        """Сериализация"""
        return {
            'id': self.id,
            'x': self.x,
            'y': self.y,
            'w': self.w,
            'h': self.h,
            'room_type': self.room_type,
            'biome': self.biome,
            'enemies': self.enemies,
            'items': self.items,
            'obstacles': self.obstacles,
            'connected_rooms': self.connected_rooms,
            'cleared': self.cleared,
            'explored': self.explored,
            'locked': self.locked,
            'door_positions': self.door_positions
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Room':
        """Десериализация"""
        room = cls()
        room.id = data.get('id', 0)
        room.x = data.get('x', 0)
        room.y = data.get('y', 0)
        room.w = data.get('w', 200)
        room.h = data.get('h', 200)
        room.room_type = data.get('room_type', 'normal')
        room.biome = data.get('biome', 'city')
        room.enemies = data.get('enemies', [])
        room.items = data.get('items', [])
        room.obstacles = data.get('obstacles', [])
        room.connected_rooms = data.get('connected_rooms', [])
        room.cleared = data.get('cleared', False)
        room.explored = data.get('explored', False)
        room.locked = data.get('locked', False)
        room.door_positions = data.get('door_positions', {})
        return room


@dataclass
class Corridor:
    """Коридор между комнатами"""
    start: Tuple[int, int]
    end: Tuple[int, int]
    width: int = 40

    def get_points(self) -> List[Tuple[int, int]]:
        """Получение точек коридора (L-образный)"""
        corner = (self.end[0], self.start[1])
        return [self.start, corner, self.end]

    def to_dict(self) -> dict:
        """Сериализация"""
        return {
            'start': self.start,
            'end': self.end,
            'width': self.width
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Corridor':
        """Десериализация"""
        return cls(
            start=tuple(data['start']),
            end=tuple(data['end']),
            width=data.get('width', 40)
        )


# ============================================================
# ГЕНЕРАТОР УРОВНЕЙ
# ============================================================

class ProceduralGenerator:
    """Полноценный генератор процедурных уровней"""

    def __init__(self, width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT):
        self.width = width
        self.height = height
        self.rooms: List[Room] = []
        self.corridors: List[Corridor] = []
        self.rng = random.Random()
        self.seed = 0

        # Конфигурация генерации
        self.min_room_size = 150
        self.max_room_size = 300
        self.min_rooms = 8
        self.max_rooms = 15
        self.room_padding = 30

        # Типы комнат по биомам
        self.biome_rooms = {
            'city': {
                'start': 1,
                'normal': 5,
                'boss': 1,
                'treasure': 2,
                'shop': 1,
                'trap': 2,
                'secret': 1
            },
            'lab': {
                'start': 1,
                'normal': 4,
                'boss': 1,
                'treasure': 2,
                'experiment': 2,
                'trap': 2,
                'secret': 2
            },
            'forest': {
                'start': 1,
                'normal': 4,
                'boss': 1,
                'treasure': 2,
                'nest': 2,
                'trap': 1,
                'secret': 2
            },
            'wasteland': {
                'start': 1,
                'normal': 6,
                'boss': 1,
                'treasure': 1,
                'trap': 2,
                'secret': 1
            }
        }

        # Враги по биомам
        self.biome_enemies = {
            'city': ['basic', 'fast', 'shooter', 'tank'],
            'lab': ['basic', 'shooter', 'elite', 'hybrid'],
            'forest': ['fast', 'tank', 'hybrid', 'elite'],
            'wasteland': ['fast', 'tank', 'basic', 'shooter']
        }

        # Предметы
        self.treasure_items = [
            {'type': 'weapon', 'name': 'pistol'},
            {'type': 'weapon', 'name': 'shotgun'},
            {'type': 'weapon', 'name': 'laser'},
            {'type': 'consumable', 'name': 'medkit'},
            {'type': 'consumable', 'name': 'energy_cell'},
            {'type': 'material', 'name': 'scrap', 'amount': 10},
            {'type': 'material', 'name': 'circuit', 'amount': 5},
            {'type': 'material', 'name': 'crystal', 'amount': 1},
            {'type': 'effect', 'name': 'shield'},
            {'type': 'effect', 'name': 'double_damage'},
            {'type': 'effect', 'name': 'haste'},
            {'type': 'effect', 'name': 'invisibility'}
        ]

        self.shop_items = [
            {'type': 'weapon', 'name': 'shotgun', 'price': 500},
            {'type': 'weapon', 'name': 'laser', 'price': 800},
            {'type': 'weapon', 'name': 'plasma_rifle', 'price': 1500},
            {'type': 'consumable', 'name': 'medkit', 'price': 100},
            {'type': 'consumable', 'name': 'energy_cell', 'price': 150},
            {'type': 'effect', 'name': 'shield', 'price': 200},
            {'type': 'effect', 'name': 'haste', 'price': 300},
            {'type': 'upgrade', 'name': 'damage', 'price': 400}
        ]

    def generate_level(self, seed: int = None, biome: str = 'city',
                       num_rooms: int = None) -> List[Room]:
        """Генерация уровня"""
        # Установка сида
        if seed is not None:
            self.seed = seed
            self.rng.seed(seed)
        else:
            self.seed = random.randint(0, 999999)
            self.rng.seed(self.seed)

        self.rooms = []
        self.corridors = []

        # Определение количества комнат
        if num_rooms is None:
            num_rooms = self.rng.randint(self.min_rooms, self.max_rooms)

        # Создание стартовой комнаты
        start_room = Room(
            id=0,
            x=self.width // 2 - 100,
            y=self.height // 2 - 100,
            w=200,
            h=200,
            room_type='start',
            biome=biome
        )
        self.rooms.append(start_room)

        # Генерация остальных комнат
        attempts = 0
        max_attempts = 200

        while len(self.rooms) < num_rooms and attempts < max_attempts:
            attempts += 1

            # Выбор родительской комнаты
            parent = self.rng.choice(self.rooms)

            # Генерация новой комнаты
            new_room = self._generate_room_near(parent, biome)

            if new_room and not self._room_overlaps(new_room):
                new_room.id = len(self.rooms)
                self.rooms.append(new_room)

                # Соединение комнат
                parent.connected_rooms.append(new_room.id)
                new_room.connected_rooms.append(parent.id)

                # Создание коридора
                corridor = Corridor(
                    start=parent.get_center(),
                    end=new_room.get_center()
                )
                self.corridors.append(corridor)

                # Определение позиций дверей
                self._calculate_door_positions(parent, new_room)

        # Назначение типов комнат
        self._assign_room_types(biome)

        # Наполнение комнат
        self._populate_rooms(biome)

        return self.rooms

    def _generate_room_near(self, parent: Room, biome: str) -> Optional[Room]:
        """Генерация комнаты рядом с родительской"""
        w = self.rng.randint(self.min_room_size, self.max_room_size)
        h = self.rng.randint(self.min_room_size, self.max_room_size)

        # Случайное направление
        direction = self.rng.choice(['up', 'down', 'left', 'right'])

        if direction == 'up':
            x = parent.x + self.rng.randint(-w, w)
            y = parent.y - h - self.room_padding
        elif direction == 'down':
            x = parent.x + self.rng.randint(-w, w)
            y = parent.y + parent.h + self.room_padding
        elif direction == 'left':
            x = parent.x - w - self.room_padding
            y = parent.y + self.rng.randint(-h, h)
        else:  # right
            x = parent.x + parent.w + self.room_padding
            y = parent.y + self.rng.randint(-h, h)

        # Проверка границ
        if x < 0 or y < 0 or x + w > self.width or y + h > self.height:
            return None

        return Room(
            x=x,
            y=y,
            w=w,
            h=h,
            biome=biome
        )

    def _room_overlaps(self, room: Room) -> bool:
        """Проверка пересечения комнаты с существующими"""
        for other in self.rooms:
            if room.intersects(other, self.room_padding):
                return True
        return False

    def _calculate_door_positions(self, room1: Room, room2: Room):
        """Расчёт позиций дверей между комнатами"""
        center1 = room1.get_center()
        center2 = room2.get_center()

        # Определение направления
        dx = center2[0] - center1[0]
        dy = center2[1] - center1[1]

        if abs(dx) > abs(dy):
            # Горизонтальное соединение
            if dx > 0:
                door_y = center1[1]
                room1.door_positions['right'] = (room1.x + room1.w, door_y)
                room2.door_positions['left'] = (room2.x, door_y)
            else:
                door_y = center1[1]
                room1.door_positions['left'] = (room1.x, door_y)
                room2.door_positions['right'] = (room2.x + room2.w, door_y)
        else:
            # Вертикальное соединение
            if dy > 0:
                door_x = center1[0]
                room1.door_positions['down'] = (door_x, room1.y + room1.h)
                room2.door_positions['up'] = (door_x, room2.y)
            else:
                door_x = center1[0]
                room1.door_positions['up'] = (door_x, room1.y)
                room2.door_positions['down'] = (door_x, room2.y + room2.h)

    def _assign_room_types(self, biome: str):
        """Назначение типов комнат"""
        biome_config = self.biome_rooms.get(biome, self.biome_rooms['city'])

        # Список типов для назначения
        types_to_assign = []
        for room_type, count in biome_config.items():
            if room_type != 'start':
                types_to_assign.extend([room_type] * count)

        # Перемешивание
        self.rng.shuffle(types_to_assign)

        # Назначение типов (кроме стартовой)
        type_index = 0
        for room in self.rooms:
            if room.room_type == 'start':
                continue
            if type_index < len(types_to_assign):
                room.room_type = types_to_assign[type_index]
                type_index += 1
            else:
                room.room_type = 'normal'

        # Обеспечение наличия комнаты босса
        has_boss = any(r.room_type == 'boss' for r in self.rooms)
        if not has_boss:
            # Назначение самой дальней комнаты как босса
            start_room = self._get_start_room()
            if start_room:
                farthest = max(self.rooms, key=lambda r:
                math.hypot(r.x - start_room.x, r.y - start_room.y) if r.room_type != 'start' else 0)
                if farthest.room_type != 'start':
                    farthest.room_type = 'boss'

    def _get_start_room(self) -> Optional[Room]:
        """Получение стартовой комнаты"""
        for room in self.rooms:
            if room.room_type == 'start':
                return room
        return self.rooms[0] if self.rooms else None

    def _populate_rooms(self, biome: str):
        """Наполнение комнат контентом"""
        enemy_types = self.biome_enemies.get(biome, self.biome_enemies['city'])

        for room in self.rooms:
            # Наполнение врагами
            self._populate_enemies(room, enemy_types)

            # Наполнение предметами
            self._populate_items(room)

            # Наполнение препятствиями
            self._populate_obstacles(room)

    def _populate_enemies(self, room: Room, enemy_types: List[str]):
        """Наполнение врагами"""
        if room.room_type == 'start':
            return

        enemy_counts = {
            'normal': (2, 5),
            'boss': (1, 1),
            'treasure': (0, 1),
            'shop': (0, 0),
            'trap': (3, 7),
            'secret': (1, 2),
            'experiment': (3, 5),
            'nest': (4, 8)
        }

        count_range = enemy_counts.get(room.room_type, (1, 3))
        num_enemies = self.rng.randint(count_range[0], count_range[1])

        for _ in range(num_enemies):
            enemy_type = self.rng.choice(enemy_types)

            if room.room_type == 'boss':
                enemy_type = 'avatar'

            # Случайная позиция в комнате
            x = room.x + self.rng.randint(50, room.w - 50)
            y = room.y + self.rng.randint(50, room.h - 50)

            room.enemies.append({
                'type': enemy_type,
                'x': x,
                'y': y,
                'wave': 1
            })

    def _populate_items(self, room: Room):
        """Наполнение предметами"""
        if room.room_type == 'treasure':
            num_items = self.rng.randint(2, 4)
            for _ in range(num_items):
                item = self.rng.choice(self.treasure_items)
                x = room.x + self.rng.randint(50, room.w - 50)
                y = room.y + self.rng.randint(50, room.h - 50)
                room.items.append({**item, 'x': x, 'y': y})

        elif room.room_type == 'shop':
            num_items = self.rng.randint(3, 6)
            for _ in range(num_items):
                item = self.rng.choice(self.shop_items)
                x = room.x + self.rng.randint(80, room.w - 80)
                y = room.y + self.rng.randint(80, room.h - 80)
                room.items.append({**item, 'x': x, 'y': y})

        elif room.room_type == 'secret':
            # Секретная комната с редким лутом
            rare_items = [
                {'type': 'weapon', 'name': 'plasma_rifle'},
                {'type': 'weapon', 'name': 'rocket_launcher'},
                {'type': 'effect', 'name': 'quantum_entanglement'},
                {'type': 'effect', 'name': 'singularity'},
                {'type': 'artifact', 'name': 'ai_core'}
            ]
            item = self.rng.choice(rare_items)
            x = room.get_center()[0]
            y = room.get_center()[1]
            room.items.append({**item, 'x': x, 'y': y})

    def _populate_obstacles(self, room: Room):
        """Наполнение препятствиями"""
        if room.room_type == 'start':
            return

        obstacle_counts = {
            'normal': (3, 8),
            'trap': (5, 10),
            'experiment': (4, 8),
            'nest': (2, 5),
            'boss': (0, 2)
        }

        count_range = obstacle_counts.get(room.room_type, (0, 3))
        num_obstacles = self.rng.randint(count_range[0], count_range[1])

        for _ in range(num_obstacles):
            x = room.x + self.rng.randint(30, room.w - 30)
            y = room.y + self.rng.randint(30, room.h - 30)
            w = self.rng.randint(20, 60)
            h = self.rng.randint(20, 60)

            obstacle_type = self.rng.choice(['box', 'crate', 'barrel'])

            room.obstacles.append({
                'type': obstacle_type,
                'x': x,
                'y': y,
                'w': w,
                'h': h
            })

    # ============================================================
    # МЕТОДЫ ДЛЯ ИНТЕГРАЦИИ С ИГРОЙ
    # ============================================================

    def generate_for_game(self, game, biome: str = None, seed: int = None):
        """Генерация уровня и применение к игре"""
        if biome is None:
            biome = game.current_location if hasattr(game, 'current_location') else 'city'

        # Определение биома из локации
        if biome in LOCATIONS:
            biome = LOCATIONS[biome].get('biome', 'city')

        # Генерация комнат
        self.generate_level(seed, biome)

        # Очистка текущих объектов
        game.obstacles.clear()
        game.enemies.clear()
        game.pickups.clear()

        # Применение комнат к игре
        for room in self.rooms:
            self._apply_room_to_game(room, game)

        # Установка игрока в стартовую комнату
        start_room = self._get_start_room()
        if start_room:
            center = start_room.get_center()
            game.player.x = center[0]
            game.player.y = center[1]

        # Установка текущей комнаты
        game.current_room = start_room
        game.current_rooms = self.rooms

        return self.rooms

    def _apply_room_to_game(self, room: Room, game):
        """Применение комнаты к игре"""
        # Препятствия
        for obs_data in room.obstacles:
            obstacle = Obstacle(
                obs_data['x'], obs_data['y'],
                obs_data['w'], obs_data['h'],
                50 + game.wave * 10,
                obs_data.get('type', 'box')
            )
            game.obstacles.append(obstacle)

        # Враги
        for enemy_data in room.enemies:
            enemy = Enemy(
                enemy_data['x'], enemy_data['y'],
                game.wave,
                enemy_data.get('type', 'basic')
            )
            game.enemies.append(enemy)

        # Предметы
        for item_data in room.items:
            if item_data['type'] == 'weapon':
                pickup = Pickup(item_data['x'], item_data['y'], 'weapon_' + item_data['name'])
            elif item_data['type'] == 'consumable':
                pickup = Pickup(item_data['x'], item_data['y'], item_data['name'])
            elif item_data['type'] == 'material':
                pickup = Pickup(item_data['x'], item_data['y'], item_data['name'],
                                item_data.get('amount', 1))
            elif item_data['type'] == 'effect':
                pickup = Pickup(item_data['x'], item_data['y'], 'effect_' + item_data['name'])
            else:
                pickup = Pickup(item_data['x'], item_data['y'], 'scrap')
            game.pickups.append(pickup)

    # ============================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ С КОМНАТАМИ В ИГРЕ
    # ============================================================

    def get_room_at(self, x: float, y: float) -> Optional[Room]:
        """Получение комнаты по координатам"""
        for room in self.rooms:
            if room.contains_point(int(x), int(y)):
                return room
        return None

    def get_current_room(self, player_x: float, player_y: float) -> Optional[Room]:
        """Получение текущей комнаты игрока"""
        return self.get_room_at(player_x, player_y)

    def is_in_corridor(self, x: float, y: float) -> bool:
        """Проверка, находится ли точка в коридоре"""
        for corridor in self.corridors:
            points = corridor.get_points()
            for i in range(len(points) - 1):
                if self._point_near_line(x, y, points[i], points[i + 1], corridor.width):
                    return True
        return False

    def _point_near_line(self, x: float, y: float,
                         line_start: Tuple[int, int], line_end: Tuple[int, int],
                         threshold: float) -> bool:
        """Проверка, находится ли точка рядом с линией"""
        x1, y1 = line_start
        x2, y2 = line_end

        # Расстояние от точки до отрезка
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1) < threshold

        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))

        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        return math.hypot(x - closest_x, y - closest_y) < threshold

    # ============================================================
    # СОХРАНЕНИЕ И ЗАГРУЗКА
    # ============================================================

    def save_level(self, filename: str):
        """Сохранение уровня"""
        data = {
            'seed': self.seed,
            'width': self.width,
            'height': self.height,
            'rooms': [room.to_dict() for room in self.rooms],
            'corridors': [corridor.to_dict() for corridor in self.corridors]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_level(self, filename: str):
        """Загрузка уровня"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.seed = data.get('seed', 0)
        self.width = data.get('width', SCREEN_WIDTH)
        self.height = data.get('height', SCREEN_HEIGHT)
        self.rooms = [Room.from_dict(r) for r in data.get('rooms', [])]
        self.corridors = [Corridor.from_dict(c) for c in data.get('corridors', [])]

    # ============================================================
    # ОТРИСОВКА (ДЛЯ ОТЛАДКИ ИЛИ МИНИ-КАРТЫ)
    # ============================================================

    def draw_debug(self, screen: pygame.Surface, offset_x: int = 0, offset_y: int = 0):
        """Отрисовка отладочной информации"""
        # Отрисовка коридоров
        for corridor in self.corridors:
            points = corridor.get_points()
            for i in range(len(points) - 1):
                pygame.draw.line(screen, (60, 60, 60),
                                 (points[i][0] + offset_x, points[i][1] + offset_y),
                                 (points[i + 1][0] + offset_x, points[i + 1][1] + offset_y),
                                 corridor.width)

        # Отрисовка комнат
        for room in self.rooms:
            colors = {
                'start': GREEN,
                'normal': GRAY,
                'boss': RED,
                'treasure': YELLOW,
                'shop': BLUE,
                'trap': ORANGE,
                'secret': PURPLE,
                'experiment': MAGENTA,
                'nest': DARK_GREEN
            }
            color = colors.get(room.room_type, GRAY)

            rect = pygame.Rect(
                room.x + offset_x, room.y + offset_y,
                room.w, room.h
            )
            pygame.draw.rect(screen, color, rect, 2)

            # Отрисовка дверей
            for door_pos in room.door_positions.values():
                pygame.draw.circle(screen, WHITE,
                                   (door_pos[0] + offset_x, door_pos[1] + offset_y), 5)

    def draw_minimap(self, screen: pygame.Surface, x: int, y: int, scale: float = 0.1):
        """Отрисовка миникарты"""
        for room in self.rooms:
            colors = {
                'start': GREEN,
                'normal': GRAY,
                'boss': RED,
                'treasure': YELLOW,
                'shop': BLUE,
                'trap': ORANGE,
                'secret': PURPLE,
                'explored': LIGHT_GRAY
            }

            if room.explored:
                color = colors.get(room.room_type, LIGHT_GRAY)
            else:
                color = DARK_GRAY

            mini_x = x + int(room.x * scale)
            mini_y = y + int(room.y * scale)
            mini_w = max(1, int(room.w * scale))
            mini_h = max(1, int(room.h * scale))

            pygame.draw.rect(screen, color, (mini_x, mini_y, mini_w, mini_h))