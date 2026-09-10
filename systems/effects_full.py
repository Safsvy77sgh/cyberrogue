# systems/effects_full.py
import random
import math
import pygame
from typing import Dict, List, Tuple, Any, Optional
from settings import *


class EffectData:
    """Данные эффекта"""

    def __init__(self, effect_id: str, name: str, description: str,
                 duration: float = 0, permanent: bool = False,
                 effect_type: str = 'buff', rarity: str = 'common'):
        self.id = effect_id
        self.name = name
        self.description = description
        self.duration = duration
        self.permanent = permanent
        self.type = effect_type  # buff, debuff, aura, passive, trigger
        self.rarity = rarity  # common, rare, epic, legendary
        self.params = {}


class EffectInstance:
    """Конкретный экземпляр эффекта на сущности"""

    def __init__(self, effect_data: EffectData, source=None):
        self.data = effect_data
        self.source = source
        self.timer = effect_data.duration
        self.stacks = 1
        self.active = True
        self.params = effect_data.params.copy()

    def update(self, dt: float) -> bool:
        if not self.data.permanent:
            self.timer -= dt
            return self.timer > 0
        return True

    def add_stack(self, amount: int = 1):
        self.stacks += amount
        self.timer = self.data.duration  # Обновление таймера


class EffectSystem:
    """Полная система эффектов"""

    def __init__(self):
        self.effect_database = {}
        self._initialize_all_effects()

    def _initialize_all_effects(self):
        """Инициализация всех 100 эффектов"""
        # ===== 50 УНИКАЛЬНЫХ ЭФФЕКТОВ =====

        # 1. Хронозамедление
        self._add_effect('chrono_slow', 'Хронозамедление',
                         'Критические попадания замедляют время', 1.0, False, 'trigger', 'epic')

        # 2. Энергетический вампиризм
        self._add_effect('energy_vampirism', 'Энергетический вампиризм',
                         'Урон восстанавливает энергию', 0, True, 'passive', 'rare')

        # 3. Гравитационный колодец
        self._add_effect('gravity_well', 'Гравитационный колодец',
                         'Выстрелы создают зону притяжения', 2.0, False, 'trigger', 'epic')

        # 4. Электрическая дуга
        self._add_effect('electric_arc', 'Электрическая дуга',
                         'Пули перескакивают на ближайших врагов', 0, True, 'passive', 'rare')

        # 5. Нанороботы-ремонтники
        self._add_effect('nanobots_repair', 'Нанороботы-ремонтники',
                         'Постепенное лечение вне боя', 0, True, 'passive', 'rare')

        # 6. Термобарический взрыв
        self._add_effect('thermobaric', 'Термобарический взрыв',
                         'Огненные пули оставляют горящую область', 0, True, 'passive', 'epic')

        # 7. Зеркальный щит
        self._add_effect('mirror_shield', 'Зеркальный щит',
                         'Отражает снаряды', 3.0, False, 'buff', 'epic')

        # 8. Квантовая запутанность
        self._add_effect('quantum_entanglement', 'Квантовая запутанность',
                         'Урон передаётся случайному врагу', 0, True, 'passive', 'legendary')

        # 9. Хамелеон
        self._add_effect('chameleon', 'Хамелеон',
                         'Невидимость после рывка', 2.0, False, 'trigger', 'rare')

        # 10. Сингулярность
        self._add_effect('singularity', 'Сингулярность',
                         'Создаёт чёрную дыру', 5.0, False, 'active', 'legendary')

        # 11. Воспламенение
        self._add_effect('ignite', 'Воспламенение',
                         'Поджигает врагов', 4.0, False, 'debuff', 'common')

        # 12. Замораживание
        self._add_effect('freeze', 'Замораживание',
                         'Замораживает врагов', 3.0, False, 'debuff', 'common')

        # 13. Отравление
        self._add_effect('poison', 'Отравление',
                         'Ядовитое облако', 5.0, False, 'debuff', 'common')

        # 14. ЭМИ
        self._add_effect('emp', 'Электромагнитный импульс',
                         'Отключает роботов', 3.0, False, 'active', 'epic')

        # 15. Взрывная перегрузка
        self._add_effect('explosive_overload', 'Взрывная перегрузка',
                         'Враги взрываются при смерти', 0, True, 'passive', 'rare')

        # 16. Регенерация щита
        self._add_effect('shield_regen', 'Регенерация щита',
                         'Быстрое восстановление щита', 0, True, 'passive', 'rare')

        # 17. Адреналиновый рывок
        self._add_effect('adrenaline', 'Адреналиновый рывок',
                         'Скорость при низком HP', 0, True, 'passive', 'common')

        # 18. Инверсия урона
        self._add_effect('damage_inversion', 'Инверсия урона',
                         'Урон превращается в энергию', 0, True, 'passive', 'epic')

        # 19. Фазовый сдвиг
        self._add_effect('phase_shift', 'Фазовый сдвиг',
                         'Неуязвимость и проход сквозь стены', 1.5, False, 'buff', 'epic')

        # 20. Дупликация
        self._add_effect('duplication', 'Дупликация',
                         'Шанс создания второй пули', 0, True, 'passive', 'rare')

        # 21. Критический каскад
        self._add_effect('crit_cascade', 'Критический каскад',
                         'Криты увеличивают шанс крита', 0, True, 'passive', 'epic')

        # 22. Вампирская аура
        self._add_effect('vampiric_aura', 'Вампирская аура',
                         'Лечение от ближних врагов', 0, True, 'aura', 'rare')

        # 23. Плазменный след
        self._add_effect('plasma_trail', 'Плазменный след',
                         'Пули оставляют горящий след', 0, True, 'passive', 'rare')

        # 24. Телепортационный удар
        self._add_effect('teleport_strike', 'Телепортационный удар',
                         'Попадание телепортирует к врагу', 0, True, 'trigger', 'epic')

        # 25. Отражение урона
        self._add_effect('thorns', 'Отражение урона',
                         'Часть урона возвращается', 0, True, 'passive', 'common')

        # 26. Гравитационный разлом
        self._add_effect('gravity_rift', 'Гравитационный разлом',
                         'Искривляет траектории снарядов', 0, True, 'aura', 'epic')

        # 27. Пожиратель душ
        self._add_effect('soul_eater', 'Пожиратель душ',
                         'Убийства временно повышают урон', 5.0, False, 'buff', 'rare')

        # 28. Энергетический всплеск
        self._add_effect('energy_surge', 'Энергетический всплеск',
                         'Переполнение энергии создаёт волну', 0, True, 'trigger', 'epic')

        # 29. Песчаная буря
        self._add_effect('sandstorm', 'Песчаная буря',
                         'Снижает точность врагов', 6.0, False, 'aura', 'rare')

        # 30. Электрический шторм
        self._add_effect('electric_storm', 'Электрический шторм',
                         'Призывает молнии', 4.0, False, 'active', 'epic')

        # 31. Токсичный туман
        self._add_effect('toxic_fog', 'Токсичный туман',
                         'Ядовитое облако следует за игроком', 5.0, False, 'aura', 'rare')

        # 32. Костяная броня
        self._add_effect('bone_armor', 'Костяная броня',
                         'Создаёт осколки при уроне', 0, True, 'passive', 'rare')

        # 33. Рой нанитов
        self._add_effect('nanite_swarm', 'Рой нанитов',
                         'Рой атакует ближайших врагов', 6.0, False, 'active', 'epic')

        # 34. Временной разрыв
        self._add_effect('time_rift', 'Временной разрыв',
                         'Возврат во времени', 3.0, False, 'active', 'legendary')

        # 35. Взрывная цепь
        self._add_effect('explosion_chain', 'Взрывная цепь',
                         'Взрывы вызывают цепную реакцию', 0, True, 'passive', 'epic')

        # 36. Сфера антимагии
        self._add_effect('antimagic_sphere', 'Сфера антимагии',
                         'Поглощает пули и лечит', 4.0, False, 'buff', 'epic')

        # 37. Галлюцинация
        self._add_effect('hallucination', 'Галлюцинация',
                         'Создаёт отвлекающие копии', 5.0, False, 'active', 'rare')

        # 38. Берсерк
        self._add_effect('berserk', 'Берсерк',
                         'Урон и скорость при низком HP', 0, True, 'passive', 'epic')

        # 39. Кровавый туман
        self._add_effect('blood_mist', 'Кровавый туман',
                         'Убийства создают лечащие облака', 0, True, 'passive', 'rare')

        # 40. Инферно
        self._add_effect('inferno', 'Инферно',
                         'Поджигает всё вокруг', 3.0, False, 'active', 'legendary')

        # 41. Электрическое поле
        self._add_effect('electric_field', 'Электрическое поле',
                         'Зона урона врагам', 4.0, False, 'aura', 'rare')

        # 42. Гравитационный толчок
        self._add_effect('gravity_push', 'Гравитационный толчок',
                         'Отбрасывает врагов при выстреле', 0, True, 'passive', 'common')

        # 43. Магнитный захват
        self._add_effect('magnet', 'Магнитный захват',
                         'Притягивает пикапы', 0, True, 'passive', 'common')

        # 44. Пространственный карман
        self._add_effect('spatial_pocket', 'Пространственный карман',
                         'Увеличивает инвентарь', 0, True, 'passive', 'rare')

        # 45. Ледяная корка
        self._add_effect('ice_crust', 'Ледяная корка',
                         'Замораживает при контакте', 0, True, 'aura', 'rare')

        # 46. Плазменный разряд
        self._add_effect('plasma_discharge', 'Плазменный разряд',
                         'Молнии по случайным врагам', 0, True, 'passive', 'epic')

        # 47. Демонический контракт
        self._add_effect('demonic_contract', 'Демонический контракт',
                         'HP за мощный бафф', 10.0, False, 'active', 'legendary')

        # 48. Астральная проекция
        self._add_effect('astral_projection', 'Астральная проекция',
                         'Атака в астрале', 5.0, False, 'active', 'legendary')

        # 49. Квантовый сдвиг
        self._add_effect('quantum_shift', 'Квантовый сдвиг',
                         'Пули проходят сквозь стены', 0, True, 'passive', 'epic')

        # 50. Апокалипсис
        self._add_effect('apocalypse', 'Апокалипсис',
                         'Метеоритный дождь', 8.0, False, 'active', 'legendary')

        # ===== 50 КЛАССИЧЕСКИХ ЭФФЕКТОВ =====

        # 51. Двойной урон
        self._add_effect('double_damage', 'Двойной урон',
                         'Урон удвоен', 5.0, False, 'buff', 'common')

        # 52. Тройной выстрел
        self._add_effect('triple_shot', 'Тройной выстрел',
                         'Три пули вместо одной', 0, True, 'passive', 'common')

        # 53. Скорострельность
        self._add_effect('rapid_fire', 'Скорострельность',
                         'Увеличенная скорострельность', 0, True, 'passive', 'common')

        # 54. Бесконечные патроны
        self._add_effect('infinite_ammo', 'Бесконечные патроны',
                         'Без перезарядки', 0, True, 'passive', 'rare')

        # 55. Вампиризм
        self._add_effect('vampirism', 'Вампиризм',
                         'Лечение от урона', 0, True, 'passive', 'rare')

        # 56. Невидимость
        self._add_effect('invisibility', 'Невидимость',
                         'Полная невидимость', 3.0, False, 'buff', 'rare')

        # 57. Магнит для монет
        self._add_effect('coin_magnet', 'Магнит для монет',
                         'Притягивает монеты', 0, True, 'passive', 'common')

        # 58. Щит
        self._add_effect('shield', 'Щит',
                         'Поглощает урон', 0, True, 'buff', 'common')

        # 59. Отравление
        self._add_effect('poison_classic', 'Отравление',
                         'Урон со временем', 4.0, False, 'debuff', 'common')

        # 60. Заморозка
        self._add_effect('freeze_classic', 'Заморозка',
                         'Замедление и урон', 3.0, False, 'debuff', 'common')

        # 61. Поджог
        self._add_effect('burn', 'Поджог',
                         'Горение', 3.0, False, 'debuff', 'common')

        # 62. Крит-шанс
        self._add_effect('crit_chance', 'Крит-шанс',
                         'Увеличенный шанс крита', 0, True, 'passive', 'common')

        # 63. Крит-урон
        self._add_effect('crit_damage', 'Крит-урон',
                         'Увеличенный урон крита', 0, True, 'passive', 'common')

        # 64. Увеличение HP
        self._add_effect('max_hp', 'Увеличение HP',
                         'Больше здоровья', 0, True, 'passive', 'common')

        # 65. Регенерация
        self._add_effect('regen', 'Регенерация',
                         'Постепенное лечение', 0, True, 'passive', 'common')

        # 66. Снижение урона
        self._add_effect('damage_reduction', 'Снижение урона',
                         'Получаемый урон снижен', 0, True, 'passive', 'common')

        # 67. Отражение снарядов
        self._add_effect('reflect', 'Отражение снарядов',
                         'Снаряды отражаются', 0, True, 'passive', 'rare')

        # 68. Призыв союзника
        self._add_effect('summon_ally', 'Призыв союзника',
                         'Призывает дрона', 0, True, 'active', 'rare')

        # 69. Взрывные пули
        self._add_effect('explosive_bullets', 'Взрывные пули',
                         'Пули взрываются', 0, True, 'passive', 'rare')

        # 70. Пробивание
        self._add_effect('piercing', 'Пробивание',
                         'Пули проходят насквозь', 0, True, 'passive', 'common')

        # 71. Рикошет
        self._add_effect('ricochet', 'Рикошет',
                         'Пули отскакивают', 0, True, 'passive', 'rare')

        # 72. Самонаведение
        self._add_effect('homing', 'Самонаведение',
                         'Пули наводятся', 0, True, 'passive', 'rare')

        # 73. Паутина
        self._add_effect('web', 'Паутина',
                         'Замедляет врагов', 3.0, False, 'debuff', 'common')

        # 74. Электрический урон
        self._add_effect('electric_damage', 'Электрический урон',
                         'Дополнительный урон электричеством', 0, True, 'passive', 'rare')

        # 75. Кислотный урон
        self._add_effect('acid_damage', 'Кислотный урон',
                         'Дополнительный урон кислотой', 0, True, 'passive', 'rare')

        # 76. Святой урон
        self._add_effect('holy_damage', 'Святой урон',
                         'Дополнительный святой урон', 0, True, 'passive', 'rare')

        # 77. Теневой урон
        self._add_effect('shadow_damage', 'Теневой урон',
                         'Дополнительный теневой урон', 0, True, 'passive', 'rare')

        # 78. Скорость передвижения
        self._add_effect('move_speed', 'Скорость передвижения',
                         'Увеличенная скорость', 0, True, 'passive', 'common')

        # 79. Снижение перезарядки
        self._add_effect('cooldown_reduction', 'Снижение перезарядки',
                         'Быстрая перезарядка', 0, True, 'passive', 'common')

        # 80. Вампирский выстрел
        self._add_effect('vampiric_shot', 'Вампирский выстрел',
                         'Выстрелы лечат', 0, True, 'passive', 'epic')

        # 81. Магическая стрела
        self._add_effect('magic_arrow', 'Магическая стрела',
                         'Самонаводящаяся стрела', 0, True, 'passive', 'rare')

        # 82. Разброс
        self._add_effect('spread', 'Разброс',
                         'Пули разлетаются веером', 0, True, 'passive', 'common')

        # 83. Конусный огонь
        self._add_effect('cone_fire', 'Конусный огонь',
                         'Огонь конусом', 0, True, 'passive', 'rare')

        # 84. Кольцевой выстрел
        self._add_effect('ring_shot', 'Кольцевой выстрел',
                         'Пули во все стороны', 0, True, 'active', 'epic')

        # 85. Лазерный луч
        self._add_effect('laser_beam', 'Лазерный луч',
                         'Непрерывный лазер', 0, True, 'active', 'epic')

        # 86. Плазменный шар
        self._add_effect('plasma_ball', 'Плазменный шар',
                         'Медленный мощный шар', 0, True, 'active', 'epic')

        # 87. Ракетный залп
        self._add_effect('rocket_barrage', 'Ракетный залп',
                         'Множество ракет', 0, True, 'active', 'legendary')

        # 88. Мина
        self._add_effect('mine', 'Мина',
                         'Устанавливает мину', 0, True, 'active', 'common')

        # 89. Турель
        self._add_effect('turret', 'Турель',
                         'Устанавливает турель', 0, True, 'active', 'rare')

        # 90. Дрон
        self._add_effect('drone', 'Дрон',
                         'Боевой дрон', 0, True, 'passive', 'rare')

        # 91. Аура урона
        self._add_effect('damage_aura', 'Аура урона',
                         'Постоянный урон вокруг', 0, True, 'aura', 'epic')

        # 92. Клинковый вихрь
        self._add_effect('blade_vortex', 'Клинковый вихрь',
                         'Вихрь клинков', 4.0, False, 'active', 'epic')

        # 93. Телекинез
        self._add_effect('telekinesis', 'Телекинез',
                         'Подбор предметов на расстоянии', 0, True, 'passive', 'rare')

        # 94. Телепортация
        self._add_effect('teleport', 'Телепортация',
                         'Мгновенное перемещение', 0, True, 'active', 'rare')

        # 95. Огненное кольцо
        self._add_effect('fire_ring', 'Огненное кольцо',
                         'Кольцо огня', 3.0, False, 'active', 'rare')

        # 96. Ледяная стрела
        self._add_effect('ice_arrow', 'Ледяная стрела',
                         'Замораживающая стрела', 0, True, 'passive', 'common')

        # 97. Ядовитое облако
        self._add_effect('poison_cloud', 'Ядовитое облако',
                         'Облако яда', 4.0, False, 'active', 'rare')

        # 98. Кровавая жертва
        self._add_effect('blood_sacrifice', 'Кровавая жертва',
                         'HP за бафф', 0, True, 'active', 'epic')

        # 99. Благословение
        self._add_effect('blessing', 'Благословение',
                         'Случайный бафф', 5.0, False, 'buff', 'rare')

        # 100. Проклятие
        self._add_effect('curse', 'Проклятие',
                         'Случайный дебафф', 5.0, False, 'debuff', 'rare')

    def _add_effect(self, effect_id: str, name: str, description: str,
                    duration: float = 0, permanent: bool = False,
                    effect_type: str = 'buff', rarity: str = 'common'):
        """Добавление эффекта в базу"""
        effect = EffectData(effect_id, name, description, duration, permanent, effect_type, rarity)
        self.effect_database[effect_id] = effect

    def get_effect(self, effect_id: str) -> Optional[EffectData]:
        """Получение эффекта по ID"""
        return self.effect_database.get(effect_id)

    def create_instance(self, effect_id: str, source=None) -> Optional[EffectInstance]:
        """Создание экземпляра эффекта"""
        effect_data = self.get_effect(effect_id)
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

    def get_effects_by_type(self, effect_type: str) -> List[EffectData]:
        """Получение эффектов по типу"""
        return [e for e in self.effect_database.values() if e.type == effect_type]

    def get_effects_by_rarity(self, rarity: str) -> List[EffectData]:
        """Получение эффектов по редкости"""
        return [e for e in self.effect_database.values() if e.rarity == rarity]

    def apply_effect_to_entity(self, entity, effect_id: str, source=None) -> bool:
        """Применение эффекта к сущности"""
        effect_instance = self.create_instance(effect_id, source)
        if effect_instance:
            if hasattr(entity, 'effect_system'):
                entity.effect_system.add_effect(effect_instance)
                return True
        return False