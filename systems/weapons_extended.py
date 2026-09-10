# systems/weapons_extended.py

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
        self._init_extended_weapons()

    def _init_default_weapons(self):
        self.add_weapon("pistol", "Пистолет", {"damage": 25, "fire_rate": 0.3, "bullet_speed": 700, "bullet_radius": 5, "ammo": -1, "weapon_type": "hitscan", "color": YELLOW})
        self.add_weapon("shotgun", "Дробовик", {"damage": 15, "fire_rate": 0.8, "bullet_speed": 600, "bullet_radius": 4, "pellets": 7, "spread": 0.3, "ammo": 30, "weapon_type": "shotgun", "color": ORANGE})
        self.add_weapon("laser", "Лазер", {"damage": 40, "fire_rate": 0.15, "bullet_speed": 900, "bullet_radius": 3, "piercing": True, "ammo": 100, "weapon_type": "laser", "color": RED})
        self.add_weapon("rocket_launcher", "Ракетница", {"damage": 60, "fire_rate": 1.5, "bullet_speed": 500, "bullet_radius": 8, "explosive": True, "explosion_radius": 100, "ammo": 15, "weapon_type": "rocket", "color": MAGENTA})
        self.add_weapon("plasma_rifle", "Плазменная винтовка", {"damage": 35, "fire_rate": 0.2, "bullet_speed": 800, "bullet_radius": 6, "piercing": True, "ammo": 50, "weapon_type": "plasma", "color": PURPLE})
        self.add_weapon("minigun", "Миниган", {"damage": 10, "fire_rate": 0.05, "bullet_speed": 750, "bullet_radius": 3, "ammo": 200, "weapon_type": "hitscan", "color": CYAN})
        self.add_weapon("flamethrower", "Огнемёт", {"damage": 8, "fire_rate": 0.1, "bullet_speed": 400, "bullet_radius": 6, "ammo": 50, "weapon_type": "flame", "color": ORANGE})
        self.add_weapon("ice_gun", "Ледяная пушка", {"damage": 20, "fire_rate": 0.4, "bullet_speed": 600, "bullet_radius": 5, "ammo": 40, "weapon_type": "ice", "color": CYAN})
        self.add_weapon("shock_gun", "Шокер", {"damage": 30, "fire_rate": 0.5, "bullet_speed": 700, "bullet_radius": 4, "ammo": 30, "weapon_type": "shock", "color": YELLOW})
        self.add_weapon("gravity_gun", "Гравитационная пушка", {"damage": 25, "fire_rate": 0.6, "bullet_speed": 500, "bullet_radius": 7, "piercing": True, "ammo": 20, "weapon_type": "gravity", "color": MAGENTA})
        self.add_weapon("homing_launcher", "Самонаводящаяся ракетница", {"damage": 45, "fire_rate": 1.2, "bullet_speed": 550, "bullet_radius": 6, "explosive": True, "explosion_radius": 80, "ammo": 12, "weapon_type": "homing", "color": PURPLE})
        self.add_weapon("orbital_cannon", "Орбитальная пушка", {"damage": 50, "fire_rate": 2.0, "bullet_speed": 600, "bullet_radius": 7, "ammo": 10, "weapon_type": "orbital", "color": RED})
        self.add_weapon("bouncing_bullets", "Рикошетная пушка", {"damage": 18, "fire_rate": 0.4, "bullet_speed": 650, "bullet_radius": 5, "ammo": 40, "weapon_type": "bouncing", "color": GREEN})
        self.add_weapon("chain_lightning", "Цепная молния", {"damage": 22, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 4, "piercing": True, "ammo": 25, "weapon_type": "chain", "color": CYAN})
        self.add_weapon("void_rifle", "Винтовка Пустоты", {"damage": 70, "fire_rate": 0.9, "bullet_speed": 800, "bullet_radius": 6, "piercing": True, "explosive": True, "explosion_radius": 60, "ammo": 15, "weapon_type": "void", "color": (50, 0, 100)})
        self.add_weapon("spread_shot", "Разброс", {"damage": 12, "fire_rate": 0.5, "bullet_speed": 600, "bullet_radius": 4, "pellets": 10, "spread": 0.5, "ammo": 35, "weapon_type": "spread", "color": ORANGE})
        self.add_weapon("burst_rifle", "Очередная винтовка", {"damage": 20, "fire_rate": 0.6, "bullet_speed": 700, "bullet_radius": 4, "ammo": 30, "weapon_type": "burst", "color": LIGHT_BLUE})

    def _init_extended_weapons(self):
        # Добавляем оставшиеся 83 оружия, чтобы всего было 100
        weapons_to_add = [
            ("railgun", "Рельсотрон", {"damage": 100, "fire_rate": 2.5, "bullet_speed": 1500, "bullet_radius": 4, "piercing": True, "ammo": 10, "weapon_type": "laser", "color": LIGHT_CYAN}),
            ("gauss_rifle", "Пушка Гаусса", {"damage": 80, "fire_rate": 1.8, "bullet_speed": 1200, "bullet_radius": 5, "piercing": True, "ammo": 15, "weapon_type": "hitscan", "color": LIGHT_BLUE}),
            ("tesla_gun", "Тесла-пушка", {"damage": 35, "fire_rate": 0.4, "bullet_speed": 700, "bullet_radius": 6, "ammo": 40, "weapon_type": "chain", "color": YELLOW}),
            ("arc_thrower", "Дуговой метатель", {"damage": 40, "fire_rate": 0.8, "bullet_speed": 600, "bullet_radius": 5, "piercing": True, "ammo": 30, "weapon_type": "chain", "color": CYAN}),
            ("plasma_caster", "Плазменный кастер", {"damage": 55, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 7, "explosive": True, "explosion_radius": 70, "ammo": 20, "weapon_type": "plasma", "color": MAGENTA}),
            ("fusion_rifle", "Термоядерная винтовка", {"damage": 90, "fire_rate": 1.5, "bullet_speed": 900, "bullet_radius": 5, "piercing": True, "ammo": 12, "weapon_type": "laser", "color": ORANGE}),
            ("disruptor", "Разрушитель", {"damage": 45, "fire_rate": 0.6, "bullet_speed": 650, "bullet_radius": 6, "ammo": 25, "weapon_type": "shock", "color": PURPLE}),
            ("scattergun", "Дробовик-разброс", {"damage": 10, "fire_rate": 0.9, "bullet_speed": 550, "bullet_radius": 3, "pellets": 15, "spread": 0.7, "ammo": 40, "weapon_type": "spread", "color": ORANGE}),
            ("particle_beam", "Пучок частиц", {"damage": 30, "fire_rate": 0.1, "bullet_speed": 800, "bullet_radius": 3, "piercing": True, "ammo": 60, "weapon_type": "laser", "color": LIGHT_MAGENTA}),
            ("bio_rifle", "Биовинтовка", {"damage": 25, "fire_rate": 0.5, "bullet_speed": 500, "bullet_radius": 6, "ammo": 30, "weapon_type": "flame", "color": DARK_GREEN}),
            ("acid_gun", "Кислотная пушка", {"damage": 28, "fire_rate": 0.45, "bullet_speed": 450, "bullet_radius": 6, "ammo": 35, "weapon_type": "flame", "color": (100, 255, 0)}),
            ("needler", "Игломёт", {"damage": 12, "fire_rate": 0.08, "bullet_speed": 700, "bullet_radius": 2, "ammo": 100, "weapon_type": "hitscan", "color": (200, 200, 200)}),
            ("splinter_gun", "Щепочная пушка", {"damage": 15, "fire_rate": 0.35, "bullet_speed": 600, "bullet_radius": 4, "pellets": 5, "spread": 0.2, "ammo": 30, "weapon_type": "spread", "color": BROWN}),
            ("bolt_rifle", "Болтовая винтовка", {"damage": 35, "fire_rate": 0.7, "bullet_speed": 750, "bullet_radius": 4, "ammo": 25, "weapon_type": "hitscan", "color": GRAY}),
            ("storm_rifle", "Штормовая винтовка", {"damage": 22, "fire_rate": 0.15, "bullet_speed": 700, "bullet_radius": 3, "ammo": 60, "weapon_type": "hitscan", "color": LIGHT_BLUE}),
            ("nova_cannon", "Пушка Нова", {"damage": 80, "fire_rate": 2.0, "bullet_speed": 600, "bullet_radius": 10, "explosive": True, "explosion_radius": 120, "ammo": 8, "weapon_type": "rocket", "color": WHITE}),
            ("singularity_gun", "Сингулярная пушка", {"damage": 100, "fire_rate": 3.0, "bullet_speed": 400, "bullet_radius": 8, "piercing": True, "explosive": True, "explosion_radius": 150, "ammo": 5, "weapon_type": "void", "color": (0, 0, 0)}),
            ("tachyon_rifle", "Тахионная винтовка", {"damage": 60, "fire_rate": 1.0, "bullet_speed": 2000, "bullet_radius": 3, "piercing": True, "ammo": 15, "weapon_type": "laser", "color": (150, 0, 255)}),
            ("chrono_gun", "Хронопушка", {"damage": 40, "fire_rate": 0.8, "bullet_speed": 500, "bullet_radius": 5, "ammo": 20, "weapon_type": "homing", "color": (0, 255, 255)}),
            ("quantum_cannon", "Квантовая пушка", {"damage": 75, "fire_rate": 1.4, "bullet_speed": 700, "bullet_radius": 6, "piercing": True, "ammo": 12, "weapon_type": "orbital", "color": (100, 0, 200)}),
            ("dark_matter_rifle", "Винтовка тёмной материи", {"damage": 85, "fire_rate": 1.2, "bullet_speed": 800, "bullet_radius": 5, "piercing": True, "explosive": True, "explosion_radius": 80, "ammo": 10, "weapon_type": "void", "color": (20, 0, 40)}),
            ("hellfire_launcher", "Адский огонь", {"damage": 50, "fire_rate": 1.0, "bullet_speed": 600, "bullet_radius": 7, "explosive": True, "explosion_radius": 100, "ammo": 15, "weapon_type": "rocket", "color": DARK_RED}),
            ("cryo_cannon", "Криопушка", {"damage": 15, "fire_rate": 0.2, "bullet_speed": 400, "bullet_radius": 8, "ammo": 40, "weapon_type": "ice", "color": LIGHT_CYAN}),
            ("emp_rifle", "ЭМИ-винтовка", {"damage": 25, "fire_rate": 0.5, "bullet_speed": 700, "bullet_radius": 5, "ammo": 30, "weapon_type": "shock", "color": (0, 100, 200)}),
            ("sonic_gun", "Звуковая пушка", {"damage": 20, "fire_rate": 0.4, "bullet_speed": 500, "bullet_radius": 8, "ammo": 25, "weapon_type": "gravity", "color": (200, 200, 100)}),
            ("vortex_rifle", "Вихревая винтовка", {"damage": 35, "fire_rate": 0.6, "bullet_speed": 650, "bullet_radius": 6, "piercing": True, "ammo": 20, "weapon_type": "gravity", "color": (150, 100, 255)}),
            ("blaster", "Бластер", {"damage": 30, "fire_rate": 0.35, "bullet_speed": 750, "bullet_radius": 5, "ammo": 50, "weapon_type": "hitscan", "color": RED}),
            ("pulse_rifle", "Импульсная винтовка", {"damage": 28, "fire_rate": 0.12, "bullet_speed": 800, "bullet_radius": 3, "ammo": 80, "weapon_type": "burst", "color": CYAN}),
            ("shredder", "Шредер", {"damage": 18, "fire_rate": 0.04, "bullet_speed": 700, "bullet_radius": 2, "ammo": 150, "weapon_type": "hitscan", "color": ORANGE}),
            ("thunder_gun", "Громовая пушка", {"damage": 45, "fire_rate": 0.9, "bullet_speed": 600, "bullet_radius": 7, "explosive": True, "explosion_radius": 90, "ammo": 15, "weapon_type": "shock", "color": YELLOW}),
            ("storm_cannon", "Штормовая пушка", {"damage": 40, "fire_rate": 1.1, "bullet_speed": 550, "bullet_radius": 6, "explosive": True, "explosion_radius": 85, "ammo": 12, "weapon_type": "rocket", "color": (100, 100, 255)}),
            ("frost_thrower", "Морозный метатель", {"damage": 10, "fire_rate": 0.15, "bullet_speed": 350, "bullet_radius": 7, "ammo": 45, "weapon_type": "ice", "color": (200, 230, 255)}),
            ("poison_spitter", "Ядовитый плеватель", {"damage": 15, "fire_rate": 0.3, "bullet_speed": 400, "bullet_radius": 6, "ammo": 40, "weapon_type": "flame", "color": DARK_GREEN}),
            ("lava_gun", "Лавовая пушка", {"damage": 40, "fire_rate": 0.5, "bullet_speed": 450, "bullet_radius": 8, "ammo": 20, "weapon_type": "flame", "color": (255, 100, 0)}),
            ("wind_blade", "Клинок ветра", {"damage": 30, "fire_rate": 0.4, "bullet_speed": 800, "bullet_radius": 4, "piercing": True, "ammo": 30, "weapon_type": "gravity", "color": LIGHT_GRAY}),
            ("earth_shaker", "Землетряс", {"damage": 50, "fire_rate": 1.5, "bullet_speed": 500, "bullet_radius": 10, "explosive": True, "explosion_radius": 110, "ammo": 10, "weapon_type": "rocket", "color": BROWN}),
            ("shadow_rifle", "Теневая винтовка", {"damage": 35, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 5, "ammo": 25, "weapon_type": "void", "color": (30, 30, 50)}),
            ("holy_rifle", "Святая винтовка", {"damage": 45, "fire_rate": 0.6, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "laser", "color": GOLD}),
            ("demonic_gun", "Демоническая пушка", {"damage": 55, "fire_rate": 0.8, "bullet_speed": 650, "bullet_radius": 6, "explosive": True, "explosion_radius": 75, "ammo": 15, "weapon_type": "rocket", "color": (150, 0, 0)}),
            ("angelic_bow", "Ангельский лук", {"damage": 40, "fire_rate": 0.5, "bullet_speed": 900, "bullet_radius": 4, "piercing": True, "ammo": 30, "weapon_type": "laser", "color": (255, 255, 200)}),
            ("titan_cannon", "Титанская пушка", {"damage": 90, "fire_rate": 2.5, "bullet_speed": 550, "bullet_radius": 12, "explosive": True, "explosion_radius": 130, "ammo": 6, "weapon_type": "rocket", "color": (100, 100, 100)}),
            ("dragon_breath", "Дыхание дракона", {"damage": 35, "fire_rate": 0.3, "bullet_speed": 500, "bullet_radius": 7, "ammo": 30, "weapon_type": "flame", "color": (255, 50, 0)}),
            ("phoenix_gun", "Пушка Феникса", {"damage": 45, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 6, "explosive": True, "explosion_radius": 80, "ammo": 15, "weapon_type": "rocket", "color": (255, 100, 0)}),
            ("warp_rifle", "Деформационная винтовка", {"damage": 50, "fire_rate": 0.9, "bullet_speed": 800, "bullet_radius": 5, "piercing": True, "ammo": 18, "weapon_type": "gravity", "color": (150, 0, 150)}),
            ("doom_cannon", "Пушка Рока", {"damage": 120, "fire_rate": 3.0, "bullet_speed": 500, "bullet_radius": 15, "explosive": True, "explosion_radius": 200, "ammo": 4, "weapon_type": "void", "color": (0, 0, 0)}),
            ("star_gun", "Звёздная пушка", {"damage": 30, "fire_rate": 0.4, "bullet_speed": 700, "bullet_radius": 5, "ammo": 40, "weapon_type": "orbital", "color": (255, 255, 0)}),
            ("comet_launcher", "Кометная ракетница", {"damage": 55, "fire_rate": 1.3, "bullet_speed": 600, "bullet_radius": 7, "explosive": True, "explosion_radius": 90, "ammo": 12, "weapon_type": "homing", "color": (200, 200, 255)}),
            ("meteor_gun", "Метеоритная пушка", {"damage": 70, "fire_rate": 1.8, "bullet_speed": 550, "bullet_radius": 9, "explosive": True, "explosion_radius": 120, "ammo": 10, "weapon_type": "rocket", "color": (150, 100, 50)}),
            ("nebula_rifle", "Туманностная винтовка", {"damage": 40, "fire_rate": 0.6, "bullet_speed": 700, "bullet_radius": 5, "piercing": True, "ammo": 25, "weapon_type": "plasma", "color": (100, 0, 200)}),
            ("galaxy_cannon", "Галактическая пушка", {"damage": 80, "fire_rate": 2.0, "bullet_speed": 650, "bullet_radius": 8, "explosive": True, "explosion_radius": 100, "ammo": 8, "weapon_type": "void", "color": (30, 0, 60)}),
            ("proton_gun", "Протонная пушка", {"damage": 35, "fire_rate": 0.35, "bullet_speed": 750, "bullet_radius": 5, "ammo": 40, "weapon_type": "plasma", "color": (0, 150, 255)}),
            ("neutron_rifle", "Нейтронная винтовка", {"damage": 45, "fire_rate": 0.8, "bullet_speed": 700, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "laser", "color": (200, 200, 200)}),
            ("electron_gun", "Электронная пушка", {"damage": 25, "fire_rate": 0.2, "bullet_speed": 800, "bullet_radius": 4, "ammo": 50, "weapon_type": "shock", "color": (0, 100, 255)}),
            ("photon_rifle", "Фотонная винтовка", {"damage": 40, "fire_rate": 0.5, "bullet_speed": 850, "bullet_radius": 4, "piercing": True, "ammo": 25, "weapon_type": "laser", "color": (255, 255, 100)}),
            ("graviton_gun", "Гравитонная пушка", {"damage": 50, "fire_rate": 1.0, "bullet_speed": 600, "bullet_radius": 7, "piercing": True, "ammo": 15, "weapon_type": "gravity", "color": (100, 0, 100)}),
            ("temporal_gun", "Временная пушка", {"damage": 45, "fire_rate": 0.9, "bullet_speed": 700, "bullet_radius": 5, "ammo": 18, "weapon_type": "homing", "color": (0, 200, 200)}),
            ("void_cannon", "Пустотная пушка", {"damage": 85, "fire_rate": 2.2, "bullet_speed": 550, "bullet_radius": 10, "explosive": True, "explosion_radius": 140, "ammo": 6, "weapon_type": "void", "color": (0, 0, 0)}),
            ("soul_rifle", "Винтовка душ", {"damage": 40, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "homing", "color": (100, 0, 200)}),
            ("spirit_gun", "Духовная пушка", {"damage": 35, "fire_rate": 0.5, "bullet_speed": 750, "bullet_radius": 5, "ammo": 30, "weapon_type": "laser", "color": (200, 200, 255)}),
            ("phantom_rifle", "Фантомная винтовка", {"damage": 30, "fire_rate": 0.4, "bullet_speed": 800, "bullet_radius": 4, "piercing": True, "ammo": 30, "weapon_type": "void", "color": (50, 50, 80)}),
            ("ghost_gun", "Призрачная пушка", {"damage": 35, "fire_rate": 0.6, "bullet_speed": 700, "bullet_radius": 5, "ammo": 25, "weapon_type": "gravity", "color": (200, 200, 200)}),
            ("poltergeist", "Полтергейст", {"damage": 40, "fire_rate": 0.8, "bullet_speed": 650, "bullet_radius": 6, "explosive": True, "explosion_radius": 70, "ammo": 15, "weapon_type": "rocket", "color": (150, 150, 150)}),
            ("haunt_rifle", "Винтовка призрака", {"damage": 30, "fire_rate": 0.5, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 25, "weapon_type": "void", "color": (100, 100, 150)}),
            ("specter_cannon", "Спектральная пушка", {"damage": 50, "fire_rate": 1.1, "bullet_speed": 600, "bullet_radius": 7, "explosive": True, "explosion_radius": 85, "ammo": 12, "weapon_type": "rocket", "color": (180, 180, 200)}),
            ("wraith_gun", "Пушка духа", {"damage": 45, "fire_rate": 0.9, "bullet_speed": 700, "bullet_radius": 5, "ammo": 18, "weapon_type": "homing", "color": (100, 100, 200)}),
            ("shadow_cannon", "Теневая пушка", {"damage": 60, "fire_rate": 1.4, "bullet_speed": 600, "bullet_radius": 8, "explosive": True, "explosion_radius": 95, "ammo": 10, "weapon_type": "void", "color": (20, 20, 30)}),
            ("night_rifle", "Ночная винтовка", {"damage": 35, "fire_rate": 0.6, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 22, "weapon_type": "void", "color": (10, 10, 20)}),
            ("eclipse_gun", "Пушка затмения", {"damage": 55, "fire_rate": 1.2, "bullet_speed": 650, "bullet_radius": 7, "explosive": True, "explosion_radius": 90, "ammo": 12, "weapon_type": "rocket", "color": (50, 0, 50)}),
            ("twilight_rifle", "Сумеречная винтовка", {"damage": 40, "fire_rate": 0.7, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "laser", "color": (100, 50, 100)}),
            ("dawn_cannon", "Пушка рассвета", {"damage": 45, "fire_rate": 1.0, "bullet_speed": 650, "bullet_radius": 6, "explosive": True, "explosion_radius": 80, "ammo": 15, "weapon_type": "rocket", "color": (255, 200, 100)}),
            ("sun_rifle", "Солнечная винтовка", {"damage": 50, "fire_rate": 0.6, "bullet_speed": 800, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "laser", "color": (255, 255, 0)}),
            ("solar_cannon", "Солнечная пушка", {"damage": 70, "fire_rate": 1.5, "bullet_speed": 600, "bullet_radius": 8, "explosive": True, "explosion_radius": 110, "ammo": 10, "weapon_type": "rocket", "color": (255, 200, 0)}),
            ("star_cannon", "Звёздная пушка", {"damage": 65, "fire_rate": 1.3, "bullet_speed": 650, "bullet_radius": 7, "explosive": True, "explosion_radius": 100, "ammo": 10, "weapon_type": "orbital", "color": (255, 255, 200)}),
            ("cosmic_rifle", "Космическая винтовка", {"damage": 45, "fire_rate": 0.5, "bullet_speed": 850, "bullet_radius": 4, "piercing": True, "ammo": 25, "weapon_type": "plasma", "color": (0, 100, 255)}),
            ("astral_gun", "Астральная пушка", {"damage": 40, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 5, "ammo": 22, "weapon_type": "homing", "color": (150, 0, 255)}),
            ("ethereal_rifle", "Эфирная винтовка", {"damage": 35, "fire_rate": 0.6, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 25, "weapon_type": "gravity", "color": (200, 150, 255)}),
            ("mystic_gun", "Мистическая пушка", {"damage": 50, "fire_rate": 0.8, "bullet_speed": 700, "bullet_radius": 6, "explosive": True, "explosion_radius": 85, "ammo": 15, "weapon_type": "rocket", "color": (150, 0, 150)}),
            ("arcane_rifle", "Арканная винтовка", {"damage": 45, "fire_rate": 0.6, "bullet_speed": 800, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "laser", "color": (100, 0, 200)}),
            ("rune_gun", "Руническая пушка", {"damage": 40, "fire_rate": 0.7, "bullet_speed": 700, "bullet_radius": 5, "ammo": 25, "weapon_type": "homing", "color": (0, 150, 150)}),
            ("glyph_cannon", "Глиф-пушка", {"damage": 60, "fire_rate": 1.2, "bullet_speed": 650, "bullet_radius": 7, "explosive": True, "explosion_radius": 95, "ammo": 12, "weapon_type": "rocket", "color": (0, 200, 200)}),
            ("sigil_rifle", "Сигильная винтовка", {"damage": 35, "fire_rate": 0.5, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 22, "weapon_type": "plasma", "color": (200, 0, 200)}),
            ("totem_gun", "Тотемная пушка", {"damage": 45, "fire_rate": 0.9, "bullet_speed": 700, "bullet_radius": 6, "explosive": True, "explosion_radius": 80, "ammo": 15, "weapon_type": "rocket", "color": (150, 100, 0)}),
            ("relic_rifle", "Реликтовая винтовка", {"damage": 40, "fire_rate": 0.6, "bullet_speed": 750, "bullet_radius": 5, "piercing": True, "ammo": 20, "weapon_type": "laser", "color": (200, 150, 0)}),
            ("artifact_gun", "Артефактная пушка", {"damage": 55, "fire_rate": 1.0, "bullet_speed": 700, "bullet_radius": 6, "explosive": True, "explosion_radius": 90, "ammo": 12, "weapon_type": "rocket", "color": (255, 200, 100)}),
        ]

        for weapon_id, name, config in weapons_to_add:
            self.add_weapon(weapon_id, name, config)

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