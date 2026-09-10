# entities/pickup.py
import pygame
import random
import math
from typing import Tuple, Optional
from settings import *


class Pickup:
    def __init__(self, x: float, y: float, type_: str, amount: int = 1):
        self.x = x
        self.y = y
        self.type = type_
        self.amount = amount
        self.radius = 12
        self.life = 15.0
        self.bob_offset = random.uniform(0, 2 * math.pi)
        self.bob_speed = 3.0
        self.glow_pulse = 0
        self.magnet_radius = 50  # Радиус притяжения к игроку

    def update(self, dt: float, player_pos: Tuple[float, float]) -> bool:
        """Обновление пикапа"""
        self.life -= dt
        self.bob_offset += dt * self.bob_speed
        self.glow_pulse = (self.glow_pulse + dt * 2) % (2 * math.pi)

        if self.life <= 0:
            return False

        # Магнитное притяжение к игроку
        dist = math.hypot(self.x - player_pos[0], self.y - player_pos[1])
        if dist < self.magnet_radius:
            # Притяжение
            dx = player_pos[0] - self.x
            dy = player_pos[1] - self.y
            norm = math.hypot(dx, dy)
            if norm > 0:
                magnet_strength = 200 * (1 - dist / self.magnet_radius)
                self.x += (dx / norm) * magnet_strength * dt
                self.y += (dy / norm) * magnet_strength * dt

        # Проверка сбора
        if dist < self.radius + PLAYER_RADIUS:
            return False  # Collected

        return True

    def apply_effect(self, game):
        """Применение эффекта пикапа"""
        player = game.player

        if self.type == 'fire_rate':
            player.fire_rate = max(0.15, player.fire_rate - 0.03 * self.amount)
        elif self.type == 'shield':
            player.shield_timer = 3.0 * self.amount
        elif self.type == 'speed':
            player.speed_boost_timer = 3.0 * self.amount
        elif self.type == 'repair':
            player.heal(REPAIR_AMOUNT * self.amount)
        elif self.type == 'energy':
            player.energy = min(PLAYER_MAX_ENERGY, player.energy + 15 * self.amount)
        elif self.type == 'scrap':
            player.scrap += self.amount
        elif self.type == 'circuit':
            player.circuits += self.amount
        elif self.type == 'credits':
            player.credits += self.amount * 10
        elif self.type == 'weapon_shotgun':
            player.add_weapon('shotgun')
            player.current_weapon = 'shotgun'
        elif self.type == 'weapon_laser':
            player.add_weapon('laser')
            player.current_weapon = 'laser'
        elif self.type == 'exp':
            player.add_exp(self.amount * 10)

    def draw(self, screen: pygame.Surface):
        """Отрисовка пикапа"""
        # Покачивание
        bob_y = math.sin(self.bob_offset) * 5

        # Цвет пикапа
        color = self._get_color()

        # Свечение
        glow_alpha = int(100 + 100 * math.sin(self.glow_pulse))
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, glow_alpha),
                           (self.radius * 2, self.radius * 2), self.radius * 2)
        screen.blit(glow_surf, (self.x - self.radius * 2, self.y + bob_y - self.radius * 2))

        # Основной круг
        pygame.draw.circle(screen, color, (int(self.x), int(self.y + bob_y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y + bob_y)), self.radius, 2)

        # Иконка
        self._draw_icon(screen, color, bob_y)

        # Количество (если больше 1)
        if self.amount > 1:
            font = pygame.font.Font(None, 16)
            amount_text = font.render(str(self.amount), True, WHITE)
            screen.blit(amount_text, (self.x - amount_text.get_width() // 2,
                                      self.y + bob_y - amount_text.get_height() // 2))

    def _get_color(self) -> Tuple[int, int, int]:
        """Получение цвета пикапа"""
        colors = {
            'fire_rate': ORANGE,
            'shield': CYAN,
            'speed': YELLOW,
            'repair': GREEN,
            'energy': BLUE,
            'scrap': GRAY,
            'circuit': PURPLE,
            'credits': YELLOW,
            'weapon_shotgun': RED,
            'weapon_laser': MAGENTA,
            'exp': CYAN
        }
        return colors.get(self.type, WHITE)

    def _draw_icon(self, screen: pygame.Surface, color: Tuple[int, int, int], bob_y: float):
        """Отрисовка иконки пикапа"""
        icon_x = int(self.x)
        icon_y = int(self.y + bob_y)

        if self.type == 'fire_rate':
            pygame.draw.line(screen, WHITE, (icon_x - 5, icon_y), (icon_x + 5, icon_y), 3)
        elif self.type == 'shield':
            pygame.draw.arc(screen, WHITE, (icon_x - 5, icon_y - 5, 10, 10), 0, math.pi, 3)
        elif self.type == 'repair':
            pygame.draw.circle(screen, WHITE, (icon_x, icon_y), 3)
            pygame.draw.line(screen, WHITE, (icon_x, icon_y - 3), (icon_x, icon_y + 3), 2)
            pygame.draw.line(screen, WHITE, (icon_x - 3, icon_y), (icon_x + 3, icon_y), 2)
        elif self.type == 'energy':
            pygame.draw.polygon(screen, WHITE, [
                (icon_x, icon_y - 5),
                (icon_x + 4, icon_y),
                (icon_x, icon_y + 5),
                (icon_x - 4, icon_y)
            ])
        elif self.type == 'weapon_shotgun':
            pygame.draw.rect(screen, WHITE, (icon_x - 6, icon_y - 1, 12, 3))
            pygame.draw.rect(screen, WHITE, (icon_x - 2, icon_y - 4, 4, 8))
        elif self.type == 'weapon_laser':
            pygame.draw.line(screen, WHITE, (icon_x - 5, icon_y), (icon_x + 5, icon_y), 4)