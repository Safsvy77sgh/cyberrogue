# systems/coop.py
import pygame
import math
from typing import List, Dict, Optional
from settings import *


class CoopPlayer:
    """Кооперативный игрок"""

    def __init__(self, x: float, y: float, player_id: int):
        self.x = x
        self.y = y
        self.player_id = player_id
        self.hp = 100
        self.max_hp = 100
        self.radius = 18
        self.alive = True
        self.color = self._get_color(player_id)
        self.damage_multiplier = 1.0

    def _get_color(self, player_id: int):
        """Получение цвета игрока"""
        colors = [BLUE, GREEN, ORANGE, PURPLE]
        return colors[player_id % len(colors)]

    def update(self, dt: float, keys, game):
        """Обновление игрока"""
        if not self.alive:
            return

        # Управление в зависимости от ID игрока
        if self.player_id == 1:
            # WASD
            dx = 0
            dy = 0
            if keys[pygame.K_w]:
                dy -= 1
            if keys[pygame.K_s]:
                dy += 1
            if keys[pygame.K_a]:
                dx -= 1
            if keys[pygame.K_d]:
                dx += 1
        else:
            # Стрелки
            dx = 0
            dy = 0
            if keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_DOWN]:
                dy += 1
            if keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_RIGHT]:
                dx += 1

        if dx != 0 or dy != 0:
            norm = math.hypot(dx, dy)
            self.x += (dx / norm) * PLAYER_SPEED * dt
            self.y += (dy / norm) * PLAYER_SPEED * dt

    def take_damage(self, damage: int):
        """Получение урона"""
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def draw(self, screen: pygame.Surface):
        """Отрисовка игрока"""
        if not self.alive:
            return

        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)


class CoopSystem:
    """Система кооператива"""

    def __init__(self, game):
        self.game = game
        self.players = []
        self.max_players = 4
        self.coop_active = False

    def add_player(self, x: float, y: float) -> bool:
        """Добавление игрока"""
        if len(self.players) >= self.max_players:
            return False

        player_id = len(self.players) + 1
        player = CoopPlayer(x, y, player_id)
        self.players.append(player)
        self.coop_active = True
        return True

    def update(self, dt: float, keys):
        """Обновление всех игроков"""
        for player in self.players:
            player.update(dt, keys, self.game)

    def draw(self, screen: pygame.Surface):
        """Отрисовка всех игроков"""
        for player in self.players:
            player.draw(screen)

    def check_all_dead(self) -> bool:
        """Проверка, все ли игроки мертвы"""
        return all(not player.alive for player in self.players) if self.players else True

    def revive_player(self, player: CoopPlayer):
        """Возрождение игрока"""
        player.hp = player.max_hp
        player.alive = True
        player.x = self.game.player.x
        player.y = self.game.player.y