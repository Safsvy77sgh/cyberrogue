# systems/building.py
import pygame
import math
from typing import List, Dict, Tuple, Optional
from settings import *


class Building:
    """Строение"""

    def __init__(self, x: float, y: float, building_type: str):
        self.x = x
        self.y = y
        self.type = building_type
        self.hp = 100
        self.max_hp = 100
        self.alive = True
        self.level = 1
        self.upgrade_cost = 100

        # Типы строений
        self.stats = self._get_stats()

    def _get_stats(self) -> Dict:
        """Получение характеристик строения"""
        if self.type == 'turret':
            return {'damage': 10, 'fire_rate': 1.0, 'range': 300}
        elif self.type == 'wall':
            return {'hp': 200, 'armor': 10}
        elif self.type == 'generator':
            return {'energy_per_sec': 5}
        elif self.type == 'medstation':
            return {'heal_per_sec': 5}
        elif self.type == 'factory':
            return {'production': 'scrap', 'rate': 1}
        else:
            return {}

    def upgrade(self) -> bool:
        """Улучшение строения"""
        self.level += 1
        self.max_hp += 50
        self.hp = self.max_hp
        self.upgrade_cost = int(self.upgrade_cost * 1.5)

        # Улучшение характеристик
        if 'damage' in self.stats:
            self.stats['damage'] += 5
        if 'fire_rate' in self.stats:
            self.stats['fire_rate'] *= 0.9
        if 'range' in self.stats:
            self.stats['range'] += 50
        if 'hp' in self.stats:
            self.stats['hp'] += 100
        if 'energy_per_sec' in self.stats:
            self.stats['energy_per_sec'] += 5
        if 'heal_per_sec' in self.stats:
            self.stats['heal_per_sec'] += 3

        return True

    def update(self, dt: float, game):
        """Обновление строения"""
        if not self.alive:
            return

        if self.type == 'turret':
            # Атака ближайшего врага
            target = self._find_target(game.enemies)
            if target:
                self._attack(target, game, dt)

        elif self.type == 'generator':
            # Генерация энергии
            game.player.energy = min(PLAYER_MAX_ENERGY,
                                     game.player.energy + self.stats['energy_per_sec'] * dt)

        elif self.type == 'medstation':
            # Лечение игрока рядом
            if math.hypot(self.x - game.player.x, self.y - game.player.y) < 150:
                game.player.heal(int(self.stats['heal_per_sec'] * dt))

        elif self.type == 'factory':
            # Производство ресурсов
            if self.stats['production'] == 'scrap':
                game.player.scrap += self.stats['rate'] * dt

    def _find_target(self, enemies: List) -> Optional[object]:
        """Поиск ближайшего врага"""
        closest = None
        closest_dist = self.stats.get('range', 300)

        for enemy in enemies:
            if enemy.alive:
                dist = math.hypot(self.x - enemy.x, self.y - enemy.y)
                if dist < closest_dist:
                    closest_dist = dist
                    closest = enemy

        return closest

    def _attack(self, target, game, dt: float = 0.0):
        """Атака цели"""
        if hasattr(self, 'fire_cooldown'):
            self.fire_cooldown -= dt
        else:
            self.fire_cooldown = 0

        if self.fire_cooldown <= 0:
            self.fire_cooldown = self.stats.get('fire_rate', 1.0)
            damage = self.stats.get('damage', 10)
            target.take_damage(damage)
            game.add_damage_number(target.x, target.y - target.radius, damage, ORANGE)

    def take_damage(self, damage: int) -> bool:
        """Получение урона"""
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def draw(self, screen: pygame.Surface):
        """Отрисовка строения"""
        if not self.alive:
            return

        # Цвет в зависимости от типа
        colors = {
            'turret': BLUE,
            'wall': GRAY,
            'generator': YELLOW,
            'medstation': GREEN,
            'factory': ORANGE
        }
        color = colors.get(self.type, WHITE)

        # Отрисовка
        size = 30
        pygame.draw.rect(screen, color, (self.x - size // 2, self.y - size // 2, size, size))
        pygame.draw.rect(screen, WHITE, (self.x - size // 2, self.y - size // 2, size, size), 2)

        # Полоска HP
        if self.hp < self.max_hp:
            bar_width = 40
            bar_height = 5
            ratio = self.hp / self.max_hp
            pygame.draw.rect(screen, BLACK, (self.x - bar_width // 2, self.y - 30, bar_width, bar_height))
            pygame.draw.rect(screen, GREEN, (self.x - bar_width // 2, self.y - 30, bar_width * ratio, bar_height))

        # Уровень
        font = pygame.font.Font(None, 16)
        level_text = font.render(f"Ур.{self.level}", True, WHITE)
        screen.blit(level_text, (self.x - level_text.get_width() // 2, self.y - 20))


class BuildingSystem:
    """Система строительства"""

    def __init__(self):
        self.buildings = []
        self.selected_type = 'turret'
        self.build_mode = False

    def add_building(self, x: float, y: float, building_type: str, player=None) -> bool:
        """Добавление строения"""
        costs = {
            'turret': {'scrap': 10, 'circuit': 2},
            'wall': {'scrap': 5},
            'generator': {'scrap': 15, 'circuit': 5},
            'medstation': {'scrap': 12, 'circuit': 3},
            'factory': {'scrap': 20, 'circuit': 8}
        }

        cost = costs.get(building_type, {})

        # Проверка ресурсов игрока (если игрок передан)
        if player is not None:
            required_scrap = cost.get('scrap', 0)
            required_circuit = cost.get('circuit', 0)
            if getattr(player, 'scrap', 0) < required_scrap or getattr(player, 'circuits', 0) < required_circuit:
                return False
            player.scrap -= required_scrap
            player.circuits -= required_circuit

        building = Building(x, y, building_type)
        self.buildings.append(building)
        return True

    def remove_building(self, building: Building):
        """Удаление строения"""
        if building in self.buildings:
            self.buildings.remove(building)

    def update(self, dt: float, game):
        """Обновление всех строений"""
        for building in self.buildings:
            building.update(dt, game)

    def draw(self, screen: pygame.Surface):
        """Отрисовка всех строений"""
        for building in self.buildings:
            building.draw(screen)

    def get_building_at(self, x: float, y: float) -> Optional[Building]:
        """Получение строения по координатам"""
        for building in self.buildings:
            if math.hypot(building.x - x, building.y - y) < 30:
                return building
        return None