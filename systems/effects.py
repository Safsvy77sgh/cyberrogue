# systems/effects.py
import random
import math
import pygame
from typing import Dict, List, Tuple, Optional, Any, Callable
from settings import *
from systems.synergy import SynergySystem
# systems/effects.py
import random
import math
import pygame
from typing import Dict, List, Tuple, Optional, Any, Callable
from settings import *
from entities.bullet import Bullet  # ДОБАВЬТЕ ЭТУ СТРОКУ


class EffectData:
    """Данные эффекта с функциональностью"""

    def __init__(self, effect_id: str, name: str, description: str,
                 duration: float = 0, permanent: bool = False,
                 effect_type: str = 'buff', rarity: str = 'common',
                 apply_func: Callable = None, remove_func: Callable = None,
                 update_func: Callable = None, trigger_func: Callable = None):
        self.id = effect_id
        self.name = name
        self.description = description
        self.duration = duration
        self.permanent = permanent
        self.type = effect_type
        self.rarity = rarity
        self.apply_func = apply_func
        self.remove_func = remove_func
        self.update_func = update_func
        self.trigger_func = trigger_func
        self.params = {}


class EffectInstance:
    """Экземпляр эффекта на сущности"""

    def __init__(self, effect_data: EffectData, source=None):
        self.data = effect_data
        self.source = source
        self.timer = effect_data.duration
        self.stacks = 1
        self.active = True
        self.params = effect_data.params.copy()
        self.accumulated_damage = 0
        self.trigger_count = 0

    def update(self, dt: float, owner=None, game=None) -> bool:
        """Обновление эффекта"""
        if not self.active:
            return False

        # Вызов функции обновления
        if self.data.update_func and owner and game:
            self.data.update_func(owner, self, dt, game)

        if not self.data.permanent:
            self.timer -= dt
            return self.timer > 0
        return True

    def trigger(self, owner=None, target=None, game=None, **kwargs):
        """Срабатывание эффекта"""
        if self.data.trigger_func and owner:
            self.data.trigger_func(owner, self, target, game, **kwargs)
            self.trigger_count += 1

    def add_stack(self, amount: int = 1):
        """Добавление стака"""
        self.stacks += amount
        self.timer = self.data.duration


class EffectSystem:
    """Полная функциональная система эффектов"""

    def __init__(self, owner=None, game=None):
        self.owner = owner
        self.game = game  # Добавлена ссылка на игру
        self.active_effects: List[EffectInstance] = []
        self.effect_database = {}
        self.synergy_system = SynergySystem()
        self._initialize_all_effects()

    def _initialize_all_effects(self):
        """Инициализация всех эффектов с функциями"""

        # ===== БАЗОВЫЕ ЭФФЕКТЫ =====

        # Двойной урон
        self._register_effect(
            'double_damage', 'Двойной урон', 'Урон удвоен',
            duration=5.0, rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'damage_multiplier',
                                                         owner.damage_multiplier * 2),
            remove_func=lambda owner, inst, game: setattr(owner, 'damage_multiplier',
                                                          owner.damage_multiplier / 2)
        )

        # Скорострельность
        self._register_effect(
            'rapid_fire', 'Скорострельность', 'Увеличенная скорострельность',
            duration=5.0, rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'fire_rate',
                                                         owner.fire_rate * 0.5),
            remove_func=lambda owner, inst, game: setattr(owner, 'fire_rate',
                                                          owner.fire_rate * 2)
        )

        # Щит
        self._register_effect(
            'shield', 'Щит', 'Поглощает урон',
            duration=3.0, rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'shield_timer',
                                                         owner.shield_timer + 3.0),
            update_func=lambda owner, inst, dt, game: setattr(owner, 'shield_timer',
                                                              max(owner.shield_timer, inst.timer))
        )

        # Невидимость
        self._register_effect(
            'invisibility', 'Невидимость', 'Полная невидимость',
            duration=3.0, rarity='rare',
            apply_func=lambda owner, inst, game: setattr(owner, 'invisible', True),
            remove_func=lambda owner, inst, game: setattr(owner, 'invisible', False)
        )

        # Регенерация
        self._register_effect(
            'regen', 'Регенерация', 'Постепенное лечение',
            duration=5.0, rarity='common',
            update_func=lambda owner, inst, dt, game: owner.heal(int(5 * dt))
        )

        # Вампиризм
        self._register_effect(
            'vampirism', 'Вампиризм', 'Лечение от урона',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, damage=0, **kw:
            owner.heal(int(damage * 0.15))
        )

        # Отравление
        self._register_effect(
            'poison', 'Отравление', 'Урон со временем',
            duration=4.0, effect_type='debuff', rarity='common',
            update_func=lambda owner, inst, dt, game: owner.take_damage(int(8 * dt))
        )

        # Поджог
        self._register_effect(
            'burn', 'Поджог', 'Горение',
            duration=3.0, effect_type='debuff', rarity='common',
            update_func=lambda owner, inst, dt, game: owner.take_damage(int(12 * dt))
        )

        # Заморозка
        self._register_effect(
            'freeze', 'Заморозка', 'Замедление',
            duration=3.0, effect_type='debuff', rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'speed_multiplier',
                                                         owner.speed_multiplier * 0.3),
            remove_func=lambda owner, inst, game: setattr(owner, 'speed_multiplier',
                                                          owner.speed_multiplier / 0.3)
        )

        # ===== УНИКАЛЬНЫЕ ЭФФЕКТЫ =====

        # Хронозамедление
        self._register_effect(
            'chrono_slow', 'Хронозамедление', 'Криты замедляют время',
            duration=1.0, rarity='epic',
            trigger_func=lambda owner, inst, target, game, is_crit=False, **kw:
            self._trigger_chrono_slow(owner, inst, game) if is_crit else None
        )

        # Энергетический вампиризм
        self._register_effect(
            'energy_vampirism', 'Энергетический вампиризм', 'Урон восстанавливает энергию',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, damage=0, **kw:
            setattr(owner, 'energy', min(PLAYER_MAX_ENERGY, owner.energy + int(damage * 0.1)))
        )

        # Электрическая дуга
        self._register_effect(
            'electric_arc', 'Электрическая дуга', 'Пули перескакивают на врагов',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, **kw:
            self._trigger_electric_arc(owner, inst, target, game)
        )

        # Взрывные пули
        self._register_effect(
            'explosive_bullets', 'Взрывные пули', 'Пули взрываются',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, bullet=None, **kw:
            self._trigger_explosion(owner, inst, target, game, bullet)
        )

        # Пробивание
        self._register_effect(
            'piercing', 'Пробивание', 'Пули проходят насквозь',
            duration=0, permanent=True, rarity='common'
        )

        # Рикошет
        self._register_effect(
            'ricochet', 'Рикошет', 'Пули отскакивают',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, bullet=None, **kw:
            self._trigger_ricochet(owner, inst, target, game, bullet)
        )

        # Самонаведение
        self._register_effect(
            'homing', 'Самонаведение', 'Пули наводятся на цель',
            duration=0, permanent=True, rarity='rare'
        )

        # Гравитационный колодец
        self._register_effect(
            'gravity_well', 'Гравитационный колодец', 'Притягивает врагов',
            duration=3.0, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_gravity_well(owner, inst, dt, game)
        )

        # Магнитный захват
        self._register_effect(
            'magnet', 'Магнитный захват', 'Притягивает пикапы',
            duration=0, permanent=True, rarity='common',
            update_func=lambda owner, inst, dt, game: self._update_magnet(owner, inst, dt, game)
        )

        # Кровавая жертва
        self._register_effect(
            'blood_sacrifice', 'Кровавая жертва', 'HP за урон',
            duration=8.0, rarity='epic',
            apply_func=lambda owner, inst, game: (
                setattr(owner, 'hp', owner.hp - 30),
                setattr(owner, 'damage_multiplier', owner.damage_multiplier * 3)
            ),
            remove_func=lambda owner, inst, game: setattr(owner, 'damage_multiplier',
                                                          owner.damage_multiplier / 3)
        )

        # Берсерк
        self._register_effect(
            'berserk', 'Берсерк', 'Сила при низком HP',
            duration=0, permanent=True, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_berserk(owner, inst, dt, game)
        )

        # Адреналиновый рывок
        self._register_effect(
            'adrenaline', 'Адреналиновый рывок', 'Скорость при низком HP',
            duration=0, permanent=True, rarity='common',
            update_func=lambda owner, inst, dt, game: self._update_adrenaline(owner, inst, dt, game)
        )

        # Фазовый сдвиг
        self._register_effect(
            'phase_shift', 'Фазовый сдвиг', 'Неуязвимость и проход сквозь стены',
            duration=1.5, rarity='epic',
            apply_func=lambda owner, inst, game: (
                setattr(owner, 'invulnerable_timer', 1.5),
                setattr(owner, 'phase_shift', True)
            ),
            remove_func=lambda owner, inst, game: setattr(owner, 'phase_shift', False)
        )

        # Дупликация
        self._register_effect(
            'duplication', 'Дупликация', 'Шанс создания второй пули',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, bullet=None, **kw:
            self._trigger_duplication(owner, inst, game, bullet)
        )

        # Критический каскад
        self._register_effect(
            'crit_cascade', 'Критический каскад', 'Криты увеличивают шанс крита',
            duration=0, permanent=True, rarity='epic',
            trigger_func=lambda owner, inst, target, game, is_crit=False, **kw:
            self._trigger_crit_cascade(owner, inst, is_crit)
        )

        # Вампирская аура
        self._register_effect(
            'vampiric_aura', 'Вампирская аура', 'Лечение от ближних врагов',
            duration=0, permanent=True, rarity='rare',
            update_func=lambda owner, inst, dt, game: self._update_vampiric_aura(owner, inst, dt, game)
        )

        # Аура урона
        self._register_effect(
            'damage_aura', 'Аура урона', 'Урон врагам вокруг',
            duration=0, permanent=True, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_damage_aura(owner, inst, dt, game)
        )

        # Телекинез
        self._register_effect(
            'telekinesis', 'Телекинез', 'Подбор предметов на расстоянии',
            duration=0, permanent=True, rarity='rare',
            update_func=lambda owner, inst, dt, game: self._update_telekinesis(owner, inst, dt, game)
        )

        # Огненное кольцо
        self._register_effect(
            'fire_ring', 'Огненное кольцо', 'Кольцо огня вокруг',
            duration=3.0, rarity='rare',
            update_func=lambda owner, inst, dt, game: self._update_fire_ring(owner, inst, dt, game)
        )

        # Электрическое поле
        self._register_effect(
            'electric_field', 'Электрическое поле', 'Зона урона врагам',
            duration=4.0, rarity='rare',
            update_func=lambda owner, inst, dt, game: self._update_electric_field(owner, inst, dt, game)
        )

        # Ядовитое облако
        self._register_effect(
            'poison_cloud', 'Ядовитое облако', 'Облако яда',
            duration=4.0, rarity='rare',
            update_func=lambda owner, inst, dt, game: self._update_poison_cloud(owner, inst, dt, game)
        )

        # Сингулярность
        self._register_effect(
            'singularity', 'Сингулярность', 'Чёрная дыра',
            duration=5.0, rarity='legendary',
            apply_func=lambda owner, inst, game: self._apply_singularity(owner, inst, game),
            update_func=lambda owner, inst, dt, game: self._update_singularity(owner, inst, dt, game),
            remove_func=lambda owner, inst, game: self._remove_singularity(owner, inst, game)
        )

        # Электрический шторм
        self._register_effect(
            'electric_storm', 'Электрический шторм', 'Молнии по площади',
            duration=4.0, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_electric_storm(owner, inst, dt, game)
        )

        # Рой нанитов
        self._register_effect(
            'nanite_swarm', 'Рой нанитов', 'Рой атакует врагов',
            duration=6.0, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_nanite_swarm(owner, inst, dt, game)
        )

        # Апокалипсис
        self._register_effect(
            'apocalypse', 'Апокалипсис', 'Метеоритный дождь',
            duration=8.0, rarity='legendary',
            update_func=lambda owner, inst, dt, game: self._update_apocalypse(owner, inst, dt, game)
        )

        # Квантовая запутанность
        self._register_effect(
            'quantum_entanglement', 'Квантовая запутанность', 'Урон передаётся случайному врагу',
            duration=0, permanent=True, rarity='legendary',
            trigger_func=lambda owner, inst, target, game, damage=0, **kw:
            self._trigger_quantum_entanglement(owner, inst, target, game, damage)
        )

        # Отражение урона
        self._register_effect(
            'thorns', 'Отражение урона', 'Часть урона возвращается',
            duration=0, permanent=True, rarity='common',
            trigger_func=lambda owner, inst, target, game, damage=0, **kw:
            self._trigger_thorns(owner, inst, target, game, damage)
        )

        # Пожиратель душ
        self._register_effect(
            'soul_eater', 'Пожиратель душ', 'Убийства повышают урон',
            duration=5.0, rarity='rare',
            apply_func=lambda owner, inst, game: setattr(inst, 'accumulated_damage', 0),
            trigger_func=lambda owner, inst, target, game, **kw:
            self._trigger_soul_eater(owner, inst, game)
        )

        # Благословение
        self._register_effect(
            'blessing', 'Благословение', 'Случайный бафф',
            duration=5.0, rarity='rare',
            apply_func=lambda owner, inst, game: self._apply_blessing(owner, inst, game)
        )

        # Проклятие
        self._register_effect(
            'curse', 'Проклятие', 'Случайный дебафф',
            duration=5.0, effect_type='debuff', rarity='rare',
            apply_func=lambda owner, inst, game: self._apply_curse(owner, inst, game)
        )

        # Дополнительные функциональные эффекты
        self._register_effect(
            'double_exp', 'Двойной опыт', 'Удвоенный опыт',
            duration=30.0, rarity='rare',
            apply_func=lambda owner, inst, game: setattr(owner, 'exp_multiplier',
                                                         owner.exp_multiplier * 2),
            remove_func=lambda owner, inst, game: setattr(owner, 'exp_multiplier',
                                                          owner.exp_multiplier / 2)
        )

        self._register_effect(
            'damage_reduction', 'Снижение урона', 'Получаемый урон снижен',
            duration=5.0, rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'damage_reduction',
                                                         owner.__dict__.get('damage_reduction', 1.0) * 0.5),
            remove_func=lambda owner, inst, game: setattr(owner, 'damage_reduction',
                                                          owner.__dict__.get('damage_reduction', 1.0) * 2)
        )

        self._register_effect(
            'move_speed', 'Скорость передвижения', 'Увеличенная скорость',
            duration=5.0, rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'speed',
                                                         owner.speed * 1.5),
            remove_func=lambda owner, inst, game: setattr(owner, 'speed',
                                                          owner.speed / 1.5)
        )

        self._register_effect(
            'cooldown_reduction', 'Снижение перезарядки', 'Быстрая перезарядка',
            duration=5.0, rarity='common',
            apply_func=lambda owner, inst, game: setattr(owner, 'fire_rate_multiplier',
                                                         owner.fire_rate_multiplier * 0.7),
            remove_func=lambda owner, inst, game: setattr(owner, 'fire_rate_multiplier',
                                                          owner.fire_rate_multiplier / 0.7)
        )

        self._register_effect(
            'invulnerability', 'Неуязвимость', 'Полная неуязвимость',
            duration=2.0, rarity='epic',
            apply_func=lambda owner, inst, game: setattr(owner, 'invulnerable_timer',
                                                         max(owner.invulnerable_timer, 2.0)),
            update_func=lambda owner, inst, dt, game: setattr(owner, 'invulnerable_timer',
                                                              max(owner.invulnerable_timer, inst.timer))
        )

        self._register_effect(
            'damage_reflection', 'Отражение урона', 'Урон возвращается атакующему',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, damage=0, **kw:
            self._trigger_damage_reflection(owner, inst, target, game, damage)
        )

        self._register_effect(
            'life_steal', 'Похищение жизни', 'Лечение от урона',
            duration=0, permanent=True, rarity='rare',
            trigger_func=lambda owner, inst, target, game, damage=0, **kw:
            owner.heal(int(damage * 0.2)) if damage > 0 else None
        )

        self._register_effect(
            'explosive_death', 'Взрывная смерть', 'Взрыв при смерти',
            duration=0, permanent=True, rarity='epic',
            trigger_func=lambda owner, inst, target, game, **kw:
            game.collision_system._handle_explosion(owner.x, owner.y, 150) if not owner.alive else None
        )

        self._register_effect(
            'freeze_aura', 'Аура заморозки', 'Замораживает врагов вокруг',
            duration=0, permanent=True, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_freeze_aura(owner, inst, dt, game)
        )

        self._register_effect(
            'fire_aura', 'Аура огня', 'Поджигает врагов вокруг',
            duration=0, permanent=True, rarity='epic',
            update_func=lambda owner, inst, dt, game: self._update_fire_aura(owner, inst, dt, game)
        )

        self._register_effect(
            'healing_aura', 'Аура лечения', 'Лечит союзников вокруг',
            duration=0, permanent=True, rarity='rare',
            update_func=lambda owner, inst, dt, game: self._update_healing_aura(owner, inst, dt, game)
        )

        self._register_effect(
            'critical_strike', 'Критический удар', 'Увеличенный шанс крита',
            duration=5.0, rarity='rare',
            apply_func=lambda owner, inst, game: setattr(owner, 'crit_chance',
                                                         min(1.0, owner.crit_chance + 0.25)),
            remove_func=lambda owner, inst, game: setattr(owner, 'crit_chance',
                                                          max(0.0, owner.crit_chance - 0.25))
        )

        self._register_effect(
            'haste', 'Ускорение', 'Увеличенная скорость атаки',
            duration=5.0, rarity='rare',
            apply_func=lambda owner, inst, game: setattr(owner, 'fire_rate_multiplier',
                                                         owner.fire_rate_multiplier * 0.5),
            remove_func=lambda owner, inst, game: setattr(owner, 'fire_rate_multiplier',
                                                          owner.fire_rate_multiplier * 2)
        )



    def _register_effect(self, effect_id: str, name: str, description: str,
                         duration: float = 0, permanent: bool = False,
                         effect_type: str = 'buff', rarity: str = 'common',
                         apply_func: Callable = None, remove_func: Callable = None,
                         update_func: Callable = None, trigger_func: Callable = None):
        """Регистрация эффекта"""
        effect = EffectData(effect_id, name, description, duration, permanent,
                            effect_type, rarity, apply_func, remove_func,
                            update_func, trigger_func)
        self.effect_database[effect_id] = effect

    # ===== ФУНКЦИИ ЭФФЕКТОВ =====

    def _trigger_chrono_slow(self, owner, inst, game):
        """Хронозамедление"""
        game.time_scale = 0.3
        game.time_scale_timer = 1.0
        game.spawn_particles(owner.x, owner.y, 10, CYAN)

    def _trigger_electric_arc(self, owner, inst, target, game):
        """Электрическая дуга"""
        if not target or not target.alive:
            return

        # Поиск ближайших врагов
        for enemy in game.enemies:
            if enemy != target and enemy.alive:
                dist = math.hypot(target.x - enemy.x, target.y - enemy.y)
                if dist < 200:
                    # Перескок молнии
                    damage = int(15 * inst.stacks)
                    enemy.take_damage(damage)
                    game.add_damage_number(enemy.x, enemy.y - enemy.radius, damage, CYAN)
                    game.spawn_sparks(enemy.x, enemy.y, 3)
                    # Рисование линии молнии
                    game.lightning_effects.append({
                        'start': (target.x, target.y),
                        'end': (enemy.x, enemy.y),
                        'life': 0.3
                    })

    def _trigger_explosion(self, owner, inst, target, game, bullet=None):
        """Взрывные пули"""
        if bullet:
            game.collision_system._handle_explosion(bullet.x, bullet.y, 80)
        elif target:
            game.collision_system._handle_explosion(target.x, target.y, 80)

    def _trigger_ricochet(self, owner, inst, target, game, bullet=None):
        """Рикошет"""
        if bullet and bullet not in game.bullets:
            # Создание отскочившей пули
            new_bullet = Bullet(bullet.x, bullet.y,
                                (random.uniform(-1, 1), random.uniform(-1, 1)),
                                True, int(bullet.damage * 0.7))
            new_bullet.set_bouncing(False)
            game.bullets.append(new_bullet)

    def _trigger_duplication(self, owner, inst, game, bullet=None):
        """Дупликация"""
        if bullet and random.random() < 0.25:
            new_bullet = Bullet(bullet.x, bullet.y,
                                (bullet.vx / BULLET_SPEED, bullet.vy / BULLET_SPEED),
                                True, bullet.damage)
            game.bullets.append(new_bullet)

    def _trigger_crit_cascade(self, owner, inst, is_crit=False):
        """Критический каскад"""
        if is_crit:
            owner.crit_chance = min(0.8, owner.crit_chance + 0.05)
            inst.accumulated_damage += 1
        elif inst.accumulated_damage > 0:
            owner.crit_chance = max(0.15, owner.crit_chance - 0.05 * inst.accumulated_damage)
            inst.accumulated_damage = 0

    def _trigger_quantum_entanglement(self, owner, inst, target, game, damage=0):
        """Квантовая запутанность"""
        if target and game.enemies:
            other_enemies = [e for e in game.enemies if e != target and e.alive]
            if other_enemies:
                other = random.choice(other_enemies)
                other.take_damage(damage)
                game.add_damage_number(other.x, other.y - other.radius, damage, PURPLE)
                game.spawn_particles(other.x, other.y, 5, PURPLE)

    def _trigger_thorns(self, owner, inst, target, game, damage=0):
        """Отражение урона"""
        if target and damage > 0:
            reflected = int(damage * 0.3)
            target.take_damage(reflected)
            game.add_damage_number(target.x, target.y - target.radius, reflected, ORANGE)

    def _trigger_soul_eater(self, owner, inst, game):
        """Пожиратель душ"""
        inst.accumulated_damage += 5
        owner.damage_multiplier += inst.accumulated_damage * 0.01

    def _apply_blessing(self, owner, inst, game):
        """Благословение"""
        buffs = ['damage_up', 'speed_up', 'heal', 'shield']
        choice = random.choice(buffs)
        if choice == 'damage_up':
            owner.damage_multiplier *= 1.5
            inst.params['original_damage'] = owner.damage_multiplier / 1.5
        elif choice == 'speed_up':
            owner.speed *= 1.5
            inst.params['original_speed'] = owner.speed / 1.5
        elif choice == 'heal':
            owner.heal(50)
        elif choice == 'shield':
            owner.shield_timer = max(owner.shield_timer, 5.0)

    def _apply_curse(self, owner, inst, game):
        """Проклятие"""
        debuffs = ['damage_down', 'speed_down', 'poison', 'burn']
        choice = random.choice(debuffs)
        if choice == 'damage_down':
            owner.damage_multiplier *= 0.7
            inst.params['original_damage'] = owner.damage_multiplier / 0.7
        elif choice == 'speed_down':
            owner.speed *= 0.7
            inst.params['original_speed'] = owner.speed / 0.7
        elif choice == 'poison':
            poison = self.create_instance('poison')
            owner.effect_system.add_effect(poison)
        elif choice == 'burn':
            burn = self.create_instance('burn')
            owner.effect_system.add_effect(burn)

    def _update_gravity_well(self, owner, inst, dt, game):
        """Обновление гравитационного колодца"""
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 300:
                    angle = math.atan2(owner.y - enemy.y, owner.x - enemy.x)
                    pull = (300 - dist) * 0.5 * dt
                    enemy.x += math.cos(angle) * pull
                    enemy.y += math.sin(angle) * pull

    def _update_magnet(self, owner, inst, dt, game):
        """Обновление магнита"""
        for pickup in game.pickups[:]:
            dist = math.hypot(owner.x - pickup.x, owner.y - pickup.y)
            if dist < 200:
                angle = math.atan2(owner.y - pickup.y, owner.x - pickup.x)
                pull = (200 - dist) * 2 * dt
                pickup.x += math.cos(angle) * pull
                pickup.y += math.sin(angle) * pull

    def _update_berserk(self, owner, inst, dt, game):
        """Обновление берсерка"""
        hp_ratio = owner.hp / owner.max_hp
        if hp_ratio < 0.3:
            owner.damage_multiplier = 2.0
            owner.speed_multiplier = 1.5
        elif hp_ratio < 0.5:
            owner.damage_multiplier = 1.5
            owner.speed_multiplier = 1.2
        else:
            owner.damage_multiplier = 1.0
            owner.speed_multiplier = 1.0

    def _update_adrenaline(self, owner, inst, dt, game):
        """Обновление адреналина"""
        hp_ratio = owner.hp / owner.max_hp
        if hp_ratio < 0.25:
            owner.speed_multiplier = 1.8
        elif hp_ratio < 0.5:
            owner.speed_multiplier = 1.4
        else:
            owner.speed_multiplier = 1.0

    def _update_vampiric_aura(self, owner, inst, dt, game):
        """Обновление вампирской ауры"""
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 150:
                    drain = int(3 * dt * inst.stacks)
                    enemy.take_damage(drain)
                    owner.heal(drain)

    def _update_damage_aura(self, owner, inst, dt, game):
        """Обновление ауры урона"""
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 100:
                    damage = int(10 * dt * inst.stacks)
                    enemy.take_damage(damage)

    def _update_telekinesis(self, owner, inst, dt, game):
        """Обновление телекинеза"""
        for pickup in game.pickups[:]:
            dist = math.hypot(owner.x - pickup.x, owner.y - pickup.y)
            if dist < 300:
                angle = math.atan2(owner.y - pickup.y, owner.x - pickup.x)
                pull = (300 - dist) * 3 * dt
                pickup.x += math.cos(angle) * pull
                pickup.y += math.sin(angle) * pull

    def _update_fire_ring(self, owner, inst, dt, game):
        """Обновление огненного кольца"""
        inst.params['ring_timer'] = inst.params.get('ring_timer', 0) + dt
        if inst.params['ring_timer'] >= 0.5:
            inst.params['ring_timer'] = 0
            for enemy in game.enemies:
                if enemy.alive:
                    dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                    if 80 < dist < 120:
                        enemy.take_damage(20)
                        burn = self.create_instance('burn')
                        enemy.effect_system.add_effect(burn)

    def _update_electric_field(self, owner, inst, dt, game):
        """Обновление электрического поля"""
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 150:
                    damage = int(8 * dt * inst.stacks)
                    enemy.take_damage(damage)
                    if random.random() < 0.01:
                        game.spawn_sparks(enemy.x, enemy.y, 3)

    def _update_poison_cloud(self, owner, inst, dt, game):
        """Обновление ядовитого облака"""
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 100:
                    if not enemy.effect_system.has_effect('poison'):
                        poison = self.create_instance('poison')
                        enemy.effect_system.add_effect(poison)

    def _apply_singularity(self, owner, inst, game):
        """Применение сингулярности"""
        inst.params['singularity_x'] = owner.x
        inst.params['singularity_y'] = owner.y
        inst.params['singularity_radius'] = 0
        game.spawn_particles(owner.x, owner.y, 30, PURPLE)

    def _update_singularity(self, owner, inst, dt, game):
        """Обновление сингулярности"""
        sx = inst.params.get('singularity_x', owner.x)
        sy = inst.params.get('singularity_y', owner.y)
        radius = inst.params.get('singularity_radius', 0)

        # Расширение радиуса
        radius = min(300, radius + 30 * dt)
        inst.params['singularity_radius'] = radius

        # Притяжение всего
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(sx - enemy.x, sy - enemy.y)
                if dist < radius:
                    angle = math.atan2(sy - enemy.y, sx - enemy.x)
                    pull = (radius - dist) * 3 * dt
                    enemy.x += math.cos(angle) * pull
                    enemy.y += math.sin(angle) * pull
                    if dist < 30:
                        enemy.take_damage(int(50 * dt))

        # Притяжение пикапов
        for pickup in game.pickups[:]:
            dist = math.hypot(sx - pickup.x, sy - pickup.y)
            if dist < radius:
                angle = math.atan2(sy - pickup.y, sx - pickup.x)
                pull = (radius - dist) * 3 * dt
                pickup.x += math.cos(angle) * pull
                pickup.y += math.sin(angle) * pull

    def _remove_singularity(self, owner, inst, game):
        """Удаление сингулярности"""
        sx = inst.params.get('singularity_x', owner.x)
        sy = inst.params.get('singularity_y', owner.y)
        radius = inst.params.get('singularity_radius', 0)
        game.collision_system._handle_explosion(sx, sy, radius)

    def _update_electric_storm(self, owner, inst, dt, game):
        """Обновление электрического шторма"""
        inst.params['storm_timer'] = inst.params.get('storm_timer', 0) + dt
        if inst.params['storm_timer'] >= 0.3:
            inst.params['storm_timer'] = 0
            if game.enemies:
                target = random.choice(game.enemies)
                if target.alive:
                    target.take_damage(30)
                    game.add_damage_number(target.x, target.y - target.radius, 30, CYAN)
                    game.spawn_sparks(target.x, target.y, 5)

    def _update_nanite_swarm(self, owner, inst, dt, game):
        """Обновление роя нанитов"""
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 200:
                    damage = int(5 * dt * inst.stacks)
                    enemy.take_damage(damage)

    def _update_apocalypse(self, owner, inst, dt, game):
        """Обновление апокалипсиса"""
        inst.params['apoc_timer'] = inst.params.get('apoc_timer', 0) + dt
        if inst.params['apoc_timer'] >= 0.5:
            inst.params['apoc_timer'] = 0
            # Метеорит
            if game.enemies:
                target = random.choice(game.enemies)
                if target.alive:
                    x = target.x + random.randint(-50, 50)
                    y = target.y + random.randint(-50, 50)
                    game.collision_system._handle_explosion(x, y, 100)
                    game.spawn_particles(x, y, 20, ORANGE)

    def _trigger_damage_reflection(self, owner, inst, target, game, damage=0):
        """Отражение урона"""
        if target and damage > 0:
            reflected = int(damage * 0.5)
            target.take_damage(reflected)
            if game:
                game.add_damage_number(target.x, target.y - target.radius, reflected, MAGENTA)

    def _update_freeze_aura(self, owner, inst, dt, game):
        """Обновление ауры заморозки"""
        if not game:
            return
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 100:
                    if not enemy.effect_system:
                        enemy.effect_system = EffectSystem(enemy, game)
                    if not enemy.effect_system.has_effect('freeze'):
                        freeze = self.create_instance('freeze')
                        enemy.effect_system.add_effect(freeze)

    def _update_fire_aura(self, owner, inst, dt, game):
        """Обновление ауры огня"""
        if not game:
            return
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(owner.x - enemy.x, owner.y - enemy.y)
                if dist < 100:
                    if not enemy.effect_system:
                        enemy.effect_system = EffectSystem(enemy, game)
                    if not enemy.effect_system.has_effect('burn'):
                        burn = self.create_instance('burn')
                        enemy.effect_system.add_effect(burn)

    def _update_healing_aura(self, owner, inst, dt, game):
        """Обновление ауры лечения"""
        if not game:
            return
        # Лечение игрока
        owner.heal(int(2 * dt * inst.stacks))
        # Лечение союзников
        if hasattr(game, 'ally_system'):
            for ally in game.ally_system.allies:
                if ally.alive:
                    dist = math.hypot(owner.x - ally.x, owner.y - ally.y)
                    if dist < 150:
                        ally.hp = min(ally.max_hp, ally.hp + int(2 * dt * inst.stacks))

    # ===== ОСНОВНЫЕ МЕТОДЫ =====

    def add_effect(self, effect: EffectInstance):
        """Добавление эффекта"""
        # Проверка на существующий эффект
        for existing in self.active_effects:
            if existing.data.id == effect.data.id:
                existing.add_stack()
                return

        self.active_effects.append(effect)

        # Применение эффекта с передачей game
        if effect.data.apply_func and self.owner:
            effect.data.apply_func(self.owner, effect, self.game)

    def remove_effect(self, effect_id: str):
        """Удаление эффекта"""
        for effect in self.active_effects[:]:
            if effect.data.id == effect_id:
                if effect.data.remove_func and self.owner:
                    effect.data.remove_func(self.owner, effect, self.game)
                self.active_effects.remove(effect)

    def apply_effect_by_id(self, effect_id: str, source=None) -> bool:
        """Применение эффекта по ID"""
        effect_instance = self.create_instance(effect_id, source)
        if effect_instance:
            self.add_effect(effect_instance)
            return True
        return False

    def remove_all_effects(self):
        """Удаление всех эффектов"""
        for effect in self.active_effects[:]:
            self.remove_effect(effect.data.id)

    def get_effects_by_type(self, effect_type: str) -> List[EffectInstance]:
        """Получение эффектов по типу"""
        return [e for e in self.active_effects if e.data.type == effect_type]

    def get_effects_by_rarity(self, rarity: str) -> List[EffectInstance]:
        """Получение эффектов по редкости"""
        return [e for e in self.active_effects if e.data.rarity == rarity]

    def get_total_effect_count(self) -> int:
        """Получение общего количества активных эффектов"""
        return len(self.active_effects)

    def get_effect_stacks(self, effect_id: str) -> int:
        """Получение количества стаков эффекта"""
        for effect in self.active_effects:
            if effect.data.id == effect_id:
                return effect.stacks
        return 0

    def trigger(self, effect_id: str, target=None, game=None, **kwargs):
        """Срабатывание эффекта"""
        if game:
            self.game = game
        for effect in self.active_effects:
            if effect.data.id == effect_id:
                effect.trigger(self.owner, target, self.game, **kwargs)
                return True
        return False

    def clear_expired_effects(self):
        """Очистка истёкших эффектов"""
        for effect in self.active_effects[:]:
            if not effect.active or effect.timer <= 0:
                self.remove_effect(effect.data.id)

    def has_effect(self, effect_id: str) -> bool:
        """Проверка наличия эффекта"""
        return any(e.data.id == effect_id for e in self.active_effects)

    def get_effect(self, effect_id: str) -> Optional[EffectInstance]:
        """Получение эффекта"""
        for effect in self.active_effects:
            if effect.data.id == effect_id:
                return effect
        return None

    def update(self, dt: float, game=None):
        """Обновление всех эффектов"""
        if game:
            self.game = game

        to_remove = []
        for effect in self.active_effects:
            if not effect.update(dt, self.owner, self.game):
                to_remove.append(effect)

        for effect in to_remove:
            if effect.data.remove_func and self.owner:
                effect.data.remove_func(self.owner, effect, self.game)
            self.active_effects.remove(effect)

    def trigger(self, effect_id: str, target=None, game=None, **kwargs):
        """Срабатывание эффекта"""
        for effect in self.active_effects:
            if effect.data.id == effect_id:
                effect.trigger(self.owner, target, game, **kwargs)

    def trigger_all(self, target=None, game=None, **kwargs):
        """Срабатывание всех эффектов"""
        if game:
            self.game = game
        for effect in self.active_effects:
            effect.trigger(self.owner, target, self.game, **kwargs)

    def create_instance(self, effect_id: str, source=None) -> Optional[EffectInstance]:
        """Создание экземпляра эффекта"""
        effect_data = self.effect_database.get(effect_id)
        if effect_data:
            return EffectInstance(effect_data, source)
        return None

    def get_random_effect(self, rarity: str = None) -> Optional[EffectData]:
        """Получение случайного эффекта"""
        effects = list(self.effect_database.values())
        if rarity:
            effects = [e for e in effects if e.rarity == rarity]
        if effects:
            return random.choice(effects)
        return None

    def get_all_effects(self) -> List[EffectData]:
        """Получение всех эффектов"""
        return list(self.effect_database.values())

    def get_active_effects_info(self) -> List[Dict]:
        """Получение информации об активных эффектах"""
        info = []
        for effect in self.active_effects:
            info.append({
                'id': effect.data.id,
                'name': effect.data.name,
                'stacks': effect.stacks,
                'timer': effect.timer,
                'type': effect.data.type,
                'rarity': effect.data.rarity
            })
        return info
