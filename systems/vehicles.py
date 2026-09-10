# systems/vehicles.py
import math
import pygame
from typing import List, Tuple, Optional
from settings import *


class Vehicle:
    """Транспортное средство"""

    def __init__(self, x: float, y: float, vehicle_type: str):
        self.x = x
        self.y = y
        self.type = vehicle_type
        self.hp = 100
        self.max_hp = 100
        self.speed = 0
        self.damage = 0
        self.armor = 0
        self.fuel = 100
        self.max_fuel = 100
        self.occupied = False
        self.alive = True

        # Настройка типа
        if vehicle_type == 'motorcycle':
            self.speed = 500
            self.hp = 50
            self.max_hp = 50
            self.armor = 0
            self.fuel = 50
            self.max_fuel = 50
        elif vehicle_type == 'car':
            self.speed = 350
            self.hp = 150
            self.max_hp = 150
            self.armor = 5
            self.fuel = 100
            self.max_fuel = 100
        elif vehicle_type == 'tank':
            self.speed = 150
            self.hp = 500
            self.max_hp = 500
            self.armor = 30
            self.damage = 100
            self.fuel = 200
            self.max_fuel = 200
        elif vehicle_type == 'drone':
            self.speed = 300
            self.hp = 30
            self.max_hp = 30
            self.armor = 0
            self.damage = 20
            self.fuel = 75
            self.max_fuel = 75

    def update(self, dt: float, keys, game):
        """Обновление транспорта"""
        if not self.occupied or not self.alive:
            return

        # Движение
        dx = 0
        dy = 0
        if keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_s]:
            dy += 1
        if keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_d]:
            dx += 1

        if dx != 0 or dy != 0:
            norm = math.hypot(dx, dy)
            self.x += (dx / norm) * self.speed * dt
            self.y += (dy / norm) * self.speed * dt

            # Расход топлива
            self.fuel = max(0, self.fuel - 10 * dt)
            if self.fuel <= 0:
                self.occupied = False

        # Перемещение игрока вместе с транспортом
        game.player.x = self.x
        game.player.y = self.y

        # Границы
        self.x = max(30, min(SCREEN_WIDTH - 30, self.x))
        self.y = max(30, min(SCREEN_HEIGHT - 30, self.y))

    def enter(self, player) -> bool:
        """Посадка в транспорт"""
        if not self.occupied and self.alive and self.fuel > 0:
            self.occupied = True
            player.in_vehicle = True
            player.vehicle = self
            return True
        return False

    def exit(self, player):
        """Выход из транспорта"""
        self.occupied = False
        player.in_vehicle = False
        player.vehicle = None

    def take_damage(self, damage: int) -> bool:
        """Получение урона"""
        actual_damage = max(1, damage - self.armor)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def refuel(self, amount: int):
        """Заправка"""
        self.fuel = min(self.max_fuel, self.fuel + amount)

    def repair(self, amount: int):
        """Ремонт"""
        self.hp = min(self.max_hp, self.hp + amount)

    def draw(self, screen: pygame.Surface):
        """Отрисовка транспорта"""
        if not self.alive:
            return

        colors = {
            'motorcycle': GRAY,
            'car': BLUE,
            'tank': DARK_GREEN,
            'drone': CYAN
        }
        color = colors.get(self.type, WHITE)

        # Размеры в зависимости от типа
        sizes = {
            'motorcycle': (20, 10),
            'car': (40, 25),
            'tank': (60, 40),
            'drone': (25, 25)
        }
        w, h = sizes.get(self.type, (30, 20))

        # Отрисовка корпуса
        rect = pygame.Rect(self.x - w // 2, self.y - h // 2, w, h)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, WHITE, rect, 2)

        # Полоска HP
        if self.hp < self.max_hp:
            bar_width = w
            bar_height = 4
            ratio = self.hp / self.max_hp
            pygame.draw.rect(screen, BLACK, (self.x - bar_width // 2, self.y - h // 2 - 10, bar_width, bar_height))
            pygame.draw.rect(screen, GREEN,
                             (self.x - bar_width // 2, self.y - h // 2 - 10, bar_width * ratio, bar_height))

        # Полоска топлива
        fuel_width = w
        fuel_height = 3
        fuel_ratio = self.fuel / self.max_fuel
        pygame.draw.rect(screen, BLACK, (self.x - fuel_width // 2, self.y - h // 2 - 15, fuel_width, fuel_height))
        pygame.draw.rect(screen, YELLOW,
                         (self.x - fuel_width // 2, self.y - h // 2 - 15, fuel_width * fuel_ratio, fuel_height))


class VehicleSystem:
    """Система управления транспортом"""

    def __init__(self, game):
        self.game = game
        self.vehicles = []

    def spawn_vehicle(self, x: float, y: float, vehicle_type: str):
        """Спавн транспорта"""
        vehicle = Vehicle(x, y, vehicle_type)
        self.vehicles.append(vehicle)
        return vehicle

    def update(self, dt: float, keys):
        """Обновление всех транспортных средств"""
        for vehicle in self.vehicles:
            vehicle.update(dt, keys, self.game)

    def draw(self, screen: pygame.Surface):
        """Отрисовка всех транспортных средств"""
        for vehicle in self.vehicles:
            vehicle.draw(screen)

    def get_vehicle_at(self, x: float, y: float) -> Optional[Vehicle]:
        """Получение транспорта по координатам"""
        for vehicle in self.vehicles:
            if math.hypot(vehicle.x - x, vehicle.y - y) < 50:
                return vehicle
        return None