# systems/protection.py

import math
import random
import pygame
from typing import Dict, List, Tuple, Optional, Any
from settings import *


class Protection:
    def __init__(self, protection_id: str, name: str, config: dict):
        self.id = protection_id
        self.name = name
        self.config = config
        self.armor = config.get("armor", 0)
        self.shield = config.get("shield", 0)
        self.regen = config.get("regen", 0)
        self.reflect = config.get("reflect", 0.0)
        self.elemental_resistance = config.get("elemental_resistance", {})
        self.special = config.get("special", None)
        self.durability = config.get("durability", 100)
        self.max_durability = self.durability
        self.level = 1
        self.active = True

    def upgrade(self):
        self.level += 1
        self.armor = int(self.armor * 1.2)
        self.shield = int(self.shield * 1.2)
        self.regen = int(self.regen * 1.1)
        self.durability = self.max_durability
        return self

    def take_damage(self, damage):
        absorbed = min(self.armor, damage)
        remaining = damage - absorbed
        self.durability -= int(absorbed * 0.5)
        if self.durability <= 0:
            self.active = False
        return remaining

    def get_reflected_damage(self, damage):
        return int(damage * self.reflect)

    def get_resistance(self, element):
        return self.elemental_resistance.get(element, 0.0)

    def apply_regen(self, player):
        if self.regen > 0 and self.active:
            player.hp = min(player.max_hp, player.hp + self.regen)


class ProtectionManager:
    def __init__(self):
        self.protections: Dict[str, Protection] = {}
        self._init_default_protections()
        self._init_extended_protections()

    def _init_default_protections(self):
        self.add_protection("light_armor", "Лёгкая броня", {"armor": 10, "durability": 50})
        self.add_protection("medium_armor", "Средняя броня", {"armor": 20, "durability": 100})
        self.add_protection("heavy_armor", "Тяжёлая броня", {"armor": 40, "durability": 200})
        self.add_protection("energy_shield", "Энергетический щит", {"shield": 50, "regen": 5, "durability": 150})
        self.add_protection("reflective_shield", "Отражающий щит", {"shield": 30, "reflect": 0.3, "durability": 100})

    def _init_extended_protections(self):
        protections_to_add = [
            ("nanite_armor", "Нанитная броня", {"armor": 25, "regen": 10, "durability": 120, "special": "nanite_repair"}),
            ("crystal_shield", "Кристальный щит", {"shield": 70, "reflect": 0.5, "durability": 80, "special": "crystal_reflect"}),
            ("flame_armor", "Огненная броня", {"armor": 15, "elemental_resistance": {"fire": 0.5}, "durability": 90}),
            ("ice_armor", "Ледяная броня", {"armor": 15, "elemental_resistance": {"ice": 0.5}, "durability": 90}),
            ("shock_armor", "Электрическая броня", {"armor": 15, "elemental_resistance": {"shock": 0.5}, "durability": 90}),
            ("acid_armor", "Кислотная броня", {"armor": 15, "elemental_resistance": {"acid": 0.5}, "durability": 90}),
            ("void_armor", "Пустотная броня", {"armor": 20, "elemental_resistance": {"void": 0.6}, "durability": 110}),
            ("holy_armor", "Святая броня", {"armor": 20, "elemental_resistance": {"holy": 0.6}, "durability": 110}),
            ("shadow_armor", "Теневая броня", {"armor": 20, "elemental_resistance": {"shadow": 0.6}, "durability": 110}),
            ("dragon_scale", "Чешуя дракона", {"armor": 35, "elemental_resistance": {"fire": 0.7}, "durability": 180}),
            ("phoenix_feather", "Перо Феникса", {"armor": 10, "regen": 20, "special": "phoenix_rebirth", "durability": 50}),
            ("titan_plate", "Титановая пластина", {"armor": 60, "durability": 300, "special": "damage_reduction"}),
            ("quantum_shield", "Квантовый щит", {"shield": 100, "reflect": 0.7, "durability": 60, "special": "phase_shift"}),
            ("bio_armor", "Биоброня", {"armor": 20, "regen": 15, "durability": 100, "special": "self_healing"}),
            ("techno_shield", "Технощит", {"shield": 40, "regen": 8, "durability": 130, "special": "emp_resistance"}),
            ("gravity_armor", "Гравитационная броня", {"armor": 25, "special": "gravity_manipulation", "durability": 100}),
            ("chrono_armor", "Хроноброня", {"armor": 20, "special": "time_slow", "durability": 90}),
            ("plasma_shield", "Плазменный щит", {"shield": 60, "elemental_resistance": {"plasma": 0.5}, "durability": 110}),
            ("magnetic_armor", "Магнитная броня", {"armor": 30, "special": "bullet_magnet", "durability": 140}),
            ("sonic_shield", "Звуковой щит", {"shield": 35, "special": "sound_absorption", "durability": 80}),
            ("toxic_armor", "Токсичная броня", {"armor": 18, "elemental_resistance": {"poison": 0.6}, "durability": 85}),
            ("frost_shield", "Морозный щит", {"shield": 45, "elemental_resistance": {"ice": 0.6}, "durability": 95}),
            ("ember_armor", "Угольная броня", {"armor": 22, "elemental_resistance": {"fire": 0.7}, "durability": 100}),
            ("storm_shield", "Штормовой щит", {"shield": 50, "elemental_resistance": {"shock": 0.7}, "durability": 90}),
            ("earth_armor", "Земляная броня", {"armor": 45, "durability": 250, "special": "stone_skin"}),
            ("wind_shield", "Щит ветра", {"shield": 30, "special": "dodge_boost", "durability": 70}),
            ("water_armor", "Водяная броня", {"armor": 15, "regen": 12, "durability": 80, "special": "flow"}),
            ("light_shield", "Световой щит", {"shield": 55, "elemental_resistance": {"holy": 0.5}, "durability": 100}),
            ("dark_shield", "Тёмный щит", {"shield": 55, "elemental_resistance": {"shadow": 0.5}, "durability": 100}),
            ("nature_armor", "Природная броня", {"armor": 18, "regen": 18, "durability": 90, "special": "photosynthesis"}),
            ("arcane_shield", "Арканный щит", {"shield": 65, "elemental_resistance": {"arcane": 0.6}, "durability": 85}),
            ("divine_armor", "Божественная броня", {"armor": 30, "regen": 10, "elemental_resistance": {"holy": 0.8}, "durability": 150}),
            ("demonic_armor", "Демоническая броня", {"armor": 35, "elemental_resistance": {"shadow": 0.7}, "durability": 160, "special": "soul_drain"}),
            ("angelic_armor", "Ангельская броня", {"armor": 32, "regen": 15, "elemental_resistance": {"holy": 0.7}, "durability": 140}),
            ("dragon_armor", "Драконья броня", {"armor": 40, "elemental_resistance": {"fire": 0.8}, "durability": 200, "special": "dragon_rage"}),
            ("phoenix_armor", "Броня Феникса", {"armor": 25, "regen": 25, "special": "phoenix_rebirth", "durability": 70}),
            ("titan_armor", "Титанская броня", {"armor": 70, "durability": 400, "special": "damage_reduction"}),
            ("quantum_armor", "Квантовая броня", {"armor": 28, "special": "phase_shift", "durability": 110}),
            ("void_armor_extended", "Пустотная броня+", {"armor": 25, "elemental_resistance": {"void": 0.8}, "durability": 130, "special": "void_blink"}),
            ("galaxy_armor", "Галактическая броня", {"armor": 50, "elemental_resistance": {"void": 0.5, "holy": 0.5}, "durability": 220}),
            ("cosmic_armor", "Космическая броня", {"armor": 55, "elemental_resistance": {"void": 0.6}, "durability": 250, "special": "cosmic_power"}),
            ("nebula_armor", "Туманностная броня", {"armor": 45, "elemental_resistance": {"void": 0.4}, "durability": 200, "special": "nebula_mist"}),
            ("star_armor", "Звёздная броня", {"armor": 48, "elemental_resistance": {"holy": 0.5}, "durability": 210, "special": "star_blessing"}),
            ("solar_armor", "Солнечная броня", {"armor": 42, "elemental_resistance": {"fire": 0.6, "holy": 0.4}, "durability": 190, "special": "solar_flare"}),
            ("lunar_armor", "Лунная броня", {"armor": 38, "elemental_resistance": {"shadow": 0.5}, "durability": 180, "special": "lunar_phase"}),
            ("eclipse_armor", "Броня затмения", {"armor": 50, "elemental_resistance": {"shadow": 0.6, "holy": 0.6}, "durability": 230, "special": "eclipse_shift"}),
            ("twilight_armor", "Сумеречная броня", {"armor": 44, "elemental_resistance": {"shadow": 0.4, "holy": 0.4}, "durability": 200, "special": "twilight_veil"}),
            ("dawn_armor", "Броня рассвета", {"armor": 40, "elemental_resistance": {"holy": 0.6}, "durability": 185, "special": "dawn_light"}),
            ("sun_armor", "Солнечная броня+", {"armor": 52, "elemental_resistance": {"fire": 0.7, "holy": 0.5}, "durability": 240, "special": "sun_burst"}),
            ("star_plate", "Звёздная пластина", {"armor": 58, "elemental_resistance": {"void": 0.3}, "durability": 260, "special": "star_fall"}),
            ("cosmic_plate", "Космическая пластина", {"armor": 62, "elemental_resistance": {"void": 0.4}, "durability": 280, "special": "cosmic_ray"}),
            ("nebula_plate", "Туманностная пластина", {"armor": 55, "elemental_resistance": {"void": 0.3}, "durability": 250, "special": "nebula_cloud"}),
            ("galaxy_plate", "Галактическая пластина", {"armor": 60, "elemental_resistance": {"void": 0.5}, "durability": 270, "special": "galaxy_shift"}),
            ("proton_armor", "Протонная броня", {"armor": 35, "elemental_resistance": {"shock": 0.5}, "durability": 150, "special": "proton_beam"}),
            ("neutron_armor", "Нейтронная броня", {"armor": 38, "elemental_resistance": {"shock": 0.6}, "durability": 160, "special": "neutron_pulse"}),
            ("electron_armor", "Электронная броня", {"armor": 32, "elemental_resistance": {"shock": 0.4}, "durability": 140, "special": "electron_charge"}),
            ("photon_armor", "Фотонная броня", {"armor": 36, "elemental_resistance": {"holy": 0.5}, "durability": 155, "special": "photon_blast"}),
            ("graviton_armor", "Гравитонная броня", {"armor": 40, "elemental_resistance": {"gravity": 0.5}, "durability": 170, "special": "graviton_pull"}),
            ("temporal_armor", "Временная броня", {"armor": 34, "special": "time_stop", "durability": 145}),
            ("void_plate", "Пустотная пластина", {"armor": 50, "elemental_resistance": {"void": 0.7}, "durability": 220, "special": "void_walk"}),
            ("soul_armor", "Броня душ", {"armor": 30, "special": "soul_drain", "durability": 130}),
            ("spirit_armor", "Духовная броня", {"armor": 28, "regen": 20, "durability": 120, "special": "spirit_walk"}),
            ("phantom_armor", "Фантомная броня", {"armor": 26, "special": "phase_shift", "durability": 110}),
            ("ghost_armor", "Призрачная броня", {"armor": 24, "special": "invisibility", "durability": 100}),
            ("poltergeist_armor", "Броня полтергейста", {"armor": 22, "special": "telekinesis", "durability": 95}),
            ("haunt_armor", "Призрачная броня+", {"armor": 27, "special": "haunt", "durability": 115}),
            ("specter_armor", "Спектральная броня", {"armor": 29, "special": "spectral_form", "durability": 125}),
            ("wraith_armor", "Броня духа+", {"armor": 31, "special": "wraith_curse", "durability": 135}),
            ("shadow_plate", "Теневая пластина", {"armor": 46, "elemental_resistance": {"shadow": 0.6}, "durability": 210, "special": "shadow_step"}),
            ("night_armor", "Ночная броня", {"armor": 33, "elemental_resistance": {"shadow": 0.4}, "durability": 145, "special": "night_vision"}),
            ("eclipse_plate", "Пластина затмения", {"armor": 52, "elemental_resistance": {"shadow": 0.5, "holy": 0.5}, "durability": 235, "special": "eclipse_blast"}),
            ("twilight_plate", "Сумеречная пластина", {"armor": 47, "elemental_resistance": {"shadow": 0.3, "holy": 0.3}, "durability": 205, "special": "twilight_step"}),
            ("dawn_plate", "Пластина рассвета", {"armor": 43, "elemental_resistance": {"holy": 0.5}, "durability": 195, "special": "dawn_heal"}),
            ("sun_plate", "Солнечная пластина", {"armor": 54, "elemental_resistance": {"fire": 0.6, "holy": 0.4}, "durability": 245, "special": "sun_flare"}),
        ]

        for prot_id, name, config in protections_to_add:
            self.add_protection(prot_id, name, config)

    def add_protection(self, prot_id, name, config):
        self.protections[prot_id] = Protection(prot_id, name, config)

    def get_protection(self, prot_id):
        return self.protections.get(prot_id)

    def get_all_protections(self):
        return list(self.protections.values())

    def get_random_protection(self):
        return random.choice(list(self.protections.values()))