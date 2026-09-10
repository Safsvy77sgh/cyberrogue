# systems/time_system.py
import math
import pygame
from typing import Tuple
from settings import *


class TimeSystem:
    """Система времени суток"""

    def __init__(self):
        self.time_of_day = 0.0  # 0.0 = полночь, 0.5 = полдень, 1.0 = полночь
        self.day_length = 300.0  # 5 минут реального времени = 1 игровой день
        self.day = 1
        self.time_scale = 1.0

        # Модификаторы времени суток
        self.modifiers = {
            'dawn': {'enemy_spawn_rate': 0.7, 'visibility': 0.8, 'special_enemies': False},
            'day': {'enemy_spawn_rate': 1.0, 'visibility': 1.0, 'special_enemies': False},
            'dusk': {'enemy_spawn_rate': 1.2, 'visibility': 0.8, 'special_enemies': True},
            'night': {'enemy_spawn_rate': 1.5, 'visibility': 0.4, 'special_enemies': True}
        }

    def update(self, dt: float):
        """Обновление времени"""
        self.time_of_day = (self.time_of_day + dt * self.time_scale / self.day_length) % 1.0

        # Новый день
        if self.time_of_day < dt * self.time_scale / self.day_length:
            self.day += 1

    def get_period(self) -> str:
        """Получение текущего периода"""
        if 0.05 < self.time_of_day < 0.25:
            return 'dawn'
        elif 0.25 < self.time_of_day < 0.75:
            return 'day'
        elif 0.75 < self.time_of_day < 0.95:
            return 'dusk'
        else:
            return 'night'

    def get_modifiers(self) -> dict:
        """Получение модификаторов текущего периода"""
        return self.modifiers.get(self.get_period(), self.modifiers['day'])

    def get_light_level(self) -> float:
        """Получение уровня освещения"""
        period = self.get_period()
        if period == 'day':
            return 1.0
        elif period == 'dawn':
            return 0.6 + 0.4 * (self.time_of_day - 0.05) / 0.2
        elif period == 'dusk':
            return 0.6 - 0.4 * (self.time_of_day - 0.75) / 0.2
        else:
            return 0.2

    def draw_overlay(self, screen: pygame.Surface):
        """Отрисовка оверлея времени суток"""
        light = self.get_light_level()

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        if light < 1.0:
            darkness = int((1.0 - light) * 150)
            overlay.fill((0, 0, 30, darkness))

        # Оранжевый оттенок на закате/рассвете
        period = self.get_period()
        if period in ['dawn', 'dusk']:
            orange_alpha = int(30 * (1.0 - abs(light - 0.8) * 5))
            orange_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            orange_overlay.fill((255, 100, 0, orange_alpha))
            screen.blit(orange_overlay, (0, 0))

        screen.blit(overlay, (0, 0))