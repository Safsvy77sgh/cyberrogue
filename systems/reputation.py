# systems/reputation.py
from typing import Dict, List, Tuple, Optional
from settings import *


class ReputationSystem:
    """Система репутации с фракциями"""

    def __init__(self):
        self.factions = {
            'resistance': {'name': 'Сопротивление', 'reputation': 0, 'max': 100, 'min': -100},
            'machines': {'name': 'Машины', 'reputation': -50, 'max': 100, 'min': -100},
            'merchants': {'name': 'Торговцы', 'reputation': 0, 'max': 100, 'min': -100},
            'survivors': {'name': 'Выжившие', 'reputation': 0, 'max': 100, 'min': -100},
            'hybrids': {'name': 'Гибриды', 'reputation': -100, 'max': 100, 'min': -100}
        }

        self.reputation_levels = {
            (-100, -75): 'Враг',
            (-75, -50): 'Враждебный',
            (-50, -25): 'Недружелюбный',
            (-25, 0): 'Нейтральный',
            (0, 25): 'Дружелюбный',
            (25, 50): 'Союзник',
            (50, 75): 'Уважаемый',
            (75, 100): 'Легенда'
        }

    def change_reputation(self, faction: str, amount: int):
        """Изменение репутации с фракцией"""
        if faction in self.factions:
            self.factions[faction]['reputation'] = max(
                self.factions[faction]['min'],
                min(self.factions[faction]['max'],
                    self.factions[faction]['reputation'] + amount)
            )

    def get_reputation(self, faction: str) -> int:
        """Получение репутации с фракцией"""
        return self.factions.get(faction, {}).get('reputation', 0)

    def get_reputation_level(self, faction: str) -> str:
        """Получение уровня репутации"""
        rep = self.get_reputation(faction)

        for (min_rep, max_rep), level in self.reputation_levels.items():
            if min_rep <= rep < max_rep:
                return level

        return 'Нейтральный'

    def get_faction_discount(self, faction: str) -> float:
        """Получение скидки от фракции"""
        rep = self.get_reputation(faction)
        if rep >= 50:
            return 0.7  # 30% скидка
        elif rep >= 25:
            return 0.85  # 15% скидка
        elif rep >= 0:
            return 1.0  # Нет скидки
        elif rep >= -25:
            return 1.2  # 20% наценка
        else:
            return 1.5  # 50% наценка

    def get_faction_quests(self, faction: str) -> List[str]:
        """Получение доступных квестов от фракции"""
        rep = self.get_reputation(faction)
        quests = []

        if faction == 'resistance':
            if rep >= 0:
                quests.append('patrol')
            if rep >= 25:
                quests.append('rescue')
            if rep >= 50:
                quests.append('boss_hunt')
        elif faction == 'merchants':
            if rep >= 0:
                quests.append('delivery')
            if rep >= 25:
                quests.append('escort')

        return quests

    def is_hostile(self, faction: str) -> bool:
        """Проверка враждебности фракции"""
        return self.get_reputation(faction) <= -50