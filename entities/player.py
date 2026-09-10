# entities/player.py

import math
import pygame
import random
from typing import Tuple, List, Optional, Dict, Any
from settings import *
from settings import WEAPON_TYPES
from entities.bullet import Bullet
from entities.wall import EnergyWall
from systems.weapons_extended import WeaponManager, Weapon
from systems.protection import ProtectionManager, Protection
from systems.minions import MinionManager, Minion
from systems.effects import EffectSystem
from systems.crafting import CraftingSystem


class Player:
    def __init__(self, x: float, y: float):
        # Позиция и движение
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = PLAYER_RADIUS
        self.just_shot = False
        self.dash_timer = 0.0

        # Здоровье и энергия
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.energy = 0
        self.max_energy = PLAYER_MAX_ENERGY
        self.shield_timer = 0.0
        self.invulnerable_timer = 0.0

        # Оружие
        self.fire_rate = PLAYER_FIRE_RATE
        self.fire_cooldown = 0.0
        self.weapons = ['pistol']
        self.current_weapon = 'pistol'
        self.weapon_levels = {'pistol': 1}
        self.ammo = {}
        self.reloading = False
        self.reload_timer = 0.0
        self.weapon_manager = WeaponManager()
        self._init_ammo()

        # Защита
        self.protections = []
        self.active_protection = None
        self.protection_manager = ProtectionManager()

        # Миньоны
        self.minions = []
        self.minion_manager = MinionManager()

        # Способности
        self.dash_cooldown = 0.0
        self.dash_timer = 0.0
        self.wall_cooldown = 0.0
        self.stealth_cooldown = 0.0
        self.emp_cooldown = 0.0
        self.speed_boost_timer = 0.0
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_direction = (1, 0)
        self.dash_effect_timer = 0.0  # Для визуального эффекта размытия

        # Статы
        self.speed = PLAYER_SPEED
        self.damage_multiplier = 1.0
        self.fire_rate_multiplier = 1.0
        self.crit_chance = PLAYER_CRIT_CHANCE
        self.crit_multiplier = PLAYER_CRIT_MULTIPLIER
        self.armor = PLAYER_ARMOR
        self.regen_rate = PLAYER_REGEN_RATE
        self.exp_multiplier = 1.0
        self.damage_reduction = 1.0

        # Прокачка
        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        self.skill_points = 0
        self.permanent_speed_boost = 0
        self.permanent_damage_boost = 0
        self.permanent_fire_rate_boost = 0
        self.skills = {
            'combat': {
                'damage': 0,
                'crit_chance': 0,
                'crit_damage': 0,
                'fire_rate': 0,
                'piercing': 0,
                'explosive': 0
            },
            'tech': {
                'energy_efficiency': 0,
                'hack_speed': 0,
                'turret_damage': 0,
                'drone_damage': 0,
                'shield_duration': 0,
                'emp_radius': 0
            },
            'survival': {
                'max_hp': 0,
                'regen': 0,
                'armor': 0,
                'speed': 0,
                'dash_cooldown': 0,
                'healing_boost': 0
            }
        }

        # Статистика
        self.kills = 0
        self.damage_dealt = 0
        self.damage_taken = 0
        self.pickups_collected = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_timer = 0.0
        self.combo_multiplier = 1.0
        self.energy_used_in_fight = 0

        # Ресурсы
        self.scrap = 0
        self.circuits = 0
        self.energy_cells = 0
        self.crystals = 0
        self.ai_cores = 0
        self.organic_tissue = 0
        self.credits = 0
        self.plasma_fragments = 0
        self.dark_matter = 0
        self.void_shards = 0
        self.star_dust = 0
        self.quantum_foam = 0
        self.nano_swarm = 0
        self.bio_gel = 0
        self.mechanical_parts = 0
        self.laser_lenses = 0
        self.rocket_fuel = 0
        self.ice_cores = 0
        self.thunder_cores = 0
        self.gravity_cores = 0
        self.soul_essence = 0

        # Сюжет
        self.completed_quests = []
        self.current_quest = None
        self.reputation = 0
        self.story_flags = {}

        # Состояние
        self.alive = True
        self.in_vehicle = False
        self.vehicle = None
        self.invisible = False
        self.phase_shift = False
        self.poison_timer = 0.0
        self.poison_damage = 0
        self.burn_timer = 0.0
        self.burn_damage = 0
        self.slow_timer = 0.0
        self.slow_multiplier = 1.0
        self.confusion_timer = 0.0
        self.stun_timer = 0.0
        self.hp_drain = 0
        self.energy_drain = 0
        self.fire_vulnerability = 1.0
        self.light_sensitivity = 1.0
        self.emp_vulnerability = 1.0
        self.recoil = 1.0

        # Модификаторы от навыков (используются в _apply_skill_effect)
        self.energy_efficiency = 1.0
        self.hack_speed_multiplier = 1.0
        self.turret_damage_multiplier = 1.0
        self.drone_damage_multiplier = 1.0
        self.shield_duration_multiplier = 1.0
        self.piercing = False
        self.explosive = False

        # Визуальные эффекты
        self.muzzle_flash = 0.0
        self.hit_flash = 0.0
        self.dash_ghosts = []

        # Система эффектов
        self.effect_system = EffectSystem(self)

        # Крафтинг
        self.crafting_system = CraftingSystem()

    def _init_ammo(self):
        for weapon_id, weapon in self.weapon_manager.weapons.items():
            self.ammo[weapon_id] = weapon.ammo

    def update(self, dt: float, keys, mouse_pos: Tuple[float, float], mouse_buttons: Tuple[bool, bool, bool], game):
        if not self.alive:
            return

        self._update_timers(dt)
        self._update_status_effects(dt)

        if self.regen_rate > 0:
            self.hp = min(self.max_hp, self.hp + self.regen_rate * dt)

        if self.hp_drain > 0:
            self.hp = max(0, self.hp - self.hp_drain * dt)

        if self.energy_drain > 0:
            self.energy = max(0, self.energy - self.energy_drain * dt)

        self.combo_timer -= dt
        if self.combo_timer <= 0:
            self.combo = 0
            self.combo_multiplier = 1.0

        if self.stun_timer > 0:
            return

        self._handle_movement(dt, keys)
        self._clamp_to_screen()

        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reloading = False
                self._finish_reload()

        if mouse_buttons[0] and self.fire_cooldown <= 0 and not self.reloading:
            self._shoot(mouse_pos, game)

        if (mouse_buttons[2] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and self.dash_cooldown <= 0:
            self._dash(mouse_pos, game)

        if keys[pygame.K_SPACE] and self.wall_cooldown <= 0:
            self._create_wall(mouse_pos, game)

        if keys[pygame.K_q] and self.energy >= REPAIR_COST and self.hp < self.max_hp:
            self._repair(game)

        if keys[pygame.K_e] and self.stealth_cooldown <= 0:
            self._activate_stealth(game)

        if keys[pygame.K_f] and self.emp_cooldown <= 0:
            self._activate_emp(game)

        self._handle_weapon_switch(keys)

        if keys[pygame.K_r] and not self.reloading:
            self._start_reload()

        self.muzzle_flash = max(0, self.muzzle_flash - dt * 10)
        self.hit_flash = max(0, self.hit_flash - dt * 5)

        if self.is_dashing:
            self.dash_ghosts.append({'x': self.x, 'y': self.y, 'life': 0.3})
        for ghost in self.dash_ghosts[:]:
            ghost['life'] -= dt
            if ghost['life'] <= 0:
                self.dash_ghosts.remove(ghost)

        self.effect_system.update(dt, game)

        for minion in self.minions:
            if minion.alive:
                minion.owner = self
                minion.update(dt, game)

        if self.active_protection:
            self.active_protection.apply_regen(self)

    def _update_timers(self, dt: float):
        self.dash_cooldown -= dt
        if self.dash_timer > 0:
            self.dash_timer -= dt
        if self.dash_effect_timer > 0:
            self.dash_effect_timer -= dt
        self.fire_cooldown = max(0, self.fire_cooldown - dt)
        self.dash_cooldown = max(0, self.dash_cooldown - dt)
        self.wall_cooldown = max(0, self.wall_cooldown - dt)
        self.stealth_cooldown = max(0, self.stealth_cooldown - dt)
        self.emp_cooldown = max(0, self.emp_cooldown - dt)
        self.shield_timer = max(0, self.shield_timer - dt)
        self.speed_boost_timer = max(0, self.speed_boost_timer - dt)
        self.invulnerable_timer = max(0, self.invulnerable_timer - dt)

    def _update_status_effects(self, dt: float):
        if self.poison_timer > 0:
            self.poison_timer -= dt
            self.take_damage(int(self.poison_damage * dt), ignore_shield=True)

        if self.burn_timer > 0:
            self.burn_timer -= dt
            self.take_damage(int(self.burn_damage * self.fire_vulnerability * dt), ignore_shield=True)

        if self.slow_timer > 0:
            self.slow_timer -= dt
        else:
            self.slow_multiplier = 1.0

        if self.confusion_timer > 0:
            self.confusion_timer -= dt

        if self.stun_timer > 0:
            self.stun_timer -= dt

    def _handle_movement(self, dt: float, keys):
        if self.confusion_timer > 0:
            dx = 0
            dy = 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy += 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy -= 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx += 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx -= 1
        else:
            dx = 0
            dy = 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1

        current_speed = self.speed * self.slow_multiplier
        if self.speed_boost_timer > 0:
            current_speed *= 1.8

        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.is_dashing = False
            self.x += self.vx * dt
            self.y += self.vy * dt
        else:
            if dx != 0 or dy != 0:
                norm = math.hypot(dx, dy)
                dx = dx / norm * current_speed
                dy = dy / norm * current_speed

            self.vx += (dx - self.vx) * min(1, dt * 10)
            self.vy += (dy - self.vy) * min(1, dt * 10)

            self.x += self.vx * dt
            self.y += self.vy * dt

    def _clamp_to_screen(self):
        if not self.phase_shift:
            self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
            self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))

    def _handle_weapon_switch(self, keys):
        weapon_keys = {
            pygame.K_1: 'pistol',
            pygame.K_2: 'shotgun',
            pygame.K_3: 'laser',
            pygame.K_4: 'plasma_rifle',
            pygame.K_5: 'rocket_launcher',
            pygame.K_6: 'minigun',
            pygame.K_7: 'flamethrower',
            pygame.K_8: 'ice_gun',
            pygame.K_9: 'shock_gun',
            pygame.K_0: 'gravity_gun',
        }

        for key, weapon in weapon_keys.items():
            if keys[key] and weapon in self.weapons and self.current_weapon != weapon:
                self.current_weapon = weapon
                self.reloading = False
                break

    def _shoot(self, mouse_pos: Tuple[float, float], game):
        weapon = self.weapon_manager.get_weapon(self.current_weapon)
        if not weapon:
            weapon_config = WEAPON_TYPES.get(self.current_weapon, WEAPON_TYPES['pistol'])
        else:
            weapon_config = weapon.config

        if self.ammo.get(self.current_weapon, -1) == 0:
            self._start_reload()
            return

        self.fire_cooldown = weapon_config.get('fire_rate', 0.3) * self.fire_rate_multiplier

        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        norm = math.hypot(dx, dy)

        if norm > 0:
            dx /= norm
            dy /= norm

            if self.ammo.get(self.current_weapon, -1) > 0:
                self.ammo[self.current_weapon] -= 1

            if weapon:
                bullets = weapon.shoot(self.x, self.y, (dx, dy), game)
                for bullet in bullets:
                    bullet.damage = int(bullet.damage * self.damage_multiplier)
                    game.bullets.append(bullet)
                    self.just_shot = True
            else:
                self._create_bullet(dx, dy, weapon_config, game)

            self.muzzle_flash = 1.0
            game.sound_manager.play('shoot')

    def _create_bullet(self, dx: float, dy: float, weapon_config: dict, game):
        is_crit = random.random() < self.crit_chance
        damage = int(weapon_config.get('damage', 25) * self.damage_multiplier * (self.crit_multiplier if is_crit else 1))

        bullet = Bullet(self.x, self.y, (dx, dy), True, damage)
        bullet.is_crit = is_crit
        bullet.radius = weapon_config.get('bullet_radius', BULLET_RADIUS)

        if weapon_config.get('piercing'):
            bullet.set_piercing(True)
        if weapon_config.get('explosive'):
            bullet.set_explosive(weapon_config.get('explosion_radius', 50))

        if self.skills['combat']['piercing'] > 0:
            bullet.set_piercing(True)
        if self.skills['combat']['explosive'] > 0:
            bullet.set_explosive(50 + self.skills['combat']['explosive'] * 20)

        game.bullets.append(bullet)

    def _dash(self, mouse_pos: Tuple[float, float], game):
        dash_cd = DASH_COOLDOWN * (1 - self.skills['survival']['dash_cooldown'] * 0.05)
        self.dash_cooldown = dash_cd
        self.dash_effect_timer = 0.25  # Длительность эффекта размытия
        self.is_dashing = True
        self.dash_timer = DASH_DURATION

        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        norm = math.hypot(dx, dy)

        if norm > 0:
            dx = dx / norm * DASH_SPEED
            dy = dy / norm * DASH_SPEED

        self.vx = dx
        self.vy = dy
        self.dash_direction = (dx, dy)
        self.invulnerable_timer = 0.1

        if game.sound_manager:
            game.sound_manager.play('dash')

    def _create_wall(self, mouse_pos: Tuple[float, float], game):
        self.wall_cooldown = WALL_COOLDOWN

        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        norm = math.hypot(dx, dy)

        if norm > 0:
            dx /= norm
            dy /= norm

        wall_x = self.x + dx * 60
        wall_y = self.y + dy * 60

        wall = EnergyWall(wall_x, wall_y)
        game.energy_walls.append(wall)
        game.sound_manager.play('wall')

    def _repair(self, game):
        self.energy -= REPAIR_COST
        heal_amount = REPAIR_AMOUNT * (1 + self.skills['survival']['healing_boost'] * 0.1)
        self.heal(int(heal_amount))
        game.sound_manager.play('repair')

    def _activate_stealth(self, game):
        self.stealth_cooldown = STEALTH_COOLDOWN
        self.invisible = True
        stealth_effect = self.effect_system.create_instance('invisibility')
        if stealth_effect:
            self.effect_system.add_effect(stealth_effect)
        game.sound_manager.play('dash')

    def _activate_emp(self, game):
        self.emp_cooldown = 10.0
        radius = EMP_RADIUS * (1 + self.skills['tech']['emp_radius'] * 0.1)

        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if dist < radius:
                    enemy.take_damage(EMP_DAMAGE)
                    enemy.state = 'patrol'
                    enemy.state_timer = 5.0

        game.spawn_particles(self.x, self.y, 30, CYAN)
        game.spawn_sparks(self.x, self.y, 20)
        game.sound_manager.play('explosion')

    def _start_reload(self):
        weapon = self.weapon_manager.get_weapon(self.current_weapon)
        if weapon:
            max_ammo = weapon.ammo
        else:
            weapon_config = WEAPON_TYPES.get(self.current_weapon, WEAPON_TYPES['pistol'])
            max_ammo = weapon_config.get('ammo', -1)
        if max_ammo > 0 and self.ammo.get(self.current_weapon, -1) < max_ammo:
            self.reloading = True
            self.reload_timer = 1.0

    def _finish_reload(self):
        weapon = self.weapon_manager.get_weapon(self.current_weapon)
        if weapon:
            max_ammo = weapon.ammo
        else:
            weapon_config = WEAPON_TYPES.get(self.current_weapon, WEAPON_TYPES['pistol'])
            max_ammo = weapon_config.get('ammo', -1)
        if max_ammo > 0:
            self.ammo[self.current_weapon] = max_ammo

    def take_damage(self, damage: int, ignore_shield: bool = False):
        if self.invulnerable_timer > 0:
            return

        if not ignore_shield and self.shield_timer > 0:
            return

        damage = int(damage * self.damage_reduction)

        actual_damage = max(1, damage - self.armor)
        self.hp -= actual_damage
        self.damage_taken += actual_damage
        self.hit_flash = 1.0

        if self.effect_system:
            self.effect_system.trigger_all(target=None, game=None, damage=actual_damage, is_damage=True)

        self.combo = 0
        self.combo_multiplier = 1.0

        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def add_exp(self, amount: int):
        self.exp += int(amount * self.exp_multiplier)
        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level += 1
            self.exp_to_next = int(self.exp_to_next * 1.5)
            self.skill_points += 1
            self.max_hp += 5
            self.hp = min(self.max_hp, self.hp + 5)

    def upgrade_skill(self, tree: str, skill: str) -> bool:
        if self.skill_points <= 0:
            return False

        if tree not in self.skills or skill not in self.skills[tree]:
            return False

        self.skills[tree][skill] += 1
        self.skill_points -= 1

        self._apply_skill_effect(tree, skill)

        return True

    def _apply_skill_effect(self, tree: str, skill: str):
        level = self.skills[tree][skill]

        if tree == 'combat':
            if skill == 'damage':
                self.permanent_damage_boost += 10
            elif skill == 'crit_chance':
                self.crit_chance += 0.02
            elif skill == 'crit_damage':
                self.crit_multiplier += 0.1
            elif skill == 'fire_rate':
                self.permanent_fire_rate_boost += 0.05
            elif skill == 'piercing':
                # Also read directly from self.skills['combat']['piercing']
                # in _create_bullet; this flag mirrors that for anything
                # else that wants a simple boolean check.
                self.piercing = level > 0
            elif skill == 'explosive':
                self.explosive = level > 0

        elif tree == 'tech':
            if skill == 'energy_efficiency':
                self.energy_efficiency = 1 - level * 0.05
            elif skill == 'hack_speed':
                self.hack_speed_multiplier = 1 + level * 0.1
            elif skill == 'turret_damage':
                self.turret_damage_multiplier = 1 + level * 0.1
            elif skill == 'drone_damage':
                self.drone_damage_multiplier = 1 + level * 0.1
            elif skill == 'shield_duration':
                self.shield_duration_multiplier = 1 + level * 0.1

        elif tree == 'survival':
            if skill == 'max_hp':
                self.max_hp += 20
                self.hp = min(self.max_hp, self.hp + 20)
            elif skill == 'regen':
                self.regen_rate += 1
            elif skill == 'armor':
                self.armor += 5
            elif skill == 'speed':
                self.permanent_speed_boost += 25
            elif skill == 'dash_cooldown':
                # dash_cooldown skill level is also read directly in _dash()
                # when computing dash_cd; nothing else to do here beyond
                # incrementing the stored skill level (handled by caller).
                pass
            elif skill == 'healing_boost':
                # healing_boost skill level is read directly in _repair()
                # when computing heal_amount; nothing else to do here.
                pass

    def add_combo(self, amount: int = 1):
        self.combo += amount
        self.max_combo = max(self.max_combo, self.combo)
        self.combo_timer = 3.0
        self.combo_multiplier = min(3.0, 1.0 + self.combo * 0.1)

    def get_combo_multiplier(self) -> float:
        return self.combo_multiplier

    def add_weapon(self, weapon: str):
        if weapon not in self.weapons:
            self.weapons.append(weapon)
            self.weapon_levels[weapon] = 1
            if weapon in self.weapon_manager.weapons:
                self.ammo[weapon] = self.weapon_manager.weapons[weapon].ammo
            elif weapon in WEAPON_TYPES and WEAPON_TYPES[weapon].get('ammo', -1) > 0:
                self.ammo[weapon] = WEAPON_TYPES[weapon]['ammo']

    def add_protection(self, protection_id: str):
        protection = self.protection_manager.get_protection(protection_id)
        if protection:
            new_protection = Protection(protection.id, protection.name, protection.config)
            self.protections.append(new_protection)
            if not self.active_protection:
                self.active_protection = new_protection
            return new_protection
        return None

    def equip_protection(self, protection_id: str):
        for protection in self.protections:
            if protection.id == protection_id:
                self.active_protection = protection
                return True
        return False

    def add_minion(self, minion_id: str):
        minion = self.minion_manager.get_minion(minion_id)
        if minion:
            new_minion = Minion(minion.id, minion.name, minion.config)
            new_minion.owner = self
            new_minion.x = self.x + random.randint(-50, 50)
            new_minion.y = self.y + random.randint(-50, 50)
            self.minions.append(new_minion)
            return new_minion
        return None

    def apply_temporary_buff(self, buff_type: str, duration: float):
        if buff_type == "damage_boost":
            self.damage_multiplier *= 1.5
        elif buff_type == "speed_boost":
            self.speed_boost_timer = max(self.speed_boost_timer, duration)
        elif buff_type == "shield":
            self.shield_timer = max(self.shield_timer, duration)

    def save_player_data(self) -> dict:
        data = {
            "x": self.x,
            "y": self.y,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "energy": self.energy,
            "max_energy": self.max_energy,
            "level": self.level,
            "exp": self.exp,
            "exp_to_next": self.exp_to_next,
            "skill_points": self.skill_points,
            "kills": self.kills,
            "damage_dealt": self.damage_dealt,
            "damage_taken": self.damage_taken,
            "pickups_collected": self.pickups_collected,
            "max_combo": self.max_combo,
            "weapons": self.weapons,
            "current_weapon": self.current_weapon,
            "weapon_levels": self.weapon_levels,
            "ammo": self.ammo,
            "skills": self.skills,
            "scrap": self.scrap,
            "circuits": self.circuits,
            "energy_cells": self.energy_cells,
            "crystals": self.crystals,
            "ai_cores": self.ai_cores,
            "organic_tissue": self.organic_tissue,
            "credits": self.credits,
            "plasma_fragments": self.plasma_fragments,
            "dark_matter": self.dark_matter,
            "void_shards": self.void_shards,
            "star_dust": self.star_dust,
            "quantum_foam": self.quantum_foam,
            "nano_swarm": self.nano_swarm,
            "bio_gel": self.bio_gel,
            "mechanical_parts": self.mechanical_parts,
            "laser_lenses": self.laser_lenses,
            "rocket_fuel": self.rocket_fuel,
            "ice_cores": self.ice_cores,
            "thunder_cores": self.thunder_cores,
            "gravity_cores": self.gravity_cores,
            "soul_essence": self.soul_essence,
            "permanent_speed_boost": self.permanent_speed_boost,
            "permanent_damage_boost": self.permanent_damage_boost,
            "permanent_fire_rate_boost": self.permanent_fire_rate_boost,
            "reputation": self.reputation,
            "story_flags": self.story_flags,
            "completed_quests": self.completed_quests,
        }
        return data

    def load_player_data(self, data: dict):
        self.x = data.get("x", self.x)
        self.y = data.get("y", self.y)
        self.hp = data.get("hp", self.hp)
        self.max_hp = data.get("max_hp", self.max_hp)
        self.energy = data.get("energy", self.energy)
        self.max_energy = data.get("max_energy", self.max_energy)
        self.level = data.get("level", self.level)
        self.exp = data.get("exp", self.exp)
        self.exp_to_next = data.get("exp_to_next", self.exp_to_next)
        self.skill_points = data.get("skill_points", self.skill_points)
        self.kills = data.get("kills", self.kills)
        self.damage_dealt = data.get("damage_dealt", self.damage_dealt)
        self.damage_taken = data.get("damage_taken", self.damage_taken)
        self.pickups_collected = data.get("pickups_collected", self.pickups_collected)
        self.max_combo = data.get("max_combo", self.max_combo)
        self.weapons = data.get("weapons", self.weapons)
        self.current_weapon = data.get("current_weapon", self.current_weapon)
        self.weapon_levels = data.get("weapon_levels", self.weapon_levels)
        self.ammo = data.get("ammo", self.ammo)
        self.skills = data.get("skills", self.skills)
        self.scrap = data.get("scrap", self.scrap)
        self.circuits = data.get("circuits", self.circuits)
        self.energy_cells = data.get("energy_cells", self.energy_cells)
        self.crystals = data.get("crystals", self.crystals)
        self.ai_cores = data.get("ai_cores", self.ai_cores)
        self.organic_tissue = data.get("organic_tissue", self.organic_tissue)
        self.credits = data.get("credits", self.credits)
        self.plasma_fragments = data.get("plasma_fragments", self.plasma_fragments)
        self.dark_matter = data.get("dark_matter", self.dark_matter)
        self.void_shards = data.get("void_shards", self.void_shards)
        self.star_dust = data.get("star_dust", self.star_dust)
        self.quantum_foam = data.get("quantum_foam", self.quantum_foam)
        self.nano_swarm = data.get("nano_swarm", self.nano_swarm)
        self.bio_gel = data.get("bio_gel", self.bio_gel)
        self.mechanical_parts = data.get("mechanical_parts", self.mechanical_parts)
        self.laser_lenses = data.get("laser_lenses", self.laser_lenses)
        self.rocket_fuel = data.get("rocket_fuel", self.rocket_fuel)
        self.ice_cores = data.get("ice_cores", self.ice_cores)
        self.thunder_cores = data.get("thunder_cores", self.thunder_cores)
        self.gravity_cores = data.get("gravity_cores", self.gravity_cores)
        self.soul_essence = data.get("soul_essence", self.soul_essence)
        self.permanent_speed_boost = data.get("permanent_speed_boost", self.permanent_speed_boost)
        self.permanent_damage_boost = data.get("permanent_damage_boost", self.permanent_damage_boost)
        self.permanent_fire_rate_boost = data.get("permanent_fire_rate_boost", self.permanent_fire_rate_boost)
        self.reputation = data.get("reputation", self.reputation)
        self.story_flags = data.get("story_flags", self.story_flags)
        self.completed_quests = data.get("completed_quests", self.completed_quests)
        self._init_ammo()

    def get_resource_dict(self) -> Dict[str, int]:
        return {
            "scrap": self.scrap,
            "circuit": self.circuits,
            "energy_cell": self.energy_cells,
            "crystal": self.crystals,
            "ai_core": self.ai_cores,
            "organic_tissue": self.organic_tissue,
            "plasma_fragment": self.plasma_fragments,
            "dark_matter": self.dark_matter,
            "void_shard": self.void_shards,
            "star_dust": self.star_dust,
            "quantum_foam": self.quantum_foam,
            "nano_swarm": self.nano_swarm,
            "bio_gel": self.bio_gel,
            "mechanical_parts": self.mechanical_parts,
            "laser_lens": self.laser_lenses,
            "rocket_fuel": self.rocket_fuel,
            "ice_core": self.ice_cores,
            "thunder_core": self.thunder_cores,
            "gravity_core": self.gravity_cores,
            "soul_essence": self.soul_essence,
        }

    def add_resource(self, resource_id: str, amount: int = 1):
        if resource_id == "scrap":
            self.scrap += amount
        elif resource_id == "circuit":
            self.circuits += amount
        elif resource_id == "energy_cell":
            self.energy_cells += amount
        elif resource_id == "crystal":
            self.crystals += amount
        elif resource_id == "ai_core":
            self.ai_cores += amount
        elif resource_id == "organic_tissue":
            self.organic_tissue += amount
        elif resource_id == "plasma_fragment":
            self.plasma_fragments += amount
        elif resource_id == "dark_matter":
            self.dark_matter += amount
        elif resource_id == "void_shard":
            self.void_shards += amount
        elif resource_id == "star_dust":
            self.star_dust += amount
        elif resource_id == "quantum_foam":
            self.quantum_foam += amount
        elif resource_id == "nano_swarm":
            self.nano_swarm += amount
        elif resource_id == "bio_gel":
            self.bio_gel += amount
        elif resource_id == "mechanical_parts":
            self.mechanical_parts += amount
        elif resource_id == "laser_lens":
            self.laser_lenses += amount
        elif resource_id == "rocket_fuel":
            self.rocket_fuel += amount
        elif resource_id == "ice_core":
            self.ice_cores += amount
        elif resource_id == "thunder_core":
            self.thunder_cores += amount
        elif resource_id == "gravity_core":
            self.gravity_cores += amount
        elif resource_id == "soul_essence":
            self.soul_essence += amount

    def remove_resource(self, resource_id: str, amount: int = 1) -> bool:
        resources = self.get_resource_dict()
        if resources.get(resource_id, 0) >= amount:
            self.add_resource(resource_id, -amount)
            return True
        return False

    def craft_item(self, recipe_id: str) -> bool:
        return self.crafting_system.craft(recipe_id)

    def get_crafting_inventory(self) -> Dict[str, int]:
        return self.crafting_system.get_inventory()

    def set_crafting_inventory(self, inventory: Dict[str, int]):
        self.crafting_system.set_inventory(inventory)

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        for ghost in self.dash_ghosts:
            alpha = int(255 * ghost['life'] / 0.3)
            ghost_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surf, (0, 200, 255, alpha), (self.radius, self.radius), self.radius)
            screen.blit(ghost_surf, (ghost['x'] - self.radius, ghost['y'] - self.radius))

        if self.invisible:
            color = (50, 50, 50)
        elif self.shield_timer > 0:
            color = CYAN
        elif self.invulnerable_timer > 0:
            color = WHITE
        else:
            color = BLUE

        if self.hit_flash > 0:
            color = RED

        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 3)

        mouse_x, mouse_y = pygame.mouse.get_pos()
        angle = math.atan2(mouse_y - self.y, mouse_x - self.x)
        eye_x = self.x + math.cos(angle) * self.radius * 0.5
        eye_y = self.y + math.sin(angle) * self.radius * 0.5
        pygame.draw.circle(screen, WHITE, (int(eye_x), int(eye_y)), 4)

        if self.muzzle_flash > 0:
            flash_radius = int(self.radius * (1 + self.muzzle_flash))
            pygame.draw.circle(screen, YELLOW, (int(eye_x), int(eye_y)), flash_radius, 2)

        if self.shield_timer > 0:
            shield_alpha = int(100 + 50 * math.sin(pygame.time.get_ticks() * 0.01))
            shield_surf = pygame.Surface((self.radius * 3, self.radius * 3), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (0, 200, 255, shield_alpha),
                               (self.radius * 1.5, self.radius * 1.5), self.radius * 1.3, 3)
            screen.blit(shield_surf, (self.x - self.radius * 1.5, self.y - self.radius * 1.5))

        self._draw_health_bar(screen)
        self._draw_energy_bar(screen)

        if self.reloading:
            self._draw_reload_indicator(screen)

        if self.combo > 5:
            self._draw_combo(screen)

        for minion in self.minions:
            if minion.alive:
                minion.draw(screen)

    def _draw_health_bar(self, screen: pygame.Surface):
        bar_width = 50
        bar_height = 6
        ratio = self.hp / self.max_hp
        bar_x = self.x - bar_width // 2
        bar_y = self.y - self.radius - 15

        pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_width, bar_height))
        hp_color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
        pygame.draw.rect(screen, hp_color, (bar_x, bar_y, bar_width * ratio, bar_height))
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_energy_bar(self, screen: pygame.Surface):
        bar_width = 50
        bar_height = 4
        ratio = self.energy / PLAYER_MAX_ENERGY
        bar_x = self.x - bar_width // 2
        bar_y = self.y - self.radius - 8

        pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, YELLOW, (bar_x, bar_y, bar_width * ratio, bar_height))

    def _draw_reload_indicator(self, screen: pygame.Surface):
        font = pygame.font.Font(None, 20)
        text = font.render("Перезарядка...", True, YELLOW)
        screen.blit(text, (self.x - text.get_width() // 2, self.y + self.radius + 10))

    def _draw_combo(self, screen: pygame.Surface):
        font = pygame.font.Font(None, 24)
        combo_text = f"x{self.combo_multiplier:.1f}"
        text_surf = font.render(combo_text, True, ORANGE)
        screen.blit(text_surf, (self.x - text_surf.get_width() // 2, self.y - self.radius - 40))