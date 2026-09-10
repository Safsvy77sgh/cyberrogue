# entities/enemy.py
import math
import pygame
import random
from typing import Tuple, List, Optional, Dict, Any
from settings import *
from entities.bullet import Bullet


class Enemy:
    def __init__(self, x: float, y: float, wave: int, enemy_type: str = None):
        # Позиция
        self.x = x
        self.y = y
        self.radius = ENEMY_BASE_RADIUS

        # Статы
        self.hp = ENEMY_BASE_HP + wave * 10
        self.max_hp = self.hp
        self.speed = ENEMY_BASE_SPEED + wave * 10
        self.fire_rate = max(0.8, ENEMY_FIRE_RATE - wave * 0.1)
        self.fire_cooldown = 0.0
        self.damage = 15
        self.armor = 0
        self.regen_rate = 0

        # Состояние
        self.alive = True
        self.state = 'patrol'
        self.state_timer = 0.0
        self.patrol_target = (random.randint(50, SCREEN_WIDTH - 50),
                              random.randint(50, SCREEN_HEIGHT - 50))
        self.strafe_dir = 1 if random.random() < 0.5 else -1

        # Тип врага
        self.type = enemy_type if enemy_type else self._determine_type()
        self.wave = wave
        self.is_boss = False
        self.boss_phase = 1
        self.boss_ability_cooldown = 0.0
        self.is_elite = False

        # Способности
        self.abilities = []
        self._setup_abilities()

        # Визуальные эффекты
        self.hit_flash = 0.0
        self.attack_animation = 0.0
        self.death_animation = 0.0

    def _determine_type(self) -> str:
        """Определение типа врага"""
        roll = random.random()
        if roll < 0.15:
            return 'fast'
        elif roll < 0.30:
            return 'tank'
        elif roll < 0.45:
            return 'shooter'
        elif roll < 0.55:
            return 'elite'
        else:
            return 'basic'

    def _setup_abilities(self):
        """Настройка способностей в зависимости от типа"""
        if self.type == 'fast':
            self.speed *= 1.5
            self.hp = int(self.hp * 0.7)
            self.max_hp = self.hp
            self.radius = 15
            self.abilities.append('dodge')
            self.abilities.append('dash')
        elif self.type == 'tank':
            self.speed *= 0.7
            self.hp = int(self.hp * 1.8)
            self.max_hp = self.hp
            self.radius = 28
            self.armor = 10
            self.abilities.append('shield')
            self.abilities.append('heavy_armor')
        elif self.type == 'shooter':
            self.fire_rate *= 0.7
            self.radius = 22
            self.abilities.append('rapid_fire')
            self.abilities.append('long_range')
        elif self.type == 'elite':
            self.is_elite = True
            self.hp = int(self.hp * 1.5)
            self.max_hp = self.hp
            self.speed *= 1.2
            self.radius = 25
            self.armor = 5
            self.regen_rate = 2
            self.damage = 25
            self.abilities.append('regen')
            self.abilities.append('dash')
            self.abilities.append('multi_shot')
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

    def update(self, dt: float, player_pos: Tuple[float, float], game):
        """Обновление врага"""
        if not self.alive:
            # Анимация смерти
            if self.death_animation > 0:
                self.death_animation -= dt
            return

        # Обновление таймеров
        self.fire_cooldown = max(0, self.fire_cooldown - dt)
        self.state_timer = max(0, self.state_timer - dt)
        self.hit_flash = max(0, self.hit_flash - dt * 5)

        # Регенерация
        if 'regen' in self.abilities and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.regen_rate * dt)

        # Обновление ИИ
        if self.is_boss:
            self._update_boss(dt, player_pos, game)
        else:
            self._update_normal(dt, player_pos, game)

        # Границы
        self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))

    def _update_normal(self, dt: float, player_pos: Tuple[float, float], game):
        """Обновление обычного врага"""
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

    def _patrol(self, dt: float):
        """Патрулирование"""
        if self.state_timer <= 0 or math.hypot(self.x - self.patrol_target[0],
                                               self.y - self.patrol_target[1]) < 50:
            self.state_timer = 3.0
            self.patrol_target = (random.randint(50, SCREEN_WIDTH - 50),
                                  random.randint(50, SCREEN_HEIGHT - 50))

        dx = self.patrol_target[0] - self.x
        dy = self.patrol_target[1] - self.y
        norm = math.hypot(dx, dy)
        if norm > 0:
            self.x += (dx / norm) * self.speed * 0.5 * dt
            self.y += (dy / norm) * self.speed * 0.5 * dt

    def _chase(self, dt: float, player_pos: Tuple[float, float], dist_to_player: float, game):
        """Преследование игрока"""
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        norm = math.hypot(dx, dy)

        if norm > 0:
            dir_x, dir_y = dx / norm, dy / norm
            strafe_x, strafe_y = -dir_y, dir_x

            # Движение
            if 'dash' in self.abilities and random.random() < 0.01:
                # Случайный рывок
                self.x += dir_x * self.speed * 3 * dt
                self.y += dir_y * self.speed * 3 * dt
            elif dist_to_player < 250:
                # Отступление
                self.x -= dir_x * self.speed * dt
                self.y -= dir_y * self.speed * dt
            else:
                # Преследование
                self.x += dir_x * self.speed * dt
                self.y += dir_y * self.speed * dt

            # Стрейф
            self.x += strafe_x * self.speed * 0.3 * self.strafe_dir * dt
            self.y += strafe_y * self.speed * 0.3 * self.strafe_dir * dt

            # Смена направления стрейфа
            if self.state_timer <= 0:
                self.strafe_dir *= -1
                self.state_timer = 2.0

            # Телепортация — ОЧЕНЬ редкий шанс
            if 'teleport' in self.abilities and random.random() < 0.0001:
                self.x = player_pos[0] + random.randint(-50, 50)
                self.y = player_pos[1] + random.randint(-50, 50)

            # Стрельба
            if self.fire_cooldown <= 0 and dist_to_player < self._get_attack_range():
                self.fire_cooldown = self.fire_rate
                self._attack(dir_x, dir_y, game)

    def _get_attack_range(self) -> float:
        """Получение дальности атаки"""
        if 'long_range' in self.abilities:
            return 600
        return 450

    def _attack(self, dir_x: float, dir_y: float, game):
        """Атака"""
        self.attack_animation = 0.3

        if 'multi_shot' in self.abilities:
            # Множественный выстрел
            for i in range(3):
                angle_offset = (i - 1) * 0.2
                angle = math.atan2(dir_y, dir_x) + angle_offset
                bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                game.enemy_bullets.append(bullet)
        elif 'rapid_fire' in self.abilities:
            # Быстрая стрельба
            for i in range(2):
                bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
                bullet.radius = 3
                game.enemy_bullets.append(bullet)
        else:
            # Обычный выстрел
            bullet = Bullet(self.x, self.y, (dir_x, dir_y), False, self.damage)
            game.enemy_bullets.append(bullet)

    def _update_boss(self, dt: float, player_pos: Tuple[float, float], game):
        """Обновление босса"""
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist = math.hypot(dx, dy)

        if dist > 0:
            dir_x, dir_y = dx / dist, dy / dist
        else:
            dir_x, dir_y = 1, 0

        self.boss_ability_cooldown -= dt

        # Фазы босса
        if self.boss_phase == 1 and self.hp < self.max_hp * 0.7:
            self.boss_phase = 2
            self.boss_ability_cooldown = 3.0
            self.speed *= 1.2
            game.sound_manager.play('boss')

        if self.boss_phase == 2 and self.hp < self.max_hp * 0.3:
            self.boss_phase = 3
            self.boss_ability_cooldown = 2.0
            self.speed *= 1.5
            game.sound_manager.play('boss')

        # Поведение в зависимости от фазы
        if self.boss_phase == 1:
            # Обычное преследование
            if dist > 200:
                self.x += dir_x * self.speed * dt
                self.y += dir_y * self.speed * dt
            elif dist < 100:
                self.x -= dir_x * self.speed * 0.5 * dt
                self.y -= dir_y * self.speed * 0.5 * dt

            if self.fire_cooldown <= 0:
                self.fire_cooldown = self.fire_rate
                self._attack(dir_x, dir_y, game)

        elif self.boss_phase == 2:
            # Агрессивная атака
            if self.boss_ability_cooldown > 0:
                # Рывок
                self.x += dir_x * self.speed * 2.5 * dt
                self.y += dir_y * self.speed * 2.5 * dt
            else:
                self.boss_ability_cooldown = 5.0
                # Круговой залп
                for i in range(12):
                    angle = i * math.pi / 6
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)

        else:  # Фаза 3
            # Берсерк — призыв новых врагов
            if 'summon' in self.abilities and random.random() < 0.001:
                # Призыв миньонов через фабрику
                from entities.enemy_extended import EnemyFactory
                for _ in range(3):
                    minion = EnemyFactory.create_enemy(
                        self.x + random.randint(-100, 100),
                        self.y + random.randint(-100, 100),
                        self.wave, 'basic'
                    )
                    minion.hp = int(minion.hp * 0.5)
                    minion.max_hp = minion.hp
                    game.enemies.append(minion)
            # Постоянная атака
            if self.fire_cooldown <= 0:
                self.fire_cooldown = 0.3
                # Веерная атака
                for i in range(-2, 3):
                    angle = math.atan2(dir_y, dir_x) + i * 0.3
                    bullet = Bullet(self.x, self.y, (math.cos(angle), math.sin(angle)), False, self.damage)
                    game.enemy_bullets.append(bullet)

    def take_damage(self, damage: int) -> bool:
        """Получение урона"""
        if not self.alive:
            return False

        # Учёт брони
        actual_damage = max(1, damage - self.armor)

        # Уклонение
        if 'dodge' in self.abilities and random.random() < 0.2:
            return False

        # Щит
        if 'shield' in self.abilities and random.random() < 0.15:
            actual_damage = int(actual_damage * 0.3)

        self.hp -= actual_damage
        self.hit_flash = 1.0

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.death_animation = 0.5
            return True

        return False

    def apply_wave_buff(self, new_wave: int):
        """Усиление с волной"""
        self.wave = new_wave
        self.hp += 20
        self.max_hp += 20
        self.speed += 10
        self.fire_rate = max(0.5, self.fire_rate - 0.1)
        self.damage += 2

    def draw(self, screen: pygame.Surface):
        """Отрисовка врага"""
        if not self.alive and self.death_animation <= 0:
            return

        # Анимация смерти
        if not self.alive:
            alpha = int(255 * self.death_animation / 0.5)
            radius = int(self.radius * (1 + (0.5 - self.death_animation) * 2))
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), radius, 2)
            return

        # Цвет врага
        color = self._get_color()

        # Вспышка при попадании
        if self.hit_flash > 0:
            color = WHITE

        # Отрисовка тела
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)

        # Броня
        if self.armor > 0:
            armor_radius = self.radius - 3
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), armor_radius, 2)

        # Полоска HP
        self._draw_health_bar(screen)

        # Индикаторы
        if self.is_boss:
            self._draw_boss_indicator(screen)
        elif self.is_elite:
            self._draw_elite_indicator(screen)

        # Анимация атаки
        if self.attack_animation > 0:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)),
                               int(self.radius * 1.5), 2)

    def _get_color(self) -> Tuple[int, int, int]:
        """Получение цвета врага"""
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

    def _draw_health_bar(self, screen: pygame.Surface):
        """Отрисовка полосы здоровья"""
        if self.is_boss:
            # Большая полоса для босса
            bar_width = 200
            bar_height = 15
            bar_x = SCREEN_WIDTH // 2 - bar_width // 2
            bar_y = 20
        else:
            # Обычная полоса
            bar_width = self.radius * 2
            bar_height = 5
            bar_x = self.x - self.radius
            bar_y = self.y - self.radius - 12

        ratio = self.hp / self.max_hp

        # Фон
        pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_width, bar_height))
        # Здоровье
        hp_color = GREEN if ratio > 0.5 else YELLOW if ratio > 0.25 else RED
        pygame.draw.rect(screen, hp_color, (bar_x, bar_y, bar_width * ratio, bar_height))
        # Обводка
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

    def _draw_boss_indicator(self, screen: pygame.Surface):
        """Индикатор босса"""
        font = pygame.font.Font(None, 24)
        boss_text = f"БОСС - Фаза {self.boss_phase}"
        text_surf = font.render(boss_text, True, YELLOW)
        screen.blit(text_surf, (SCREEN_WIDTH // 2 - text_surf.get_width() // 2, 40))

    def _draw_elite_indicator(self, screen: pygame.Surface):
        """Индикатор элитного врага"""
        font = pygame.font.Font(None, 16)
        elite_text = "ЭЛИТА"
        text_surf = font.render(elite_text, True, YELLOW)
        screen.blit(text_surf, (self.x - text_surf.get_width() // 2,
                                self.y - self.radius - 25))