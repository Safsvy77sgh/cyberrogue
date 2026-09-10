# entities/wall.py
import pygame
import math
import random
from typing import List
from settings import *


class EnergyWall:
    def __init__(self, x: float, y: float, radius: float = WALL_RADIUS,
                 duration: float = WALL_DURATION):
        # Позиция и размер
        self.x = x
        self.y = y
        self.radius = radius
        self.duration = duration
        self.life = duration
        self.active = True

        # Визуальные эффекты
        self.pulse_alpha = 0
        self.pulse_speed = 2.0
        self.rotation = 0
        self.rotation_speed = 30  # градусов в секунду

        # Боевые свойства
        self.damage = 5
        self.damage_cooldown = 0.5
        self.current_cooldown = 0
        self.push_strength = 200

        # Энергетические точки
        self.energy_points = []
        for i in range(6):
            angle = i * math.pi / 3
            self.energy_points.append({
                'angle': angle,
                'distance': self.radius * 0.8,
                'size': 3
            })

    def update(self, dt: float, enemies: list) -> bool:
        """Обновление стены"""
        self.life -= dt
        self.pulse_alpha += dt * self.pulse_speed
        self.rotation += self.rotation_speed * dt
        self.current_cooldown = max(0, self.current_cooldown - dt)

        if self.life <= 0:
            self.active = False
            return False

        # Отталкивание и урон врагам
        for enemy in enemies:
            if enemy.alive:
                dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if dist < self.radius + enemy.radius:
                    # Отталкивание
                    angle = math.atan2(enemy.y - self.y, enemy.x - self.x)
                    push = (self.radius + enemy.radius - dist) * 0.5
                    enemy.x += math.cos(angle) * push
                    enemy.y += math.sin(angle) * push

                    # Дополнительное отталкивание
                    push_force = self.push_strength * dt
                    enemy.x += math.cos(angle) * push_force
                    enemy.y += math.sin(angle) * push_force

                    # Урон
                    if self.current_cooldown <= 0:
                        enemy.take_damage(self.damage)
                        self.current_cooldown = self.damage_cooldown

        # Обновление энергетических точек
        for point in self.energy_points:
            point['angle'] += dt * self.rotation_speed * 0.5

        return True

    def draw(self, screen: pygame.Surface):
        """Отрисовка стены"""
        if not self.active:
            return

        # Пульсирующее свечение
        pulse = int(100 + 50 * math.sin(self.pulse_alpha))
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (150, 0, 200, pulse),
                           (self.radius * 2, self.radius * 2), self.radius * 2)
        screen.blit(glow_surf, (self.x - self.radius * 2, self.y - self.radius * 2))

        # Основной круг
        pygame.draw.circle(screen, PURPLE, (int(self.x), int(self.y)), self.radius, 3)

        # Вращающийся шестиугольник
        points = []
        for i in range(6):
            angle = self.rotation * math.pi / 180 + i * math.pi / 3
            x = self.x + math.cos(angle) * self.radius * 0.8
            y = self.y + math.sin(angle) * self.radius * 0.8
            points.append((x, y))

        pygame.draw.polygon(screen, PURPLE, points, 2)

        # Энергетические точки
        for point in self.energy_points:
            x = self.x + math.cos(point['angle']) * point['distance']
            y = self.y + math.sin(point['angle']) * point['distance']
            pygame.draw.circle(screen, CYAN, (int(x), int(y)), point['size'])

        # Индикатор жизни
        life_ratio = self.life / self.duration
        bar_width = 40
        bar_height = 5
        bar_x = self.x - bar_width / 2
        bar_y = self.y - self.radius - 15

        pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, PURPLE, (bar_x, bar_y, bar_width * life_ratio, bar_height))

    def is_point_inside(self, x: float, y: float) -> bool:
        """Проверка, находится ли точка внутри стены"""
        dist = math.hypot(x - self.x, y - self.y)
        return dist < self.radius