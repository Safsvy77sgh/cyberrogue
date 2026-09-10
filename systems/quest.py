# systems/quest.py
import pygame
import random
import math
import json
from entities.pickup import Pickup
import os
from typing import Dict, List, Tuple, Optional, Any, Callable
from settings import *
from data.story_data import (
    SIDE_QUESTS,
    QUEST_CHAINS,
    CHARACTERS,
    LORE_ENTRIES,
    FLAG_DEFINITIONS,
    REPUTATION_EFFECTS
)


class QuestObjective:
    """Отдельная цель квеста."""
    def __init__(self, objective_type: str, target: str, count: int = 1, duration: float = 0, description: str = ""):
        self.type = objective_type
        self.target = target
        self.count = count
        self.duration = duration
        self.description = description
        self.progress = 0
        self.completed = False

    def update(self, dt: float, game=None):
        """Обновляет прогресс цели."""
        if self.completed:
            return
        if self.type == "survive":
            self.progress += dt
            if self.progress >= self.duration:
                self.completed = True

    def check_completion(self, event_type: str, value: int = 1, target: str = None) -> bool:
        """Проверяет, выполнена ли цель на основе события."""
        if self.completed:
            return False
        if target and self.target != target and self.target != "any":
            return False
        if event_type == self.type:
            self.progress += value
            if self.progress >= self.count:
                self.completed = True
                return True
        return False

    def get_progress_ratio(self) -> float:
        """Возвращает прогресс от 0.0 до 1.0."""
        if self.count > 0:
            return min(1.0, self.progress / self.count)
        elif self.duration > 0:
            return min(1.0, self.progress / self.duration)
        return 0.0

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "target": self.target,
            "count": self.count,
            "duration": self.duration,
            "description": self.description,
            "progress": self.progress,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'QuestObjective':
        obj = cls(data["type"], data["target"], data.get("count", 1), data.get("duration", 0), data.get("description", ""))
        obj.progress = data.get("progress", 0)
        obj.completed = data.get("completed", False)
        return obj


class Quest:
    """Полноценный квест с целями, наградами и сюжетными связями."""
    def __init__(self, quest_id: str, title: str, description: str, objectives: List[QuestObjective], reward: dict = None, chapter_available: int = 1, repeatable: bool = False):
        self.id = quest_id
        self.title = title
        self.description = description
        self.objectives = objectives
        self.reward = reward or {}
        self.chapter_available = chapter_available
        self.repeatable = repeatable
        self.completed = False
        self.active = False
        self.progress = 0
        self.completed_objectives = 0
        self.total_objectives = len(objectives)

    def activate(self):
        """Активирует квест."""
        self.active = True
        self.completed = False
        for obj in self.objectives:
            obj.progress = 0
            obj.completed = False

    def update(self, dt: float, game=None):
        """Обновляет все цели квеста."""
        if not self.active or self.completed:
            return
        for obj in self.objectives:
            obj.update(dt, game)
        self._check_completion()

    def _check_completion(self):
        """Проверяет, выполнены ли все цели."""
        self.completed_objectives = sum(1 for obj in self.objectives if obj.completed)
        if self.completed_objectives >= self.total_objectives:
            self.completed = True
            self.active = False

    def handle_event(self, event_type: str, value: int = 1, target: str = None) -> bool:
        """Обрабатывает событие (убийство, сбор и т.д.) и возвращает True, если квест выполнен."""
        if not self.active or self.completed:
            return False
        changed = False
        for obj in self.objectives:
            if obj.check_completion(event_type, value, target):
                changed = True
        if changed:
            self._check_completion()
        return self.completed

    def get_progress_ratio(self) -> float:
        """Возвращает общий прогресс квеста (0.0 - 1.0)."""
        if self.total_objectives == 0:
            return 1.0 if self.completed else 0.0
        total = sum(obj.get_progress_ratio() for obj in self.objectives) / self.total_objectives
        return total

    def get_objectives_text(self) -> List[str]:
        """Возвращает список строк с описанием целей."""
        texts = []
        for obj in self.objectives:
            status = "✓" if obj.completed else "□"
            if obj.type == "survive":
                texts.append(f"{status} {obj.description} ({int(obj.progress)}/{int(obj.duration)} сек)")
            else:
                texts.append(f"{status} {obj.description} ({obj.progress}/{obj.count})")
        return texts

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "objectives": [obj.to_dict() for obj in self.objectives],
            "reward": self.reward,
            "chapter_available": self.chapter_available,
            "repeatable": self.repeatable,
            "completed": self.completed,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Quest':
        quest = cls(
            data["id"],
            data["title"],
            data["description"],
            [QuestObjective.from_dict(obj) for obj in data.get("objectives", [])],
            data.get("reward", {}),
            data.get("chapter_available", 1),
            data.get("repeatable", False)
        )
        quest.completed = data.get("completed", False)
        quest.active = data.get("active", False)
        return quest


class QuestManager:
    """Менеджер всех квестов: сюжетных, побочных, цепочек."""
    def __init__(self, game):
        self.game = game
        self.all_quests: Dict[str, Quest] = {}
        self.active_quests: List[Quest] = []
        self.completed_quests: List[str] = []
        self.side_quests_available: List[str] = []
        self.quest_chains: Dict[str, List[str]] = {}
        self.event_listeners: List[Callable] = []
        self._init_quests_from_data()
        self._init_quest_chains()

    def _init_quests_from_data(self):
        """Загружает все побочные квесты из данных."""
        for quest_data in SIDE_QUESTS:
            objectives = []
            for obj_data in quest_data.get("objectives", []):
                obj = QuestObjective(
                    obj_data.get("type", "custom"),
                    obj_data.get("target", ""),
                    obj_data.get("count", 1),
                    obj_data.get("duration", 0),
                    obj_data.get("description", "")
                )
                objectives.append(obj)
            quest = Quest(
                quest_id=quest_data["id"],
                title=quest_data["name"],
                description=quest_data.get("description", ""),
                objectives=objectives,
                reward=quest_data.get("reward", {}),
                chapter_available=quest_data.get("chapter_available", 1),
                repeatable=quest_data.get("repeatable", False)
            )
            self.all_quests[quest.id] = quest
            if quest.chapter_available <= 1:
                self.side_quests_available.append(quest.id)

    def _init_quest_chains(self):
        """Инициализирует квестовые цепочки из QUEST_CHAINS."""
        for chain_id, chain_data in QUEST_CHAINS.items():
            quest_ids = []
            for quest_data in chain_data.get("quests", []):
                objectives = []
                for obj_data in quest_data.get("objectives", []):
                    obj = QuestObjective(
                        obj_data.get("type", "custom"),
                        obj_data.get("target", ""),
                        obj_data.get("count", 1),
                        obj_data.get("duration", 0),
                        obj_data.get("description", "")
                    )
                    objectives.append(obj)
                quest = Quest(
                    quest_id=quest_data["id"],
                    title=quest_data["title"],
                    description=quest_data.get("description", ""),
                    objectives=objectives,
                    reward=quest_data.get("reward", {}),
                )
                self.all_quests[quest.id] = quest
                quest_ids.append(quest.id)
            self.quest_chains[chain_id] = quest_ids

    def update(self, dt: float):
        """Обновляет все активные квесты."""
        for quest in self.active_quests[:]:
            quest.update(dt, self.game)
            if quest.completed:
                self._on_quest_completed(quest)

    def _on_quest_completed(self, quest: Quest):
        """Обрабатывает завершение квеста."""
        if quest.id not in self.completed_quests:
            self.completed_quests.append(quest.id)
        self.active_quests.remove(quest)
        # Выдача награды
        self._grant_reward(quest.reward)
        self.game.ui.show_notification(f"Квест выполнен: {quest.title}", GREEN, 3.0)
        self.game.sound_manager.play("achievement")
        # Проверяем цепочки
        self._check_chain_progress(quest.id)

    def _grant_reward(self, reward: dict):
        """Выдаёт награду за квест."""
        if not reward:
            return
        if "flag" in reward:
            self.game.story_manager.set_flag(reward["flag"])
        if "item" in reward:
            self.game.pickups.append(Pickup(self.game.player.x, self.game.player.y, reward["item"]))
        if "weapon_upgrade" in reward:
            self.game.player.upgrade_weapon(self.game.player.current_weapon)
        if "exp" in reward:
            self.game.player.add_exp(reward["exp"])
        if "score" in reward:
            self.game.score += reward["score"]
        if "reputation" in reward:
            for faction, amount in reward["reputation"].items():
                self.game.story_manager.change_reputation(faction, amount)

    def _check_chain_progress(self, completed_quest_id: str):
        """Проверяет и запускает следующие квесты в цепочке."""
        for chain_id, quest_ids in self.quest_chains.items():
            if completed_quest_id in quest_ids:
                index = quest_ids.index(completed_quest_id)
                if index + 1 < len(quest_ids):
                    next_quest_id = quest_ids[index + 1]
                    self.start_quest(next_quest_id)

    def start_quest(self, quest_id: str) -> bool:
        """Запускает квест по ID."""
        if quest_id not in self.all_quests:
            return False
        quest = self.all_quests[quest_id]
        if quest.completed and not quest.repeatable:
            return False
        if not quest.active:
            quest.activate()
            self.active_quests.append(quest)
            self.game.ui.show_notification(f"Новое задание: {quest.title}", CYAN, 3.0)
            self.game.sound_manager.play("quest")
            return True
        return False

    def start_quest_chain(self, chain_id: str):
        """Запускает первый квест в цепочке."""
        if chain_id in self.quest_chains and self.quest_chains[chain_id]:
            self.start_quest(self.quest_chains[chain_id][0])

    def complete_quest_manually(self, quest_id: str):
        """Вручную завершает квест (для отладки или особых сюжетных моментов)."""
        if quest_id in self.all_quests:
            quest = self.all_quests[quest_id]
            if quest.active:
                quest.completed = True
                self._on_quest_completed(quest)

    def handle_game_event(self, event_type: str, value: int = 1, target: str = None):
        """Передаёт игровое событие (убийство, сбор и т.д.) всем активным квестам."""
        for quest in self.active_quests[:]:
            if quest.handle_event(event_type, value, target):
                self._on_quest_completed(quest)

    def get_active_quests(self) -> List[Quest]:
        """Возвращает список активных квестов."""
        return self.active_quests

    def get_completed_quests(self) -> List[str]:
        """Возвращает список выполненных квестов."""
        return self.completed_quests

    def get_quest_by_id(self, quest_id: str) -> Optional[Quest]:
        """Возвращает квест по ID."""
        return self.all_quests.get(quest_id)

    def get_available_side_quests(self) -> List[str]:
        """Возвращает доступные побочные квесты с учётом главы."""
        available = []
        current_chapter = self.game.story_manager.current_chapter_id
        for quest_id in self.side_quests_available:
            quest = self.all_quests.get(quest_id)
            if quest and quest.chapter_available <= current_chapter and not quest.completed:
                available.append(quest_id)
        return available

    def get_quest_progress_text(self, quest_id: str) -> List[str]:
        """Возвращает текст целей квеста для UI."""
        quest = self.get_quest_by_id(quest_id)
        if not quest:
            return []
        return quest.get_objectives_text()

    def get_total_progress(self) -> float:
        """Возвращает общий прогресс по всем активным квестам."""
        if not self.active_quests:
            return 1.0
        return sum(q.get_progress_ratio() for q in self.active_quests) / len(self.active_quests)

    def save_quests(self) -> dict:
        """Сохраняет состояние всех квестов."""
        return {
            "completed_quests": self.completed_quests,
            "active_quests": [q.id for q in self.active_quests],
            "side_quests_available": self.side_quests_available,
        }

    def load_quests(self, data: dict):
        """Загружает состояние квестов."""
        self.completed_quests = data.get("completed_quests", [])
        active_ids = data.get("active_quests", [])
        self.active_quests = []
        for qid in active_ids:
            quest = self.get_quest_by_id(qid)
            if quest:
                quest.activate()
                self.active_quests.append(quest)
        self.side_quests_available = data.get("side_quests_available", [])

    def register_event_listener(self, callback: Callable):
        """Регистрирует функцию, вызываемую при событиях квестов."""
        self.event_listeners.append(callback)

    def _notify_listeners(self, event_type: str, quest_id: str):
        """Уведомляет слушателей о событии квеста."""
        for listener in self.event_listeners:
            listener(event_type, quest_id)

    def debug_print_quests(self):
        """Выводит все квесты в консоль для отладки."""
        print("=== КВЕСТЫ ===")
        print(f"Всего квестов: {len(self.all_quests)}")
        print(f"Активных: {len(self.active_quests)}")
        print(f"Выполнено: {len(self.completed_quests)}")
        for quest in self.active_quests:
            print(f"- {quest.title} ({quest.get_progress_ratio():.0%})")
            for text in quest.get_objectives_text():
                print(f"  {text}")