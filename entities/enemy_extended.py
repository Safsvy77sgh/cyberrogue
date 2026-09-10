# entities/enemy_extended.py — ЧАСТЬ 1
# entities/enemy_extended.py — добавьте в начало файла

from entities.pickup import Pickup
import math
import random
import pygame
import json
import os
from typing import Dict, List, Tuple, Optional, Any, Callable
from settings import *
from entities.bullet import Bullet
from systems.evolutionary_ai import AIIndividual, BehaviorGene, SituationalRule
from systems.adaptive_enemies import AdaptiveEnemyController, CombatMemory
from systems.weapons_extended import WeaponManager, Weapon
from systems.protection import ProtectionManager, Protection
from systems.minions import MinionManager, Minion
from systems.effects import EffectSystem, EffectData, EffectInstance
from systems.crafting_extended import CraftingSystemExtended


class EnemyLootTable:
    def __init__(self):
        self.loot_entries = []
        self._init_default_loot()

    def _init_default_loot(self):
        self.loot_entries = [
            {"type": "scrap", "weight": 30, "min_amount": 1, "max_amount": 5},
            {"type": "circuit", "weight": 20, "min_amount": 1, "max_amount": 3},
            {"type": "energy_cell", "weight": 10, "min_amount": 1, "max_amount": 2},
            {"type": "organic_tissue", "weight": 15, "min_amount": 1, "max_amount": 3},
            {"type": "bio_gel", "weight": 10, "min_amount": 1, "max_amount": 2},
            {"type": "mechanical_parts", "weight": 15, "min_amount": 1, "max_amount": 3},
            {"type": "crystal", "weight": 3, "min_amount": 1, "max_amount": 1},
            {"type": "plasma_fragment", "weight": 2, "min_amount": 1, "max_amount": 1},
            {"type": "quantum_foam", "weight": 1, "min_amount": 1, "max_amount": 1},
            {"type": "nano_swarm", "weight": 1, "min_amount": 1, "max_amount": 1},
            {"type": "laser_lens", "weight": 1, "min_amount": 1, "max_amount": 1},
            {"type": "rocket_fuel", "weight": 1, "min_amount": 1, "max_amount": 1},
            {"type": "ice_core", "weight": 0.5, "min_amount": 1, "max_amount": 1},
            {"type": "thunder_core", "weight": 0.5, "min_amount": 1, "max_amount": 1},
            {"type": "gravity_core", "weight": 0.2, "min_amount": 1, "max_amount": 1},
            {"type": "void_shard", "weight": 0.1, "min_amount": 1, "max_amount": 1},
            {"type": "dark_matter", "weight": 0.05, "min_amount": 1, "max_amount": 1},
            {"type": "star_dust", "weight": 0.05, "min_amount": 1, "max_amount": 1},
            {"type": "soul_essence", "weight": 0.1, "min_amount": 1, "max_amount": 1},
            {"type": "ai_core", "weight": 0.05, "min_amount": 1, "max_amount": 1},
        ]

    def generate_loot(self, wave: int = 1) -> List[Dict]:
        loot = []
        total_weight = sum(entry["weight"] for entry in self.loot_entries)
        num_rolls = random.randint(1, 3 + wave // 5)
        for _ in range(num_rolls):
            roll = random.uniform(0, total_weight)
            for entry in self.loot_entries:
                roll -= entry["weight"]
                if roll <= 0:
                    amount = random.randint(entry["min_amount"], entry["max_amount"])
                    loot.append({"type": entry["type"], "amount": amount})
                    break
        return loot


class EnemyWeaponDrop:
    def __init__(self):
        self.weapon_drops = []
        self._init_weapon_drops()

    def _init_weapon_drops(self):
        self.weapon_drops = [
            {"weapon_id": "pistol", "weight": 20, "min_wave": 1},
            {"weapon_id": "shotgun", "weight": 15, "min_wave": 2},
            {"weapon_id": "laser", "weight": 12, "min_wave": 3},
            {"weapon_id": "rocket_launcher", "weight": 8, "min_wave": 4},
            {"weapon_id": "plasma_rifle", "weight": 6, "min_wave": 5},
            {"weapon_id": "minigun", "weight": 5, "min_wave": 5},
            {"weapon_id": "flamethrower", "weight": 5, "min_wave": 3},
            {"weapon_id": "ice_gun", "weight": 5, "min_wave": 3},
            {"weapon_id": "shock_gun", "weight": 5, "min_wave": 3},
            {"weapon_id": "gravity_gun", "weight": 4, "min_wave": 4},
            {"weapon_id": "homing_launcher", "weight": 3, "min_wave": 5},
            {"weapon_id": "void_rifle", "weight": 2, "min_wave": 6},
            {"weapon_id": "railgun", "weight": 2, "min_wave": 5},
            {"weapon_id": "gauss_rifle", "weight": 2, "min_wave": 5},
            {"weapon_id": "tesla_gun", "weight": 2, "min_wave": 4},
            {"weapon_id": "nova_cannon", "weight": 1, "min_wave": 6},
            {"weapon_id": "singularity_gun", "weight": 0.5, "min_wave": 7},
            {"weapon_id": "doom_cannon", "weight": 0.1, "min_wave": 8},
        ]

    def generate_weapon_drop(self, wave: int) -> Optional[str]:
        available = [w for w in self.weapon_drops if wave >= w["min_wave"]]
        if not available:
            return None
        total_weight = sum(w["weight"] for w in available)
        roll = random.uniform(0, total_weight)
        for weapon in available:
            roll -= weapon["weight"]
            if roll <= 0:
                return weapon["weapon_id"]
        return None


class EnemyProtectionDrop:
    def __init__(self):
        self.protection_drops = []
        self._init_protection_drops()

    def _init_protection_drops(self):
        self.protection_drops = [
            {"protection_id": "light_armor", "weight": 20, "min_wave": 1},
            {"protection_id": "medium_armor", "weight": 15, "min_wave": 2},
            {"protection_id": "heavy_armor", "weight": 10, "min_wave": 3},
            {"protection_id": "energy_shield", "weight": 8, "min_wave": 3},
            {"protection_id": "reflective_shield", "weight": 5, "min_wave": 4},
            {"protection_id": "nanite_armor", "weight": 4, "min_wave": 5},
            {"protection_id": "crystal_shield", "weight": 3, "min_wave": 5},
            {"protection_id": "titan_plate", "weight": 2, "min_wave": 6},
            {"protection_id": "quantum_shield", "weight": 1, "min_wave": 6},
            {"protection_id": "dragon_scale", "weight": 1, "min_wave": 5},
            {"protection_id": "phoenix_feather", "weight": 0.5, "min_wave": 6},
            {"protection_id": "titan_armor", "weight": 0.3, "min_wave": 7},
            {"protection_id": "void_armor_extended", "weight": 0.2, "min_wave": 7},
            {"protection_id": "galaxy_armor", "weight": 0.1, "min_wave": 8},
        ]

    def generate_protection_drop(self, wave: int) -> Optional[str]:
        available = [p for p in self.protection_drops if wave >= p["min_wave"]]
        if not available:
            return None
        total_weight = sum(p["weight"] for p in available)
        roll = random.uniform(0, total_weight)
        for protection in available:
            roll -= protection["weight"]
            if roll <= 0:
                return protection["protection_id"]
        return None


class EnemyMinionDrop:
    def __init__(self):
        self.minion_drops = []
        self._init_minion_drops()

    def _init_minion_drops(self):
        self.minion_drops = [
            {"minion_id": "drone", "weight": 15, "min_wave": 1},
            {"minion_id": "turret", "weight": 10, "min_wave": 2},
            {"minion_id": "healer", "weight": 8, "min_wave": 2},
            {"minion_id": "assault_drone", "weight": 5, "min_wave": 3},
            {"minion_id": "sniper_drone", "weight": 3, "min_wave": 3},
            {"minion_id": "heavy_drone", "weight": 2, "min_wave": 4},
            {"minion_id": "shield_drone", "weight": 2, "min_wave": 3},
            {"minion_id": "repair_drone", "weight": 2, "min_wave": 3},
            {"minion_id": "emp_drone", "weight": 1, "min_wave": 4},
            {"minion_id": "flame_drone", "weight": 1, "min_wave": 3},
            {"minion_id": "ice_drone", "weight": 1, "min_wave": 3},
            {"minion_id": "shock_drone", "weight": 1, "min_wave": 3},
            {"minion_id": "ninja_drone", "weight": 0.5, "min_wave": 4},
            {"minion_id": "kamikaze_drone", "weight": 0.5, "min_wave": 3},
            {"minion_id": "teleport_drone", "weight": 0.3, "min_wave": 4},
            {"minion_id": "gravity_drone", "weight": 0.3, "min_wave": 5},
            {"minion_id": "summoner_drone", "weight": 0.2, "min_wave": 5},
            {"minion_id": "void_drone", "weight": 0.1, "min_wave": 6},
            {"minion_id": "artillery_drone", "weight": 0.1, "min_wave": 5},
        ]

    def generate_minion_drop(self, wave: int) -> Optional[str]:
        available = [m for m in self.minion_drops if wave >= m["min_wave"]]
        if not available:
            return None
        total_weight = sum(m["weight"] for m in available)
        roll = random.uniform(0, total_weight)
        for minion in available:
            roll -= minion["weight"]
            if roll <= 0:
                return minion["minion_id"]
        return None


class EnemyBossAI:
    def __init__(self, enemy):
        self.enemy = enemy
        self.phase = 1
        self.ability_cooldowns = {}
        self.attack_patterns = []
        self.current_pattern = None
        self.pattern_timer = 0.0
        self.pattern_index = 0
        self._init_ability_cooldowns()
        self._init_attack_patterns()

    def _init_ability_cooldowns(self):
        self.ability_cooldowns = {
            "summon": 10.0,
            "teleport": 5.0,
            "multi_shot": 3.0,
            "regen_burst": 8.0,
            "shield_wall": 12.0,
            "meteor_strike": 15.0,
            "void_rift": 20.0,
            "time_stop": 18.0,
            "gravity_well": 7.0,
        }

    def _init_attack_patterns(self):
        self.attack_patterns = [
            {"name": "basic_shot", "duration": 2.0},
            {"name": "multi_shot", "duration": 1.5},
            {"name": "summon", "duration": 3.0},
            {"name": "teleport", "duration": 1.0},
            {"name": "meteor", "duration": 2.5},
            {"name": "void_rift", "duration": 2.0},
            {"name": "time_stop", "duration": 1.5},
            {"name": "gravity_well", "duration": 2.5},
        ]

    def update(self, dt, player, game):
        for ability in self.ability_cooldowns:
            self.ability_cooldowns[ability] = max(0, self.ability_cooldowns[ability] - dt)

        if self.current_pattern is None:
            self._choose_pattern()
        else:
            self.pattern_timer -= dt
            if self.pattern_timer <= 0:
                self.current_pattern = None

        if self.current_pattern:
            self._execute_pattern(dt, player, game)

    def _choose_pattern(self):
        if self.enemy.boss_phase == 1:
            patterns = ["basic_shot", "multi_shot", "summon"]
        elif self.enemy.boss_phase == 2:
            patterns = ["basic_shot", "multi_shot", "teleport", "gravity_well"]
        else:
            patterns = ["basic_shot", "multi_shot", "summon", "teleport", "meteor", "void_rift", "time_stop", "gravity_well"]
        self.current_pattern = random.choice(patterns)
        pattern_data = next((p for p in self.attack_patterns if p["name"] == self.current_pattern), None)
        if pattern_data:
            self.pattern_timer = pattern_data["duration"]

    def _execute_pattern(self, dt, player, game):
        if self.current_pattern == "basic_shot":
            self._basic_shot(player, game)
        elif self.current_pattern == "multi_shot":
            self._multi_shot(player, game)
        elif self.current_pattern == "summon":
            self._summon_minions(game)
        elif self.current_pattern == "teleport":
            self._teleport(player)
        elif self.current_pattern == "meteor":
            self._meteor_strike(player, game)
        elif self.current_pattern == "void_rift":
            self._void_rift(player, game)
        elif self.current_pattern == "time_stop":
            self._time_stop(game)
        elif self.current_pattern == "gravity_well":
            self._gravity_well(player, game)

    def _basic_shot(self, player, game):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            bullet = Bullet(self.enemy.x, self.enemy.y, (dx/norm, dy/norm), False, self.enemy.damage)
            game.enemy_bullets.append(bullet)

    def _multi_shot(self, player, game):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            for i in range(-3, 4):
                angle = math.atan2(dy, dx) + i * 0.3
                bullet = Bullet(self.enemy.x, self.enemy.y, (math.cos(angle), math.sin(angle)), False, self.enemy.damage)
                game.enemy_bullets.append(bullet)

    def _summon_minions(self, game):
        if self.ability_cooldowns["summon"] > 0:
            return
        self.ability_cooldowns["summon"] = 10.0
        minion_manager = MinionManager()
        for _ in range(3):
            minion_id = random.choice(["drone", "assault_drone", "heavy_drone"])
            minion = minion_manager.spawn_minion(minion_id, self.enemy.x + random.randint(-100, 100), self.enemy.y + random.randint(-100, 100), self.enemy)
            if minion:
                # Minions are not Enemy instances, so they must not go into
                # game.enemies (player-vs-enemy collision/update code assumes
                # the Enemy interface there). Keep them in their own list
                # instead, created lazily so no other file needs to know
                # about this ahead of time.
                if not hasattr(game, 'enemy_minions'):
                    game.enemy_minions = []
                game.enemy_minions.append(minion)

    def _teleport(self, player):
        if self.ability_cooldowns["teleport"] > 0:
            return
        self.ability_cooldowns["teleport"] = 5.0
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(150, 300)
        self.enemy.x = player.x + math.cos(angle) * distance
        self.enemy.y = player.y + math.sin(angle) * distance

    def _meteor_strike(self, player, game):
        if self.ability_cooldowns["meteor_strike"] > 0:
            return
        self.ability_cooldowns["meteor_strike"] = 15.0
        for _ in range(5):
            x = player.x + random.randint(-200, 200)
            y = player.y + random.randint(-200, 200)
            game.collision_system._handle_explosion(x, y, 80)

    def _void_rift(self, player, game):
        if self.ability_cooldowns["void_rift"] > 0:
            return
        self.ability_cooldowns["void_rift"] = 20.0
        game.collision_system._handle_explosion(self.enemy.x, self.enemy.y, 150)

    def _time_stop(self, game):
        if self.ability_cooldowns["time_stop"] > 0:
            return
        self.ability_cooldowns["time_stop"] = 18.0
        game.time_scale = 0.2
        game.time_scale_timer = 2.0

    def _gravity_well(self, player, game):
        if self.ability_cooldowns["gravity_well"] > 0:
            return
        self.ability_cooldowns["gravity_well"] = 7.0
        for enemy in game.enemies:
            if enemy.alive and enemy != self.enemy:
                dx = self.enemy.x - enemy.x
                dy = self.enemy.y - enemy.y
                enemy.x += dx * 0.1
                enemy.y += dy * 0.1


class EnemySpecialAttacks:
    def __init__(self, enemy):
        self.enemy = enemy
        self.special_attacks = []
        self._init_special_attacks()

    def _init_special_attacks(self):
        if self.enemy.type == 'fast':
            self.special_attacks.append('blitz')
            self.special_attacks.append('afterimage')
        elif self.enemy.type == 'tank':
            self.special_attacks.append('ground_slam')
            self.special_attacks.append('shield_bash')
        elif self.enemy.type == 'shooter':
            self.special_attacks.append('barrage')
            self.special_attacks.append('sniper_shot')
        elif self.enemy.type == 'elite':
            self.special_attacks.append('dash_strike')
            self.special_attacks.append('energy_blast')
            self.special_attacks.append('teleport_strike')
        elif self.enemy.type == 'hybrid':
            self.special_attacks.append('bio_plasma')
            self.special_attacks.append('neural_disrupt')
            self.special_attacks.append('regeneration_burst')
        elif self.enemy.type == 'avatar':
            self.special_attacks.append('reality_break')
            self.special_attacks.append('dimensional_shift')
            self.special_attacks.append('cosmic_ray')
            self.special_attacks.append('void_implosion')

    def execute_special_attack(self, attack_name, player, game):
        if attack_name == 'blitz':
            self._blitz(player)
        elif attack_name == 'afterimage':
            self._afterimage()
        elif attack_name == 'ground_slam':
            self._ground_slam(game)
        elif attack_name == 'shield_bash':
            self._shield_bash(player)
        elif attack_name == 'barrage':
            self._barrage(player, game)
        elif attack_name == 'sniper_shot':
            self._sniper_shot(player, game)
        elif attack_name == 'dash_strike':
            self._dash_strike(player)
        elif attack_name == 'energy_blast':
            self._energy_blast(player, game)
        elif attack_name == 'teleport_strike':
            self._teleport_strike(player)
        elif attack_name == 'bio_plasma':
            self._bio_plasma(player, game)
        elif attack_name == 'neural_disrupt':
            self._neural_disrupt(player)
        elif attack_name == 'regeneration_burst':
            self._regeneration_burst()
        elif attack_name == 'reality_break':
            self._reality_break(game)
        elif attack_name == 'dimensional_shift':
            self._dimensional_shift()
        elif attack_name == 'cosmic_ray':
            self._cosmic_ray(player, game)
        elif attack_name == 'void_implosion':
            self._void_implosion(game)

    def _blitz(self, player):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            self.enemy.x += (dx/norm) * self.enemy.speed * 5
            self.enemy.y += (dy/norm) * self.enemy.speed * 5

    def _afterimage(self):
        self.enemy.invulnerable_timer = max(getattr(self.enemy, 'invulnerable_timer', 0), 0.5)

    def _ground_slam(self, game):
        game.collision_system._handle_explosion(self.enemy.x, self.enemy.y, 100)

    def _shield_bash(self, player):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            player.x += (dx/norm) * 50
            player.y += (dy/norm) * 50
            player.take_damage(self.enemy.damage * 1.5)

    def _barrage(self, player, game):
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            bullet = Bullet(self.enemy.x, self.enemy.y, (math.cos(angle), math.sin(angle)), False, self.enemy.damage)
            game.enemy_bullets.append(bullet)

    def _sniper_shot(self, player, game):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            bullet = Bullet(self.enemy.x, self.enemy.y, (dx/norm, dy/norm), False, self.enemy.damage * 3)
            bullet.set_piercing(True)
            game.enemy_bullets.append(bullet)

    def _dash_strike(self, player):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            self.enemy.x += (dx/norm) * 200
            self.enemy.y += (dy/norm) * 200
            if math.hypot(player.x - self.enemy.x, player.y - self.enemy.y) < self.enemy.radius + player.radius:
                player.take_damage(self.enemy.damage * 2)

    def _energy_blast(self, player, game):
        game.collision_system._handle_explosion(self.enemy.x, self.enemy.y, 150)

    def _teleport_strike(self, player):
        self.enemy.x = player.x
        self.enemy.y = player.y
        player.take_damage(self.enemy.damage * 1.5)

    def _bio_plasma(self, player, game):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            bullet = Bullet(self.enemy.x, self.enemy.y, (dx/norm, dy/norm), False, self.enemy.damage * 2)
            bullet.set_explosive(60)
            game.enemy_bullets.append(bullet)

    def _neural_disrupt(self, player):
        player.confusion_timer = 3.0

    def _regeneration_burst(self):
        self.enemy.hp = min(self.enemy.max_hp, self.enemy.hp + self.enemy.max_hp * 0.3)

    def _reality_break(self, game):
        game.screen_shake = 1.0
        game.flash_alpha = 0.5
        game.flash_color = WHITE
        game.time_scale = 0.5
        game.time_scale_timer = 2.0

    def _dimensional_shift(self):
        self.enemy.invulnerable_timer = max(getattr(self.enemy, 'invulnerable_timer', 0), 2.0)

    def _cosmic_ray(self, player, game):
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            bullet = Bullet(self.enemy.x, self.enemy.y, (dx/norm, dy/norm), False, self.enemy.damage * 5)
            bullet.set_piercing(True)
            bullet.set_explosive(120)
            game.enemy_bullets.append(bullet)

    def _void_implosion(self, game):
        game.collision_system._handle_explosion(self.enemy.x, self.enemy.y, 300)


class EnemyEffectController:
    def __init__(self, enemy):
        self.enemy = enemy
        self.effect_system = EffectSystem(enemy)
        self.active_effects = []

    def apply_effect(self, effect_id, source=None):
        effect_instance = self.effect_system.create_instance(effect_id, source)
        if effect_instance:
            self.effect_system.add_effect(effect_instance)
            self.active_effects.append(effect_instance)
            return True
        return False

    def remove_effect(self, effect_id):
        self.effect_system.remove_effect(effect_id)
        self.active_effects = [e for e in self.active_effects if e.data.id != effect_id]

    def update(self, dt, game):
        self.effect_system.update(dt, game)

    def trigger_all(self, target=None, game=None, **kwargs):
        self.effect_system.trigger_all(target=target, game=game, **kwargs)

    def has_effect(self, effect_id):
        return self.effect_system.has_effect(effect_id)


class EnemyCombatAI:
    def __init__(self, enemy):
        self.enemy = enemy
        self.combat_memory = CombatMemory()
        self.adaptive_params = {
            'aggression_modifier': 1.0,
            'dodge_modifier': 1.0,
            'retreat_modifier': 1.0,
            'strafe_modifier': 1.0,
            'attack_range_modifier': 1.0,
            'ability_usage_modifier': 1.0,
        }
        self.effectiveness_tracker = {
            'aggression_success': 0,
            'aggression_fail': 0,
            'dodge_success': 0,
            'dodge_fail': 0,
            'retreat_success': 0,
            'retreat_fail': 0,
            'strafe_success': 0,
            'strafe_fail': 0,
        }
        self.last_adaptation_time = 0
        self.adaptation_interval = 2.0
        self.predicted_player_position = (0, 0)
        self.prediction_confidence = 0.0
        self.current_strategy = 'balanced'
        self.strategy_history = []
        self.strategy_success = {}

    def update(self, dt, player, game):
        self._update_memory(dt, player)
        self._update_prediction(player)
        self._adapt_parameters(dt)
        self._select_strategy(player)
        self._apply_strategy(dt, player, game)
        self._update_effectiveness(dt, player)

    def _update_memory(self, dt, player):
        self.combat_memory.add_player_position(player.x, player.y)
        speed = math.hypot(player.vx, player.vy) if hasattr(player, 'vx') else 0
        if speed > 300:
            action = 'sprinting'
        elif speed > 100:
            action = 'moving'
        elif hasattr(player, 'is_dashing') and player.is_dashing:
            action = 'dashing'
        elif hasattr(player, 'fire_cooldown') and player.fire_cooldown > 0:
            action = 'attacking'
        else:
            action = 'idle'
        self.combat_memory.add_player_action(action)
        if hasattr(player, 'is_dashing') and player.is_dashing:
            direction = self.combat_memory.get_player_movement_direction()
            self.combat_memory.player_dodge_pattern.append(direction)

    def _update_prediction(self, player):
        self.predicted_player_position = self.combat_memory.predict_player_position(0.5)
        if len(self.combat_memory.player_positions) >= 5:
            movement_direction = self.combat_memory.get_player_movement_direction()
            self.prediction_confidence = 0.9 if movement_direction == 'stationary' else 0.6
        else:
            self.prediction_confidence = 0.3

    def _adapt_parameters(self, dt):
        self.last_adaptation_time += dt
        if self.last_adaptation_time < self.adaptation_interval:
            return
        self.last_adaptation_time = 0
        total_aggression = self.effectiveness_tracker['aggression_success'] + self.effectiveness_tracker['aggression_fail']
        if total_aggression > 0:
            success_rate = self.effectiveness_tracker['aggression_success'] / total_aggression
            self.adaptive_params['aggression_modifier'] *= 0.8 if success_rate < 0.3 else 1.2 if success_rate > 0.7 else 1.0
        total_dodge = self.effectiveness_tracker['dodge_success'] + self.effectiveness_tracker['dodge_fail']
        if total_dodge > 0:
            success_rate = self.effectiveness_tracker['dodge_success'] / total_dodge
            self.adaptive_params['dodge_modifier'] *= 0.7 if success_rate < 0.3 else 1.3 if success_rate > 0.7 else 1.0
        total_retreat = self.effectiveness_tracker['retreat_success'] + self.effectiveness_tracker['retreat_fail']
        if total_retreat > 0:
            success_rate = self.effectiveness_tracker['retreat_success'] / total_retreat
            self.adaptive_params['retreat_modifier'] *= 0.7 if success_rate < 0.3 else 1.3 if success_rate > 0.7 else 1.0
        total_strafe = self.effectiveness_tracker['strafe_success'] + self.effectiveness_tracker['strafe_fail']
        if total_strafe > 0:
            success_rate = self.effectiveness_tracker['strafe_success'] / total_strafe
            self.adaptive_params['strafe_modifier'] *= 0.8 if success_rate < 0.3 else 1.2 if success_rate > 0.7 else 1.0
        for key in self.adaptive_params:
            self.adaptive_params[key] = max(0.3, min(3.0, self.adaptive_params[key]))
        for key in self.effectiveness_tracker:
            self.effectiveness_tracker[key] = 0

    def _select_strategy(self, player):
        dist = math.hypot(self.enemy.x - player.x, self.enemy.y - player.y)
        player_hp_ratio = player.hp / player.max_hp if hasattr(player, 'max_hp') else 1.0
        enemy_hp_ratio = self.enemy.hp / self.enemy.max_hp if hasattr(self.enemy, 'max_hp') else 1.0
        if enemy_hp_ratio < 0.3:
            strategy = 'desperate'
        elif player_hp_ratio < 0.3:
            strategy = 'aggressive'
        elif dist < 150:
            strategy = 'close_combat'
        elif dist > 400:
            strategy = 'long_range'
        elif hasattr(player, 'shield_timer') and player.shield_timer > 0:
            strategy = 'defensive'
        elif hasattr(player, 'reloading') and player.reloading:
            strategy = 'opportunistic'
        else:
            strategy = 'balanced'
        if strategy != self.current_strategy:
            self.strategy_history.append(self.current_strategy)
            self.current_strategy = strategy

    def _apply_strategy(self, dt, player, game):
        dist = math.hypot(self.enemy.x - player.x, self.enemy.y - player.y)
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)
        if norm == 0:
            return
        dir_x, dir_y = dx/norm, dy/norm

        if self.current_strategy == 'aggressive':
            aggression = self.enemy.aggression * self.adaptive_params['aggression_modifier']
            if random.random() < aggression:
                self.enemy.x += dir_x * self.enemy.speed * dt
                self.enemy.y += dir_y * self.enemy.speed * dt
            if self.enemy.fire_cooldown <= 0 and dist < 450:
                self.enemy.fire_cooldown = self.enemy.fire_rate
                self.enemy._attack(dir_x, dir_y, game)
                self.effectiveness_tracker['aggression_success'] += 1

        elif self.current_strategy == 'defensive':
            retreat = self.adaptive_params['retreat_modifier']
            if random.random() < retreat:
                self.enemy.x -= dir_x * self.enemy.speed * dt
                self.enemy.y -= dir_y * self.enemy.speed * dt
                self.effectiveness_tracker['retreat_success'] += 1
            if self.enemy.fire_cooldown <= 0 and dist > 200:
                self.enemy.fire_cooldown = self.enemy.fire_rate
                self.enemy._attack(dir_x, dir_y, game)

        elif self.current_strategy == 'close_combat':
            strafe = self.adaptive_params['strafe_modifier']
            if random.random() < strafe:
                strafe_dir = 1 if random.random() < 0.5 else -1
                self.enemy.x += -dir_y * strafe_dir * self.enemy.speed * dt
                self.enemy.y += dir_x * strafe_dir * self.enemy.speed * dt
                self.effectiveness_tracker['strafe_success'] += 1
            if self.enemy.fire_cooldown <= 0:
                self.enemy.fire_cooldown = self.enemy.fire_rate
                self.enemy._attack(dir_x, dir_y, game)

        elif self.current_strategy == 'long_range':
            if dist < 300:
                self.enemy.x -= dir_x * self.enemy.speed * dt
                self.enemy.y -= dir_y * self.enemy.speed * dt
            else:
                if self.enemy.fire_cooldown <= 0:
                    self.enemy.fire_cooldown = self.enemy.fire_rate
                    pred_x, pred_y = self.predicted_player_position
                    pred_dx = pred_x - self.enemy.x
                    pred_dy = pred_y - self.enemy.y
                    pred_norm = math.hypot(pred_dx, pred_dy)
                    if pred_norm > 0:
                        self.enemy._attack(pred_dx/pred_norm, pred_dy/pred_norm, game)

        elif self.current_strategy == 'opportunistic':
            rush = self.enemy.aggression * self.adaptive_params['aggression_modifier']
            if random.random() < rush:
                self.enemy.x += dir_x * self.enemy.speed * 2 * dt
                self.enemy.y += dir_y * self.enemy.speed * 2 * dt
                self.effectiveness_tracker['aggression_success'] += 1
            if self.enemy.fire_cooldown <= 0:
                self.enemy.fire_cooldown = self.enemy.fire_rate
                self.enemy._attack(dir_x, dir_y, game)

        elif self.current_strategy == 'desperate':
            dodge = self.adaptive_params['dodge_modifier']
            if random.random() < dodge:
                angle = random.uniform(0, 2 * math.pi)
                self.enemy.x += math.cos(angle) * self.enemy.speed * 1.5 * dt
                self.enemy.y += math.sin(angle) * self.enemy.speed * 1.5 * dt
                self.effectiveness_tracker['dodge_success'] += 1
            if self.enemy.fire_cooldown <= 0:
                self.enemy.fire_cooldown = self.enemy.fire_rate
                self.enemy._attack(dir_x, dir_y, game)

        else:  # balanced
            if dist > 300:
                self.enemy.x += dir_x * self.enemy.speed * dt
                self.enemy.y += dir_y * self.enemy.speed * dt
            elif dist < 100:
                self.enemy.x -= dir_x * self.enemy.speed * dt
                self.enemy.y -= dir_y * self.enemy.speed * dt
            if self.enemy.fire_cooldown <= 0 and dist < 450:
                self.enemy.fire_cooldown = self.enemy.fire_rate
                self.enemy._attack(dir_x, dir_y, game)

    def _update_effectiveness(self, dt, player):
        pass


class ExtendedEnemy:
    def __init__(self, x, y, wave, enemy_type=None):
        self.x = x
        self.y = y
        self.wave = wave
        self.radius = ENEMY_BASE_RADIUS
        self.hp = ENEMY_BASE_HP + wave * 10
        self.max_hp = self.hp
        self.speed = ENEMY_BASE_SPEED + wave * 10
        self.fire_rate = max(0.8, ENEMY_FIRE_RATE - wave * 0.1)
        self.fire_cooldown = 0.0
        self.alive = True
        self.type = enemy_type or self._determine_type()
        self.state = 'patrol'
        self.state_timer = 0.0
        self.patrol_target = (random.randint(50, SCREEN_WIDTH-50), random.randint(50, SCREEN_HEIGHT-50))
        self.strafe_dir = 1 if random.random() < 0.5 else -1
        self.is_boss = False
        self.boss_phase = 1
        self.boss_ability_cooldown = 0.0
        self.is_elite = self.type == 'elite'
        self.abilities = []
        self._setup_abilities()
        self.damage = 15 + wave
        self.armor = 0
        self.regen_rate = 0
        self.hit_flash = 0.0
        self.death_animation = 0.0
        self.evolutionary_individual = None
        self.adaptive_controller = None
        self.effect_system = None
        self.weapon = None
        self.protection = None
        self.minions = []
        self.loot_dropped = False
        self.faction = "machines"
        self.aggression = 0.5
        self.damage_multiplier = 1.0
        self.speed_multiplier = 1.0
        self.poison_timer = 0.0
        self.poison_damage = 0
        self.burn_timer = 0.0
        self.burn_damage = 0
        self.slow_timer = 0.0
        self.slow_multiplier = 1.0
        self.stun_timer = 0.0
        self.confusion_timer = 0.0
        self.invulnerable_timer = 0.0
        self.damage_dealt_to_player = 0
        self.survival_time = 0.0
        self.boss_ai = None
        self.special_attacks = None
        self.effect_controller = None
        self.combat_ai = None
        self._init_equipment()
        self._init_systems()

    def _init_systems(self):
        if self.is_boss:
            self.boss_ai = EnemyBossAI(self)
        self.special_attacks = EnemySpecialAttacks(self)
        self.effect_controller = EnemyEffectController(self)
        self.combat_ai = EnemyCombatAI(self)

    def _init_equipment(self):
        # Оружие только с 3 волны, и только с шансом 30%
        if self.wave >= 3 and random.random() < 0.3:
            weapon_manager = WeaponManager()
            self.weapon = weapon_manager.get_random_weapon()
            if self.weapon:
                self.weapon = Weapon(self.weapon.id, self.weapon.name, self.weapon.config)
                self.damage = self.weapon.damage
        else:
            self.weapon = None
            self.damage = 15 + self.wave

        # Защита только с 2 волны, шанс 15%
        if self.wave >= 2 and random.random() < 0.15:
            protection_manager = ProtectionManager()
            self.protection = protection_manager.get_random_protection()
            if self.protection:
                self.protection = Protection(self.protection.id, self.protection.name, self.protection.config)
                self.armor = self.protection.armor
        else:
            self.protection = None

        # Миньоны только у боссов и элиты, и только с 4 волны
        if (self.is_boss or self.is_elite) and self.wave >= 4 and random.random() < 0.3:
            minion_manager = MinionManager()
            minion = minion_manager.get_random_minion()
            if minion:
                self.minions.append(Minion(minion.id, minion.name, minion.config))

    def _determine_type(self):
        roll = random.random()
        if roll < 0.15:
            return 'fast'
        elif roll < 0.30:
            return 'tank'
        elif roll < 0.45:
            return 'shooter'
        elif roll < 0.55:
            return 'elite'
        elif roll < 0.60:
            return 'hybrid'
        elif roll < 0.62:
            return 'avatar'
        else:
            return 'basic'

    def _setup_abilities(self):
        if self.type == 'fast':
            self.speed *= 1.5
            self.hp = int(self.hp * 0.7)
            self.max_hp = self.hp
            self.radius = 15
            self.abilities.extend(['dodge', 'dash'])
        elif self.type == 'tank':
            self.speed *= 0.7
            self.hp = int(self.hp * 1.8)
            self.max_hp = self.hp
            self.radius = 28
            self.armor = 10
            self.abilities.extend(['shield', 'heavy_armor'])
        elif self.type == 'shooter':
            self.fire_rate *= 0.7
            self.radius = 22
            self.abilities.extend(['rapid_fire', 'long_range'])
        elif self.type == 'elite':
            self.is_elite = True
            self.hp = int(self.hp * 1.5)
            self.max_hp = self.hp
            self.speed *= 1.2
            self.radius = 25
            self.armor = 5
            self.regen_rate = 2
            self.damage = 25
            self.abilities.extend(['regen', 'dash', 'multi_shot'])
        elif self.type == 'hybrid':
            self.is_elite = True
            self.hp = int(self.hp * 2.0)
            self.max_hp = self.hp
            self.speed *= 1.3
            self.radius = 30
            self.armor = 8
            self.regen_rate = 5
            self.damage = 30
            self.abilities.extend(['regen', 'dash', 'multi_shot', 'teleport'])
        elif self.type == 'avatar':
            self.is_boss = True
            self.hp = int(self.hp * 10)
            self.max_hp = self.hp
            self.speed = 80
            self.radius = 50
            self.armor = 15
            self.regen_rate = 10
            self.damage = 40
            self.fire_rate = 1.0
            self.abilities.extend(['regen', 'multi_shot', 'teleport', 'summon'])

    def update(self, dt, player, game):
        if not self.alive:
            if self.death_animation > 0:
                self.death_animation -= dt
            return
        self.survival_time += dt
        self.invulnerable_timer = max(0, self.invulnerable_timer - dt)
        self.fire_cooldown = max(0, self.fire_cooldown - dt)
        self.state_timer = max(0, self.state_timer - dt)
        self.hit_flash = max(0, self.hit_flash - dt * 5)
        if self.regen_rate > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.regen_rate * dt)
        if self.poison_timer > 0:
            self.poison_timer -= dt
            self.take_damage(int(self.poison_damage * dt), ignore_armor=True)
        if self.burn_timer > 0:
            self.burn_timer -= dt
            self.take_damage(int(self.burn_damage * dt), ignore_armor=True)
        if self.slow_timer > 0:
            self.slow_timer -= dt
        else:
            self.slow_multiplier = 1.0
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        if self.confusion_timer > 0:
            self.confusion_timer -= dt
        if self.boss_ai:
            self.boss_ai.update(dt, player, game)
        if self.combat_ai:
            self.combat_ai.update(dt, player, game)
        elif self.evolutionary_individual and game.evolutionary_ai:
            game.evolutionary_ai.apply_behavior(self, player, game, dt)
        else:
            self._update_normal(dt, (player.x, player.y), game)
        if self.effect_controller:
            self.effect_controller.update(dt, game)
        for minion in self.minions:
            if minion.alive:
                minion.owner = self
                minion.update(dt, game)
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))

    def _update_normal(self, dt, player_pos, game):
        dist_to_player = math.hypot(self.x - player_pos[0], self.y - player_pos[1])
        if self.state == 'patrol':
            if dist_to_player < 400:
                self.state = 'chase'
                self.state_timer = 3.0
            else:
                self._patrol(dt)
        elif self.state == 'chase':
            if dist_to_player > 500 and not self.is_elite:
                self.state = 'patrol'
                self.state_timer = 0
            else:
                self._chase(dt, player_pos, dist_to_player, game)

    def _patrol(self, dt):
        if self.state_timer <= 0 or math.hypot(self.x - self.patrol_target[0], self.y - self.patrol_target[1]) < 50:
            self.state_timer = 3.0
            self.patrol_target = (random.randint(50, SCREEN_WIDTH-50), random.randint(50, SCREEN_HEIGHT-50))
        dx = self.patrol_target[0] - self.x
        dy = self.patrol_target[1] - self.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            self.x += (dx/norm) * self.speed * self.speed_multiplier * self.slow_multiplier * 0.5 * dt
            self.y += (dy/norm) * self.speed * self.speed_multiplier * self.slow_multiplier * 0.5 * dt

    def _chase(self, dt, player_pos, dist_to_player, game):
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            dir_x, dir_y = dx/norm, dy/norm
            strafe_x, strafe_y = -dir_y, dir_x
            if 'dash' in self.abilities and random.random() < 0.01:
                self.x += dir_x * self.speed * 3 * dt
                self.y += dir_y * self.speed * 3 * dt
            elif dist_to_player < 250:
                self.x -= dir_x * self.speed * self.speed_multiplier * self.slow_multiplier * dt
                self.y -= dir_y * self.speed * self.speed_multiplier * self.slow_multiplier * dt
            else:
                self.x += dir_x * self.speed * self.speed_multiplier * self.slow_multiplier * dt
                self.y += dir_y * self.speed * self.speed_multiplier * self.slow_multiplier * dt
            self.x += strafe_x * self.speed * self.speed_multiplier * self.slow_multiplier * 0.3 * self.strafe_dir * dt
            self.y += strafe_y * self.speed * self.speed_multiplier * self.slow_multiplier * 0.3 * self.strafe_dir * dt
            if self.state_timer <= 0:
                self.strafe_dir *= -1
                self.state_timer = 2.0
            if 'teleport' in self.abilities and random.random() < 0.005:
                self.x = player_pos[0] + random.randint(-200, 200)
                self.y = player_pos[1] + random.randint(-200, 200)
            if self.fire_cooldown <= 0 and dist_to_player < self._get_attack_range():
                self.fire_cooldown = self.fire_rate
                self._attack(dir_x, dir_y, game)

    def _get_attack_range(self):
        if 'long_range' in self.abilities:
            return 600
        return 450

    def _attack(self, dir_x, dir_y, game):
        """Основная атака врага с 30+ уникальными механиками."""
        attack_roll = random.random()

        # === БОСС: 10 уникальных атак ===
        if self.is_boss:
            if attack_roll < 0.1:
                # 1. Круговой залп — 16 пуль вокруг
                for i in range(16):
                    angle = i * math.pi / 8
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.2:
                # 2. Спираль — пули по спирали
                for i in range(20):
                    angle = i * 0.5 + self.boss_ability_cooldown
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.3:
                # 3. Веер из 7 пуль
                for i in range(-3, 4):
                    angle = math.atan2(dir_y, dir_x) + i * 0.25
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.4:
                # 4. Крест — 4 направления
                for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage * 2)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.5:
                # 5. Двойная спираль
                for i in range(10):
                    angle1 = i * 0.6
                    angle2 = i * 0.6 + math.pi
                    b1 = Bullet(self.x, self.y, (math.cos(angle1), math.sin(angle1)), False, self.damage)
                    b2 = Bullet(self.x, self.y, (math.cos(angle2), math.sin(angle2)), False, self.damage)
                    game.enemy_bullets.append(b1)
                    game.enemy_bullets.append(b2)
            elif attack_roll < 0.6:
                # 6. Самонаводящиеся пули
                for i in range(5):
                    angle = math.atan2(dir_y, dir_x) + random.uniform(-0.3, 0.3)
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    bullet.set_homing(game.player)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.7:
                # 7. Взрывные пули
                for i in range(3):
                    angle = math.atan2(dir_y, dir_x) + (i - 1) * 0.4
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    bullet.set_explosive(50)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.8:
                # 8. Стена пуль
                for i in range(-5, 6):
                    bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                    bullet.radius = 6
                    bullet.life = 5.0
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.9:
                # 9. Рикошет
                for i in range(4):
                    angle = math.atan2(dir_y, dir_x) + i * math.pi / 2
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    bullet.set_bouncing(True)
                    game.enemy_bullets.append(bullet)
            else:
                # 10. Пробивающие пули
                for i in range(3):
                    bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage * 2)
                    bullet.set_piercing(True)
                    game.enemy_bullets.append(bullet)

        # === ЭЛИТА: 6 уникальных атак ===
        elif self.is_elite:
            if attack_roll < 0.15:
                # 11. Веер из 5 пуль
                for i in range(-2, 3):
                    angle = math.atan2(dir_y, dir_x) + i * 0.3
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.3:
                # 12. Тройная быстрая атака
                for i in range(3):
                    bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                    bullet.radius = 4
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.45:
                # 13. Самонаведение
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage * 2)
                bullet.set_homing(game.player)
                game.enemy_bullets.append(bullet)
            elif attack_roll < 0.6:
                # 14. Взрывная
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.set_explosive(40)
                game.enemy_bullets.append(bullet)
            elif attack_roll < 0.75:
                # 15. Рикошет
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.set_bouncing(True)
                game.enemy_bullets.append(bullet)
            else:
                # 16. Крест
                for angle in [0, math.pi/2, math.pi, 3*math.pi/2]:
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)

        # === СТРЕЛОК: 4 уникальные атаки ===
        elif self.type == 'shooter':
            if attack_roll < 0.2:
                # 17. Прицельный выстрел — 3 пули подряд
                for i in range(3):
                    bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                    bullet.radius = 3
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.4:
                # 18. Снайперский выстрел
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage * 3)
                bullet.set_piercing(True)
                game.enemy_bullets.append(bullet)
            elif attack_roll < 0.6:
                # 19. Разброс
                for i in range(-1, 2):
                    angle = math.atan2(dir_y, dir_x) + i * 0.15
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            else:
                # 20. Самонаведение
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.set_homing(game.player)
                game.enemy_bullets.append(bullet)

        # === ТАНК: 3 уникальные атаки ===
        elif self.type == 'tank':
            if attack_roll < 0.2:
                # 21. Мощный выстрел
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage * 3)
                bullet.radius = 12
                game.enemy_bullets.append(bullet)
            elif attack_roll < 0.4:
                # 22. Конусная атака
                for i in range(5):
                    angle = math.atan2(dir_y, dir_x) + (i - 2) * 0.15
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    bullet.radius = 6
                    game.enemy_bullets.append(bullet)
            else:
                # 23. Взрывная пуля
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.set_explosive(60)
                game.enemy_bullets.append(bullet)

        # === БЫСТРЫЙ: 3 уникальные атаки ===
        elif self.type == 'fast':
            if attack_roll < 0.15:
                # 24. Молниеносная атака
                for i in range(5):
                    bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                    bullet.radius = 2
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.3:
                # 25. Веер
                for i in range(-2, 3):
                    angle = math.atan2(dir_y, dir_x) + i * 0.2
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            else:
                # 26. Самонаведение
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.set_homing(game.player)
                game.enemy_bullets.append(bullet)

        # === ГИБРИД: 4 уникальные атаки ===
        elif self.type == 'hybrid':
            if attack_roll < 0.2:
                # 27. Био-плазма
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage * 2)
                bullet.set_explosive(40)
                game.enemy_bullets.append(bullet)
            elif attack_roll < 0.4:
                # 28. Тройная спираль
                for i in range(6):
                    angle = i * 0.8
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)
            elif attack_roll < 0.6:
                # 29. Пробивающий залп
                for i in range(2):
                    bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                    bullet.set_piercing(True)
                    game.enemy_bullets.append(bullet)
            else:
                # 30. Рикошет + самонаведение
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.set_bouncing(True)
                bullet.set_homing(game.player)
                game.enemy_bullets.append(bullet)

        # === ОБЫЧНЫЙ: 1 простая атака ===
        else:
            # 31. Одиночный выстрел
            bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
            game.enemy_bullets.append(bullet)


    def _shoot(self, dir_x, dir_y, game):
        """Выстрел врага с балансированным количеством пуль."""
        # Определяем максимальное количество пуль на основе типа
        if self.is_boss:
            max_pellets = 10
        elif self.is_elite:
            max_pellets = 5
        elif self.type == 'shooter':
            max_pellets = 2
        else:
            max_pellets = 1

        # Шанс на несколько пуль увеличивается с волной
        extra_shot_chance = min(0.5, self.wave * 0.05)

        # Определяем фактическое количество пуль
        pellets = 1
        if max_pellets > 1 and random.random() < extra_shot_chance:
            pellets = random.randint(2, max_pellets)

        # Разброс для нескольких пуль
        spread = 0.1 * (pellets - 1)

        for i in range(pellets):
            if pellets > 1:
                angle_offset = (i - (pellets - 1) / 2) * spread
                angle = math.atan2(dir_y, dir_x) + angle_offset
                bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
            else:
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
            game.enemy_bullets.append(bullet)

    def take_damage(self, damage, ignore_armor=False):
        if not self.alive:
            return False
        if self.invulnerable_timer > 0:
            return False
        actual_damage = damage
        if not ignore_armor:
            actual_damage = max(1, damage - self.armor)
        if 'dodge' in self.abilities and random.random() < 0.2:
            return False
        if 'shield' in self.abilities and random.random() < 0.15:
            actual_damage = int(actual_damage * 0.3)
        if self.protection:
            actual_damage = self.protection.take_damage(actual_damage)
        self.hp -= actual_damage
        self.hit_flash = 1.0
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.death_animation = 0.5
            return True
        return False

    def draw(self, screen):
        if not self.alive and self.death_animation <= 0:
            return
        if not self.alive:
            alpha = int(255 * self.death_animation / 0.5)
            radius = int(self.radius * (1 + (0.5 - self.death_animation) * 2))
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), radius, 2)
            return
        color = self._get_color()
        if self.hit_flash > 0:
            color = WHITE
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
        if self.armor > 0:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), self.radius - 3, 2)
        self._draw_health_bar(screen)
        if self.is_boss:
            self._draw_boss_indicator(screen)
        elif self.is_elite:
            self._draw_elite_indicator(screen)
        for minion in self.minions:
            if minion.alive:
                minion.draw(screen)

    def _get_color(self):
        if self.is_boss:
            return PURPLE
        elif self.type == 'fast':
            return ORANGE
        elif self.type == 'tank':
            return DARK_RED
        elif self.type == 'shooter':
            return MAGENTA
        elif self.type == 'elite':
            return YELLOW
        elif self.type == 'hybrid':
            return (255, 0, 128)
        elif self.type == 'avatar':
            return (128, 0, 255)
        else:
            return RED

    def _draw_health_bar(self, screen):
        if self.is_boss:
            bar_width = 200
            bar_height = 15
            bar_x = SCREEN_WIDTH // 2 - bar_width // 2
            bar_y = 20
        else:
            bar_width = self.radius * 2
            bar_height = 5
            bar_x = self.x - self.radius
            bar_y = self.y - self.radius - 12
        ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_width, bar_height))
        hp_color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
        pygame.draw.rect(screen, hp_color, (bar_x, bar_y, bar_width * ratio, bar_height))
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_boss_indicator(self, screen):
        font = pygame.font.Font(None, 24)
        boss_text = f"БОСС - Фаза {self.boss_phase}"
        text_surf = font.render(boss_text, True, YELLOW)
        screen.blit(text_surf, (SCREEN_WIDTH // 2 - text_surf.get_width() // 2, 40))

    def _draw_elite_indicator(self, screen):
        font = pygame.font.Font(None, 16)
        elite_text = "ЭЛИТА"
        text_surf = font.render(elite_text, True, YELLOW)
        screen.blit(text_surf, (self.x - text_surf.get_width() // 2, self.y - self.radius - 25))


# entities/enemy_extended.py — ЧАСТЬ 3 (Финальная)

class EnemyLootSystem:
    def __init__(self):
        self.loot_table = EnemyLootTable()
        self.weapon_drop = EnemyWeaponDrop()
        self.protection_drop = EnemyProtectionDrop()
        self.minion_drop = EnemyMinionDrop()
        self.loot_multiplier = 1.0
        self.rare_loot_chance = 0.05
        self.epic_loot_chance = 0.01
        self.legendary_loot_chance = 0.001

    def generate_loot(self, enemy, game):
        if enemy.loot_dropped:
            return []
        enemy.loot_dropped = True
        loot = []
        loot.extend(self.loot_table.generate_loot(enemy.wave))

        weapon_id = self.weapon_drop.generate_weapon_drop(enemy.wave)
        if weapon_id:
            loot.append({"type": "weapon", "weapon_id": weapon_id})

        protection_id = self.protection_drop.generate_protection_drop(enemy.wave)
        if protection_id:
            loot.append({"type": "protection", "protection_id": protection_id})

        minion_id = self.minion_drop.generate_minion_drop(enemy.wave)
        if minion_id:
            loot.append({"type": "minion", "minion_id": minion_id})

        if enemy.is_boss:
            loot.extend(self._generate_boss_loot(enemy))

        return loot

    def _generate_boss_loot(self, enemy):
        boss_loot = []
        boss_loot.append({"type": "ai_core", "amount": 1})
        boss_loot.append({"type": "crystal", "amount": 3})
        if random.random() < 0.5:
            boss_loot.append({"type": "dark_matter", "amount": 1})
        if random.random() < 0.3:
            boss_loot.append({"type": "void_shard", "amount": 2})
        if random.random() < 0.2:
            boss_loot.append({"type": "star_dust", "amount": 1})
        if random.random() < 0.1:
            boss_loot.append({"type": "soul_essence", "amount": 1})
        return boss_loot


class EnemySpawner:
    def __init__(self):
        self.spawn_weights = {
            'basic': 30,
            'fast': 20,
            'tank': 15,
            'shooter': 20,
            'elite': 10,
            'hybrid': 4,
            'avatar': 1,
        }
        self.min_wave_for_type = {
            'basic': 1,
            'fast': 1,
            'tank': 2,
            'shooter': 1,
            'elite': 3,
            'hybrid': 5,
            'avatar': 7,
        }

    def spawn_enemy(self, game, x=None, y=None, enemy_type=None, wave=None):
        if wave is None:
            wave = game.wave
        if enemy_type is None:
            enemy_type = self._select_enemy_type(wave)
        if x is None or y is None:
            for _ in range(50):
                x = random.randint(50, SCREEN_WIDTH - 50)
                y = random.randint(50, SCREEN_HEIGHT - 50)
                if math.hypot(x - game.player.x, y - game.player.y) > 250:
                    break
        enemy = ExtendedEnemy(x, y, wave, enemy_type)
        game.enemies.append(enemy)
        return enemy

    def _select_enemy_type(self, wave):
        available_types = []
        weights = []
        for enemy_type, min_wave in self.min_wave_for_type.items():
            if wave >= min_wave:
                available_types.append(enemy_type)
                weights.append(self.spawn_weights[enemy_type])
        if not available_types:
            return 'basic'
        total = sum(weights)
        roll = random.uniform(0, total)
        for enemy_type, weight in zip(available_types, weights):
            roll -= weight
            if roll <= 0:
                return enemy_type
        return 'basic'

    def spawn_boss(self, game, x=None, y=None):
        if x is None or y is None:
            x = random.randint(200, SCREEN_WIDTH - 200)
            y = random.randint(200, SCREEN_HEIGHT - 200)
        boss = ExtendedEnemy(x, y, game.wave, 'avatar')
        boss.is_boss = True
        boss.boss_phase = 1
        boss.hp = 300 + game.wave * 50
        boss.max_hp = boss.hp
        boss.speed = 80
        boss.fire_rate = 1.0
        boss.damage = 35
        game.enemies.append(boss)
        return boss


class EnemyManager:
    def __init__(self, game):
        self.game = game
        self.enemies = []
        self.spawner = EnemySpawner()
        self.loot_system = EnemyLootSystem()
        self.max_enemies = MAX_ENEMIES
        self.spawn_timer = 0.0
        self.spawn_rate = SPAWN_RATE_BASE

    def update(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_rate and len(self.enemies) < self.max_enemies:
            self.spawn_timer = 0.0
            self.spawn_enemy()
        self.update_enemies(dt)

    def spawn_enemy(self, enemy_type=None):
        enemy = self.spawner.spawn_enemy(self.game, enemy_type=enemy_type)
        self.enemies.append(enemy)
        return enemy

    def spawn_boss(self):
        boss = self.spawner.spawn_boss(self.game)
        self.enemies.append(boss)
        return boss

    def update_enemies(self, dt: float):
        for enemy in self.enemies[:]:
            if hasattr(enemy, 'fire_cooldown'):
                enemy.update(dt, self.game.player, self.game)
            else:
                enemy.update(dt, self.game)
            if not enemy.alive and enemy.death_animation <= 0:
                self.on_enemy_death(enemy)

    def on_enemy_death(self, enemy):
        loot = self.loot_system.generate_loot(enemy, self.game)
        for item in loot:
            self._apply_loot(enemy, item)

    def _apply_loot(self, enemy, item):
        item_type = item.get("type")
        if item_type == "weapon":
            weapon_id = item.get("weapon_id")
            pickup = Pickup(enemy.x, enemy.y, f"weapon_{weapon_id}")
            self.game.pickups.append(pickup)
        elif item_type == "protection":
            protection_id = item.get("protection_id")
            pickup = Pickup(enemy.x, enemy.y, f"protection_{protection_id}")
            self.game.pickups.append(pickup)
        elif item_type == "minion":
            minion_id = item.get("minion_id")
            pickup = Pickup(enemy.x, enemy.y, f"minion_{minion_id}")
            self.game.pickups.append(pickup)
        else:
            amount = item.get("amount", 1)
            pickup = Pickup(enemy.x + random.randint(-20, 20), enemy.y + random.randint(-20, 20), item_type, amount)
            self.game.pickups.append(pickup)

    def draw(self, screen):
        for enemy in self.enemies:
            enemy.draw(screen)

    def get_alive_enemies(self):
        return [e for e in self.enemies if e.alive]

    def get_enemies_in_radius(self, x, y, radius):
        return [e for e in self.enemies if e.alive and math.hypot(e.x - x, e.y - y) < radius]

    def clear_all(self):
        self.enemies.clear()


class EnemyEffectHandler:
    def __init__(self, enemy):
        self.enemy = enemy
        self.active_effects = {}
        self.effect_timers = {}

    def apply_effect(self, effect_id, duration, **params):
        self.active_effects[effect_id] = params
        self.effect_timers[effect_id] = duration

    def update(self, dt):
        for effect_id in list(self.effect_timers.keys()):
            self.effect_timers[effect_id] -= dt
            if self.effect_timers[effect_id] <= 0:
                self.remove_effect(effect_id)

    def remove_effect(self, effect_id):
        self.active_effects.pop(effect_id, None)
        self.effect_timers.pop(effect_id, None)

    def has_effect(self, effect_id):
        return effect_id in self.active_effects

    def get_effect_params(self, effect_id):
        return self.active_effects.get(effect_id, {})


class EnemyAbilitySystem:
    def __init__(self, enemy):
        self.enemy = enemy
        self.abilities = {}
        self.cooldowns = {}
        self._init_abilities()

    def _init_abilities(self):
        self.abilities = {
            'regen': {'cooldown': 5.0, 'duration': 2.0, 'power': 10},
            'dash': {'cooldown': 3.0, 'duration': 0.2, 'power': 300},
            'multi_shot': {'cooldown': 2.0, 'duration': 0.1, 'power': 3},
            'teleport': {'cooldown': 4.0, 'duration': 0.1, 'power': 200},
            'summon': {'cooldown': 8.0, 'duration': 0.5, 'power': 3},
            'shield': {'cooldown': 6.0, 'duration': 3.0, 'power': 0.5},
            'heavy_armor': {'cooldown': 10.0, 'duration': 5.0, 'power': 20},
            'dodge': {'cooldown': 1.0, 'duration': 0.1, 'power': 0.2},
            'rapid_fire': {'cooldown': 4.0, 'duration': 2.0, 'power': 0.5},
            'long_range': {'cooldown': 0, 'duration': 0, 'power': 150},
        }
        for ability in self.abilities:
            self.cooldowns[ability] = 0

    def update(self, dt):
        for ability in self.cooldowns:
            self.cooldowns[ability] = max(0, self.cooldowns[ability] - dt)

    def can_use(self, ability_name):
        return self.cooldowns.get(ability_name, 0) <= 0

    def use_ability(self, ability_name, player=None, game=None):
        if not self.can_use(ability_name):
            return False
        ability_data = self.abilities.get(ability_name)
        if not ability_data:
            return False
        self.cooldowns[ability_name] = ability_data['cooldown']
        if ability_name == 'regen':
            self.enemy.hp = min(self.enemy.max_hp, self.enemy.hp + ability_data['power'] * self.enemy.max_hp * 0.1)
        elif ability_name == 'dash':
            if player:
                dx = player.x - self.enemy.x
                dy = player.y - self.enemy.y
                norm = math.hypot(dx, dy)
                if norm > 0:
                    self.enemy.x += (dx / norm) * ability_data['power']
                    self.enemy.y += (dy / norm) * ability_data['power']
        elif ability_name == 'multi_shot':
            if player and game:
                dx = player.x - self.enemy.x
                dy = player.y - self.enemy.y
                norm = math.hypot(dx, dy)
                if norm > 0:
                    for i in range(ability_data['power']):
                        angle = math.atan2(dy, dx) + (i - 1) * 0.3
                        bullet = Bullet(self.enemy.x, self.enemy.y, (math.cos(angle), math.sin(angle)), False,
                                        self.enemy.damage)
                        game.enemy_bullets.append(bullet)
        elif ability_name == 'teleport':
            if player:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(100, ability_data['power'])
                self.enemy.x = player.x + math.cos(angle) * distance
                self.enemy.y = player.y + math.sin(angle) * distance
        elif ability_name == 'summon':
            if game:
                minion_manager = MinionManager()
                for _ in range(ability_data['power']):
                    minion_id = random.choice(['drone', 'assault_drone'])
                    minion = minion_manager.spawn_minion(minion_id, self.enemy.x + random.randint(-50, 50),
                                                         self.enemy.y + random.randint(-50, 50), self.enemy)
                    if minion:
                        game.enemies.append(minion)
        elif ability_name == 'shield':
            self.enemy.armor += ability_data['power'] * 50
        elif ability_name == 'heavy_armor':
            self.enemy.armor += ability_data['power']
        return True


class ExtendedEnemyFinal(ExtendedEnemy):
    def __init__(self, x, y, wave, enemy_type=None):
        super().__init__(x, y, wave, enemy_type)
        self.loot_system = EnemyLootSystem()
        self.ability_system = EnemyAbilitySystem(self)
        self.effect_handler = EnemyEffectHandler(self)
        self.special_attacks = EnemySpecialAttacks(self)
        if self.is_boss:
            self.boss_ai = EnemyBossAI(self)

    def update(self, dt, player, game):
        super().update(dt, player, game)
        self.ability_system.update(dt)
        self.effect_handler.update(dt)
        if self.ability_system.can_use('regen') and self.hp < self.max_hp * 0.5:
            self.ability_system.use_ability('regen')
        if self.ability_system.can_use('dash') and random.random() < 0.05:
            self.ability_system.use_ability('dash', player)
        if self.ability_system.can_use('multi_shot') and random.random() < 0.1:
            self.ability_system.use_ability('multi_shot', player, game)
        if self.ability_system.can_use('teleport') and random.random() < 0.03:
            self.ability_system.use_ability('teleport', player)
        if self.ability_system.can_use('summon') and random.random() < 0.02:
            self.ability_system.use_ability('summon', game=game)

    def take_damage(self, damage, ignore_armor=False):
        if self.effect_handler.has_effect('shield'):
            damage = int(damage * 0.5)
        if self.effect_handler.has_effect('damage_reduction'):
            damage = int(damage * 0.7)
        return super().take_damage(damage, ignore_armor)

    def on_death(self, game):
        loot = self.loot_system.generate_loot(self, game)
        for item in loot:
            item_type = item.get("type")
            if item_type == "weapon":
                game.pickups.append(Pickup(self.x, self.y, f"weapon_{item['weapon_id']}"))
            elif item_type == "protection":
                game.pickups.append(Pickup(self.x, self.y, f"protection_{item['protection_id']}"))
            elif item_type == "minion":
                game.pickups.append(Pickup(self.x, self.y, f"minion_{item['minion_id']}"))
            else:
                game.pickups.append(
                    Pickup(self.x + random.randint(-20, 20), self.y + random.randint(-20, 20), item_type,
                           item.get("amount", 1)))


class EnemyFactory:
    @staticmethod
    def create_enemy(x, y, wave, enemy_type=None):
        return ExtendedEnemyFinal(x, y, wave, enemy_type)

    @staticmethod
    def create_boss(x, y, wave):
        boss = ExtendedEnemyFinal(x, y, wave, 'avatar')
        boss.is_boss = True
        boss.boss_phase = 1
        boss.hp = 300 + wave * 50
        boss.max_hp = boss.hp
        boss.speed = 80
        boss.fire_rate = 1.0
        boss.damage = 35
        return boss

    @staticmethod
    def create_elite(x, y, wave):
        elite = ExtendedEnemyFinal(x, y, wave, 'elite')
        elite.is_elite = True
        elite.hp = int(elite.hp * 1.5)
        elite.max_hp = elite.hp
        return elite

    @staticmethod
    def create_hybrid(x, y, wave):
        hybrid = ExtendedEnemyFinal(x, y, wave, 'hybrid')
        return hybrid

    @staticmethod
    def create_random_enemy(x, y, wave):
        enemy_type = random.choice(['basic', 'fast', 'tank', 'shooter', 'elite'])
        return ExtendedEnemyFinal(x, y, wave, enemy_type)


class EnemyIntegration:
    def __init__(self, game):
        self.game = game
        self.enemy_manager = EnemyManager(game)
        self.enemy_factory = EnemyFactory()

    def update(self, dt):
        self.enemy_manager.update(dt)

    def spawn_enemy(self, enemy_type=None, x=None, y=None):
        return self.enemy_manager.spawn_enemy(enemy_type)

    def spawn_boss(self):
        return self.enemy_manager.spawn_boss()

    def spawn_wave(self, wave):
        count = min(3 + wave, MAX_ENEMIES)
        for _ in range(count):
            self.spawn_enemy()

    def draw(self, screen):
        self.enemy_manager.draw(screen)

    def clear(self):
        self.enemy_manager.clear_all()

# В самом конце файла, после ВСЕХ классов, на уровне модуля:

def _add_shoot_method_to_final():
    def _shoot(self, dir_x: float, dir_y: float, game):
        # Определяем максимальное количество пуль на основе типа
        if self.is_boss:
            max_pellets = 10
        elif self.is_elite:
            max_pellets = 5
        elif getattr(self, 'type', 'basic') == 'shooter':
            max_pellets = 2
        else:
            max_pellets = 1

        # Шанс на несколько пуль увеличивается с волной
        extra_shot_chance = min(0.5, self.wave * 0.05)

        # Определяем фактическое количество пуль
        pellets = 1
        if max_pellets > 1 and random.random() < extra_shot_chance:
            pellets = random.randint(2, max_pellets)

        # Разброс для нескольких пуль
        spread = 0.15 * (pellets - 1)

        for i in range(pellets):
            if pellets > 1:
                angle_offset = (i - (pellets - 1) / 2) * spread
                angle = math.atan2(dir_y, dir_x) + angle_offset
                bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
            else:
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
            game.enemy_bullets.append(bullet)

    ExtendedEnemyFinal._shoot = _shoot


# Вызываем функцию для добавления метода
_add_shoot_method_to_final()