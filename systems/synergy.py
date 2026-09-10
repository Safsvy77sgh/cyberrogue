# systems/synergy.py
import random
import math
import pygame
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from settings import *


# ============================================================
# ДАННЫЕ СИНЕРГИИ
# ============================================================

@dataclass
class SynergyData:
    """Данные синергии"""
    id: str
    name: str
    description: str
    effects_required: List[str]  # Требуемые эффекты
    result_effect: str  # Результирующий эффект
    damage_multiplier: float = 1.0
    duration_multiplier: float = 1.0
    special_action: str = None  # Особое действие
    visual_effect: str = None  # Визуальный эффект

    def to_dict(self) -> dict:
        """Сериализация"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'effects_required': self.effects_required,
            'result_effect': self.result_effect,
            'damage_multiplier': self.damage_multiplier,
            'duration_multiplier': self.duration_multiplier,
            'special_action': self.special_action,
            'visual_effect': self.visual_effect
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SynergyData':
        """Десериализация"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            effects_required=data.get('effects_required', []),
            result_effect=data.get('result_effect', ''),
            damage_multiplier=data.get('damage_multiplier', 1.0),
            duration_multiplier=data.get('duration_multiplier', 1.0),
            special_action=data.get('special_action'),
            visual_effect=data.get('visual_effect')
        )


# ============================================================
# СИСТЕМА СИНЕРГИИ
# ============================================================

class SynergySystem:
    """Полноценная система синергии эффектов"""

    def __init__(self):
        self.synergies: Dict[str, SynergyData] = {}
        self.active_synergies: List[SynergyData] = []
        self.synergy_history: List[Dict] = []
        self._initialize_synergies()

    def _initialize_synergies(self):
        """Инициализация всех синергий"""

        # ===== ОГНЕННЫЕ СИНЕРГИИ =====

        # Огонь + Масло = Взрыв
        self._add_synergy(
            'fire_oil_explosion',
            'Взрывная смесь',
            'Огонь + Масло = мощный взрыв',
            ['burn', 'oil'],
            'explosion',
            damage_multiplier=3.0,
            special_action='explosion',
            visual_effect='explosion'
        )

        # Огонь + Лёд = Пар (слепота)
        self._add_synergy(
            'fire_ice_steam',
            'Паровой взрыв',
            'Огонь + Лёд = ослепляющий пар',
            ['burn', 'freeze'],
            'blind',
            damage_multiplier=1.5,
            special_action='blind',
            visual_effect='steam'
        )

        # Огонь + Яд = Токсичный огонь
        self._add_synergy(
            'fire_poison_toxic_fire',
            'Токсичный огонь',
            'Огонь + Яд = токсичное пламя',
            ['burn', 'poison'],
            'toxic_fire',
            damage_multiplier=2.0,
            special_action='toxic_burn',
            visual_effect='green_fire'
        )

        # Огонь + Электричество = Плазменный взрыв
        self._add_synergy(
            'fire_electric_plasma',
            'Плазменный взрыв',
            'Огонь + Электричество = плазма',
            ['burn', 'electric_damage'],
            'plasma',
            damage_multiplier=2.5,
            special_action='plasma_burst',
            visual_effect='plasma'
        )

        # ===== ЛЕДЯНЫЕ СИНЕРГИИ =====

        # Лёд + Вода = Заморозка по площади
        self._add_synergy(
            'ice_water_freeze_area',
            'Ледяная волна',
            'Лёд + Вода = заморозка по площади',
            ['freeze', 'water'],
            'freeze_area',
            damage_multiplier=1.0,
            special_action='freeze_area',
            visual_effect='ice_wave'
        )

        # Лёд + Электричество = Сверхпроводимость
        self._add_synergy(
            'ice_electric_superconduct',
            'Сверхпроводимость',
            'Лёд + Электричество = усиленный урон',
            ['freeze', 'electric_damage'],
            'superconduct',
            damage_multiplier=3.0,
            special_action='chain_lightning',
            visual_effect='superconduct'
        )

        # ===== ЭЛЕКТРИЧЕСКИЕ СИНЕРГИИ =====

        # Электричество + Вода = Электролиз
        self._add_synergy(
            'electric_water_electrolysis',
            'Электролиз',
            'Электричество + Вода = урон по площади',
            ['electric_damage', 'water'],
            'area_damage',
            damage_multiplier=2.0,
            special_action='electrolysis',
            visual_effect='electrolysis'
        )

        # Электричество + Металл = Магнитный удар
        self._add_synergy(
            'electric_metal_magnetic',
            'Магнитный удар',
            'Электричество + Металл = магнитный удар',
            ['electric_damage', 'metal'],
            'magnetic_strike',
            damage_multiplier=2.0,
            special_action='magnetic_pull',
            visual_effect='magnetic'
        )

        # ===== ЯДОВИТЫЕ СИНЕРГИИ =====

        # Яд + Кислота = Сильный яд
        self._add_synergy(
            'poison_acid_strong_poison',
            'Токсичный коктейль',
            'Яд + Кислота = усиленный яд',
            ['poison', 'acid_damage'],
            'strong_poison',
            damage_multiplier=2.5,
            special_action='strong_poison',
            visual_effect='toxic_cloud'
        )

        # Яд + Кровь = Заражение
        self._add_synergy(
            'poison_blood_infection',
            'Заражение',
            'Яд + Кровь = распространение заражения',
            ['poison', 'blood'],
            'infection',
            damage_multiplier=1.5,
            special_action='spread_infection',
            visual_effect='infection'
        )

        # ===== ТЕМНЫЕ СИНЕРГИИ =====

        # Тьма + Свет = Хаос
        self._add_synergy(
            'shadow_holy_chaos',
            'Хаотический взрыв',
            'Тьма + Свет = хаос',
            ['shadow_damage', 'holy_damage'],
            'chaos',
            damage_multiplier=3.0,
            special_action='chaos_blast',
            visual_effect='chaos'
        )

        # Тьма + Кровь = Пожирание
        self._add_synergy(
            'shadow_blood_devour',
            'Пожирание',
            'Тьма + Кровь = пожирание жизни',
            ['shadow_damage', 'blood'],
            'devour',
            damage_multiplier=2.0,
            special_action='life_drain',
            visual_effect='dark_drain'
        )

        # ===== СВЕТЛЫЕ СИНЕРГИИ =====

        # Свет + Огонь = Святое пламя
        self._add_synergy(
            'holy_fire_sacred_flame',
            'Святое пламя',
            'Свет + Огонь = священный огонь',
            ['holy_damage', 'burn'],
            'sacred_fire',
            damage_multiplier=2.0,
            special_action='holy_burn',
            visual_effect='sacred_flame'
        )

        # Свет + Лёд = Очищение
        self._add_synergy(
            'holy_ice_purify',
            'Очищение',
            'Свет + Лёд = очищение от эффектов',
            ['holy_damage', 'freeze'],
            'purify',
            damage_multiplier=1.0,
            special_action='remove_debuffs',
            visual_effect='purify'
        )

        # ===== ФИЗИЧЕСКИЕ СИНЕРГИИ =====

        # Кровь + Металл = Кровавая броня
        self._add_synergy(
            'blood_metal_blood_armor',
            'Кровавая броня',
            'Кровь + Металл = защитная броня',
            ['blood', 'metal'],
            'blood_armor',
            damage_multiplier=0.5,
            special_action='armor_bonus',
            visual_effect='blood_armor'
        )

        # Ветер + Огонь = Огненный шторм
        self._add_synergy(
            'wind_fire_firestorm',
            'Огненный шторм',
            'Ветер + Огонь = огненный шторм',
            ['wind', 'burn'],
            'firestorm',
            damage_multiplier=2.5,
            special_action='firestorm',
            visual_effect='firestorm'
        )

        # Ветер + Лёд = Метель
        self._add_synergy(
            'wind_ice_blizzard',
            'Метель',
            'Ветер + Лёд = метель',
            ['wind', 'freeze'],
            'blizzard',
            damage_multiplier=1.5,
            special_action='slow_area',
            visual_effect='blizzard'
        )

        # ===== КОМБИНИРОВАННЫЕ СИНЕРГИИ =====

        # Тройная синергия: Огонь + Лёд + Электричество
        self._add_synergy(
            'fire_ice_electric_triple',
            'Элементальный хаос',
            'Огонь + Лёд + Электричество = элементальный хаос',
            ['burn', 'freeze', 'electric_damage'],
            'elemental_chaos',
            damage_multiplier=4.0,
            special_action='elemental_blast',
            visual_effect='elemental_chaos'
        )

        # Тройная синергия: Яд + Кислота + Кровь
        self._add_synergy(
            'poison_acid_blood_plague',
            'Чума',
            'Яд + Кислота + Кровь = чума',
            ['poison', 'acid_damage', 'blood'],
            'plague',
            damage_multiplier=3.5,
            special_action='plague_spread',
            visual_effect='plague'
        )

        # Тройная синергия: Тьма + Свет + Хаос
        self._add_synergy(
            'shadow_holy_chaos_apocalypse',
            'Апокалипсис',
            'Тьма + Свет + Хаос = апокалипсис',
            ['shadow_damage', 'holy_damage', 'chaos'],
            'apocalypse',
            damage_multiplier=5.0,
            special_action='apocalypse',
            visual_effect='apocalypse'
        )

    def _add_synergy(self, synergy_id: str, name: str, description: str,
                     effects_required: List[str], result_effect: str,
                     damage_multiplier: float = 1.0,
                     duration_multiplier: float = 1.0,
                     special_action: str = None,
                     visual_effect: str = None):
        """Добавление синергии"""
        synergy = SynergyData(
            id=synergy_id,
            name=name,
            description=description,
            effects_required=effects_required,
            result_effect=result_effect,
            damage_multiplier=damage_multiplier,
            duration_multiplier=duration_multiplier,
            special_action=special_action,
            visual_effect=visual_effect
        )
        self.synergies[synergy_id] = synergy

    # ============================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # ============================================================

    def check_synergy(self, active_effects: List[str]) -> Optional[SynergyData]:
        """Проверка наличия синергии среди активных эффектов"""
        active_set = set(active_effects)

        for synergy in self.synergies.values():
            required_set = set(synergy.effects_required)
            if required_set.issubset(active_set):
                return synergy

        return None

    def check_all_synergies(self, active_effects: List[str]) -> List[SynergyData]:
        """Проверка всех возможных синергий"""
        active_set = set(active_effects)
        found_synergies = []

        for synergy in self.synergies.values():
            required_set = set(synergy.effects_required)
            if required_set.issubset(active_set):
                found_synergies.append(synergy)

        return found_synergies

    def apply_synergy(self, synergy: SynergyData, target, game=None):
        """Применение синергии к цели"""
        if not synergy.special_action:
            return

        action = synergy.special_action

        if action == 'explosion':
            # Взрыв
            if game:
                game.collision_system._handle_explosion(
                    target.x, target.y,
                    int(100 * synergy.damage_multiplier)
                )
            elif hasattr(target, 'take_damage'):
                target.take_damage(int(50 * synergy.damage_multiplier))

        elif action == 'blind':
            # Ослепление
            if hasattr(target, 'blind_timer'):
                target.blind_timer = 3.0 * synergy.duration_multiplier

        elif action == 'toxic_burn':
            # Токсичный огонь
            if hasattr(target, 'take_damage'):
                target.take_damage(int(30 * synergy.damage_multiplier))
                if hasattr(target, 'burn_timer'):
                    target.burn_timer = 5.0
                    target.burn_damage = 15
                if hasattr(target, 'poison_timer'):
                    target.poison_timer = 5.0
                    target.poison_damage = 10

        elif action == 'plasma_burst':
            # Плазменный взрыв
            if game:
                game.collision_system._handle_explosion(
                    target.x, target.y,
                    int(120 * synergy.damage_multiplier)
                )
            elif hasattr(target, 'take_damage'):
                target.take_damage(int(60 * synergy.damage_multiplier))

        elif action == 'freeze_area':
            # Заморозка по площади
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 150:
                            if not enemy.effect_system:
                                enemy.effect_system = EffectSystem(enemy, game)
                            freeze = enemy.effect_system.create_instance('freeze')
                            enemy.effect_system.add_effect(freeze)

        elif action == 'chain_lightning':
            # Цепная молния
            if game:
                hit_enemies = [target]
                current = target
                for _ in range(3):
                    nearest = None
                    nearest_dist = 200
                    for enemy in game.enemies:
                        if enemy.alive and enemy not in hit_enemies:
                            dist = math.hypot(current.x - enemy.x, current.y - enemy.y)
                            if dist < nearest_dist:
                                nearest_dist = dist
                                nearest = enemy

                    if nearest:
                        nearest.take_damage(int(25 * synergy.damage_multiplier))
                        game.lightning_effects.append({
                            'start': (current.x, current.y),
                            'end': (nearest.x, nearest.y),
                            'life': 0.3,
                            'color': CYAN
                        })
                        hit_enemies.append(nearest)
                        current = nearest
                    else:
                        break

        elif action == 'electrolysis':
            # Электролиз
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 120:
                            enemy.take_damage(int(30 * synergy.damage_multiplier))

        elif action == 'magnetic_pull':
            # Магнитный удар
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 200:
                            # Притягивание
                            angle = math.atan2(target.y - enemy.y, target.x - enemy.x)
                            enemy.x += math.cos(angle) * 50
                            enemy.y += math.sin(angle) * 50
                            enemy.take_damage(int(40 * synergy.damage_multiplier))

        elif action == 'strong_poison':
            # Сильный яд
            if hasattr(target, 'take_damage'):
                target.take_damage(int(35 * synergy.damage_multiplier))
                if hasattr(target, 'poison_timer'):
                    target.poison_timer = 8.0
                    target.poison_damage = 20

        elif action == 'spread_infection':
            # Распространение заражения
            if game:
                for enemy in game.enemies:
                    if enemy.alive and enemy != target:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 100:
                            if not enemy.effect_system:
                                enemy.effect_system = EffectSystem(enemy, game)
                            poison = enemy.effect_system.create_instance('poison')
                            enemy.effect_system.add_effect(poison)

        elif action == 'chaos_blast':
            # Хаотический взрыв
            if game:
                game.collision_system._handle_explosion(
                    target.x, target.y,
                    int(150 * synergy.damage_multiplier)
                )
            elif hasattr(target, 'take_damage'):
                target.take_damage(int(80 * synergy.damage_multiplier))

        elif action == 'life_drain':
            # Пожирание жизни
            if hasattr(target, 'take_damage'):
                drained = int(25 * synergy.damage_multiplier)
                target.take_damage(drained)
                if game and game.player:
                    game.player.heal(drained)

        elif action == 'holy_burn':
            # Святое пламя
            if hasattr(target, 'take_damage'):
                target.take_damage(int(35 * synergy.damage_multiplier))
                if hasattr(target, 'burn_timer'):
                    target.burn_timer = 6.0
                    target.burn_damage = 20

        elif action == 'remove_debuffs':
            # Очищение от дебаффов
            if game and game.player:
                game.player.poison_timer = 0
                game.player.burn_timer = 0
                game.player.slow_timer = 0
                game.player.confusion_timer = 0
                game.player.heal(20)

        elif action == 'armor_bonus':
            # Бонус брони
            if game and game.player:
                game.player.armor += 10
                game.player.heal(30)

        elif action == 'firestorm':
            # Огненный шторм
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 200:
                            enemy.take_damage(int(40 * synergy.damage_multiplier))
                            if not enemy.effect_system:
                                enemy.effect_system = EffectSystem(enemy, game)
                            burn = enemy.effect_system.create_instance('burn')
                            enemy.effect_system.add_effect(burn)

        elif action == 'slow_area':
            # Замедление по площади
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 180:
                            enemy.speed_multiplier = 0.3
                            enemy.slow_timer = 4.0

        elif action == 'elemental_blast':
            # Элементальный взрыв
            if game:
                game.collision_system._handle_explosion(
                    target.x, target.y,
                    int(200 * synergy.damage_multiplier)
                )

        elif action == 'plague_spread':
            # Чума
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                        if dist < 150:
                            enemy.take_damage(int(50 * synergy.damage_multiplier))
                            if not enemy.effect_system:
                                enemy.effect_system = EffectSystem(enemy, game)
                            poison = enemy.effect_system.create_instance('poison')
                            enemy.effect_system.add_effect(poison)

        elif action == 'apocalypse':
            # Апокалипсис
            if game:
                for enemy in game.enemies:
                    if enemy.alive:
                        enemy.take_damage(int(100 * synergy.damage_multiplier))
                game.screen_shake = 1.0
                game.flash_alpha = 0.5
                game.flash_color = WHITE

        # Запись в историю
        self.synergy_history.append({
            'synergy': synergy.id,
            'action': action,
            'target': id(target)
        })

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================================

    def get_synergy_by_effects(self, effect1: str, effect2: str) -> Optional[SynergyData]:
        """Получение синергии по двум эффектам"""
        for synergy in self.synergies.values():
            if effect1 in synergy.effects_required and effect2 in synergy.effects_required:
                return synergy
        return None

    def get_all_synergies(self) -> List[SynergyData]:
        """Получение всех синергий"""
        return list(self.synergies.values())

    def get_active_synergies(self, active_effects: List[str]) -> List[SynergyData]:
        """Получение активных синергий"""
        return self.check_all_synergies(active_effects)

    def get_synergy_history(self) -> List[Dict]:
        """Получение истории синергий"""
        return self.synergy_history[-20:]

    def trigger_synergy_on_hit(self, source_effects: List[str], target, game=None, damage: int = 0):
        """Срабатывание синергии при попадании"""
        synergies = self.check_all_synergies(source_effects)

        for synergy in synergies:
            if random.random() < 0.3:  # 30% шанс срабатывания
                # Умножение урона
                if damage > 0 and hasattr(target, 'take_damage'):
                    bonus_damage = int(damage * (synergy.damage_multiplier - 1))
                    if bonus_damage > 0:
                        target.take_damage(bonus_damage)
                        if game:
                            game.add_damage_number(
                                target.x, target.y - target.radius,
                                bonus_damage, MAGENTA, True
                            )

                # Применение особого действия
                self.apply_synergy(synergy, target, game)

                # Визуальный эффект
                if game and synergy.visual_effect:
                    self._spawn_visual_effect(synergy.visual_effect, target, game)

    def _spawn_visual_effect(self, effect_type: str, target, game):
        """Создание визуального эффекта"""
        colors = {
            'explosion': ORANGE,
            'steam': WHITE,
            'green_fire': GREEN,
            'plasma': PURPLE,
            'ice_wave': CYAN,
            'superconduct': LIGHT_CYAN,
            'electrolysis': LIGHT_BLUE,
            'magnetic': GRAY,
            'toxic_cloud': DARK_GREEN,
            'infection': (100, 0, 50),
            'chaos': MAGENTA,
            'dark_drain': (50, 0, 50),
            'sacred_flame': LIGHT_YELLOW,
            'purify': WHITE,
            'blood_armor': DARK_RED,
            'firestorm': ORANGE,
            'blizzard': LIGHT_BLUE,
            'elemental_chaos': (255, 100, 255),
            'plague': (0, 100, 0),
            'apocalypse': WHITE
        }

        color = colors.get(effect_type, WHITE)

        if game:
            game.spawn_particles(target.x, target.y, 15, color)
            game.spawn_sparks(target.x, target.y, 10)

    def save_synergies(self, filename: str = "synergy_data.json"):
        """Сохранение данных синергий"""
        import json
        data = {
            'synergies': [s.to_dict() for s in self.synergies.values()],
            'history': self.synergy_history
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_synergies(self, filename: str = "synergy_data.json"):
        """Загрузка данных синергий"""
        import json, os
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.synergies = {
                    s['id']: SynergyData.from_dict(s) for s in data.get('synergies', [])
                }
                self.synergy_history = data.get('history', [])

    def draw_debug(self, screen: pygame.Surface, active_effects: List[str]):
        """Отрисовка отладочной информации"""
        font = pygame.font.Font(None, 20)
        y = 500

        active = self.get_active_synergies(active_effects)

        debug_texts = [
            f"Синергии: {len(active)}/{len(self.synergies)}"
        ]

        for synergy in active[:5]:
            debug_texts.append(f"- {synergy.name}: {synergy.description[:30]}")

        for text in debug_texts:
            rendered = font.render(text, True, MAGENTA)
            screen.blit(rendered, (10, y))
            y += 20