# systems/events.py
import random
import math
import pygame
from entities.pickup import Pickup
from entities.obstacle import Obstacle
from typing import Dict, List, Callable
from settings import *


class GameEvent:
    """Игровое событие"""

    def __init__(self, event_id: str, name: str, description: str,
                 duration: float, effect_func: Callable, weight: float = 1.0,
                 end_func: Callable = None):
        self.id = event_id
        self.name = name
        self.description = description
        self.duration = duration
        self.effect_func = effect_func
        self.end_func = end_func
        self.weight = weight
        self.timer = 0
        self.active = False


class EventSystem:
    """Система случайных событий"""

    def __init__(self, game):
        self.game = game
        self.events = []
        self.active_events = []
        self.event_cooldown = 90.0  # Секунд между событиями (реже)
        self.current_cooldown = random.uniform(30, 60)  # Первое событие через 30-60 сек
        self.max_active_events = 2  # Не больше 2 событий одновременно
        self._register_events()

    def _register_events(self):
        """Регистрация всех событий"""

        # === ПОЛОЖИТЕЛЬНЫЕ СОБЫТИЯ ===
        self.events.append(GameEvent(
            'supply_drop', '📦 Сброс припасов', 'Прибыли припасы!',
            5.0, self._supply_drop, 1.5
        ))
        self.events.append(GameEvent(
            'double_exp', '✨ Двойной опыт', 'Удвоенный опыт на 30 секунд!',
            30.0, self._double_exp, 1.2, self._end_double_exp
        ))
        self.events.append(GameEvent(
            'healing_wave', '💚 Волна исцеления', 'Все лечатся!',
            3.0, self._healing_wave, 1.0
        ))
        self.events.append(GameEvent(
            'weapon_surge', '⚔️ Оружейный всплеск', 'Урон увеличен на 50%!',
            15.0, self._weapon_surge, 0.8, self._end_weapon_surge
        ))
        self.events.append(GameEvent(
            'shield_overload', '🛡 Перегрузка щита', 'Щит восстановлен!',
            5.0, self._shield_overload, 0.7
        ))
        self.events.append(GameEvent(
            'energy_surge', '🔋 Энергетический всплеск', 'Энергия восстановлена!',
            3.0, self._energy_surge, 0.8
        ))
        self.events.append(GameEvent(
            'lucky_drop', '🍀 Удачный дроп', 'Редкие предметы падают с врагов!',
            20.0, self._lucky_drop, 0.6, self._end_lucky_drop
        ))
        self.events.append(GameEvent(
            'speed_boost', '💨 Ускорение', 'Скорость увеличена!',
            15.0, self._speed_boost, 0.7, self._end_speed_boost
        ))
        self.events.append(GameEvent(
            'infinite_ammo', '♾ Бесконечные патроны', 'Бесконечные патроны!',
            20.0, self._infinite_ammo, 0.5, self._end_infinite_ammo
        ))
        self.events.append(GameEvent(
            'crit_surge', '💥 Критовый всплеск', 'Шанс крита увеличен!',
            15.0, self._crit_surge, 0.6, self._end_crit_surge
        ))

        # === ОТРИЦАТЕЛЬНЫЕ СОБЫТИЯ ===
        self.events.append(GameEvent(
            'enemy_raid', '👾 Нашествие врагов', 'Орда врагов атакует!',
            15.0, self._enemy_raid, 1.5
        ))
        self.events.append(GameEvent(
            'meteor_shower', '☄️ Метеоритный дождь', 'Метеориты падают с неба!',
            12.0, self._meteor_shower, 1.0, self._end_meteor_shower
        ))
        self.events.append(GameEvent(
            'gravity_anomaly', '🌀 Гравитационная аномалия', 'Гравитация нарушена!',
            10.0, self._gravity_anomaly, 0.7, self._end_gravity_anomaly
        ))
        self.events.append(GameEvent(
            'darkness', '🌑 Тьма', 'Внезапная тьма опустилась!',
            12.0, self._darkness, 0.8, self._end_darkness
        ))
        self.events.append(GameEvent(
            'poison_cloud', '☠️ Ядовитое облако', 'Ядовитый газ заполняет комнату!',
            10.0, self._poison_cloud, 0.7, self._end_poison_cloud
        ))
        self.events.append(GameEvent(
            'slow_motion', '🐌 Замедление', 'Всё замедляется!',
            8.0, self._slow_motion, 0.5, self._end_slow_motion
        ))
        self.events.append(GameEvent(
            'damage_curse', '💔 Проклятие урона', 'Получаемый урон увеличен!',
            15.0, self._damage_curse, 0.6, self._end_damage_curse
        ))
        self.events.append(GameEvent(
            'enemy_buff', '👹 Усиление врагов', 'Враги становятся сильнее!',
            20.0, self._enemy_buff, 0.7, self._end_enemy_buff
        ))
        self.events.append(GameEvent(
            'item_drought', '🚫 Засуха предметов', 'Предметы не выпадают!',
            15.0, self._item_drought, 0.4, self._end_item_drought
        ))
        self.events.append(GameEvent(
            'ice_age', '❄️ Ледниковый период', 'Всё замерзает!',
            10.0, self._ice_age, 0.5, self._end_ice_age
        ))

        # === НЕЙТРАЛЬНЫЕ / ОСОБЫЕ СОБЫТИЯ ===
        self.events.append(GameEvent(
            'trader_arrival', '🧑‍💼 Прибытие торговца', 'Торговец прибыл!',
            25.0, self._trader_arrival, 0.5
        ))
        self.events.append(GameEvent(
            'chest_spawn', '🎁 Сундук', 'Сундук появился!',
            5.0, self._chest_spawn, 0.6
        ))
        self.events.append(GameEvent(
            'wall_break', '🧱 Разрушение стен', 'Часть стен разрушена!',
            3.0, self._wall_break, 0.4
        ))
        self.events.append(GameEvent(
            'teleport_shuffle', '🌀 Телепортация', 'Все телепортированы!',
            2.0, self._teleport_shuffle, 0.3
        ))
        self.events.append(GameEvent(
            'golden_enemy', '⭐ Золотой враг', 'Золотой враг появился!',
            10.0, self._golden_enemy, 0.4
        ))
        self.events.append(GameEvent(
            'mirror_world', '🪞 Зеркальный мир', 'Управление инвертировано!',
            12.0, self._mirror_world, 0.3, self._end_mirror_world
        ))
        self.events.append(GameEvent(
            'rain_heal', '🌧 Дождь исцеления', 'Лёгкий дождь лечит!',
            15.0, self._rain_heal, 0.5
        ))
        self.events.append(GameEvent(
            'electric_storm', '⚡ Электрическая буря', 'Молнии бьют случайно!',
            10.0, self._electric_storm, 0.6
        ))
        self.events.append(GameEvent(
            'mystery_box', '🎲 Загадочный ящик', 'Случайный предмет!',
            5.0, self._mystery_box, 0.7
        ))
        self.events.append(GameEvent(
            'time_anomaly', '⏰ Временная аномалия', 'Время искажается!',
            8.0, self._time_anomaly, 0.4, self._end_time_anomaly
        ))
        self.events.append(GameEvent(
            'ghost_enemy', '👻 Призрачный враг', 'Призрак вселился во врага!',
            10.0, self._ghost_enemy, 0.3
        ))
        self.events.append(GameEvent(
            'magnetic_field', '🧲 Магнитное поле', 'Предметы притягиваются!',
            15.0, self._magnetic_field, 0.5
        ))
        self.events.append(GameEvent(
            'fire_floor', '🔥 Огненный пол', 'Пол горит!',
            12.0, self._fire_floor, 0.5, self._end_fire_floor
        ))
        self.events.append(GameEvent(
            'wind_blast', '💨 Порыв ветра', 'Ветер сдувает!',
            8.0, self._wind_blast, 0.4
        ))
        self.events.append(GameEvent(
            'reverse_controls', '🔄 Инверсия управления', 'Управление инвертировано!',
            10.0, self._reverse_controls, 0.3, self._end_reverse_controls
        ))
        self.events.append(GameEvent(
            'shadow_clone', '👥 Теневой клон', 'Появился тёмный двойник!',
            15.0, self._shadow_clone, 0.3
        ))
        self.events.append(GameEvent(
            'crystal_rain', '💎 Кристальный дождь', 'Кристаллы падают!',
            8.0, self._crystal_rain, 0.5
        ))
        self.events.append(GameEvent(
            'berserk', '😡 Берсерк', 'Урон увеличен, защита снижена!',
            20.0, self._berserk, 0.4, self._end_berserk
        ))
        self.events.append(GameEvent(
            'invisibility', '👻 Невидимость', 'Вы невидимы!',
            10.0, self._invisibility, 0.3, self._end_invisibility
        ))
        self.events.append(GameEvent(
            'trap_spam', '🕳 Ловушки', 'Ловушки появляются!',
            8.0, self._trap_spam, 0.4
        ))

    # ==================== ОСНОВНЫЕ МЕТОДЫ ====================

    def update(self, dt: float):
        """Обновление событий"""
        self.current_cooldown -= dt

        # Запуск нового события
        if self.current_cooldown <= 0 and len(self.active_events) < self.max_active_events:
            self._trigger_random_event()
            self.current_cooldown = random.uniform(60, 120)  # Следующее через 60-120 сек

        # Обновление активных событий
        for event in self.active_events[:]:
            event.timer -= dt
            if event.timer <= 0:
                event.active = False
                self.active_events.remove(event)
                if event.end_func:
                    event.end_func(self.game)

    def _trigger_random_event(self):
        """Запуск случайного события"""
        available = [e for e in self.events if not e.active]
        if not available:
            return
        total_weight = sum(e.weight for e in available)
        if total_weight <= 0:
            return
        roll = random.uniform(0, total_weight)
        for event in available:
            roll -= event.weight
            if roll <= 0:
                self._activate_event(event)
                return

    def _activate_event(self, event: GameEvent):
        """Активация события"""
        event.active = True
        event.timer = event.duration
        self.active_events.append(event)
        event.effect_func(self.game)
        self.game.ui.show_notification(f"Событие: {event.name}", ORANGE, 3.0)

    # ==================== ПОЛОЖИТЕЛЬНЫЕ ЭФФЕКТЫ ====================

    def _supply_drop(self, game):
        for _ in range(5):
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            type_ = random.choice(['repair', 'energy', 'scrap', 'circuit', 'crystal'])
            game.pickups.append(Pickup(x, y, type_))

    def _double_exp(self, game):
        game.exp_multiplier = 2.0

    def _end_double_exp(self, game):
        game.exp_multiplier = 1.0

    def _healing_wave(self, game):
        game.player.heal(50)

    def _weapon_surge(self, game):
        game.player.damage_multiplier *= 1.5

    def _end_weapon_surge(self, game):
        game.player.damage_multiplier /= 1.5

    def _shield_overload(self, game):
        game.player.shield_timer = max(game.player.shield_timer, 10.0)

    def _energy_surge(self, game):
        game.player.energy = min(game.player.max_energy, game.player.energy + 100)

    def _lucky_drop(self, game):
        game.lucky_drop_active = True

    def _end_lucky_drop(self, game):
        game.lucky_drop_active = False

    def _speed_boost(self, game):
        game.player.speed *= 1.5

    def _end_speed_boost(self, game):
        game.player.speed /= 1.5

    def _infinite_ammo(self, game):
        game.player.infinite_ammo = True

    def _end_infinite_ammo(self, game):
        game.player.infinite_ammo = False

    def _crit_surge(self, game):
        game.player.crit_chance += 0.25

    def _end_crit_surge(self, game):
        game.player.crit_chance -= 0.25

    # ==================== ОТРИЦАТЕЛЬНЫЕ ЭФФЕКТЫ ====================

    def _enemy_raid(self, game):
        for _ in range(random.randint(5, 8)):
            if hasattr(game, 'spawn_enemy'):
                game.spawn_enemy()
            elif game.current_room:
                from entities.enemy_extended import EnemyFactory
                enemy_types = game.location_data.get(game.current_location, {}).get('enemy_types', ['basic'])
                enemy_type = random.choice(enemy_types)
                x = random.randint(game.current_room['x'] + 50,
                                   game.current_room['x'] + game.current_room['width'] - 50)
                y = random.randint(game.current_room['y'] + 50,
                                   game.current_room['y'] + game.current_room['height'] - 50)
                enemy = EnemyFactory.create_enemy(x, y, game.room_manager.get_effective_wave(), enemy_type)
                game.enemies.append(enemy)

    def _meteor_shower(self, game):
        game.meteor_shower_active = True
        game.meteor_timer = 0

    def _end_meteor_shower(self, game):
        game.meteor_shower_active = False

    def _gravity_anomaly(self, game):
        game.gravity_multiplier = 0.3

    def _end_gravity_anomaly(self, game):
        game.gravity_multiplier = 1.0

    def _darkness(self, game):
        game.darkness_active = True

    def _end_darkness(self, game):
        game.darkness_active = False

    def _poison_cloud(self, game):
        game.poison_cloud_active = True

    def _end_poison_cloud(self, game):
        game.poison_cloud_active = False

    def _slow_motion(self, game):
        game.time_scale = 0.5

    def _end_slow_motion(self, game):
        game.time_scale = 1.0

    def _damage_curse(self, game):
        game.player.damage_taken_multiplier = getattr(game.player, 'damage_taken_multiplier', 1.0) * 1.5

    def _end_damage_curse(self, game):
        game.player.damage_taken_multiplier = 1.0

    def _enemy_buff(self, game):
        for enemy in game.enemies:
            enemy.max_hp *= 1.5
            enemy.hp *= 1.5
            if hasattr(enemy, 'damage'):
                enemy.damage *= 1.3

    def _end_enemy_buff(self, game):
        for enemy in game.enemies:
            enemy.max_hp /= 1.5
            enemy.hp /= 1.5
            if hasattr(enemy, 'damage'):
                enemy.damage /= 1.3

    def _item_drought(self, game):
        game.item_drought_active = True

    def _end_item_drought(self, game):
        game.item_drought_active = False

    def _ice_age(self, game):
        game.ice_age_active = True
        for enemy in game.enemies:
            if hasattr(enemy, 'speed'):
                enemy.speed *= 0.5

    def _end_ice_age(self, game):
        game.ice_age_active = False
        for enemy in game.enemies:
            if hasattr(enemy, 'speed'):
                enemy.speed *= 2.0

    # ==================== НЕЙТРАЛЬНЫЕ / ОСОБЫЕ ====================

    def _trader_arrival(self, game):
        game.trader_active = True
        game.trader_position = (random.randint(100, SCREEN_WIDTH - 100),
                                random.randint(100, SCREEN_HEIGHT - 100))

    def _chest_spawn(self, game):
        x = random.randint(100, SCREEN_WIDTH - 100)
        y = random.randint(100, SCREEN_HEIGHT - 100)
        game.pickups.append(Pickup(x, y, 'weapon_pistol'))

    def _wall_break(self, game):
        if game.obstacles:
            for _ in range(min(3, len(game.obstacles))):
                if game.obstacles:
                    game.obstacles.pop(random.randint(0, len(game.obstacles) - 1))

    def _teleport_shuffle(self, game):
        for enemy in game.enemies:
            enemy.x = random.randint(50, SCREEN_WIDTH - 50)
            enemy.y = random.randint(50, SCREEN_HEIGHT - 50)
        game.player.x = random.randint(50, SCREEN_WIDTH - 50)
        game.player.y = random.randint(50, SCREEN_HEIGHT - 50)

    def _golden_enemy(self, game):
        if hasattr(game, 'spawn_enemy'):
            game.spawn_enemy('elite')

    def _mirror_world(self, game):
        game.mirror_world_active = True

    def _end_mirror_world(self, game):
        game.mirror_world_active = False

    def _rain_heal(self, game):
        game.rain_heal_active = True

    def _electric_storm(self, game):
        game.electric_storm_active = True
        game.electric_storm_timer = 0

    def _mystery_box(self, game):
        x = game.player.x + random.randint(-50, 50)
        y = game.player.y + random.randint(-50, 50)
        item = random.choice(['scrap', 'circuit', 'crystal', 'medkit', 'energy_cell', 'ai_core'])
        game.pickups.append(Pickup(x, y, item))

    def _time_anomaly(self, game):
        game.time_scale = random.choice([0.5, 1.5])

    def _end_time_anomaly(self, game):
        game.time_scale = 1.0

    def _ghost_enemy(self, game):
        if game.enemies:
            enemy = random.choice(game.enemies)
            enemy.ghost = True
            enemy.alpha = 128

    def _magnetic_field(self, game):
        game.magnetic_field_active = True

    def _fire_floor(self, game):
        game.fire_floor_active = True

    def _end_fire_floor(self, game):
        game.fire_floor_active = False

    def _wind_blast(self, game):
        game.wind_blast_active = True

    def _reverse_controls(self, game):
        game.reverse_controls_active = True

    def _end_reverse_controls(self, game):
        game.reverse_controls_active = False

    def _shadow_clone(self, game):
        if hasattr(game, 'spawn_enemy'):
            game.spawn_enemy('elite')

    def _crystal_rain(self, game):
        for _ in range(3):
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            game.pickups.append(Pickup(x, y, 'crystal'))

    def _berserk(self, game):
        game.player.damage_multiplier *= 2.0
        game.player.armor = 0

    def _end_berserk(self, game):
        game.player.damage_multiplier /= 2.0

    def _invisibility(self, game):
        game.player.invisible = True

    def _end_invisibility(self, game):
        game.player.invisible = False

    def _trap_spam(self, game):
        for _ in range(3):
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            game.room_hazards.append({
                'x': x, 'y': y, 'radius': 40,
                'timer': 0, 'period': 2.0,
                'active_time': 0.5, 'damage': 10, 'cooldown': 0.0,
            })

    # ==================== ОТРИСОВКА ====================

    def draw_active_events(self, screen):
        """Отрисовка активных событий"""
        font = pygame.font.Font(None, 24)
        y = 100
        for event in self.active_events:
            text = font.render(f"{event.name}: {int(event.timer)}с", True, ORANGE)
            screen.blit(text, (SCREEN_WIDTH - 250, y))
            y += 30