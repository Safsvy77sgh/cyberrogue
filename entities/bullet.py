# entities/bullet.py
import math
import pygame
from typing import Tuple, List, Optional
from settings import *


class Bullet:
    def __init__(self, x: float, y: float, direction: Tuple[float, float],
                 from_player: bool, damage: int = None):
        # Позиция
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y

        # Направление и скорость
        self.vx, self.vy = direction
        speed = BULLET_SPEED if from_player else ENEMY_BULLET_SPEED
        norm = math.hypot(self.vx, self.vy)
        if norm > 0:
            self.vx = self.vx / norm * speed
            self.vy = self.vy / norm * speed

        # Свойства
        self.radius = BULLET_RADIUS
        self.from_player = from_player
        self.life = 2.0
        self.max_life = 2.0
        self.damage = damage if damage else (25 if from_player else 15)

        # Специальные свойства
        self.piercing = False
        self.explosive = False
        self.explosion_radius = 50
        self.homing = False
        self.homing_target = None
        self.homing_strength = 0.5
        self.bouncing = False
        self.bounce_count = 0
        self.max_bounces = 3

        # Визуальные эффекты
        self.trail = []
        self.max_trail = 10
        self.color = YELLOW if from_player else RED
        self.is_crit = False
        self.glow_pulse = 0

    def set_piercing(self, pierce: bool = True):
        """Установка пробивания"""
        self.piercing = pierce

    def set_explosive(self, radius: float = 50):
        """Установка взрыва"""
        self.explosive = True
        self.explosion_radius = radius

    def set_homing(self, target, strength: float = 0.5):
        """Установка самонаведения"""
        self.homing = True
        self.homing_target = target
        self.homing_strength = strength

    def set_bouncing(self, bounce: bool = True, max_bounces: int = 3):
        """Установка отскока"""
        self.bouncing = bounce
        self.max_bounces = max_bounces

    def update(self, dt: float) -> bool:
        """Обновление пули"""
        # Сохранение следа
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)

        # Самонаведение
        if self.homing and self.homing_target and self.homing_target.alive:
            target_x = self.homing_target.x
            target_y = self.homing_target.y
            dx = target_x - self.x
            dy = target_y - self.y
            norm = math.hypot(dx, dy)
            if norm > 0:
                # Поворот к цели
                self.vx += (dx / norm) * self.homing_strength * 10 * dt
                self.vy += (dy / norm) * self.homing_strength * 10 * dt

                # Нормализация скорости
                current_speed = math.hypot(self.vx, self.vy)
                max_speed = BULLET_SPEED if self.from_player else ENEMY_BULLET_SPEED
                if current_speed > max_speed:
                    self.vx = self.vx / current_speed * max_speed
                    self.vy = self.vy / current_speed * max_speed

        # Движение
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Отскок от стен
        if self.bouncing and self.bounce_count < self.max_bounces:
            bounced = False
            if self.x < self.radius or self.x > SCREEN_WIDTH - self.radius:
                self.vx = -self.vx
                bounced = True
            if self.y < self.radius or self.y > SCREEN_HEIGHT - self.radius:
                self.vy = -self.vy
                bounced = True
            if bounced:
                self.bounce_count += 1

        # Обновление свечения
        self.glow_pulse = (self.glow_pulse + dt * 5) % (2 * math.pi)

        # Время жизни
        self.life -= dt
        if self.life <= 0:
            return False

        # Проверка выхода за экран
        if (self.x < -100 or self.x > SCREEN_WIDTH + 100 or
                self.y < -100 or self.y > SCREEN_HEIGHT + 100):
            return False

        return True

    def draw(self, screen: pygame.Surface):
        """Отрисовка пули"""
        # Отрисовка следа
        if len(self.trail) > 2:
            for i in range(len(self.trail) - 1):
                alpha = int(255 * (i / len(self.trail)))
                trail_color = (self.color[0], self.color[1], self.color[2], alpha)
                pygame.draw.line(screen, trail_color,
                                 self.trail[i], self.trail[i + 1], 2)

        # Свечение
        glow_radius = self.radius + 2 + math.sin(self.glow_pulse) * 2
        glow_surf = pygame.Surface((glow_radius * 4, glow_radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color, 100),
                           (glow_radius * 2, glow_radius * 2), glow_radius)
        screen.blit(glow_surf, (self.x - glow_radius * 2, self.y - glow_radius * 2))

        # Основной круг
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

        # Обводка для критов
        if self.is_crit:
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)),
                               self.radius + 2, 2)

        # Индикатор взрывных пуль
        if self.explosive:
            pygame.draw.circle(screen, ORANGE, (int(self.x), int(self.y)),
                               self.radius + 3, 1)

    def get_explosion(self) -> Tuple[float, float, float]:
        """Получение данных взрыва"""
        if self.explosive:
            return (self.x, self.y, self.explosion_radius)
        return None