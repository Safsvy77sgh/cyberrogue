# entities/obstacle.py
import pygame
import random
import math
from typing import Tuple, List, Optional
from settings import *


class Obstacle:
    def __init__(self, x: float, y: float, w: float, h: float, hp: int = 50,
                 type_: str = 'box', destructible: bool = True):
        self.rect = pygame.Rect(x, y, w, h)
        self.hp = hp
        self.max_hp = hp
        self.alive = True
        self.type = type_
        self.destructible = destructible
        self.break_progress = 0.0
        self.cracks = []

        # Визуальные эффекты
        self.hit_flash = 0.0
        self.shake_timer = 0.0
        self.shake_offset = [0, 0]

        # Генерация трещин
        if destructible:
            for _ in range(random.randint(3, 8)):
                self.cracks.append({
                    'start': (random.randint(0, int(w)), random.randint(0, int(h))),
                    'end': (random.randint(0, int(w)), random.randint(0, int(h))),
                    'width': random.randint(1, 3)
                })

    def take_damage(self, damage: int) -> bool:
        """Получение урона"""
        if not self.destructible:
            return False

        self.hp -= damage
        self.break_progress = 1 - (self.hp / self.max_hp)
        self.hit_flash = 1.0
        self.shake_timer = 0.1

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def update(self, dt: float):
        """Обновление препятствия"""
        self.hit_flash = max(0, self.hit_flash - dt * 5)
        self.shake_timer = max(0, self.shake_timer - dt)

        if self.shake_timer > 0:
            self.shake_offset = [
                random.randint(-3, 3),
                random.randint(-3, 3)
            ]
        else:
            self.shake_offset = [0, 0]

    def draw(self, screen: pygame.Surface):
        """Отрисовка препятствия"""
        if not self.alive:
            return

        # Смещение для тряски
        draw_x = self.rect.x + self.shake_offset[0]
        draw_y = self.rect.y + self.shake_offset[1]
        draw_rect = pygame.Rect(draw_x, draw_y, self.rect.width, self.rect.height)

        # Цвет в зависимости от здоровья
        health_ratio = self.hp / self.max_hp

        if self.hit_flash > 0:
            # Белая вспышка при попадании
            base_color = WHITE
        else:
            base_color = self._get_color(health_ratio)

        # Отрисовка в зависимости от типа
        if self.type == 'box':
            pygame.draw.rect(screen, base_color, draw_rect)
            pygame.draw.rect(screen, WHITE, draw_rect, 2)
        elif self.type == 'barrel':
            pygame.draw.rect(screen, base_color, draw_rect, border_radius=10)
            pygame.draw.rect(screen, RED, draw_rect, 2, border_radius=10)
            # Полосы на бочке
            pygame.draw.line(screen, RED, draw_rect.midtop, draw_rect.midbottom, 3)
        elif self.type == 'crate':
            pygame.draw.rect(screen, base_color, draw_rect)
            pygame.draw.line(screen, BLACK, draw_rect.topleft, draw_rect.bottomright, 2)
            pygame.draw.line(screen, BLACK, draw_rect.topright, draw_rect.bottomleft, 2)
            pygame.draw.rect(screen, BLACK, draw_rect, 3)
        elif self.type == 'wall':
            pygame.draw.rect(screen, base_color, draw_rect)
            pygame.draw.rect(screen, GRAY, draw_rect, 2)
            # Кирпичная кладка
            brick_height = 20
            for y in range(int(draw_rect.top), int(draw_rect.bottom), brick_height):
                pygame.draw.line(screen, GRAY, (draw_rect.left, y), (draw_rect.right, y), 1)
                offset = 20 if (y // brick_height) % 2 == 0 else 0
                for x in range(int(draw_rect.left) + offset, int(draw_rect.right), 40):
                    pygame.draw.line(screen, GRAY, (x, y), (x, min(y + brick_height, draw_rect.bottom)), 1)

        # Отрисовка трещин при повреждении
        if self.destructible and self.break_progress > 0.3:
            for crack in self.cracks:
                start_x = draw_x + crack['start'][0]
                start_y = draw_y + crack['start'][1]
                end_x = draw_x + crack['end'][0]
                end_y = draw_y + crack['end'][1]

                if self.break_progress > 0.7:
                    pygame.draw.line(screen, BLACK, (start_x, start_y), (end_x, end_y),
                                     crack['width'] + 2)
                else:
                    pygame.draw.line(screen, BLACK, (start_x, start_y), (end_x, end_y),
                                     crack['width'])

    def _get_color(self, health_ratio: float) -> Tuple[int, int, int]:
        """Получение цвета в зависимости от типа и здоровья"""
        if self.type == 'box':
            return (int(150 * health_ratio), int(150 * health_ratio), int(150 * health_ratio))
        elif self.type == 'barrel':
            return (int(200 * health_ratio), int(100 * health_ratio), 0)
        elif self.type == 'crate':
            return (int(139 * health_ratio), int(69 * health_ratio), int(19 * health_ratio))
        elif self.type == 'wall':
            return (int(100 * health_ratio), int(100 * health_ratio), int(120 * health_ratio))
        else:
            return (150, 150, 150)

    def get_center(self) -> Tuple[float, float]:
        """Получение центра препятствия"""
        return self.rect.center

    def get_loot(self) -> List[dict]:
        """Получение лута при разрушении"""
        loot = []

        if self.type == 'barrel':
            # Бочки взрываются
            if random.random() < 0.5:
                loot.append({'type': 'scrap', 'amount': random.randint(2, 5)})
        elif self.type == 'crate':
            # Ящики дают ресурсы
            if random.random() < 0.7:
                loot.append({'type': 'scrap', 'amount': random.randint(3, 8)})
            if random.random() < 0.3:
                loot.append({'type': 'circuit', 'amount': 1})
        elif self.type == 'box':
            # Обычные коробки
            if random.random() < 0.3:
                loot.append({'type': 'scrap', 'amount': random.randint(1, 3)})

        # Шанс на аптечку
        if random.random() < 0.05:
            loot.append({'type': 'repair', 'amount': 1})

        return loot

    def is_explosive(self) -> bool:
        """Проверка на взрывоопасность"""
        return self.type == 'barrel'