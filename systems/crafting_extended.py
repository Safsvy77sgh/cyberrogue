# systems/crafting_extended.py с таким содержимым:

import math
import random
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from settings import *
from entities.pickup import Pickup
from systems.weapons_extended import WeaponManager
from systems.protection import ProtectionManager
from systems.minions import MinionManager


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


class CraftingRecipeExtended:
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
    def from_dict(cls, data: dict) -> 'CraftingRecipeExtended':
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


class CraftingSystemExtended:
    def __init__(self):
        self.materials: Dict[str, CraftingMaterial] = {}
        self.recipes: Dict[str, CraftingRecipeExtended] = {}
        self.categories: Dict[str, List[str]] = {}
        self.crafting_level = 1
        self.crafting_exp = 0
        self.crafting_exp_to_next = 100
        self.crafting_history: List[Dict] = []
        self.disassemble_multiplier = 0.5
        self._init_materials()
        self._init_recipes()

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
            ("pistol_recipe", "Пистолет", "Базовое оружие", {"scrap": 5, "mechanical_parts": 3}, {"type": "weapon", "weapon_id": "pistol"}, "weapon", 1),
            ("shotgun_recipe", "Дробовик", "Оружие ближнего боя", {"scrap": 15, "mechanical_parts": 10, "circuit": 5}, {"type": "weapon", "weapon_id": "shotgun"}, "weapon", 2),
            ("laser_recipe", "Лазер", "Пробивающее оружие", {"scrap": 20, "circuit": 10, "laser_lens": 1}, {"type": "weapon", "weapon_id": "laser"}, "weapon", 3),
            ("rocket_launcher_recipe", "Ракетница", "Взрывное оружие", {"scrap": 30, "mechanical_parts": 15, "rocket_fuel": 5}, {"type": "weapon", "weapon_id": "rocket_launcher"}, "weapon", 4),
            ("plasma_rifle_recipe", "Плазменная винтовка", "Мощное пробивающее", {"scrap": 40, "circuit": 20, "plasma_fragment": 5}, {"type": "weapon", "weapon_id": "plasma_rifle"}, "weapon", 5),
            ("minigun_recipe", "Миниган", "Скорострельное оружие", {"scrap": 50, "mechanical_parts": 25, "circuit": 15}, {"type": "weapon", "weapon_id": "minigun"}, "weapon", 5),
            ("medkit_recipe", "Аптечка", "Восстанавливает 50 HP", {"bio_gel": 3, "organic_tissue": 2}, {"type": "consumable", "effect": "heal", "value": 50}, "consumable", 1),
            ("energy_pack_recipe", "Энергопакет", "Восстанавливает 50 энергии", {"energy_cell": 2, "circuit": 1}, {"type": "consumable", "effect": "energy", "value": 50}, "consumable", 1),
            ("emp_grenade_recipe", "ЭМИ-граната", "Отключает роботов", {"circuit": 5, "thunder_core": 1, "scrap": 5}, {"type": "consumable", "effect": "emp"}, "consumable", 2),
            ("light_armor_recipe", "Лёгкая броня", "Базовая защита", {"scrap": 10, "mechanical_parts": 5}, {"type": "protection", "protection_id": "light_armor"}, "protection", 1),
            ("drone_recipe", "Боевой дрон", "Базовый миньон", {"scrap": 15, "circuit": 5, "mechanical_parts": 8}, {"type": "minion", "minion_id": "drone"}, "minion", 1),
        ]
        for recipe_id, name, description, materials, result, category, level in recipes:
            self.recipes[recipe_id] = CraftingRecipeExtended(recipe_id, name, description, materials, result, category, level)
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(recipe_id)

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

    def get_available_recipes(self) -> List[CraftingRecipeExtended]:
        return [r for r in self.recipes.values() if r.unlocked and r.level_required <= self.crafting_level]

    def get_recipes_by_category(self, category: str) -> List[CraftingRecipeExtended]:
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
        for recipe in self.recipes.values():
            if recipe.result.get("type") == item_type and recipe.result.get(f"{item_type}_id") == item_id:
                for mat_id, amount in recipe.materials.items():
                    refund = max(1, int(amount * self.disassemble_multiplier))
                    if mat_id in self.materials:
                        self.materials[mat_id].add(refund)
                return True
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
                    self.recipes[rid] = CraftingRecipeExtended.from_dict(r_data)
            self.crafting_level = data.get("crafting_level", 1)
            self.crafting_exp = data.get("crafting_exp", 0)
            self.crafting_exp_to_next = data.get("crafting_exp_to_next", 100)
            self.crafting_history = data.get("history", [])
            return True
        except:
            return False