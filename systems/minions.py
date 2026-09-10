# systems/minions.py
from entities.bullet import Bullet
import math
import random
import pygame
from typing import Dict, List, Tuple, Optional, Any
from settings import *


class Minion:
    def __init__(self, minion_id: str, name: str, config: dict):
        self.id = minion_id
        self.name = name
        self.config = config
        self.hp = config.get("hp", 50)
        self.max_hp = self.hp
        self.damage = config.get("damage", 10)
        self.speed = config.get("speed", 200)
        self.attack_range = config.get("attack_range", 150)
        self.attack_cooldown = config.get("attack_cooldown", 1.0)
        self.current_cooldown = 0.0
        self.radius = config.get("radius", 15)
        self.color = config.get("color", WHITE)
        self.type = config.get("type", "melee")
        self.special = config.get("special", None)
        self.level = 1
        self.alive = True
        self.x = 0
        self.y = 0
        self.target = None
        self.owner = None

    def upgrade(self):
        self.level += 1
        self.damage = int(self.damage * 1.3)
        self.hp = int(self.hp * 1.2)
        self.max_hp = self.hp
        return self

    def update(self, dt, game):
        if not self.alive:
            return
        self.current_cooldown = max(0, self.current_cooldown - dt)
        self._find_target(game)
        if self.target and self.target.alive:
            self._move_to_target(dt)
            if self.current_cooldown <= 0:
                dist = math.hypot(self.target.x - self.x, self.target.y - self.y)
                if dist < self.attack_range:
                    self._attack(game)
        else:
            self._follow_owner(dt)

    def _find_target(self, game):
        if not game.enemies:
            self.target = None
            return
        closest = None
        closest_dist = 999999
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if dist < closest_dist:
                    closest_dist = dist
                    closest = enemy
        self.target = closest

    def _move_to_target(self, dt):
        if not self.target:
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        norm = math.hypot(dx, dy)
        if norm > self.attack_range * 0.8:
            self.x += (dx / norm) * self.speed * dt
            self.y += (dy / norm) * self.speed * dt

    def _follow_owner(self, dt):
        if not self.owner:
            return
        target_x = self.owner.x + random.randint(-80, 80)
        target_y = self.owner.y + random.randint(-80, 80)
        dist = math.hypot(target_x - self.x, target_y - self.y)
        if dist > 100:
            dx = target_x - self.x
            dy = target_y - self.y
            norm = math.hypot(dx, dy)
            if norm > 0:
                self.x += (dx / norm) * self.speed * dt
                self.y += (dy / norm) * self.speed * dt

    def _attack(self, game):
        self.current_cooldown = self.attack_cooldown
        if self.type == "melee":
            self.target.take_damage(self.damage)
            game.add_damage_number(self.target.x, self.target.y - self.target.radius, self.damage, WHITE)
        elif self.type == "ranged":
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            norm = math.hypot(dx, dy)
            if norm > 0:
                bullet = Bullet(self.x, self.y, (dx/norm, dy/norm), True, self.damage)
                game.bullets.append(bullet)
        elif self.type == "support":
            if self.owner:
                self.owner.heal(self.damage)
        elif self.type == "tank":
            self.target.take_damage(self.damage)
            self.target.x += random.randint(-10, 10)
            self.target.y += random.randint(-10, 10)

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return self.alive

    def draw(self, screen):
        if not self.alive:
            return
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        hp_ratio = self.hp / self.max_hp
        bar_width = self.radius * 2
        pygame.draw.rect(screen, BLACK, (self.x - bar_width//2, self.y - self.radius - 12, bar_width, 5))
        pygame.draw.rect(screen, GREEN, (self.x - bar_width//2, self.y - self.radius - 12, bar_width * hp_ratio, 5))


class MinionManager:
    def __init__(self):
        self.minions: Dict[str, Minion] = {}
        self.active_minions: List[Minion] = []
        self._init_default_minions()
        self._init_extended_minions()

    def _init_default_minions(self):
        self.add_minion("drone", "Боевой дрон", {"hp": 30, "damage": 15, "speed": 250, "attack_range": 200, "attack_cooldown": 0.8, "type": "ranged", "color": CYAN})
        self.add_minion("turret", "Турель", {"hp": 80, "damage": 20, "speed": 0, "attack_range": 300, "attack_cooldown": 0.5, "type": "ranged", "color": ORANGE})
        self.add_minion("healer", "Медик", {"hp": 40, "damage": 10, "speed": 180, "attack_range": 100, "attack_cooldown": 2.0, "type": "support", "color": GREEN})

    def _init_extended_minions(self):
        minions_to_add = [
            ("assault_drone", "Штурмовой дрон", {"hp": 50, "damage": 25, "speed": 300, "attack_range": 250, "attack_cooldown": 0.6, "type": "ranged", "color": (100, 150, 255)}),
            ("sniper_drone", "Снайперский дрон", {"hp": 25, "damage": 50, "speed": 150, "attack_range": 500, "attack_cooldown": 2.5, "type": "ranged", "color": (150, 100, 255)}),
            ("heavy_drone", "Тяжёлый дрон", {"hp": 120, "damage": 35, "speed": 100, "attack_range": 200, "attack_cooldown": 1.5, "type": "tank", "color": (80, 80, 80)}),
            ("shield_drone", "Щитовой дрон", {"hp": 70, "damage": 10, "speed": 200, "attack_range": 150, "attack_cooldown": 1.0, "type": "tank", "color": (150, 150, 200), "special": "shield_ally"}),
            ("repair_drone", "Ремонтный дрон", {"hp": 35, "damage": 15, "speed": 180, "attack_range": 120, "attack_cooldown": 1.5, "type": "support", "color": (100, 200, 100), "special": "repair"}),
            ("emp_drone", "ЭМИ-дрон", {"hp": 30, "damage": 20, "speed": 220, "attack_range": 200, "attack_cooldown": 3.0, "type": "ranged", "color": (200, 200, 0), "special": "emp_blast"}),
            ("flame_drone", "Огненный дрон", {"hp": 40, "damage": 30, "speed": 200, "attack_range": 150, "attack_cooldown": 0.9, "type": "ranged", "color": (255, 100, 0), "special": "burn"}),
            ("ice_drone", "Ледяной дрон", {"hp": 40, "damage": 25, "speed": 200, "attack_range": 180, "attack_cooldown": 1.1, "type": "ranged", "color": (150, 200, 255), "special": "freeze"}),
            ("shock_drone", "Электрический дрон", {"hp": 35, "damage": 28, "speed": 240, "attack_range": 200, "attack_cooldown": 0.7, "type": "ranged", "color": (255, 255, 0), "special": "chain_lightning"}),
            ("poison_drone", "Ядовитый дрон", {"hp": 35, "damage": 22, "speed": 190, "attack_range": 170, "attack_cooldown": 1.2, "type": "ranged", "color": (100, 200, 0), "special": "poison"}),
            ("ninja_drone", "Дрон-ниндзя", {"hp": 30, "damage": 35, "speed": 350, "attack_range": 100, "attack_cooldown": 0.5, "type": "melee", "color": (50, 50, 50), "special": "backstab"}),
            ("kamikaze_drone", "Дрон-камикадзе", {"hp": 15, "damage": 80, "speed": 400, "attack_range": 50, "attack_cooldown": 99, "type": "melee", "color": (255, 50, 50), "special": "explode"}),
            ("teleport_drone", "Телепортирующий дрон", {"hp": 45, "damage": 25, "speed": 200, "attack_range": 250, "attack_cooldown": 1.3, "type": "ranged", "color": (150, 0, 150), "special": "teleport"}),
            ("gravity_drone", "Гравитационный дрон", {"hp": 55, "damage": 20, "speed": 180, "attack_range": 220, "attack_cooldown": 1.0, "type": "ranged", "color": (100, 0, 100), "special": "gravity_pull"}),
            ("summoner_drone", "Дрон-призыватель", {"hp": 60, "damage": 15, "speed": 150, "attack_range": 200, "attack_cooldown": 3.0, "type": "ranged", "color": (0, 150, 150), "special": "summon_minor_drone"}),
            ("shield_generator", "Генератор щита", {"hp": 100, "damage": 0, "speed": 0, "attack_range": 200, "attack_cooldown": 5.0, "type": "support", "color": (0, 100, 200), "special": "area_shield"}),
            ("buff_drone", "Дрон-усилитель", {"hp": 40, "damage": 5, "speed": 220, "attack_range": 150, "attack_cooldown": 4.0, "type": "support", "color": (255, 200, 0), "special": "damage_buff"}),
            ("debuff_drone", "Дрон-ослабитель", {"hp": 40, "damage": 5, "speed": 220, "attack_range": 180, "attack_cooldown": 4.0, "type": "ranged", "color": (150, 0, 0), "special": "debuff"}),
            ("heal_drone", "Лечащий дрон", {"hp": 45, "damage": 15, "speed": 200, "attack_range": 150, "attack_cooldown": 2.0, "type": "support", "color": (0, 255, 100), "special": "heal_aura"}),
            ("resurrect_drone", "Дрон-воскреситель", {"hp": 35, "damage": 10, "speed": 180, "attack_range": 100, "attack_cooldown": 10.0, "type": "support", "color": (255, 255, 255), "special": "resurrect"}),
            ("stealth_drone", "Стелс-дрон", {"hp": 30, "damage": 30, "speed": 280, "attack_range": 120, "attack_cooldown": 0.7, "type": "melee", "color": (100, 100, 100), "special": "stealth_attack"}),
            ("speed_drone", "Скоростной дрон", {"hp": 25, "damage": 15, "speed": 500, "attack_range": 100, "attack_cooldown": 0.4, "type": "melee", "color": (0, 200, 200), "special": "speed_boost"}),
            ("tank_drone", "Танковый дрон", {"hp": 200, "damage": 40, "speed": 50, "attack_range": 250, "attack_cooldown": 2.0, "type": "tank", "color": (50, 50, 50), "special": "armor_boost"}),
            ("artillery_drone", "Артиллерийский дрон", {"hp": 60, "damage": 60, "speed": 80, "attack_range": 600, "attack_cooldown": 4.0, "type": "ranged", "color": (100, 100, 100), "special": "aoe_damage"}),
            ("missile_drone", "Ракетный дрон", {"hp": 50, "damage": 45, "speed": 250, "attack_range": 400, "attack_cooldown": 2.5, "type": "ranged", "color": (150, 100, 100), "special": "homing_missile"}),
            ("laser_drone", "Лазерный дрон", {"hp": 40, "damage": 35, "speed": 220, "attack_range": 350, "attack_cooldown": 0.8, "type": "ranged", "color": (255, 0, 0), "special": "piercing_laser"}),
            ("plasma_drone", "Плазменный дрон", {"hp": 45, "damage": 40, "speed": 200, "attack_range": 300, "attack_cooldown": 1.0, "type": "ranged", "color": (255, 0, 255), "special": "plasma_blast"}),
            ("void_drone", "Пустотный дрон", {"hp": 55, "damage": 50, "speed": 180, "attack_range": 250, "attack_cooldown": 1.5, "type": "ranged", "color": (0, 0, 0), "special": "void_rift"}),
            ("gravity_minion", "Гравитационный миньон", {"hp": 70, "damage": 30, "speed": 150, "attack_range": 200, "attack_cooldown": 1.2, "type": "tank", "color": (50, 50, 100), "special": "gravity_well"}),
            ("summon_minor_drone", "Малый дрон", {"hp": 15, "damage": 10, "speed": 300, "attack_range": 120, "attack_cooldown": 0.6, "type": "ranged", "color": (200, 200, 200)}),
        ]

        for minion_id, name, config in minions_to_add:
            self.add_minion(minion_id, name, config)

    def add_minion(self, minion_id, name, config):
        self.minions[minion_id] = Minion(minion_id, name, config)

    def get_minion(self, minion_id):
        return self.minions.get(minion_id)

    def get_all_minions(self):
        return list(self.minions.values())

    def get_random_minion(self):
        return random.choice(list(self.minions.values()))

    def spawn_minion(self, minion_id, x, y, owner=None):
        minion = self.get_minion(minion_id)
        if minion:
            new_minion = Minion(minion.id, minion.name, minion.config)
            new_minion.x = x
            new_minion.y = y
            new_minion.owner = owner
            self.active_minions.append(new_minion)
            return new_minion
        return None

    def update(self, dt, game):
        for minion in self.active_minions[:]:
            minion.update(dt, game)
            if not minion.alive:
                self.active_minions.remove(minion)

    def draw(self, screen):
        for minion in self.active_minions:
            minion.draw(screen)

    def get_active_count(self):
        return len(self.active_minions)