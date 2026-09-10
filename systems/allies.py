# systems/allies.py
import math
import random
import pygame
from typing import List, Tuple, Optional
from settings import *


class Ally:
    """Союзник (дрон или NPC)"""

    def __init__(self, x: float, y: float, ally_type: str):
        self.x = x
        self.y = y
        self.type = ally_type
        self.hp = 50
        self.max_hp = 50
        self.damage = 10
        self.fire_rate = 1.0
        self.fire_cooldown = 0
        self.radius = 15
        self.alive = True
        self.level = 1

        # Типы союзников
        if ally_type == 'drone':
            self.damage = 15
            self.fire_rate = 0.8
            self.speed = 200
            self.follow_distance = 150
        elif ally_type == 'sniper':
            self.damage = 50
            self.fire_rate = 2.5
            self.speed = 150
            self.follow_distance = 250
            self.range = 600
        elif ally_type == 'engineer':
            self.damage = 10
            self.fire_rate = 1.5
            self.speed = 150
            self.follow_distance = 100
            self.heal_power = 10
            self.repair_power = 20

        self.max_hp = self.hp

    def update(self, dt: float, game):
        """Обновление союзника"""
        if not self.alive:
            return

        self.fire_cooldown = max(0, self.fire_cooldown - dt)

        # Следование за игроком
        target_x = game.player.x + random.randint(-50, 50)
        target_y = game.player.y + random.randint(-50, 50)

        dist = math.hypot(target_x - self.x, target_y - self.y)
        if dist > self.follow_distance:
            dx = (target_x - self.x) / dist
            dy = (target_y - self.y) / dist
            self.x += dx * self.speed * dt
            self.y += dy * self.speed * dt

        # Атака врагов
        nearest_enemy = self._find_nearest_enemy(game.enemies)
        if nearest_enemy:
            dist_to_enemy = math.hypot(nearest_enemy.x - self.x, nearest_enemy.y - self.y)

            if self.type == 'sniper':
                attack_range = self.range
            else:
                attack_range = 300

            if dist_to_enemy < attack_range and self.fire_cooldown <= 0:
                self._attack(nearest_enemy, game)
                self.fire_cooldown = self.fire_rate

        # Инженер лечит игрока
        if self.type == 'engineer':
            dist_to_player = math.hypot(game.player.x - self.x, game.player.y - self.y)
            if dist_to_player < 200:
                game.player.heal(int(self.heal_power * dt))

    def _find_nearest_enemy(self, enemies: List) -> Optional[object]:
        """Поиск ближайшего врага"""
        closest = None
        closest_dist = 1000000

        for enemy in enemies:
            if enemy.alive:
                dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if dist < closest_dist:
                    closest_dist = dist
                    closest = enemy

        return closest

    def _attack(self, target, game):
        """Атака цели"""
        target.take_damage(self.damage)
        game.add_damage_number(target.x, target.y - target.radius, self.damage, CYAN)

        # Эффект выстрела
        if self.type == 'drone':
            game.spawn_sparks(self.x, self.y, 3)
        elif self.type == 'sniper':
            # Лазерный луч
            game.lightning_effects.append({
                'start': (self.x, self.y),
                'end': (target.x, target.y),
                'life': 0.1,
                'color': RED
            })

    def take_damage(self, damage: int) -> bool:
        """Получение урона"""
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def upgrade(self):
        """Улучшение союзника"""
        self.level += 1
        self.damage += 5
        self.max_hp += 25
        self.hp = self.max_hp
        self.fire_rate *= 0.9

    def draw(self, screen: pygame.Surface):
        """Отрисовка союзника"""
        if not self.alive:
            return

        colors = {
            'drone': CYAN,
            'sniper': RED,
            'engineer': GREEN
        }
        color = colors.get(self.type, WHITE)

        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)

        # Полоска HP
        if self.hp < self.max_hp:
            bar_width = self.radius * 2
            bar_height = 4
            ratio = self.hp / self.max_hp
            pygame.draw.rect(screen, BLACK, (self.x - bar_width // 2, self.y - self.radius - 10, bar_width, bar_height))
            pygame.draw.rect(screen, GREEN,
                             (self.x - bar_width // 2, self.y - self.radius - 10, bar_width * ratio, bar_height))


class AllySystem:
    """Система управления союзниками"""

    def __init__(self, game):
        self.game = game
        self.allies = []
        self.max_allies = 4

    def summon_ally(self, ally_type: str) -> bool:
        """Призыв союзника"""
        if len(self.allies) >= self.max_allies:
            return False

        # Появление рядом с игроком
        x = self.game.player.x + random.randint(-50, 50)
        y = self.game.player.y + random.randint(-50, 50)

        ally = Ally(x, y, ally_type)
        self.allies.append(ally)
        return True

    def update(self, dt: float):
        """Обновление всех союзников"""
        for ally in self.allies[:]:
            ally.update(dt, self.game)
            if not ally.alive:
                self.allies.remove(ally)

    def draw(self, screen: pygame.Surface):
        """Отрисовка всех союзников"""
        for ally in self.allies:
            ally.draw(screen)

    def upgrade_all(self):
        """Улучшение всех союзников"""
        for ally in self.allies:
            ally.upgrade()

    def get_total_damage(self) -> int:
        """Получение общего урона"""
        return sum(ally.damage for ally in self.allies if ally.alive)