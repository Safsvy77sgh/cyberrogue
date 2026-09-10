# systems/adaptive_enemies.py
import random
import math
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from settings import *
from systems.evolutionary_ai import AIIndividual, BehaviorGene, SituationalRule, EvolutionaryAIManager


# ============================================================
# КРАТКОВРЕМЕННАЯ АДАПТАЦИЯ (В РАМКАХ ОДНОГО БОЯ)
# ============================================================

@dataclass
class CombatMemory:
    """Кратковременная память боя"""
    # История урона
    damage_events: List[Dict] = field(default_factory=list)  # [{time, damage, source}]

    # История позиций игрока
    player_positions: List[Tuple[float, float]] = field(default_factory=list)

    # История действий игрока
    player_actions: List[str] = field(default_factory=list)

    # Статистика боя
    total_damage_taken: int = 0
    total_damage_dealt: int = 0
    hits_landed: int = 0
    hits_missed: int = 0
    dodges_performed: int = 0

    # Тайминги
    last_attack_time: float = 0
    last_hit_time: float = 0
    last_dodge_time: float = 0

    # Паттерны игрока
    player_attack_pattern: List[float] = field(default_factory=list)  # Интервалы между атаками
    player_dodge_pattern: List[str] = field(default_factory=list)  # Направления уклонений

    def add_damage_event(self, time: float, damage: int, source: str):
        """Добавление события урона"""
        self.damage_events.append({'time': time, 'damage': damage, 'source': source})
        if len(self.damage_events) > 50:
            self.damage_events.pop(0)

    def add_player_position(self, x: float, y: float):
        """Добавление позиции игрока"""
        self.player_positions.append((x, y))
        if len(self.player_positions) > 30:
            self.player_positions.pop(0)

    def add_player_action(self, action: str):
        """Добавление действия игрока"""
        self.player_actions.append(action)
        if len(self.player_actions) > 20:
            self.player_actions.pop(0)

    def get_recent_positions(self, count: int = 10) -> List[Tuple[float, float]]:
        """Получение последних позиций"""
        return self.player_positions[-count:]

    def predict_player_position(self, dt: float = 1.0) -> Tuple[float, float]:
        """Предсказание следующей позиции игрока"""
        if len(self.player_positions) < 3:
            return self.player_positions[-1] if self.player_positions else (0, 0)

        # Вычисление вектора движения
        recent = self.get_recent_positions(5)
        start = recent[0]
        end = recent[-1]

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        # Экстраполяция
        predicted_x = end[0] + dx * dt
        predicted_y = end[1] + dy * dt

        return (predicted_x, predicted_y)

    def get_player_movement_direction(self) -> str:
        """Получение направления движения игрока"""
        if len(self.player_positions) < 2:
            return 'stationary'

        recent = self.get_recent_positions(5)
        start = recent[0]
        end = recent[-1]

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        if abs(dx) < 10 and abs(dy) < 10:
            return 'stationary'
        elif abs(dx) > abs(dy):
            return 'right' if dx > 0 else 'left'
        else:
            return 'down' if dy > 0 else 'up'

    def get_dodge_direction_tendency(self) -> str:
        """Получение тенденции уклонений"""
        if not self.player_dodge_pattern:
            return 'unknown'
        return max(set(self.player_dodge_pattern), key=self.player_dodge_pattern.count)

    def get_attack_interval(self) -> float:
        """Получение среднего интервала атак"""
        if len(self.player_attack_pattern) < 2:
            return 1.0
        return sum(self.player_attack_pattern) / len(self.player_attack_pattern)


# ============================================================
# АДАПТИВНЫЙ КОНТРОЛЛЕР ВРАГА
# ============================================================

class AdaptiveEnemyController:
    """Адаптивный контроллер для отдельного врага"""

    def __init__(self, enemy, evolutionary_individual: Optional[AIIndividual] = None):
        self.enemy = enemy
        self.evolutionary_individual = evolutionary_individual
        self.combat_memory = CombatMemory()

        # Адаптивные параметры (обновляются в бою)
        self.adaptive_params = {
            'aggression_modifier': 1.0,
            'dodge_modifier': 1.0,
            'retreat_modifier': 1.0,
            'strafe_modifier': 1.0,
            'attack_range_modifier': 1.0,
            'ability_usage_modifier': 1.0
        }

        # Счётчики эффективности
        self.effectiveness_tracker = {
            'aggression_success': 0,
            'aggression_fail': 0,
            'dodge_success': 0,
            'dodge_fail': 0,
            'retreat_success': 0,
            'retreat_fail': 0,
            'strafe_success': 0,
            'strafe_fail': 0
        }

        # Время последнего обновления адаптации
        self.last_adaptation_time = 0
        self.adaptation_interval = 2.0  # Обновление каждые 2 секунды

        # Предсказание
        self.predicted_player_position = (0, 0)
        self.prediction_confidence = 0.0

        # Состояние
        self.current_strategy = 'balanced'
        self.strategy_history = []
        self.strategy_success = {}

    def update(self, dt: float, player, game):
        """Обновление адаптивного контроллера"""
        # Обновление памяти
        self._update_memory(dt, player)

        # Предсказание позиции игрока
        self._update_prediction(player)

        # Адаптация параметров
        self._adapt_parameters(dt)

        # Выбор стратегии
        self._select_strategy(player)

        # Применение стратегии
        self._apply_strategy(dt, player, game)

        # Обновление эффективности
        self._update_effectiveness(dt, player)

    def _update_memory(self, dt: float, player):
        """Обновление памяти боя"""
        self.combat_memory.add_player_position(player.x, player.y)

        # Определение действия игрока
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

        # Запись уклонений
        if hasattr(player, 'is_dashing') and player.is_dashing:
            direction = self.combat_memory.get_player_movement_direction()
            self.combat_memory.player_dodge_pattern.append(direction)
            if len(self.combat_memory.player_dodge_pattern) > 20:
                self.combat_memory.player_dodge_pattern.pop(0)

    def _update_prediction(self, player):
        """Обновление предсказания"""
        predicted = self.combat_memory.predict_player_position(0.5)
        self.predicted_player_position = predicted

        # Оценка уверенности
        if len(self.combat_memory.player_positions) >= 5:
            # Проверка точности предыдущих предсказаний
            movement_direction = self.combat_memory.get_player_movement_direction()
            if movement_direction == 'stationary':
                self.prediction_confidence = 0.9
            else:
                self.prediction_confidence = 0.6
        else:
            self.prediction_confidence = 0.3

    def _adapt_parameters(self, dt: float):
        """Адаптация параметров на основе эффективности"""
        self.last_adaptation_time += dt

        if self.last_adaptation_time < self.adaptation_interval:
            return

        self.last_adaptation_time = 0

        # Адаптация агрессии
        total_aggression = (self.effectiveness_tracker['aggression_success'] +
                            self.effectiveness_tracker['aggression_fail'])
        if total_aggression > 0:
            success_rate = self.effectiveness_tracker['aggression_success'] / total_aggression
            if success_rate < 0.3:
                self.adaptive_params['aggression_modifier'] *= 0.8
            elif success_rate > 0.7:
                self.adaptive_params['aggression_modifier'] *= 1.2

        # Адаптация уклонения
        total_dodge = (self.effectiveness_tracker['dodge_success'] +
                       self.effectiveness_tracker['dodge_fail'])
        if total_dodge > 0:
            success_rate = self.effectiveness_tracker['dodge_success'] / total_dodge
            if success_rate < 0.3:
                self.adaptive_params['dodge_modifier'] *= 0.7
            elif success_rate > 0.7:
                self.adaptive_params['dodge_modifier'] *= 1.3

        # Адаптация отступления
        total_retreat = (self.effectiveness_tracker['retreat_success'] +
                         self.effectiveness_tracker['retreat_fail'])
        if total_retreat > 0:
            success_rate = self.effectiveness_tracker['retreat_success'] / total_retreat
            if success_rate < 0.3:
                self.adaptive_params['retreat_modifier'] *= 0.7
            elif success_rate > 0.7:
                self.adaptive_params['retreat_modifier'] *= 1.3

        # Адаптация стрейфа
        total_strafe = (self.effectiveness_tracker['strafe_success'] +
                        self.effectiveness_tracker['strafe_fail'])
        if total_strafe > 0:
            success_rate = self.effectiveness_tracker['strafe_success'] / total_strafe
            if success_rate < 0.3:
                self.adaptive_params['strafe_modifier'] *= 0.8
            elif success_rate > 0.7:
                self.adaptive_params['strafe_modifier'] *= 1.2

        # Ограничение параметров
        for key in self.adaptive_params:
            self.adaptive_params[key] = max(0.3, min(3.0, self.adaptive_params[key]))

        # Сброс счётчиков
        for key in self.effectiveness_tracker:
            self.effectiveness_tracker[key] = 0

    def _select_strategy(self, player):
        """Выбор стратегии на основе ситуации"""
        dist = math.hypot(self.enemy.x - player.x, self.enemy.y - player.y)

        # Определение характеристик игрока
        player_hp_ratio = player.hp / player.max_hp if hasattr(player, 'max_hp') else 1.0
        enemy_hp_ratio = self.enemy.hp / self.enemy.max_hp if hasattr(self.enemy, 'max_hp') else 1.0

        # Выбор стратегии
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

        # Запись стратегии
        if strategy != self.current_strategy:
            self.strategy_history.append(self.current_strategy)
            if len(self.strategy_history) > 10:
                self.strategy_history.pop(0)
            self.current_strategy = strategy

    def _fire_at(self, dir_x: float, dir_y: float, game):
        """Safely trigger the enemy's attack. Older enemies without a
        `_shoot` method fall back to a generic `attack`/`shoot` method if
        one exists, otherwise the attack is skipped rather than crashing."""
        if hasattr(self.enemy, '_shoot'):
            self.enemy._shoot(dir_x, dir_y, game)
        elif hasattr(self.enemy, 'shoot'):
            self.enemy.shoot(dir_x, dir_y, game)
        elif hasattr(self.enemy, 'attack'):
            self.enemy.attack(dir_x, dir_y, game)
        # else: enemy has no known attack method, skip silently

    def _apply_strategy(self, dt: float, player, game):
        """Применение выбранной стратегии"""
        dist = math.hypot(self.enemy.x - player.x, self.enemy.y - player.y)
        dx = player.x - self.enemy.x
        dy = player.y - self.enemy.y
        norm = math.hypot(dx, dy)

        if norm == 0:
            return

        dir_x, dir_y = dx / norm, dy / norm

        # Базовые параметры из эволюционной особи
        gene = self.evolutionary_individual.gene if self.evolutionary_individual else BehaviorGene()

        # Применение стратегии
        if self.current_strategy == 'aggressive':
            # Агрессивная стратегия
            aggression = gene.aggression * self.adaptive_params['aggression_modifier']
            if random.random() < aggression:
                self.enemy.x += dir_x * self.enemy.speed * dt
                self.enemy.y += dir_y * self.enemy.speed * dt

            # Частая атака
            if self.enemy.fire_cooldown <= 0 and dist < gene.max_attack_distance:
                self._fire_at(dir_x, dir_y, game)
                self.effectiveness_tracker['aggression_success'] += 1

        elif self.current_strategy == 'defensive':
            # Оборонительная стратегия
            retreat = gene.backpedal_probability * self.adaptive_params['retreat_modifier']
            if random.random() < retreat:
                self.enemy.x -= dir_x * self.enemy.speed * dt
                self.enemy.y -= dir_y * self.enemy.speed * dt
                self.effectiveness_tracker['retreat_success'] += 1

            # Редкая атака
            if self.enemy.fire_cooldown <= 0 and dist > gene.optimal_attack_distance:
                self._fire_at(dir_x, dir_y, game)

        elif self.current_strategy == 'close_combat':
            # Ближний бой
            strafe = gene.strafe_probability * self.adaptive_params['strafe_modifier']
            if random.random() < strafe:
                strafe_dir = 1 if random.random() < 0.5 else -1
                self.enemy.x += -dir_y * strafe_dir * self.enemy.speed * dt
                self.enemy.y += dir_x * strafe_dir * self.enemy.speed * dt
                self.effectiveness_tracker['strafe_success'] += 1

            # Атака вблизи
            if self.enemy.fire_cooldown <= 0:
                self._fire_at(dir_x, dir_y, game)

        elif self.current_strategy == 'long_range':
            # Дальний бой
            if dist < gene.optimal_attack_distance:
                # Отход
                self.enemy.x -= dir_x * self.enemy.speed * dt
                self.enemy.y -= dir_y * self.enemy.speed * dt
            else:
                # Атака с дистанции
                if self.enemy.fire_cooldown <= 0:
                    # Предсказание позиции
                    pred_x, pred_y = self.predicted_player_position
                    pred_dx = pred_x - self.enemy.x
                    pred_dy = pred_y - self.enemy.y
                    pred_norm = math.hypot(pred_dx, pred_dy)
                    if pred_norm > 0:
                        self._fire_at(pred_dx / pred_norm, pred_dy / pred_norm, game)

        elif self.current_strategy == 'opportunistic':
            # Оппортунистическая стратегия (игрок перезаряжается)
            rush = gene.rush_probability * self.adaptive_params['aggression_modifier']
            if random.random() < rush:
                self.enemy.x += dir_x * self.enemy.speed * 2 * dt
                self.enemy.y += dir_y * self.enemy.speed * 2 * dt
                self.effectiveness_tracker['aggression_success'] += 1

            # Немедленная атака
            if self.enemy.fire_cooldown <= 0:
                self._fire_at(dir_x, dir_y, game)

        elif self.current_strategy == 'desperate':
            # Отчаянная стратегия (низкое HP)
            # Попытка уклонения
            dodge = gene.dodge_probability * self.adaptive_params['dodge_modifier']
            if random.random() < dodge:
                angle = random.uniform(0, 2 * math.pi)
                self.enemy.x += math.cos(angle) * self.enemy.speed * 1.5 * dt
                self.enemy.y += math.sin(angle) * self.enemy.speed * 1.5 * dt
                self.effectiveness_tracker['dodge_success'] += 1

            # Последняя попытка атаки
            if self.enemy.fire_cooldown <= 0:
                self._fire_at(dir_x, dir_y, game)

        else:  # balanced
            # Сбалансированная стратегия
            # Поддержание оптимальной дистанции
            if dist > gene.optimal_attack_distance:
                self.enemy.x += dir_x * self.enemy.speed * dt
                self.enemy.y += dir_y * self.enemy.speed * dt
            elif dist < gene.min_attack_distance:
                self.enemy.x -= dir_x * self.enemy.speed * dt
                self.enemy.y -= dir_y * self.enemy.speed * dt

            # Атака
            if self.enemy.fire_cooldown <= 0 and dist < gene.max_attack_distance:
                self._fire_at(dir_x, dir_y, game)

    def _update_effectiveness(self, dt: float, player):
        """Обновление эффективности стратегий"""
        # Проверка успешности атак
        if self.combat_memory.hits_landed > 0:
            self.effectiveness_tracker['aggression_success'] += 1
        if self.combat_memory.hits_missed > 2:
            self.effectiveness_tracker['aggression_fail'] += 1

        # Проверка успешности уклонений
        if self.combat_memory.dodges_performed > 0:
            self.effectiveness_tracker['dodge_success'] += 1

    def record_hit(self, damage: int):
        """Запись попадания"""
        self.combat_memory.hits_landed += 1
        self.combat_memory.total_damage_dealt += damage
        self.combat_memory.last_hit_time = 0

    def record_miss(self):
        """Запись промаха"""
        self.combat_memory.hits_missed += 1

    def record_dodge(self):
        """Запись уклонения"""
        self.combat_memory.dodges_performed += 1
        self.combat_memory.last_dodge_time = 0

    def record_damage_taken(self, damage: int):
        """Запись полученного урона"""
        self.combat_memory.total_damage_taken += damage

    def get_combat_stats(self) -> dict:
        """Получение статистики боя"""
        return {
            'damage_dealt': self.combat_memory.total_damage_dealt,
            'damage_taken': self.combat_memory.total_damage_taken,
            'hits_landed': self.combat_memory.hits_landed,
            'hits_missed': self.combat_memory.hits_missed,
            'dodges': self.combat_memory.dodges_performed,
            'strategy': self.current_strategy,
            'adaptive_params': self.adaptive_params.copy()
        }


# ============================================================
# МЕНЕДЖЕР АДАПТИВНЫХ ВРАГОВ
# ============================================================

class AdaptiveEnemySystem:
    """Система адаптивных врагов (дополняет эволюционную)"""

    def __init__(self, game=None):
        self.game = game
        self.controllers: Dict[int, AdaptiveEnemyController] = {}
        self.global_stats = {
            'total_encounters': 0,
            'total_damage_dealt': 0,
            'total_damage_taken': 0,
            'total_hits': 0,
            'total_misses': 0,
            'total_dodges': 0
        }

        # Анализ игрока
        self.player_profile = {
            'preferred_weapons': {},
            'movement_patterns': {},
            'attack_patterns': {},
            'dodge_patterns': {},
            'skill_usage': {}
        }

        self.weapon_adaptation = {}

        self.save_file = "adaptive_enemy_data.json"
        self.load_data()

    def get_controller(self, enemy_id: int, enemy=None, evolutionary_individual=None) -> AdaptiveEnemyController:
        """Получение или создание контроллера для врага"""
        if enemy_id not in self.controllers:
            controller = AdaptiveEnemyController(enemy, evolutionary_individual)
            self.controllers[enemy_id] = controller
        return self.controllers[enemy_id]

    def update(self, dt: float, game):
        """Обновление системы"""
        self.game = game

        # Обновление всех контроллеров
        for enemy in game.enemies[:]:
            if enemy.alive:
                # Пропускаем миньонов и старых врагов
                if not hasattr(enemy, 'fire_cooldown'):
                    continue
                if not hasattr(enemy, '_shoot'):
                    continue

                enemy_id = id(enemy)
                controller = self.get_controller(
                    enemy_id,
                    enemy,
                    getattr(enemy, 'evolutionary_individual', None)
                )
                controller.update(dt, game.player, game)

    def record_combat_result(self, controller: AdaptiveEnemyController, enemy):
        """Запись результата боя"""
        stats = controller.get_combat_stats()

        # Обновление глобальной статистики
        self.global_stats['total_encounters'] += 1
        self.global_stats['total_damage_dealt'] += stats['damage_dealt']
        self.global_stats['total_damage_taken'] += stats['damage_taken']
        self.global_stats['total_hits'] += stats['hits_landed']
        self.global_stats['total_misses'] += stats['hits_missed']
        self.global_stats['total_dodges'] += stats['dodges']

        # Обновление профиля игрока
        self._update_player_profile(controller)

        # Сохранение
        self.save_data()

    def _update_player_profile(self, controller: AdaptiveEnemyController):
        """Обновление профиля игрока"""
        # Оружие
        if hasattr(self.game, 'player') and hasattr(self.game.player, 'current_weapon'):
            weapon = self.game.player.current_weapon
            self.player_profile['preferred_weapons'][weapon] = \
                self.player_profile['preferred_weapons'].get(weapon, 0) + 1

        # Движение
        movement = controller.combat_memory.get_player_movement_direction()
        self.player_profile['movement_patterns'][movement] = \
            self.player_profile['movement_patterns'].get(movement, 0) + 1

        # Уклонения
        dodge_dir = controller.combat_memory.get_dodge_direction_tendency()
        self.player_profile['dodge_patterns'][dodge_dir] = \
            self.player_profile['dodge_patterns'].get(dodge_dir, 0) + 1

    def get_player_preferred_weapon(self) -> str:
        """Получение предпочитаемого оружия игрока"""
        if not self.player_profile['preferred_weapons']:
            return 'pistol'
        return max(self.player_profile['preferred_weapons'],
                   key=self.player_profile['preferred_weapons'].get)

    def get_player_movement_tendency(self) -> str:
        """Получение тенденции движения игрока"""
        if not self.player_profile['movement_patterns']:
            return 'unknown'
        return max(self.player_profile['movement_patterns'],
                   key=self.player_profile['movement_patterns'].get)

    def get_player_dodge_tendency(self) -> str:
        """Получение тенденции уклонений"""
        if not self.player_profile['dodge_patterns']:
            return 'unknown'
        return max(self.player_profile['dodge_patterns'],
                   key=self.player_profile['dodge_patterns'].get)

    def get_global_stats(self) -> dict:
        """Получение глобальной статистики"""
        return self.global_stats.copy()

    def save_data(self):
        """Сохранение данных"""
        data = {
            'global_stats': self.global_stats,
            'player_profile': self.player_profile
        }
        try:
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def load_data(self):
        """Загрузка данных"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.global_stats = data.get('global_stats', self.global_stats)
                    self.player_profile = data.get('player_profile', self.player_profile)
            except:
                pass

    def reset_adaptation(self):
        """Сброс адаптации"""
        self.controllers.clear()
        self.global_stats = {
            'total_encounters': 0,
            'total_damage_dealt': 0,
            'total_damage_taken': 0,
            'total_hits': 0,
            'total_misses': 0,
            'total_dodges': 0
        }
        self.save_data()

    def draw_debug(self, screen: pygame.Surface):
        """Отрисовка отладочной информации"""
        if not hasattr(self.game, 'debug_mode') or not self.game.debug_mode:
            return

        font = pygame.font.Font(None, 20)
        y = 400

        stats = self.get_global_stats()
        debug_texts = [
            f"Адаптация ИИ:",
            f"Боёв: {stats['total_encounters']}",
            f"Урона нанесено: {stats['total_damage_dealt']}",
            f"Урона получено: {stats['total_damage_taken']}",
            f"Попаданий: {stats['total_hits']}",
            f"Промахов: {stats['total_misses']}",
            f"Уклонений: {stats['total_dodges']}",
            f"Оружие игрока: {self.get_player_preferred_weapon()}",
            f"Движение: {self.get_player_movement_tendency()}",
            f"Уклонения: {self.get_player_dodge_tendency()}"
        ]

        for text in debug_texts:
            rendered = font.render(text, True, CYAN)
            screen.blit(rendered, (10, y))
            y += 20

    def update_adaptation(self, weapon_type: str, damage: int):
        """Обновляет адаптацию врагов к оружию игрока."""
        if not hasattr(self, 'weapon_adaptation'):
            self.weapon_adaptation = {}
        if weapon_type not in self.weapon_adaptation:
            self.weapon_adaptation[weapon_type] = {'damage_taken': 0, 'adaptation': 1.0}
        self.weapon_adaptation[weapon_type]['damage_taken'] += damage
        if self.weapon_adaptation[weapon_type]['damage_taken'] > 1000:
            old_adaptation = self.weapon_adaptation[weapon_type]['adaptation']
            new_adaptation = min(2.0, old_adaptation + 0.1)
            self.weapon_adaptation[weapon_type]['adaptation'] = new_adaptation
            self.weapon_adaptation[weapon_type]['damage_taken'] = 0
            self._apply_adaptation_to_alive_enemies(new_adaptation - old_adaptation)

    def _apply_adaptation_to_alive_enemies(self, adaptation_increase: float):
        """Применяет прирост адаптации к текущим живым врагам (броня/скорость)."""
        if adaptation_increase <= 0 or not self.game or not hasattr(self.game, 'enemies'):
            return
        for enemy in self.game.enemies:
            if not getattr(enemy, 'alive', False):
                continue
            if hasattr(enemy, 'armor'):
                enemy.armor += adaptation_increase * 2
            elif hasattr(enemy, 'speed'):
                enemy.speed *= (1.0 + adaptation_increase * 0.05)