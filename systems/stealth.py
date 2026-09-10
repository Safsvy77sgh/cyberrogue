# systems/stealth.py
import math
import random
import pygame
from typing import List, Tuple, Optional
from settings import *


class StealthSystem:
    """Система скрытности"""

    def __init__(self, game):
        self.game = game
        self.visibility = 1.0  # 1.0 = полностью видим, 0.0 = невидим
        self.noise_level = 0.0
        self.last_noise_position = (0, 0)
        self.detection_radius = 300
        self.stealth_kill_bonus = 2.0  # множитель урона при скрытой атаке

    def update(self, dt: float):
        """Обновление стелс-системы"""
        player = self.game.player

        # Базовые модификаторы видимости
        self.visibility = 1.0

        # Скрытность за укрытиями
        if self._is_behind_cover(player):
            self.visibility *= 0.3

        # Невидимость от эффектов
        if hasattr(player, 'invisible') and player.invisible:
            self.visibility = 0.0

        # Скрытность при неподвижности
        if abs(player.vx) < 10 and abs(player.vy) < 10:
            self.visibility *= 0.7

        # Шум от движения
        speed = math.hypot(player.vx, player.vy)
        self.noise_level = min(1.0, speed / PLAYER_SPEED)

        # Обновление ИИ врагов на основе видимости
        self._update_enemy_detection(dt)

    def _is_behind_cover(self, player) -> bool:
        """Проверка, находится ли игрок за укрытием"""
        for obstacle in self.game.obstacles:
            if obstacle.alive:
                # Проверка, что препятствие между игроком и ближайшим врагом
                for enemy in self.game.enemies:
                    if enemy.alive:
                        if self._line_intersects_rect(
                                (player.x, player.y),
                                (enemy.x, enemy.y),
                                obstacle.rect
                        ):
                            return True
        return False

    def _line_intersects_rect(self, line_start: Tuple, line_end: Tuple, rect: pygame.Rect) -> bool:
        """Проверка пересечения линии с прямоугольником"""
        # Простая проверка: любая точка линии внутри прямоугольника
        steps = 10
        for i in range(steps + 1):
            t = i / steps
            x = line_start[0] + (line_end[0] - line_start[0]) * t
            y = line_start[1] + (line_end[1] - line_start[1]) * t
            if rect.collidepoint(x, y):
                return True
        return False

    def _update_enemy_detection(self, dt: float):
        """Обновление обнаружения врагами"""
        for enemy in self.game.enemies:
            if not enemy.alive:
                continue

            # Пропускаем миньонов и других объектов без state
            if not hasattr(enemy, 'state'):
                continue

            dist = math.hypot(enemy.x - self.game.player.x,
                              enemy.y - self.game.player.y)

            # Радиус обнаружения зависит от видимости и шума
            effective_radius = self.detection_radius * (self.visibility * 0.7 + self.noise_level * 0.3)

            if dist < effective_radius:
                enemy.state = 'chase'
                enemy.state_timer = 3.0
                enemy.last_known_player_position = (self.game.player.x, self.game.player.y)
            elif dist < effective_radius * 1.5 and enemy.state == 'chase':
                # Враг идёт к последней известной позиции
                pass

    def get_stealth_damage_multiplier(self) -> float:
        """Получение множителя урона от скрытности"""
        if self.visibility < 0.3:
            return self.stealth_kill_bonus
        return 1.0

    def draw_debug(self, screen: pygame.Surface):
        """Отрисовка отладочной информации"""
        if hasattr(self.game, 'debug_mode') and self.game.debug_mode:
            font = pygame.font.Font(None, 24)
            visibility_text = font.render(f"Видимость: {self.visibility:.2f}", True, CYAN)
            noise_text = font.render(f"Шум: {self.noise_level:.2f}", True, YELLOW)
            screen.blit(visibility_text, (10, 300))
            screen.blit(noise_text, (10, 330))