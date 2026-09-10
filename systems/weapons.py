# systems/weapons.py

import math
import random
import pygame
from typing import Dict, List, Tuple, Optional, Any
from settings import *
from entities.bullet import Bullet


class Weapon:
    def __init__(self, weapon_id: str, name: str, config: dict):
        self.id = weapon_id
        self.name = name
        self.config = config
        self.damage = config.get("damage", 25)
        self.fire_rate = config.get("fire_rate", 0.3)
        self.bullet_speed = config.get("bullet_speed", 700)
        self.bullet_radius = config.get("bullet_radius", 5)
        self.piercing = config.get("piercing", False)
        self.explosive = config.get("explosive", False)
        self.explosion_radius = config.get("explosion_radius", 50)
        self.ammo = config.get("ammo", -1)
        self.pellets = config.get("pellets", 1)
        self.spread = config.get("spread", 0.0)
        self.color = config.get("color", YELLOW)
        self.weapon_type = config.get("weapon_type", "hitscan")
        self.special = config.get("special", None)
        self.level = 1
        self.modifiers = []

    def upgrade(self):
        self.level += 1
        self.damage = int(self.damage * 1.2)
        self.fire_rate *= 0.9
        return self

    def add_modifier(self, mod):
        self.modifiers.append(mod)
        return self

    def shoot(self, x, y, direction, game):
        dx, dy = direction
        norm = math.hypot(dx, dy)
        if norm > 0:
            dx /= norm
            dy /= norm

        bullets = []
        if self.weapon_type == "shotgun":
            for i in range(self.pellets):
                angle = math.atan2(dy, dx) + random.uniform(-self.spread, self.spread)
                bullets.append(self._create_bullet(x, y, math.cos(angle), math.sin(angle), game))
        elif self.weapon_type == "laser":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_piercing(True)
            bullets.append(bullet)
        elif self.weapon_type == "rocket":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_explosive(self.explosion_radius)
            bullets.append(bullet)
        elif self.weapon_type == "spread":
            for i in range(self.pellets):
                angle = math.atan2(dy, dx) + random.uniform(-self.spread, self.spread)
                bullets.append(self._create_bullet(x, y, math.cos(angle), math.sin(angle), game))
        elif self.weapon_type == "burst":
            for _ in range(3):
                bullets.append(self._create_bullet(x, y, dx, dy, game))
        elif self.weapon_type == "homing":
            bullet = self._create_bullet(x, y, dx, dy, game)
            if game.enemies:
                target = min(game.enemies, key=lambda e: math.hypot(e.x - x, e.y - y) if e.alive else 99999)
                if target.alive:
                    bullet.set_homing(target)
            bullets.append(bullet)
        elif self.weapon_type == "orbital":
            for i in range(8):
                angle = i * math.pi / 4
                bullets.append(self._create_bullet(x, y, math.cos(angle), math.sin(angle), game))
        elif self.weapon_type == "bouncing":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_bouncing(True)
            bullets.append(bullet)
        elif self.weapon_type == "chain":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_piercing(True)
            bullets.append(bullet)
        elif self.weapon_type == "void":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_piercing(True)
            bullet.set_explosive(self.explosion_radius)
            bullets.append(bullet)
        elif self.weapon_type == "plasma":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_piercing(True)
            bullet.color = MAGENTA
            bullets.append(bullet)
        elif self.weapon_type == "flame":
            for i in range(5):
                angle = math.atan2(dy, dx) + random.uniform(-0.3, 0.3)
                bullets.append(self._create_bullet(x, y, math.cos(angle), math.sin(angle), game))
        elif self.weapon_type == "ice":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.color = CYAN
            bullets.append(bullet)
        elif self.weapon_type == "shock":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.color = YELLOW
            bullets.append(bullet)
        elif self.weapon_type == "gravity":
            bullet = self._create_bullet(x, y, dx, dy, game)
            bullet.set_piercing(True)
            bullets.append(bullet)
        else:
            bullets.append(self._create_bullet(x, y, dx, dy, game))

        return bullets

    def _create_bullet(self, x, y, dx, dy, game):
        damage = self.damage
        if random.random() < getattr(game.player, "crit_chance", 0.15):
            damage = int(damage * getattr(game.player, "crit_multiplier", 2.0))
        bullet = Bullet(x, y, (dx, dy), True, damage)
        bullet.radius = self.bullet_radius
        bullet.speed = self.bullet_speed
        bullet.color = self.color
        if self.piercing:
            bullet.set_piercing(True)
        if self.explosive:
            bullet.set_explosive(self.explosion_radius)
        return bullet


class WeaponManager:
    def __init__(self):
        self.weapons: Dict[str, Weapon] = {}
        self._init_default_weapons()

    def _init_default_weapons(self):
        self.add_weapon("pistol", "Пистолет", {
            "damage": 25,
            "fire_rate": 0.3,
            "bullet_speed": 700,
            "bullet_radius": 5,
            "ammo": -1,
            "weapon_type": "hitscan",
            "color": YELLOW,
        })
        self.add_weapon("shotgun", "Дробовик", {
            "damage": 15,
            "fire_rate": 0.8,
            "bullet_speed": 600,
            "bullet_radius": 4,
            "pellets": 7,
            "spread": 0.3,
            "ammo": 30,
            "weapon_type": "shotgun",
            "color": ORANGE,
        })
        self.add_weapon("laser", "Лазер", {
            "damage": 40,
            "fire_rate": 0.15,
            "bullet_speed": 900,
            "bullet_radius": 3,
            "piercing": True,
            "ammo": 100,
            "weapon_type": "laser",
            "color": RED,
        })
        self.add_weapon("rocket_launcher", "Ракетница", {
            "damage": 60,
            "fire_rate": 1.5,
            "bullet_speed": 500,
            "bullet_radius": 8,
            "explosive": True,
            "explosion_radius": 100,
            "ammo": 15,
            "weapon_type": "rocket",
            "color": MAGENTA,
        })
        self.add_weapon("plasma_rifle", "Плазменная винтовка", {
            "damage": 35,
            "fire_rate": 0.2,
            "bullet_speed": 800,
            "bullet_radius": 6,
            "piercing": True,
            "ammo": 50,
            "weapon_type": "plasma",
            "color": PURPLE,
        })
        self.add_weapon("minigun", "Миниган", {
            "damage": 10,
            "fire_rate": 0.05,
            "bullet_speed": 750,
            "bullet_radius": 3,
            "ammo": 200,
            "weapon_type": "hitscan",
            "color": CYAN,
        })
        self.add_weapon("flamethrower", "Огнемёт", {
            "damage": 8,
            "fire_rate": 0.1,
            "bullet_speed": 400,
            "bullet_radius": 6,
            "ammo": 50,
            "weapon_type": "flame",
            "color": ORANGE,
        })
        self.add_weapon("ice_gun", "Ледяная пушка", {
            "damage": 20,
            "fire_rate": 0.4,
            "bullet_speed": 600,
            "bullet_radius": 5,
            "ammo": 40,
            "weapon_type": "ice",
            "color": CYAN,
        })
        self.add_weapon("shock_gun", "Шокер", {
            "damage": 30,
            "fire_rate": 0.5,
            "bullet_speed": 700,
            "bullet_radius": 4,
            "ammo": 30,
            "weapon_type": "shock",
            "color": YELLOW,
        })
        self.add_weapon("gravity_gun", "Гравитационная пушка", {
            "damage": 25,
            "fire_rate": 0.6,
            "bullet_speed": 500,
            "bullet_radius": 7,
            "piercing": True,
            "ammo": 20,
            "weapon_type": "gravity",
            "color": MAGENTA,
        })
        self.add_weapon("homing_launcher", "Самонаводящаяся ракетница", {
            "damage": 45,
            "fire_rate": 1.2,
            "bullet_speed": 550,
            "bullet_radius": 6,
            "explosive": True,
            "explosion_radius": 80,
            "ammo": 12,
            "weapon_type": "homing",
            "color": PURPLE,
        })
        self.add_weapon("orbital_cannon", "Орбитальная пушка", {
            "damage": 50,
            "fire_rate": 2.0,
            "bullet_speed": 600,
            "bullet_radius": 7,
            "ammo": 10,
            "weapon_type": "orbital",
            "color": RED,
        })
        self.add_weapon("bouncing_bullets", "Рикошетная пушка", {
            "damage": 18,
            "fire_rate": 0.4,
            "bullet_speed": 650,
            "bullet_radius": 5,
            "ammo": 40,
            "weapon_type": "bouncing",
            "color": GREEN,
        })
        self.add_weapon("chain_lightning", "Цепная молния", {
            "damage": 22,
            "fire_rate": 0.7,
            "bullet_speed": 700,
            "bullet_radius": 4,
            "piercing": True,
            "ammo": 25,
            "weapon_type": "chain",
            "color": CYAN,
        })
        self.add_weapon("void_rifle", "Винтовка Пустоты", {
            "damage": 70,
            "fire_rate": 0.9,
            "bullet_speed": 800,
            "bullet_radius": 6,
            "piercing": True,
            "explosive": True,
            "explosion_radius": 60,
            "ammo": 15,
            "weapon_type": "void",
            "color": (50, 0, 100),
        })
        self.add_weapon("spread_shot", "Разброс", {
            "damage": 12,
            "fire_rate": 0.5,
            "bullet_speed": 600,
            "bullet_radius": 4,
            "pellets": 10,
            "spread": 0.5,
            "ammo": 35,
            "weapon_type": "spread",
            "color": ORANGE,
        })
        self.add_weapon("burst_rifle", "Очередная винтовка", {
            "damage": 20,
            "fire_rate": 0.6,
            "bullet_speed": 700,
            "bullet_radius": 4,
            "ammo": 30,
            "weapon_type": "burst",
            "color": LIGHT_BLUE,
        })

    def add_weapon(self, weapon_id, name, config):
        self.weapons[weapon_id] = Weapon(weapon_id, name, config)

    def get_weapon(self, weapon_id):
        return self.weapons.get(weapon_id)

    def get_all_weapons(self):
        return list(self.weapons.values())

    def get_weapons_by_type(self, weapon_type):
        return [w for w in self.weapons.values() if w.weapon_type == weapon_type]

    def get_random_weapon(self):
        return random.choice(list(self.weapons.values()))

    def apply_modifier(self, weapon_id, modifier):
        weapon = self.get_weapon(weapon_id)
        if weapon:
            weapon.add_modifier(modifier)
            return True
        return False