# systems/crafting.py — ПОЛНЫЙ НОВЫЙ КРАФТИНГ

import math
import random
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from settings import *
from entities.pickup import Pickup
from systems.weapons_extended import WeaponManager, Weapon
from systems.protection import ProtectionManager, Protection
from systems.minions import MinionManager, Minion


class CraftingMaterial:
    def __init__(self, material_id: str, name: str, rarity: str = "common", color: Tuple[int, int, int] = WHITE):
        self.id = material_id
        self.name = name
        self.rarity = rarity
        self.color = color
        self.amount = 0

    def add(self, amount: int = 1):
        self.amount += amount

    def remove(self, amount: int = 1) -> bool:
        if self.amount >= amount:
            self.amount -= amount
            return True
        return False

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "rarity": self.rarity, "color": self.color, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: dict) -> 'CraftingMaterial':
        mat = cls(data["id"], data["name"], data.get("rarity", "common"), data.get("color", WHITE))
        mat.amount = data.get("amount", 0)
        return mat


class CraftingRecipe:
    def __init__(self, recipe_id: str, name: str, description: str, materials: Dict[str, int], result: Dict, category: str = "item", level_required: int = 1):
        self.id = recipe_id
        self.name = name
        self.description = description
        self.materials = materials
        self.result = result
        self.category = category
        self.level_required = level_required
        self.unlocked = level_required <= 1

    def can_craft(self, inventory: Dict[str, int]) -> bool:
        for mat_id, amount in self.materials.items():
            if inventory.get(mat_id, 0) < amount:
                return False
        return True

    def craft(self, inventory: Dict[str, int]) -> bool:
        if not self.can_craft(inventory):
            return False
        for mat_id, amount in self.materials.items():
            inventory[mat_id] -= amount
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "materials": self.materials,
            "result": self.result,
            "category": self.category,
            "level_required": self.level_required,
            "unlocked": self.unlocked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CraftingRecipe':
        recipe = cls(
            data["id"],
            data["name"],
            data.get("description", ""),
            data.get("materials", {}),
            data.get("result", {}),
            data.get("category", "item"),
            data.get("level_required", 1),
        )
        recipe.unlocked = data.get("unlocked", True)
        return recipe


class CraftingSystem:
    def __init__(self):
        self.materials: Dict[str, CraftingMaterial] = {}
        self.recipes: Dict[str, CraftingRecipe] = {}
        self.categories: Dict[str, List[str]] = {}
        self.crafting_level = 1
        self.crafting_exp = 0
        self.crafting_exp_to_next = 100
        self.crafting_history: List[Dict] = []
        self.disassemble_multiplier = 0.5  # возврат 50% материалов
        self._init_materials()
        self._init_recipes()
        self._init_categories()

    def _init_materials(self):
        materials = [
            ("scrap", "Металлолом", "common", GRAY),
            ("circuit", "Электронные компоненты", "common", CYAN),
            ("energy_cell", "Энергоячейка", "uncommon", YELLOW),
            ("crystal", "Кристалл", "rare", MAGENTA),
            ("ai_core", "Ядро ИИ", "epic", PURPLE),
            ("organic_tissue", "Органические ткани", "common", GREEN),
            ("plasma_fragment", "Фрагмент плазмы", "rare", (200, 0, 255)),
            ("dark_matter", "Тёмная материя", "legendary", (20, 0, 40)),
            ("void_shard", "Осколок пустоты", "epic", (0, 0, 0)),
            ("star_dust", "Звёздная пыль", "legendary", (255, 255, 200)),
            ("quantum_foam", "Квантовая пена", "rare", (100, 200, 255)),
            ("nano_swarm", "Нано-рой", "uncommon", (150, 150, 150)),
            ("bio_gel", "Биогель", "common", (100, 200, 100)),
            ("mechanical_parts", "Механические части", "common", (180, 180, 180)),
            ("laser_lens", "Лазерная линза", "uncommon", (255, 0, 0)),
            ("rocket_fuel", "Ракетное топливо", "uncommon", (255, 100, 0)),
            ("ice_core", "Ледяное ядро", "uncommon", (150, 200, 255)),
            ("thunder_core", "Громовое ядро", "rare", (255, 255, 0)),
            ("gravity_core", "Гравитационное ядро", "epic", (100, 0, 100)),
            ("soul_essence", "Эссенция души", "epic", (100, 0, 200)),
        ]
        for mat_id, name, rarity, color in materials:
            self.materials[mat_id] = CraftingMaterial(mat_id, name, rarity, color)

    def _init_recipes(self):
        recipes = [
            # Оружие
            ("pistol_recipe", "Пистолет", "Базовое оружие", {"scrap": 5, "mechanical_parts": 3}, {"type": "weapon", "weapon_id": "pistol"}, "weapon", 1),
            ("shotgun_recipe", "Дробовик", "Оружие ближнего боя", {"scrap": 15, "mechanical_parts": 10, "circuit": 5}, {"type": "weapon", "weapon_id": "shotgun"}, "weapon", 2),
            ("laser_recipe", "Лазер", "Пробивающее оружие", {"scrap": 20, "circuit": 10, "laser_lens": 1}, {"type": "weapon", "weapon_id": "laser"}, "weapon", 3),
            ("rocket_launcher_recipe", "Ракетница", "Взрывное оружие", {"scrap": 30, "mechanical_parts": 15, "rocket_fuel": 5}, {"type": "weapon", "weapon_id": "rocket_launcher"}, "weapon", 4),
            ("plasma_rifle_recipe", "Плазменная винтовка", "Мощное пробивающее", {"scrap": 40, "circuit": 20, "plasma_fragment": 5}, {"type": "weapon", "weapon_id": "plasma_rifle"}, "weapon", 5),
            ("minigun_recipe", "Миниган", "Скорострельное оружие", {"scrap": 50, "mechanical_parts": 25, "circuit": 15}, {"type": "weapon", "weapon_id": "minigun"}, "weapon", 5),
            ("flamethrower_recipe", "Огнемёт", "Огненное оружие", {"scrap": 25, "mechanical_parts": 10, "rocket_fuel": 8}, {"type": "weapon", "weapon_id": "flamethrower"}, "weapon", 3),
            ("ice_gun_recipe", "Ледяная пушка", "Замораживающее оружие", {"scrap": 25, "ice_core": 3, "circuit": 8}, {"type": "weapon", "weapon_id": "ice_gun"}, "weapon", 3),
            ("shock_gun_recipe", "Шокер", "Электрическое оружие", {"scrap": 25, "thunder_core": 2, "circuit": 8}, {"type": "weapon", "weapon_id": "shock_gun"}, "weapon", 3),
            ("gravity_gun_recipe", "Гравитационная пушка", "Манипулирует гравитацией", {"scrap": 35, "gravity_core": 1, "circuit": 15}, {"type": "weapon", "weapon_id": "gravity_gun"}, "weapon", 4),
            ("homing_launcher_recipe", "Самонаводящаяся ракетница", "Ракеты с самонаведением", {"scrap": 45, "rocket_fuel": 10, "circuit": 20, "ai_core": 1}, {"type": "weapon", "weapon_id": "homing_launcher"}, "weapon", 5),
            ("void_rifle_recipe", "Винтовка Пустоты", "Оружие из пустоты", {"scrap": 60, "void_shard": 5, "dark_matter": 1}, {"type": "weapon", "weapon_id": "void_rifle"}, "weapon", 6),
            ("railgun_recipe", "Рельсотрон", "Сверхскоростное оружие", {"scrap": 50, "circuit": 25, "energy_cell": 10, "laser_lens": 3}, {"type": "weapon", "weapon_id": "railgun"}, "weapon", 5),
            ("gauss_rifle_recipe", "Пушка Гаусса", "Электромагнитное оружие", {"scrap": 45, "circuit": 20, "thunder_core": 3}, {"type": "weapon", "weapon_id": "gauss_rifle"}, "weapon", 5),
            ("tesla_gun_recipe", "Тесла-пушка", "Цепные молнии", {"scrap": 35, "thunder_core": 5, "circuit": 15}, {"type": "weapon", "weapon_id": "tesla_gun"}, "weapon", 4),
            ("nova_cannon_recipe", "Пушка Нова", "Мощный взрыв", {"scrap": 70, "energy_cell": 15, "plasma_fragment": 10, "crystal": 5}, {"type": "weapon", "weapon_id": "nova_cannon"}, "weapon", 6),
            ("singularity_gun_recipe", "Сингулярная пушка", "Создаёт чёрные дыры", {"scrap": 80, "dark_matter": 3, "void_shard": 10, "quantum_foam": 5}, {"type": "weapon", "weapon_id": "singularity_gun"}, "weapon", 7),
            ("doom_cannon_recipe", "Пушка Рока", "Уничтожает всё", {"scrap": 100, "dark_matter": 5, "void_shard": 15, "soul_essence": 3}, {"type": "weapon", "weapon_id": "doom_cannon"}, "weapon", 8),

            # Защита
            ("light_armor_recipe", "Лёгкая броня", "Базовая защита", {"scrap": 10, "mechanical_parts": 5}, {"type": "protection", "protection_id": "light_armor"}, "protection", 1),
            ("medium_armor_recipe", "Средняя броня", "Улучшенная защита", {"scrap": 20, "mechanical_parts": 10, "circuit": 3}, {"type": "protection", "protection_id": "medium_armor"}, "protection", 2),
            ("heavy_armor_recipe", "Тяжёлая броня", "Максимальная защита", {"scrap": 40, "mechanical_parts": 20, "crystal": 2}, {"type": "protection", "protection_id": "heavy_armor"}, "protection", 3),
            ("energy_shield_recipe", "Энергетический щит", "Щит с регенерацией", {"scrap": 30, "energy_cell": 8, "circuit": 10}, {"type": "protection", "protection_id": "energy_shield"}, "protection", 3),
            ("reflective_shield_recipe", "Отражающий щит", "Отражает урон", {"scrap": 35, "crystal": 5, "circuit": 12}, {"type": "protection", "protection_id": "reflective_shield"}, "protection", 4),
            ("nanite_armor_recipe", "Нанитная броня", "Самовосстанавливающаяся", {"scrap": 45, "nano_swarm": 10, "circuit": 15}, {"type": "protection", "protection_id": "nanite_armor"}, "protection", 5),
            ("crystal_shield_recipe", "Кристальный щит", "Сильное отражение", {"scrap": 40, "crystal": 10, "energy_cell": 5}, {"type": "protection", "protection_id": "crystal_shield"}, "protection", 5),
            ("titan_plate_recipe", "Титановая пластина", "Сверхпрочная броня", {"scrap": 60, "mechanical_parts": 30, "crystal": 5, "ai_core": 1}, {"type": "protection", "protection_id": "titan_plate"}, "protection", 6),
            ("quantum_shield_recipe", "Квантовый щит", "Фазовый сдвиг", {"scrap": 55, "quantum_foam": 8, "circuit": 20, "crystal": 3}, {"type": "protection", "protection_id": "quantum_shield"}, "protection", 6),
            ("dragon_scale_recipe", "Чешуя дракона", "Огненная защита", {"scrap": 50, "organic_tissue": 15, "crystal": 8, "plasma_fragment": 5}, {"type": "protection", "protection_id": "dragon_scale"}, "protection", 5),
            ("phoenix_feather_recipe", "Перо Феникса", "Возрождение", {"scrap": 30, "soul_essence": 3, "plasma_fragment": 10, "crystal": 5}, {"type": "protection", "protection_id": "phoenix_feather"}, "protection", 6),
            ("titan_armor_recipe", "Титанская броня", "Максимальная защита+", {"scrap": 80, "mechanical_parts": 40, "crystal": 10, "dark_matter": 1}, {"type": "protection", "protection_id": "titan_armor"}, "protection", 7),
            ("void_armor_recipe", "Пустотная броня", "Защита от пустоты", {"scrap": 70, "void_shard": 12, "dark_matter": 2}, {"type": "protection", "protection_id": "void_armor_extended"}, "protection", 7),
            ("galaxy_armor_recipe", "Галактическая броня", "Космическая защита", {"scrap": 90, "star_dust": 5, "dark_matter": 2, "crystal": 8}, {"type": "protection", "protection_id": "galaxy_armor"}, "protection", 8),

            # Миньоны
            ("drone_recipe", "Боевой дрон", "Базовый миньон", {"scrap": 15, "circuit": 5, "mechanical_parts": 8}, {"type": "minion", "minion_id": "drone"}, "minion", 1),
            ("turret_recipe", "Турель", "Стационарная защита", {"scrap": 25, "circuit": 10, "mechanical_parts": 15}, {"type": "minion", "minion_id": "turret"}, "minion", 2),
            ("healer_recipe", "Медик", "Лечащий миньон", {"scrap": 20, "bio_gel": 5, "circuit": 8}, {"type": "minion", "minion_id": "healer"}, "minion", 2),
            ("assault_drone_recipe", "Штурмовой дрон", "Атакующий миньон", {"scrap": 30, "circuit": 12, "mechanical_parts": 15, "laser_lens": 1}, {"type": "minion", "minion_id": "assault_drone"}, "minion", 3),
            ("sniper_drone_recipe", "Снайперский дрон", "Дальний бой", {"scrap": 35, "circuit": 15, "laser_lens": 3, "crystal": 1}, {"type": "minion", "minion_id": "sniper_drone"}, "minion", 3),
            ("heavy_drone_recipe", "Тяжёлый дрон", "Танковый миньон", {"scrap": 40, "mechanical_parts": 20, "crystal": 2}, {"type": "minion", "minion_id": "heavy_drone"}, "minion", 4),
            ("shield_drone_recipe", "Щитовой дрон", "Защитный миньон", {"scrap": 35, "energy_cell": 8, "circuit": 10}, {"type": "minion", "minion_id": "shield_drone"}, "minion", 3),
            ("repair_drone_recipe", "Ремонтный дрон", "Чинит союзников", {"scrap": 30, "nano_swarm": 5, "circuit": 10}, {"type": "minion", "minion_id": "repair_drone"}, "minion", 3),
            ("emp_drone_recipe", "ЭМИ-дрон", "Отключает врагов", {"scrap": 35, "thunder_core": 3, "circuit": 12}, {"type": "minion", "minion_id": "emp_drone"}, "minion", 4),
            ("flame_drone_recipe", "Огненный дрон", "Поджигает врагов", {"scrap": 30, "plasma_fragment": 5, "rocket_fuel": 3}, {"type": "minion", "minion_id": "flame_drone"}, "minion", 3),
            ("ice_drone_recipe", "Ледяной дрон", "Замораживает", {"scrap": 30, "ice_core": 3, "circuit": 8}, {"type": "minion", "minion_id": "ice_drone"}, "minion", 3),
            ("shock_drone_recipe", "Электрический дрон", "Цепные молнии", {"scrap": 30, "thunder_core": 3, "circuit": 8}, {"type": "minion", "minion_id": "shock_drone"}, "minion", 3),
            ("ninja_drone_recipe", "Дрон-ниндзя", "Быстрый убийца", {"scrap": 35, "circuit": 15, "crystal": 2}, {"type": "minion", "minion_id": "ninja_drone"}, "minion", 4),
            ("kamikaze_drone_recipe", "Дрон-камикадзе", "Взрывается", {"scrap": 25, "rocket_fuel": 8, "mechanical_parts": 10}, {"type": "minion", "minion_id": "kamikaze_drone"}, "minion", 3),
            ("teleport_drone_recipe", "Телепортирующий дрон", "Телепортируется", {"scrap": 40, "quantum_foam": 5, "circuit": 15}, {"type": "minion", "minion_id": "teleport_drone"}, "minion", 4),
            ("gravity_drone_recipe", "Гравитационный дрон", "Управляет гравитацией", {"scrap": 45, "gravity_core": 2, "circuit": 15}, {"type": "minion", "minion_id": "gravity_drone"}, "minion", 5),
            ("summoner_drone_recipe", "Дрон-призыватель", "Призывает миньонов", {"scrap": 50, "ai_core": 1, "circuit": 20, "soul_essence": 2}, {"type": "minion", "minion_id": "summoner_drone"}, "minion", 5),
            ("void_drone_recipe", "Пустотный дрон", "Дрон из пустоты", {"scrap": 60, "void_shard": 8, "dark_matter": 1}, {"type": "minion", "minion_id": "void_drone"}, "minion", 6),
            ("artillery_drone_recipe", "Артиллерийский дрон", "Дальнобойная артиллерия", {"scrap": 55, "rocket_fuel": 10, "circuit": 20, "crystal": 3}, {"type": "minion", "minion_id": "artillery_drone"}, "minion", 5),

            # Расходники
            ("medkit_recipe", "Аптечка", "Восстанавливает 50 HP", {"bio_gel": 3, "organic_tissue": 2}, {"type": "consumable", "effect": "heal", "value": 50}, "consumable", 1),
            ("energy_pack_recipe", "Энергопакет", "Восстанавливает 50 энергии", {"energy_cell": 2, "circuit": 1}, {"type": "consumable", "effect": "energy", "value": 50}, "consumable", 1),
            ("emp_grenade_recipe", "ЭМИ-граната", "Отключает роботов", {"circuit": 5, "thunder_core": 1, "scrap": 5}, {"type": "consumable", "effect": "emp"}, "consumable", 2),
            ("shield_cell_recipe", "Щитовой модуль", "Временный щит", {"energy_cell": 5, "crystal": 2, "circuit": 5}, {"type": "consumable", "effect": "shield", "value": 3}, "consumable", 3),
            ("damage_boost_recipe", "Усилитель урона", "Временный буст урона", {"plasma_fragment": 3, "crystal": 1, "circuit": 5}, {"type": "consumable", "effect": "damage_boost", "value": 30}, "consumable", 3),
            ("speed_boost_recipe", "Ускоритель", "Временное ускорение", {"energy_cell": 3, "circuit": 3}, {"type": "consumable", "effect": "speed_boost", "value": 15}, "consumable", 2),
        ]

        for recipe_id, name, description, materials, result, category, level in recipes:
            self.recipes[recipe_id] = CraftingRecipe(recipe_id, name, description, materials, result, category, level)

    def _init_categories(self):
        self.categories = {
            "weapon": [],
            "protection": [],
            "minion": [],
            "consumable": [],
        }
        for rid, recipe in self.recipes.items():
            if recipe.category in self.categories:
                self.categories[recipe.category].append(rid)

    def add_material(self, material_id: str, amount: int = 1):
        if material_id in self.materials:
            self.materials[material_id].add(amount)

    def remove_material(self, material_id: str, amount: int = 1) -> bool:
        if material_id in self.materials:
            return self.materials[material_id].remove(amount)
        return False

    def get_material_amount(self, material_id: str) -> int:
        if material_id in self.materials:
            return self.materials[material_id].amount
        return 0

    def get_inventory(self) -> Dict[str, int]:
        return {mat_id: mat.amount for mat_id, mat in self.materials.items()}

    def set_inventory(self, inventory: Dict[str, int]):
        for mat_id, amount in inventory.items():
            if mat_id in self.materials:
                self.materials[mat_id].amount = amount

    def unlock_recipe(self, recipe_id: str):
        if recipe_id in self.recipes:
            self.recipes[recipe_id].unlocked = True

    def unlock_all_recipes(self):
        for recipe in self.recipes.values():
            recipe.unlocked = True

    def get_available_recipes(self) -> List[CraftingRecipe]:
        return [r for r in self.recipes.values() if r.unlocked and r.level_required <= self.crafting_level]

    def get_recipes_by_category(self, category: str) -> List[CraftingRecipe]:
        return [self.recipes[rid] for rid in self.categories.get(category, []) if self.recipes[rid].unlocked]

    def can_craft(self, recipe_id: str) -> bool:
        if recipe_id not in self.recipes:
            return False
        recipe = self.recipes[recipe_id]
        if not recipe.unlocked or recipe.level_required > self.crafting_level:
            return False
        return recipe.can_craft(self.get_inventory())

    def craft(self, recipe_id: str) -> bool:
        if not self.can_craft(recipe_id):
            return False
        recipe = self.recipes[recipe_id]
        inventory = self.get_inventory()
        if recipe.craft(inventory):
            self.set_inventory(inventory)
            self.add_crafting_exp(10 + recipe.level_required * 5)
            self.crafting_history.append({"recipe": recipe_id, "time": pygame.time.get_ticks()})
            return True
        return False

    def add_crafting_exp(self, amount: int):
        self.crafting_exp += amount
        while self.crafting_exp >= self.crafting_exp_to_next:
            self.crafting_exp -= self.crafting_exp_to_next
            self.crafting_level += 1
            self.crafting_exp_to_next = int(self.crafting_exp_to_next * 1.5)
            self._unlock_recipes_for_level()

    def _unlock_recipes_for_level(self):
        for recipe in self.recipes.values():
            if recipe.level_required <= self.crafting_level:
                recipe.unlocked = True

    def get_crafting_level(self) -> int:
        return self.crafting_level

    def get_crafting_exp_progress(self) -> float:
        return self.crafting_exp / self.crafting_exp_to_next

    def disassemble_item(self, item_type: str, item_id: str) -> bool:
        """
        Разбирает предмет на материалы.
        Возвращает True, если разборка удалась.
        """
        # Находим рецепт, результатом которого является этот предмет
        for recipe in self.recipes.values():
            if recipe.result.get("type") == item_type and recipe.result.get(f"{item_type}_id") == item_id:
                # Возвращаем материалы с коэффициентом
                for mat_id, amount in recipe.materials.items():
                    refund = max(1, int(amount * self.disassemble_multiplier))
                    if mat_id in self.materials:
                        self.materials[mat_id].add(refund)
                return True
        return False

    def get_disassemble_refund(self, item_type: str, item_id: str) -> Optional[Dict[str, int]]:
        """Возвращает словарь материалов, которые вернутся при разборке."""
        for recipe in self.recipes.values():
            if recipe.result.get("type") == item_type and recipe.result.get(f"{item_type}_id") == item_id:
                refund = {}
                for mat_id, amount in recipe.materials.items():
                    refund[mat_id] = max(1, int(amount * self.disassemble_multiplier))
                return refund
        return None

    def upgrade_item(self, item_type: str, item_id: str) -> bool:
        """
        Улучшает предмет, если возможно.
        Пока заглушка: нужно больше данных.
        """
        return False

    def save_to_file(self, filename: str = "crafting_save.json"):
        data = {
            "materials": {mat_id: mat.to_dict() for mat_id, mat in self.materials.items()},
            "recipes": {rid: r.to_dict() for rid, r in self.recipes.items()},
            "crafting_level": self.crafting_level,
            "crafting_exp": self.crafting_exp,
            "crafting_exp_to_next": self.crafting_exp_to_next,
            "history": self.crafting_history,
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def load_from_file(self, filename: str = "crafting_save.json"):
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for mat_id, mat_data in data.get("materials", {}).items():
                if mat_id in self.materials:
                    self.materials[mat_id] = CraftingMaterial.from_dict(mat_data)
            for rid, r_data in data.get("recipes", {}).items():
                if rid in self.recipes:
                    self.recipes[rid] = CraftingRecipe.from_dict(r_data)
            self.crafting_level = data.get("crafting_level", 1)
            self.crafting_exp = data.get("crafting_exp", 0)
            self.crafting_exp_to_next = data.get("crafting_exp_to_next", 100)
            self.crafting_history = data.get("history", [])
            return True
        except:
            return False