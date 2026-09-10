# systems/legacy.py
from typing import Dict, List, Optional
from settings import *
import json
import os


class LegacySystem:
    """Система наследия"""

    def __init__(self):
        self.legacy_data = {}
        self.legacy_file = "legacy_data.json"
        self.load_legacy()

    def load_legacy(self):
        """Загрузка данных наследия"""
        if os.path.exists(self.legacy_file):
            try:
                with open(self.legacy_file, 'r', encoding='utf-8') as f:
                    self.legacy_data = json.load(f)
            except:
                self.legacy_data = {}

    def save_legacy(self):
        """Сохранение данных наследия"""
        try:
            with open(self.legacy_file, 'w', encoding='utf-8') as f:
                json.dump(self.legacy_data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def record_death(self, player_stats: Dict):
        """Запись смерти персонажа"""
        # Сохранение статистики
        self.legacy_data['last_death'] = player_stats

        # Обновление общего прогресса
        total_kills = self.legacy_data.get('total_kills', 0) + player_stats.get('kills', 0)
        total_score = self.legacy_data.get('total_score', 0) + player_stats.get('score', 0)
        total_deaths = self.legacy_data.get('total_deaths', 0) + 1

        self.legacy_data['total_kills'] = total_kills
        self.legacy_data['total_score'] = total_score
        self.legacy_data['total_deaths'] = total_deaths

        # Разблокировка наследия
        self._unlock_legacy_bonuses(player_stats)

        self.save_legacy()

    def _unlock_legacy_bonuses(self, player_stats: Dict):
        """Разблокировка бонусов наследия"""
        upgrades = self.legacy_data.get('upgrades', {})

        # Бонусы на основе достижений
        if player_stats.get('kills', 0) >= 100:
            upgrades['damage_boost_1'] = True
        if player_stats.get('kills', 0) >= 500:
            upgrades['damage_boost_2'] = True
        if player_stats.get('score', 0) >= 10000:
            upgrades['score_boost'] = True
        if player_stats.get('wave', 1) >= 10:
            upgrades['survivor_boost'] = True

        self.legacy_data['upgrades'] = upgrades

    def get_legacy_bonuses(self) -> Dict:
        """Получение бонусов наследия для нового персонажа"""
        upgrades = self.legacy_data.get('upgrades', {})
        bonuses = {
            'damage_multiplier': 1.0,
            'max_hp_bonus': 0,
            'starting_scrap': 0,
            'exp_multiplier': 1.0
        }

        if upgrades.get('damage_boost_1'):
            bonuses['damage_multiplier'] += 0.1
        if upgrades.get('damage_boost_2'):
            bonuses['damage_multiplier'] += 0.2
        if upgrades.get('survivor_boost'):
            bonuses['max_hp_bonus'] += 25
        if upgrades.get('score_boost'):
            bonuses['exp_multiplier'] += 0.5

        return bonuses

    def get_total_stats(self) -> Dict:
        """Получение общей статистики"""
        return {
            'total_kills': self.legacy_data.get('total_kills', 0),
            'total_score': self.legacy_data.get('total_score', 0),
            'total_deaths': self.legacy_data.get('total_deaths', 0),
            'upgrades': self.legacy_data.get('upgrades', {})
        }

    def apply_legacy_to_new_character(self, player):
        """Применение наследия к новому персонажу"""
        bonuses = self.get_legacy_bonuses()

        player.damage_multiplier = getattr(player, 'damage_multiplier', 1.0) * bonuses['damage_multiplier']
        player.max_hp += bonuses['max_hp_bonus']
        player.hp = player.max_hp
        player.scrap += bonuses['starting_scrap']
        player.exp_multiplier = getattr(player, 'exp_multiplier', 1.0) * bonuses['exp_multiplier']