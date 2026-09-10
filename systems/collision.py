# systems/collision.py — полностью исправленная версия

import pygame
import math
import random
from typing import List, Tuple, Optional
from settings import *
from entities.bullet import Bullet
from entities.pickup import Pickup


class CollisionSystem:
    def __init__(self, game):
        self.game = game

    def check_bullet_collisions(self):
        """Проверка столкновений пуль."""
        self._check_player_bullets()
        self._check_enemy_bullets()

    def _check_player_bullets(self):
        """Проверка пуль игрока."""
        for bullet in self.game.bullets[:]:
            # Пропускаем неактивные пули
            if not getattr(bullet, 'life', 0) > 0:
                if bullet in self.game.bullets:
                    self.game.bullets.remove(bullet)
                continue

            # Проверка столкновения с врагами
            hit_enemy = False
            for enemy in self.game.enemies[:]:
                if not getattr(enemy, 'alive', False):
                    continue

                if self._circle_collision(
                    bullet.x, bullet.y, bullet.radius,
                    enemy.x, enemy.y, enemy.radius
                ):
                    # Крит
                    is_crit = random.random() < self.game.player.crit_chance
                    damage = bullet.damage * (self.game.player.crit_multiplier if is_crit else 1)
                    damage = int(damage * self.game.player.damage_multiplier)

                    # Нанесение урона
                    killed = enemy.take_damage(damage)
                    self.game.add_damage_number(
                        enemy.x, enemy.y - enemy.radius,
                        damage, WHITE if is_crit else YELLOW,
                        is_crit
                    )

                    # Взрывные пули
                    if bullet.explosive:
                        self._handle_explosion(bullet.x, bullet.y, bullet.explosion_radius)

                    # Удаление пули (если не пробивающая)
                    if not bullet.piercing:
                        if bullet in self.game.bullets:
                            self.game.bullets.remove(bullet)
                        hit_enemy = True

                    # Если враг убит — обрабатываем
                    if killed and not enemy.alive:
                        self.game.on_enemy_killed(enemy)

                    break

            if hit_enemy or bullet not in self.game.bullets:
                continue

            # Проверка столкновения с препятствиями
            for obstacle in self.game.obstacles[:]:
                if not getattr(obstacle, 'alive', False):
                    continue

                if obstacle.rect.collidepoint(bullet.x, bullet.y):
                    destroyed = obstacle.take_damage(bullet.damage)

                    if destroyed:
                        self.game.spawn_particles(
                            obstacle.rect.centerx,
                            obstacle.rect.centery,
                            10, GRAY
                        )

                        # Лут
                        loot = obstacle.get_loot()
                        for item in loot:
                            self.game.pickups.append(
                                Pickup(obstacle.rect.centerx, obstacle.rect.centery,
                                       item['type'], item.get('amount', 1))
                            )

                        # Взрыв для бочек
                        if obstacle.is_explosive():
                            self._handle_explosion(
                                obstacle.rect.centerx,
                                obstacle.rect.centery,
                                100
                            )

                        if obstacle in self.game.obstacles:
                            self.game.obstacles.remove(obstacle)

                    # Взрывные пули
                    if bullet.explosive:
                        self._handle_explosion(bullet.x, bullet.y, bullet.explosion_radius)

                    if bullet in self.game.bullets:
                        self.game.bullets.remove(bullet)
                    break

    def _check_enemy_bullets(self):
        """Проверка пуль врагов."""
        for bullet in self.game.enemy_bullets[:]:
            # Пропускаем неактивные пули
            if not getattr(bullet, 'life', 0) > 0:
                if bullet in self.game.enemy_bullets:
                    self.game.enemy_bullets.remove(bullet)
                continue

            # Проверка столкновения с игроком
            if self.game.player.alive and self._circle_collision(
                bullet.x, bullet.y, bullet.radius,
                self.game.player.x, self.game.player.y,
                self.game.player.radius
            ):
                self.game.player.take_damage(bullet.damage)
                self.game.add_damage_number(
                    self.game.player.x,
                    self.game.player.y - self.game.player.radius,
                    bullet.damage, RED
                )
                if bullet in self.game.enemy_bullets:
                    self.game.enemy_bullets.remove(bullet)
                continue

            # Проверка столкновения с препятствиями
            for obstacle in self.game.obstacles[:]:
                if not getattr(obstacle, 'alive', False):
                    continue

                if obstacle.rect.collidepoint(bullet.x, bullet.y):
                    destroyed = obstacle.take_damage(bullet.damage)
                    if destroyed:
                        self.game.spawn_particles(
                            obstacle.rect.centerx,
                            obstacle.rect.centery,
                            6, GRAY
                        )
                        if obstacle in self.game.obstacles:
                            self.game.obstacles.remove(obstacle)
                    if bullet in self.game.enemy_bullets:
                        self.game.enemy_bullets.remove(bullet)
                    break

    def check_entity_collisions(self):
        """Проверка столкновений сущностей."""
        # Игрок и враги
        for enemy in self.game.enemies[:]:
            if not getattr(enemy, 'alive', False):
                continue
            if not self.game.player.alive:
                break

            if self._circle_collision(
                self.game.player.x, self.game.player.y, self.game.player.radius,
                enemy.x, enemy.y, enemy.radius
            ):
                self.game.player.take_damage(enemy.damage)

                killed = enemy.take_damage(30)
                self.game.add_damage_number(
                    enemy.x, enemy.y - enemy.radius,
                    30, WHITE
                )

                if killed and not enemy.alive:
                    self.game.on_enemy_killed(enemy)

        # Игрок и препятствия (запрет прохождения)
        for obs in self.game.obstacles:
            if not getattr(obs, 'alive', False):
                continue
            if obs.rect.colliderect(self.game.player_rect):
                self._resolve_collision(self.game.player, obs.rect)

        # Враги и препятствия
        for enemy in self.game.enemies[:]:
            if not getattr(enemy, 'alive', False):
                continue

            enemy_rect = pygame.Rect(
                int(enemy.x - enemy.radius),
                int(enemy.y - enemy.radius),
                int(enemy.radius * 2),
                int(enemy.radius * 2)
            )

            for obs in self.game.obstacles:
                if not getattr(obs, 'alive', False):
                    continue
                if obs.rect.colliderect(enemy_rect):
                    self._resolve_collision_enemy(enemy, obs.rect)

        # Энергостены блокируют игрока
        for wall in self.game.energy_walls:
            if not getattr(wall, 'active', False):
                continue

            dist = math.hypot(
                self.game.player.x - wall.x,
                self.game.player.y - wall.y
            )
            if dist < wall.radius + self.game.player.radius:
                angle = math.atan2(
                    self.game.player.y - wall.y,
                    self.game.player.x - wall.x
                )
                push = wall.radius + self.game.player.radius - dist
                self.game.player.x += math.cos(angle) * push
                self.game.player.y += math.sin(angle) * push

    def _circle_collision(self, x1, y1, r1, x2, y2, r2):
        """Проверка столкновения кругов."""
        return math.hypot(x1 - x2, y1 - y2) < r1 + r2

    def _resolve_collision(self, player, rect):
        """Выталкивание игрока из препятствия."""
        px, py = player.x, player.y
        r = player.radius
        cx, cy = rect.center
        half_w, half_h = rect.width / 2, rect.height / 2

        dx = px - cx
        dy = py - cy

        # Если игрок в центре препятствия — выталкиваем вверх
        if dx == 0 and dy == 0:
            player.y = rect.top - r
            return

        overlap_x = half_w + r - abs(dx)
        overlap_y = half_h + r - abs(dy)

        if overlap_x < overlap_y:
            if dx > 0:
                player.x = rect.right + r
            else:
                player.x = rect.left - r
        else:
            if dy > 0:
                player.y = rect.bottom + r
            else:
                player.y = rect.top - r

    def _resolve_collision_enemy(self, enemy, rect):
        """Выталкивание врага из препятствия."""
        px, py = enemy.x, enemy.y
        r = enemy.radius
        cx, cy = rect.center
        half_w, half_h = rect.width / 2, rect.height / 2

        dx = px - cx
        dy = py - cy

        if dx == 0 and dy == 0:
            enemy.y = rect.top - r
            return

        overlap_x = half_w + r - abs(dx)
        overlap_y = half_h + r - abs(dy)

        if overlap_x < overlap_y:
            if dx > 0:
                enemy.x = rect.right + r
            else:
                enemy.x = rect.left - r
        else:
            if dy > 0:
                enemy.y = rect.bottom + r
            else:
                enemy.y = rect.top - r

    def _handle_explosion(self, x, y, radius):
        """Обработка взрыва."""
        # Урон врагам
        for enemy in self.game.enemies[:]:
            if not getattr(enemy, 'alive', False):
                continue

            dist = math.hypot(x - enemy.x, y - enemy.y)
            if dist < radius:
                damage = int(50 * (1 - dist / radius))
                killed = enemy.take_damage(damage)
                self.game.add_damage_number(
                    enemy.x, enemy.y - enemy.radius,
                    damage, ORANGE
                )
                if killed and not enemy.alive:
                    self.game.on_enemy_killed(enemy)

        # Разрушение препятствий
        for obs in self.game.obstacles[:]:
            if not getattr(obs, 'alive', False):
                continue

            dist = math.hypot(x - obs.rect.centerx, y - obs.rect.centery)
            if dist < radius:
                destroyed = obs.take_damage(100)
                if destroyed:
                    self.game.spawn_particles(
                        obs.rect.centerx,
                        obs.rect.centery,
                        15, GRAY
                    )
                    if obs in self.game.obstacles:
                        self.game.obstacles.remove(obs)

        # Визуальные эффекты
        self.game.spawn_particles(x, y, 30, ORANGE)
        self.game.spawn_sparks(x, y, 15)