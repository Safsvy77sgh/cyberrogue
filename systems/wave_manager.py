# systems/wave_manager.py
"""Система этажей и комнат в стиле Binding of Isaac.

Заменяет старую волновую систему (WaveManager). Комнаты хранятся как
СЛОВАРИ, чтобы избежать ошибок доступа по ключу и несовпадения типов.
"""

import random
import pygame
from typing import Dict, List, Optional, Tuple

from settings import *

# Специальные типы комнат (кроме старта и босса)
ROOM_TYPES_SPECIAL = [
    'treasure', 'shop', 'trap', 'secret', 'curse', 'sacrifice',
    'miniboss', 'arcade', 'library', 'chest', 'blood'
]

DIRECTION_OFFSETS = {
    'up': (0, -1),
    'down': (0, 1),
    'left': (-1, 0),
    'right': (1, 0),
}
OPPOSITE_DIRECTION = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}

# Границы игровой зоны внутри комнаты
ROOM_MARGIN_X = 60
ROOM_MARGIN_TOP = 90
ROOM_MARGIN_BOTTOM = 70


class RoomManager:
    """Управляет генерацией этажей, комнат и переходами между ними."""

    def __init__(self, game):
        self.game = game
        self.floor = 1
        self.difficulty_multiplier = 1.0

        # Все комнаты текущего этажа: {(gx, gy): room_dict}
        self.rooms: Dict[Tuple[int, int], Dict] = {}
        self.current_pos: Tuple[int, int] = (0, 0)

        self.cleared_rooms = 0
        self.total_rooms = 0

        self.pending_transition: Optional[str] = None
        self.room_transition_cooldown = 0.0

        # Фиксированные пиксельные границы игровой зоны
        self.room_x = ROOM_MARGIN_X
        self.room_y = ROOM_MARGIN_TOP
        self.room_w = max(200, SCREEN_WIDTH - ROOM_MARGIN_X * 2)
        self.room_h = max(200, SCREEN_HEIGHT - ROOM_MARGIN_TOP - ROOM_MARGIN_BOTTOM)

        self.generate_floor()

    # ------------------------------------------------------------------
    # Генерация этажа
    # ------------------------------------------------------------------
    def reset(self):
        """Полный сброс менеджера (для новой игры)."""
        self.floor = 1
        self.difficulty_multiplier = 1.0
        self.generate_floor()

    def generate_floor(self):
        """Генерирует связный граф из 8-12 обычных комнат + 1 комната босса."""
        self.rooms.clear()
        self.current_pos = (0, 0)
        self.cleared_rooms = 0
        self.pending_transition = None

        target_rooms = random.randint(8, 12)
        self.rooms[(0, 0)] = self._make_room_dict((0, 0), 'start')
        positions = [(0, 0)]
        frontier = [(0, 0)]

        attempts = 0
        max_attempts = target_rooms * 40
        while len(positions) < target_rooms and attempts < max_attempts:
            attempts += 1
            base = random.choice(frontier)
            direction = random.choice(list(DIRECTION_OFFSETS.keys()))
            dx, dy = DIRECTION_OFFSETS[direction]
            new_pos = (base[0] + dx, base[1] + dy)

            if new_pos in self.rooms:
                continue
            if abs(new_pos[0]) > 4 or abs(new_pos[1]) > 4:
                continue

            self.rooms[new_pos] = self._make_room_dict(new_pos, 'normal')
            positions.append(new_pos)
            frontier.append(new_pos)

        # Комната босса — самая дальняя от старта
        boss_pos = max(positions, key=lambda p: abs(p[0]) + abs(p[1]))
        if boss_pos == (0, 0) and len(positions) > 1:
            boss_pos = positions[-1]
        self.rooms[boss_pos]['type'] = 'boss'

        # Раздаём специальные типы комнатам (кроме старта и босса)
        available = [p for p in positions if p not in ((0, 0), boss_pos)]
        random.shuffle(available)
        num_special = min(len(available), random.randint(3, 6))
        chosen_types = random.sample(
            ROOM_TYPES_SPECIAL, k=min(num_special, len(ROOM_TYPES_SPECIAL))
        )
        while len(chosen_types) < num_special:
            chosen_types.append(random.choice(ROOM_TYPES_SPECIAL))
        for pos, room_type in zip(available[:num_special], chosen_types):
            self.rooms[pos]['type'] = room_type

        # Простановка дверей на основе смежности
        for pos, room in self.rooms.items():
            for direction, (dx, dy) in DIRECTION_OFFSETS.items():
                neighbor = (pos[0] + dx, pos[1] + dy)
                room['doors'][direction] = neighbor in self.rooms

        self.total_rooms = sum(
            1 for r in self.rooms.values() if r['type'] not in ('start', 'shop')
        )

    def _make_room_dict(self, grid_pos: Tuple[int, int], room_type: str) -> Dict:
        return {
            'grid_pos': grid_pos,
            'x': self.room_x,
            'y': self.room_y,
            'width': self.room_w,
            'height': self.room_h,
            'center': (self.room_x + self.room_w / 2, self.room_y + self.room_h / 2),
            'type': room_type,
            'cleared': room_type in ('start', 'shop'),
            'visited': room_type == 'start',
            'populated': False,
            'doors': {'up': False, 'down': False, 'left': False, 'right': False},
        }

    # ------------------------------------------------------------------
    # Доступ к текущей комнате
    # ------------------------------------------------------------------
    def get_current_room(self) -> Optional[Dict]:
        return self.rooms.get(self.current_pos)

    def mark_current_cleared(self):
        room = self.get_current_room()
        if room and not room['cleared']:
            room['cleared'] = True
            self.cleared_rooms += 1

    def is_floor_cleared(self) -> bool:
        boss_rooms = [r for r in self.rooms.values() if r['type'] == 'boss']
        return all(r['cleared'] for r in boss_rooms) if boss_rooms else False

    # ------------------------------------------------------------------
    # Переходы между комнатами
    # ------------------------------------------------------------------
    def try_transition(self, direction: str) -> bool:
        """Пытается перейти в соседнюю комнату. Возвращает True при успехе."""
        room = self.get_current_room()
        if not room:
            return False
        if not room['doors'].get(direction):
            return False
        if not room['cleared']:
            return False

        dx, dy = DIRECTION_OFFSETS[direction]
        new_pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
        if new_pos not in self.rooms:
            return False

        self.current_pos = new_pos
        entered = self.rooms[new_pos]
        entered['visited'] = True
        self.pending_transition = OPPOSITE_DIRECTION[direction]
        return True

    def get_entry_position(self) -> Tuple[float, float]:
        """Позиция игрока при входе в комнату."""
        room = self.get_current_room()
        if not room:
            return SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        if not self.pending_transition:
            return room['center']

        margin = 60
        direction = self.pending_transition
        cx, cy = room['center']
        if direction == 'up':
            pos = (cx, room['y'] + margin)
        elif direction == 'down':
            pos = (cx, room['y'] + room['height'] - margin)
        elif direction == 'left':
            pos = (room['x'] + margin, cy)
        elif direction == 'right':
            pos = (room['x'] + room['width'] - margin, cy)
        else:
            pos = room['center']
        self.pending_transition = None
        return pos

    def get_door_rects(self) -> Dict[str, pygame.Rect]:
        room = self.get_current_room()
        rects: Dict[str, pygame.Rect] = {}
        if not room:
            return rects
        size = 60
        thickness = 26
        if room['doors'].get('up'):
            rects['up'] = pygame.Rect(int(room['center'][0] - size / 2), int(room['y'] - thickness / 2), size, thickness)
        if room['doors'].get('down'):
            rects['down'] = pygame.Rect(int(room['center'][0] - size / 2), int(room['y'] + room['height'] - thickness / 2), size, thickness)
        if room['doors'].get('left'):
            rects['left'] = pygame.Rect(int(room['x'] - thickness / 2), int(room['center'][1] - size / 2), thickness, size)
        if room['doors'].get('right'):
            rects['right'] = pygame.Rect(int(room['x'] + room['width'] - thickness / 2), int(room['center'][1] - size / 2), thickness, size)
        return rects

    # ------------------------------------------------------------------
    # Прогресс этажа
    # ------------------------------------------------------------------
    def advance_floor(self, game):
        """Переход на следующий этаж: лечение, рост сложности, новая карта."""
        self.floor += 1
        self.difficulty_multiplier = round(self.difficulty_multiplier * 1.2, 3)
        game.player.heal(30)
        self.generate_floor()
        game.ui.show_notification(f"Этаж {self.floor}! Сложность возросла.", CYAN, 3.0)

    def get_effective_wave(self) -> int:
        """Значение сложности, совместимое со старым параметром 'wave'."""
        return max(1, int(self.floor * self.difficulty_multiplier) + self.cleared_rooms // 3)

    def update(self, dt: float, game=None):
        if self.room_transition_cooldown > 0:
            self.room_transition_cooldown -= dt