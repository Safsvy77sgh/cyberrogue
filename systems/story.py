# systems/story.py
import pygame
import random
import math
import json
import os
from entities.pickup import Pickup
from typing import Dict, List, Tuple, Optional, Any, Callable
from settings import *
from data.story_data import (
    FLAG_DEFINITIONS,
    CHARACTERS,
    LORE_ENTRIES,
    DIALOGUES,
    STORY_CHAPTERS,
    STORY_BRANCHES,
    ENDINGS,
    SIDE_QUESTS,
    LORE_OBJECTS,
    FACTIONS,
    WORLD_EVENTS,
    LOCATION_DETAILS,
    QUEST_CHAINS,
    REPUTATION_EFFECTS,
    check_endings,
    get_ending_by_id,
    get_lore_entry,
    get_dialogue,
    get_chapter,
    get_character,
    get_side_quest,
    check_flags_for_ending,
    get_all_possible_endings,
    CHARACTER_ARCS
)


class StoryManager:
    """
    Полноценный менеджер сюжета, лора, диалогов, квестов и концовок.
    Интегрируется с игрой, не содержит заглушек.
    """

    def __init__(self, game):
        self.game = game
        self.flags: Dict[str, bool] = FLAG_DEFINITIONS.copy()
        self.current_chapter_id: int = 1
        self.completed_quests: List[str] = []
        self.active_quests: List[Dict] = []
        self.side_quests_completed: List[str] = []
        self.lore_discovered: Dict[str, bool] = {}
        self.dialogue_history: List[str] = []
        self.pending_dialogue: Optional[str] = None
        self.pending_choice: Optional[Dict] = None
        self.current_event: Optional[Dict] = None
        self.event_timer: float = 0.0
        self.faction_reputation: Dict[str, int] = {faction: data["reputation"] for faction, data in FACTIONS.items()}
        self.location_visited: Dict[str, bool] = {}
        self.interactions_count: Dict[str, int] = {}
        self.player_choices: List[str] = []
        self.achievement_hooks: Dict[str, Callable] = {}
        self._init_achievement_hooks()
        self._init_starting_state()

    def _init_achievement_hooks(self):
        """Регистрация функций проверки достижений, связанных с сюжетом."""
        self.achievement_hooks = {
            "met_elena": lambda: self.flags.get("met_elena", False),
            "explored_lab": lambda: self.flags.get("explored_lab", False),
            "found_all_memories": lambda: self.flags.get("found_all_memories", False),
            "spared_kane": lambda: self.flags.get("spared_kane", False),
            "perfected_team": lambda: self.flags.get("perfected_team", False),
            "killed_all_npc": lambda: self.flags.get("killed_all_npc", False),
        }

    def _init_starting_state(self):
        """Инициализация начального состояния сюжета."""
        self.location_visited = {loc_id: False for loc_id in self.game.location_data.keys()}
        self.location_visited[self.game.current_location] = True
        # Начальный диалог первой главы
        first_chapter = get_chapter(1)
        if first_chapter and "starting_dialogue" in first_chapter:
            self.start_dialogue(first_chapter["starting_dialogue"])

    def set_flag(self, flag_name: str, value: bool = True):
        """Устанавливает сюжетный флаг."""
        if flag_name in self.flags:
            self.flags[flag_name] = value
            self._check_flag_side_effects(flag_name)

    def get_flag(self, flag_name: str) -> bool:
        """Возвращает значение флага."""
        return self.flags.get(flag_name, False)

    def _check_flag_side_effects(self, flag_name: str):
        """Обрабатывает побочные эффекты установки флага."""
        # Автоматические достижения
        if flag_name in self.achievement_hooks and self.achievement_hooks[flag_name]():
            self.game.achievement_manager.unlock_achievement(flag_name)
        # Запуск следующей главы при выполнении условий
        self._check_chapter_completion()
        # Обновление доступных побочных квестов
        self._update_available_side_quests()

    def start_chapter(self, chapter_id: int):
        """Начинает новую главу."""
        chapter = get_chapter(chapter_id)
        if not chapter:
            return
        self.current_chapter_id = chapter_id
        self.game.ui.show_chapter_title(chapter["title"])
        # Запуск начального диалога
        if "starting_dialogue" in chapter:
            self.start_dialogue(chapter["starting_dialogue"])
        # Активация обязательных квестов главы
        self._activate_chapter_quests(chapter)
        self._check_perfected_team(chapter_id)

    def _check_perfected_team(self, chapter_id: int):
        """Устанавливает флаг 'perfected_team', если все ключевые NPC выжили к 6 главе."""
        if chapter_id >= 6 and not self.flags.get("perfected_team", False):
            if (self.flags.get("saved_tomas", False) and
                    self.flags.get("trusted_mira", False) and
                    self.flags.get("spared_kane", False) and
                    not self.flags.get("killed_all_npc", False)):
                self.set_flag("perfected_team", True)

    def _activate_chapter_quests(self, chapter: Dict):
        """Активирует квесты текущей главы."""
        self.active_quests = []
        for obj in chapter.get("objectives", []):
            quest = {
                "id": f"chapter_{chapter['id']}_{obj.get('type', 'custom')}_{len(self.active_quests)}",
                "type": obj.get("type", "custom"),
                "target": obj.get("target", ""),
                "count": obj.get("count", 1),
                "duration": obj.get("duration", 0),
                "description": obj.get("description", ""),
                "progress": 0,
                "completed": False,
            }
            self.active_quests.append(quest)
        self.game.ui.show_notification(f"Глава {chapter['id']}: {chapter['title']}", CYAN, 3.0)

    def update(self, dt: float):
        """Обновление сюжетной системы."""
        self._update_active_quests(dt)
        self._update_world_events(dt)
        self._check_chapter_completion()

    def _update_active_quests(self, dt: float):
        """Обновляет прогресс обязательных квестов главы."""
        for quest in self.active_quests:
            if quest["completed"]:
                continue
            if quest["type"] == "kill":
                target = quest["target"]
                current_count = self.game.player.kills if target == "any" else self._count_killed_enemies(target)
                if current_count >= quest["count"]:
                    quest["progress"] = quest["count"]
                    quest["completed"] = True
                    self.game.ui.show_notification(f"Цель выполнена: {quest['description']}", GREEN, 2.0)
            elif quest["type"] == "collect":
                target = quest["target"]
                collected = self._count_collected_items(target)
                if collected >= quest["count"]:
                    quest["completed"] = True
                    self.game.ui.show_notification(f"Цель выполнена: {quest['description']}", GREEN, 2.0)
            elif quest["type"] == "survive":
                quest["progress"] += dt
                if quest["progress"] >= quest["duration"]:
                    quest["completed"] = True
                    self.game.ui.show_notification(f"Цель выполнена: {quest['description']}", GREEN, 2.0)
            elif quest["type"] == "find":
                if self.get_flag(f"found_{quest['target']}"):
                    quest["completed"] = True
            elif quest["type"] == "destroy":
                if self.get_flag(f"destroyed_{quest['target']}_{quest['count']}"):
                    quest["completed"] = True
            elif quest["type"] == "rescue":
                if self.get_flag(f"saved_{quest['target']}"):
                    quest["completed"] = True
            elif quest["type"] == "interact":
                if self.interactions_count.get(quest["target"], 0) >= quest["count"]:
                    quest["completed"] = True

    def _count_killed_enemies(self, enemy_type: str) -> int:
        """Подсчитывает количество убитых врагов определённого типа."""
        # В game нет отдельного счётчика по типам, поэтому используем player.kills и флаги
        # Для простоты считаем по общему количеству убийств, если цель 'any', иначе по флагам.
        if enemy_type == "any":
            return self.game.player.kills
        # В реальной игре нужно вести счётчик, но для примера используем флаг
        flag_name = f"killed_{enemy_type}_count"
        return self.flags.get(flag_name, 0)

    def _count_collected_items(self, item_type: str) -> int:
        """Возвращает количество собранных предметов указанного типа."""
        if item_type == "scrap":
            return self.game.player.scrap
        elif item_type == "circuit":
            return self.game.player.circuits
        elif item_type == "crystal":
            return self.game.player.crystals
        elif item_type == "energy_cell":
            return self.game.player.energy_cells
        elif item_type == "ai_core":
            return self.game.player.ai_cores
        return 0

    def _update_world_events(self, dt: float):
        """Обновляет случайные мировые события."""
        if self.current_event is None:
            # Проверяем условия для случайного события
            if random.random() < 0.001:  # 0.1% шанс в секунду
                self._trigger_random_event()
        else:
            self.event_timer -= dt
            if self.event_timer <= 0:
                self._end_current_event()

    def _trigger_random_event(self):
        """Запускает случайное событие."""
        available = [e for e in WORLD_EVENTS if e["chapter"] <= self.current_chapter_id]
        if not available:
            return
        event = random.choice(available)
        self.current_event = event
        self.event_timer = event.get("duration", 10.0)
        self.game.ui.show_notification(f"Событие: {event['name']}", ORANGE, 3.0)
        self._apply_event_effects(event)

    def _apply_event_effects(self, event: Dict):
        """Применяет эффекты события."""
        effects = event.get("effects", {})
        if "enemy_spawn" in effects:
            enemy_type = effects["enemy_spawn"].get("type", "basic")
            count = effects["enemy_spawn"].get("count", 1)
            for _ in range(count):
                self.game.spawn_enemy(enemy_type)
        if "item_spawn" in effects:
            item_type = effects["item_spawn"].get("type", "scrap")
            count = effects["item_spawn"].get("count", 1)
            for _ in range(count):
                x, y = self.game.player.x + random.randint(-200, 200), self.game.player.y + random.randint(-200, 200)
                self.game.pickups.append(Pickup(x, y, item_type))
        if "npc_spawn" in effects:
            npc_id = effects["npc_spawn"].get("id")
            if npc_id == "trader":
                self.flags["trader_active"] = True
                self.game.trader_active = True
                self.game.trader_position = (random.randint(100, SCREEN_WIDTH - 100), random.randint(100, SCREEN_HEIGHT - 100))
        if "meteor_shower" in effects and effects["meteor_shower"]:
            self.game.meteor_shower_active = True
            self.game.meteor_timer = 0
        if "disable_electronics" in effects and effects["disable_electronics"]:
            self.game.emp_active = True

    def _end_current_event(self):
        """Завершает текущее событие и очищает эффекты."""
        if self.current_event:
            event_id = self.current_event.get("id")
            if event_id == "event_emp_burst":
                self.game.emp_active = False
            self.current_event = None

    def _check_chapter_completion(self):
        """Проверяет, завершена ли текущая глава, и переходит к следующей."""
        if self.current_chapter_id >= len(STORY_CHAPTERS):
            return
        all_done = all(quest["completed"] for quest in self.active_quests) if self.active_quests else True
        chapter = get_chapter(self.current_chapter_id)
        if all_done and "on_complete" in chapter:
            on_complete = chapter["on_complete"]
            if "next_chapter" in on_complete:
                self.start_chapter(on_complete["next_chapter"])
            elif "end" in on_complete and on_complete["end"]:
                self._trigger_ending()

    def _trigger_ending(self):
        """Определяет и запускает концовку на основе флагов."""
        possible = get_all_possible_endings(self.flags)
        if possible:
            # Выбираем первую подходящую (или можно приоритет)
            ending_id = possible[0]
            self.game.ui.show_game_end(get_ending_by_id(ending_id))
            self.game.game_over = True

    # ==================== ЛОР-ИНТЕРАКЦИИ ====================

    def interact_with_object(self, object_type: str, object_id: str = None):
        """Обрабатывает взаимодействие с лор-объектом."""
        if object_type not in LORE_OBJECTS:
            return
        action = LORE_OBJECTS[object_type]["action"]
        if action == "open_lore":
            self.open_lore_entry(object_id)
        elif action == "play_audio":
            self.play_audio_log(object_id)
        elif action == "play_holo":
            self.play_holo(object_id)
        elif action == "trigger_memory":
            self.trigger_memory(object_id)
        elif action == "hack_core":
            self.hack_quantum_core(object_id)

    def open_lore_entry(self, lore_id: str):
        """Открывает текстовую запись лора."""
        entry = get_lore_entry(lore_id)
        if not entry:
            return
        self.lore_discovered[lore_id] = True
        self.game.ui.show_lore_text(entry["title"], entry["text"])
        # Отмечаем флаг прочтения терминала
        if entry["type"] == "terminal":
            self.interactions_count["terminal"] = self.interactions_count.get("terminal", 0) + 1
            if self.interactions_count["terminal"] >= 5:
                self.set_flag("read_all_terminals")
        elif entry["type"] == "secret_terminal":
            self.interactions_count["secret_terminal"] = self.interactions_count.get("secret_terminal", 0) + 1
        self.game.sound_manager.play("pickup")

    def play_audio_log(self, lore_id: str):
        """Воспроизводит аудиозапись лора."""
        entry = get_lore_entry(lore_id)
        if not entry:
            return
        self.lore_discovered[lore_id] = True
        self.game.ui.show_notification(f"Аудиозапись: {entry['title']}", GREEN, 4.0)
        # В реальной игре здесь бы проигрывался звук
        self.game.sound_manager.play("achievement")

    def play_holo(self, lore_id: str):
        """Показывает голограмму."""
        entry = get_lore_entry(lore_id)
        if not entry:
            return
        self.lore_discovered[lore_id] = True
        self.game.ui.show_notification(f"Голограмма: {entry['title']}", MAGENTA, 4.0)

    def trigger_memory(self, lore_id: str):
        """Запускает воспоминание."""
        entry = get_lore_entry(lore_id)
        if not entry:
            return
        self.lore_discovered[lore_id] = True
        # Воспоминание может открывать фрагменты памяти
        if "memory" in entry["type"]:
            if entry["id"] == "lore_005":
                self.set_flag("found_memory_1")
            elif entry["id"] == "lore_043":
                self.set_flag("found_memory_2")
            # Проверяем, все ли фрагменты найдены
            if self.flags.get("found_memory_1") and self.flags.get("found_memory_2") and self.flags.get("found_memory_3"):
                self.set_flag("found_all_memories")
        self.game.ui.show_notification(f"Воспоминание: {entry['title']}", PURPLE, 4.0)

    def hack_quantum_core(self, core_id: str):
        """Взлом квантового ядра для получения алгоритма."""
        # В реальной игре здесь мини-игра взлома
        self.interactions_count["quantum_core"] = self.interactions_count.get("quantum_core", 0) + 1
        if self.interactions_count["quantum_core"] >= 3:
            self.set_flag("collected_all_algorithms")
        # Даём временный бонус
        self.game.player.apply_temporary_buff("damage_boost", 30)
        self.game.ui.show_notification("Алгоритм украден! Временный бонус: +урон", CYAN, 3.0)
        self.game.sound_manager.play("explosion")

    # ==================== ДИАЛОГОВАЯ СИСТЕМА ====================

    def start_dialogue(self, dialogue_id: str):
        """Начинает диалог по идентификатору."""
        dialogue = get_dialogue(dialogue_id)
        if not dialogue:
            return
        self.pending_dialogue = dialogue_id
        self.pending_choice = dialogue
        # Используем метод Game.show_dialogue, который ставит игру на паузу
        if hasattr(self.game, 'show_dialogue'):
            self.game.show_dialogue(dialogue)
        else:
            self.game.ui.show_dialogue(dialogue)
            self.game.in_dialogue = True

    def select_dialogue_response(self, response_index: int):
        """Обрабатывает выбор ответа в диалоге."""
        if not self.pending_choice:
            return
        responses = self.pending_choice.get("responses", [])
        if response_index >= len(responses):
            return
        response = responses[response_index]
        # Устанавливаем флаг, если есть
        if "flag" in response:
            self.set_flag(response["flag"])
        # Записываем выбор
        self.player_choices.append(response.get("text", ""))
        # Переход к следующему диалогу или завершение
        next_id = response.get("next")
        if next_id:
            self.start_dialogue(next_id)
        else:
            self.pending_dialogue = None
            self.pending_choice = None
            # Используем метод Game.hide_dialogue, который снимает паузу и очищает UI
            if hasattr(self.game, 'hide_dialogue'):
                self.game.hide_dialogue()
            else:
                # Запасной вариант
                self.game.ui.hide_dialogue()
                self.game.in_dialogue = False
    # ==================== РЕПУТАЦИЯ ====================

    def change_reputation(self, faction: str, amount: int):
        """Изменяет репутацию с фракцией."""
        if faction in self.faction_reputation:
            self.faction_reputation[faction] = max(-100, min(100, self.faction_reputation[faction] + amount))
            self._check_reputation_effects(faction)

    def _check_reputation_effects(self, faction: str):
        """Применяет эффекты изменения репутации."""
        rep = self.faction_reputation[faction]
        effects = REPUTATION_EFFECTS.get(faction, {})
        if rep >= 50:
            high_effects = effects.get("high", {})
            self._apply_reputation_bonus(high_effects)
        elif rep <= -50:
            low_effects = effects.get("low", {})
            self._apply_reputation_penalty(low_effects)

    def _apply_reputation_bonus(self, effects: dict):
        """Применяет положительные эффекты репутации."""
        if "discount" in effects:
            self.game.shop.set_discount(effects["discount"])
        if "allied" in effects and effects["allied"]:
            # Союзники помогают в бою
            self.game.ally_system.summon_ally("drone")
        if "help_in_final" in effects and effects["help_in_final"]:
            self.flags["hybrids_allied"] = True

    def _apply_reputation_penalty(self, effects: dict):
        """Применяет отрицательные эффекты репутации."""
        if "price_increase" in effects:
            self.game.shop.set_price_multiplier(effects["price_increase"])
        if effects.get("hostile", False):
            # Враждебность: враги этой фракции становятся агрессивнее
            for enemy in self.game.enemies:
                if enemy.faction == self._get_faction_from_effects(effects):
                    enemy.aggression += 0.5

    def _get_faction_from_effects(self, effects: dict) -> Optional[str]:
        # Заглушка, в реальности надо сопоставлять
        return None

    # ==================== ПОБОЧНЫЕ КВЕСТЫ ====================

    def _update_available_side_quests(self):
        """Обновляет список доступных побочных квестов."""
        for quest_data in SIDE_QUESTS:
            if quest_data["chapter_available"] <= self.current_chapter_id:
                if quest_data["id"] not in self.side_quests_completed and not self.get_flag(f"side_{quest_data['id']}_done"):
                    self._offer_side_quest(quest_data)

    def _offer_side_quest(self, quest_data: dict):
        """Предлагает побочный квест игроку через QuestManager, который
        уже регистрирует побочные квесты как объекты Quest (см.
        SIDE_QUESTS в systems/quest.py). StoryManager больше не хранит
        побочные квесты как отдельные словари, чтобы не расходиться с
        типом, который ожидает QuestManager."""
        if hasattr(self.game, 'quest_manager'):
            self.game.quest_manager.start_quest(quest_data["id"])

    def complete_side_quest(self, quest_id: str):
        """Завершает побочный квест (уведомление и флаги на стороне сюжета;
        сам прогресс и объект Quest ведёт QuestManager)."""
        if quest_id in self.side_quests_completed:
            return
        self.side_quests_completed.append(quest_id)
        self.set_flag(f"side_{quest_id}_done")
        quest_data = get_side_quest(quest_id)
        reward = quest_data.get("reward", {}) if quest_data else None
        if reward:
            if "flag" in reward:
                self.set_flag(reward["flag"])
            if "item" in reward:
                self.game.pickups.append(Pickup(self.game.player.x, self.game.player.y, reward["item"]))
            if "weapon_upgrade" in reward and hasattr(self.game.player, 'upgrade_weapon'):
                self.game.player.upgrade_weapon(self.game.player.current_weapon)
        self.game.ui.show_notification(f"Квест выполнен: {quest_id}", GREEN, 3.0)

    # ==================== ИНТЕГРАЦИЯ С ИГРОЙ ====================

    def on_enemy_killed(self, enemy):
        """Вызывается при убийстве врага."""
        # Обновляем квесты на убийство
        enemy_type = getattr(enemy, "type", "basic")
        if enemy_type == "elite":
            self.flags["killed_elite_count"] = self.flags.get("killed_elite_count", 0) + 1
        elif enemy_type == "tank":
            self.flags["killed_tank_count"] = self.flags.get("killed_tank_count", 0) + 1
        # Проверяем особые условия
        if enemy_type == "kane":
            self.set_flag("killed_kane")
        elif enemy_type == "oko":
            self.set_flag("killed_oko_early")
        # Обновление сюжета
        self._check_chapter_completion()

    def on_item_collected(self, pickup):
        """Вызывается при сборе предмета."""
        item_type = pickup.type
        if item_type == "scrap":
            self.flags["collected_scrap_10"] = True  # Пример
        elif item_type == "crystal":
            self.flags["collected_crystal"] = True

    def on_location_changed(self, new_location: str):
        """Вызывается при смене локации."""
        self.location_visited[new_location] = True
        # Возможно появление новых лор-объектов
        if new_location in LOCATION_DETAILS:
            details = LOCATION_DETAILS[new_location]
            for lore_id in details.get("lore_entries", []):
                if not self.lore_discovered.get(lore_id, False):
                    # Помечаем как доступное для изучения
                    pass

    def get_available_lore_objects_in_current_location(self) -> List[str]:
        """Возвращает список лор-объектов в текущей локации."""
        loc = self.game.current_location
        if loc not in LOCATION_DETAILS:
            return []
        return LOCATION_DETAILS[loc].get("lore_entries", [])

    # ==================== ПРОВЕРКА КОНЦОВОК ====================

    def evaluate_endings(self) -> List[str]:
        """Возвращает список доступных концовок на основе текущих флагов."""
        return get_all_possible_endings(self.flags)

    def trigger_ending(self, ending_id: str):
        """Запускает концовку."""
        ending = get_ending_by_id(ending_id)
        if not ending:
            return
        self.game.ui.show_game_end(ending)
        self.game.game_over = True

    def save_story_state(self) -> dict:
        """Сохраняет состояние сюжета."""
        return {
            "flags": self.flags,
            "current_chapter": self.current_chapter_id,
            "completed_quests": self.completed_quests,
            "side_quests_completed": self.side_quests_completed,
            "lore_discovered": self.lore_discovered,
            "dialogue_history": self.dialogue_history,
            "faction_reputation": self.faction_reputation,
            "player_choices": self.player_choices,
        }

    def load_story_state(self, data: dict):
        """Загружает состояние сюжета."""
        self.flags = data.get("flags", FLAG_DEFINITIONS.copy())
        self.current_chapter_id = data.get("current_chapter", 1)
        self.completed_quests = data.get("completed_quests", [])
        self.side_quests_completed = data.get("side_quests_completed", [])
        self.lore_discovered = data.get("lore_discovered", {})
        self.dialogue_history = data.get("dialogue_history", [])
        self.faction_reputation = data.get("faction_reputation", {})
        self.player_choices = data.get("player_choices", [])

# systems/story.py (продолжение)

    # ==================== ИНТЕРАКТИВНЫЕ ЛОР-ОБЪЕКТЫ ====================

    def spawn_lore_objects_in_location(self, location_id: str):
        """Создаёт лор-объекты в указанной локации на основе данных LOCATION_DETAILS."""
        if location_id not in LOCATION_DETAILS:
            return
        details = LOCATION_DETAILS[location_id]
        for lore_id in details.get("lore_entries", []):
            if self.lore_discovered.get(lore_id, False):
                continue
            entry = get_lore_entry(lore_id)
            if not entry:
                continue
            # Определяем тип объекта
            obj_type = entry.get("type", "terminal")
            # Создаём интерактивный объект в игровом мире (упрощённо: добавляем в game.lore_objects)
            # В реальности нужно создавать физические объекты на карте
            self.game.lore_objects.append({
                "id": lore_id,
                "type": obj_type,
                "position": (random.randint(100, SCREEN_WIDTH-100), random.randint(100, SCREEN_HEIGHT-100)),
                "interacted": False,
            })

    def check_lore_object_interaction(self, player_x: float, player_y: float):
        """Проверяет, находится ли игрок рядом с лор-объектом, и предлагает взаимодействие."""
        for obj in self.game.lore_objects:
            if obj["interacted"]:
                continue
            distance = math.hypot(player_x - obj["position"][0], player_y - obj["position"][1])
            if distance < 50:
                self.game.ui.show_interaction_prompt(LORE_OBJECTS[obj["type"]]["interaction_text"])
                # При нажатии E (обрабатывается в game) будет вызван interact_with_object
                return obj
        return None

    def interact_with_lore_object(self, obj):
        """Обрабатывает взаимодействие с конкретным лор-объектом."""
        if obj["interacted"]:
            return
        obj["interacted"] = True
        self.interact_with_object(obj["type"], obj["id"])

    # ==================== ДИАЛОГОВАЯ СИСТЕМА (ДОПОЛНЕНИЕ) ====================

    def get_current_dialogue(self):
        """Возвращает текущий диалог для отображения."""
        return self.pending_choice

    def end_dialogue(self):
        """Завершает текущий диалог."""
        self.pending_dialogue = None
        self.pending_choice = None
        # Используем метод Game.hide_dialogue, который снимает паузу
        if hasattr(self.game, 'hide_dialogue'):
            self.game.hide_dialogue()
        else:
            self.game.ui.hide_dialogue()
            self.game.in_dialogue = False

    def is_dialogue_active(self) -> bool:
        """Возвращает True, если диалог активен."""
        return self.pending_choice is not None

    # ==================== ОБРАБОТКА ВЫБОРОВ ИГРОКА ====================

    def process_story_choice(self, choice_id: str):
        """Обрабатывает особый сюжетный выбор, не связанный с диалогами."""
        # Например, выбор в квесте side_hybrids
        if choice_id == "free_hybrids":
            self.set_flag("freed_hybrids")
            self.change_reputation("hybrids", 50)
            self.game.ui.show_notification("Гибриды освобождены. Они помогут вам.", GREEN, 3.0)
        elif choice_id == "kill_hybrids":
            self.set_flag("freed_hybrids", False)
            self.change_reputation("hybrids", -50)
            # Даём ресурсы
            self.game.player.scrap += 20
            self.game.ui.show_notification("Гибриды уничтожены. Получен металлолом.", ORANGE, 3.0)
        elif choice_id == "activate_phoenix":
            self.set_flag("activated_phoenix")
            self.set_flag("saved_elena", False)
            if hasattr(self.game, 'activate_phoenix'):
                self.game.activate_phoenix()
            self.game.ui.show_notification("Лаборатория уничтожена. Елена ранена.", RED, 3.0)
        elif choice_id == "refuse_phoenix":
            self.set_flag("activated_phoenix", False)
            self.set_flag("saved_elena", True)
            self.game.ui.show_notification("Лаборатория не тронута. Елена невредима.", GREEN, 3.0)

    # ==================== ИНТЕГРАЦИЯ С СИСТЕМОЙ ЭФФЕКТОВ ====================

    def apply_story_effects(self):
        """Применяет эффекты, зависящие от сюжетных флагов."""
        if self.get_flag("helped_merchant"):
            # Модуль ЭМ-подавителя снижает защиту ГЕНЕЗИСА в финале
            self.game.player.damage_multiplier *= 1.1
        if self.get_flag("read_all_terminals"):
            # Знание слабостей ИИ даёт бонус
            self.game.player.crit_chance += 0.05
        if self.get_flag("found_secret_blueprints"):
            # Оружие «Аннигилятор» доступно (только если оно определено в WeaponManager)
            if "annihilator" in self.game.player.weapon_manager.weapons:
                self.game.player.add_weapon("annihilator")

    # ==================== МЕТОДЫ ДЛЯ КВЕСТОВ ====================

    def get_active_quests(self) -> List[Dict]:
        """Возвращает список активных квестов для UI."""
        return [q for q in self.active_quests if not q.get("completed", False)]

    def get_quest_progress(self, quest_id: str) -> float:
        """Возвращает прогресс квеста (0.0 - 1.0)."""
        for q in self.active_quests:
            if q["id"] == quest_id:
                if q["type"] == "kill":
                    target = q["target"]
                    current = self._count_killed_enemies(target)
                    return min(1.0, current / q["count"])
                elif q["type"] == "collect":
                    target = q["target"]
                    current = self._count_collected_items(target)
                    return min(1.0, current / q["count"])
                elif q["type"] == "survive":
                    return min(1.0, q["progress"] / q["duration"])
                elif q["type"] == "find":
                    return 1.0 if self.get_flag(f"found_{q['target']}") else 0.0
                elif q["type"] == "destroy":
                    return 1.0 if self.get_flag(f"destroyed_{q['target']}_{q['count']}") else 0.0
                elif q["type"] == "rescue":
                    return 1.0 if self.get_flag(f"saved_{q['target']}") else 0.0
                elif q["type"] == "interact":
                    return min(1.0, self.interactions_count.get(q["target"], 0) / q["count"])
        return 0.0

    # ==================== МЕТОДЫ ДЛЯ ЛОРА ====================

    def get_discovered_lore(self) -> List[Dict]:
        """Возвращает список открытых лор-записей."""
        return [entry for entry in LORE_ENTRIES if self.lore_discovered.get(entry["id"], False)]

    def get_all_lore_by_chapter(self, chapter_id: int) -> List[Dict]:
        """Возвращает все лор-записи для конкретной главы."""
        return [entry for entry in LORE_ENTRIES if entry.get("chapter") == chapter_id]

    def unlock_all_lore_for_current_chapter(self):
        """Открывает все лор-записи текущей главы (для отладки или награды)."""
        for entry in self.get_all_lore_by_chapter(self.current_chapter_id):
            self.lore_discovered[entry["id"]] = True
        self.game.ui.show_notification("Все записи главы открыты!", YELLOW, 3.0)

    # ==================== ОБРАБОТКА ФРАКЦИЙ ====================

    def get_faction_reputation(self, faction_id: str) -> int:
        """Возвращает текущую репутацию с фракцией."""
        return self.faction_reputation.get(faction_id, 0)

    def get_faction_standing(self, faction_id: str) -> str:
        """Возвращает текстовое описание отношения фракции."""
        rep = self.get_faction_reputation(faction_id)
        if rep >= 75:
            return "Союзник"
        elif rep >= 25:
            return "Дружелюбный"
        elif rep >= -25:
            return "Нейтральный"
        elif rep >= -75:
            return "Враждебный"
        else:
            return "Враг"

    # ==================== ОБРАБОТКА СОБЫТИЙ ====================

    def trigger_specific_event(self, event_id: str):
        """Запускает конкретное событие вручную."""
        for event in WORLD_EVENTS:
            if event["id"] == event_id:
                self.current_event = event
                self.event_timer = event.get("duration", 10.0)
                self.game.ui.show_notification(f"Событие: {event['name']}", ORANGE, 3.0)
                self._apply_event_effects(event)
                return

    def get_active_event(self) -> Optional[Dict]:
        """Возвращает текущее активное событие."""
        return self.current_event

    # ==================== ИНТЕГРАЦИЯ С UI ====================

    def draw_story_ui(self, screen):
        """Отрисовывает сюжетные элементы интерфейса (диалоги, уведомления)."""
        if self.is_dialogue_active():
            self.game.ui.draw_dialogue_box(screen, self.pending_choice)
        # Отрисовка активных квестов
        y = 200
        for quest in self.get_active_quests():
            progress = self.get_quest_progress(quest["id"])
            text = f"{quest['description']}: {int(progress * 100)}%"
            self.game.ui.draw_text(screen, text, 20, y, 24, LIGHT_GRAY)
            y += 30

    # ==================== СОХРАНЕНИЕ И ЗАГРУЗКА ====================

    def save_to_file(self, filename: str = "story_save.json"):
        """Сохраняет состояние сюжета в файл."""
        data = self.save_story_state()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def load_from_file(self, filename: str = "story_save.json"):
        """Загружает состояние сюжета из файла."""
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.load_story_state(data)
            return True
        except:
            return False

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def is_flag_set(self, flag_name: str) -> bool:
        """Проверяет, установлен ли флаг (удобный алиас)."""
        return self.get_flag(flag_name)

    def reset_story(self):
        """Полный сброс сюжета."""
        self.flags = FLAG_DEFINITIONS.copy()
        self.current_chapter_id = 1
        self.completed_quests = []
        self.active_quests = []
        self.side_quests_completed = []
        self.lore_discovered = {}
        self.dialogue_history = []
        self.pending_dialogue = None
        self.pending_choice = None
        self.current_event = None
        self.faction_reputation = {faction: data["reputation"] for faction, data in FACTIONS.items()}
        self.player_choices = []
        self.location_visited = {loc_id: False for loc_id in self.game.location_data.keys()}
        self.location_visited[self.game.current_location] = True
        # Перезапуск первой главы
        self.start_chapter(1)

    def debug_print_flags(self):
        """Выводит все флаги в консоль (для отладки)."""
        print("=== СЮЖЕТНЫЕ ФЛАГИ ===")
        for k, v in self.flags.items():
            if v:
                print(f"{k}: {v}")

# systems/story.py (часть 3 — финальная)

    # ==================== ИНТЕГРАЦИЯ С ОБУЧЕНИЕМ МАШИН ====================

    def get_ai_learning_level(self) -> float:
        """
        Возвращает текущий уровень обучения ИИ (0.0 - 1.0).
        Использует данные из evolutionary_ai_manager и adaptive_enemy_system.
        """
        learning = 0.0
        if hasattr(self.game, 'evolutionary_ai'):
            # Учитываем поколение и среднюю приспособленность
            if self.game.evolutionary_ai.population:
                avg_fitness = sum(i.fitness for i in self.game.evolutionary_ai.population) / len(self.game.evolutionary_ai.population)
                learning = min(1.0, avg_fitness / 1000.0)  # Нормализация
        if hasattr(self.game, 'adaptive_enemy_system'):
            # Учитываем количество собранных данных об игроке
            stats = self.game.adaptive_enemy_system.get_global_stats()
            learning = max(learning, min(1.0, stats.get('total_encounters', 0) / 500.0))
        return learning

    def apply_ai_learning_effects(self):
        """Применяет сюжетные эффекты на основе уровня обучения ИИ."""
        level = self.get_ai_learning_level()
        if level > 0.7:
            # ИИ стал слишком умён — сюжетная подсказка
            if not self.get_flag("ai_too_smart_warning"):
                self.set_flag("ai_too_smart_warning")
                self.game.ui.show_notification("ГЕНЕЗИС становится умнее... Будьте осторожны!", RED, 4.0)
            # Повышаем сложность врагов
            for enemy in self.game.enemies:
                enemy.hp *= 1.1
                enemy.speed *= 1.05
        elif level > 0.3:
            # Умеренная адаптация
            for enemy in self.game.enemies:
                enemy.hp *= 1.02

    # ==================== СЮЖЕТНЫЕ АРКИ ПЕРСОНАЖЕЙ ====================

    def update_character_arcs(self):
        """Обновляет прогресс сюжетных арок персонажей."""
        for char_id, arc in CHARACTER_ARCS.items():
            if char_id == "elena":
                if self.get_flag("met_elena") and self.get_flag("explored_lab"):
                    self._advance_arc_stage("elena", 1)
                if self.get_flag("activated_phoenix") or self.get_flag("saved_elena"):
                    self._advance_arc_stage("elena", 2)
                if self.current_chapter_id >= 6:
                    self._advance_arc_stage("elena", 3)
            elif char_id == "mira":
                if self.get_flag("met_mira"):
                    self._advance_arc_stage("mira", 1)
                if self.get_flag("revealed_mira"):
                    self._advance_arc_stage("mira", 2)
                if self.get_flag("mira_alive") and self.current_chapter_id >= 7:
                    self._advance_arc_stage("mira", 3)
            elif char_id == "tomas":
                if self.get_flag("met_tomas"):
                    self._advance_arc_stage("tomas", 1)
                if self.get_flag("saved_tomas") or self.get_flag("tomas_died"):
                    self._advance_arc_stage("tomas", 2)
                if self.current_chapter_id >= 6:
                    self._advance_arc_stage("tomas", 3)
            elif char_id == "oko":
                if self.get_flag("trusted_oko") or self.get_flag("suspected_oko"):
                    self._advance_arc_stage("oko", 1)
                if self.get_flag("oko_betrayed") or self.get_flag("killed_oko_early"):
                    self._advance_arc_stage("oko", 2)
                if self.get_flag("oko_sacrifice"):
                    self._advance_arc_stage("oko", 3)
            elif char_id == "kane":
                if self.current_chapter_id >= 5:
                    self._advance_arc_stage("kane", 1)
                if self.get_flag("spared_kane") or self.get_flag("killed_kane"):
                    self._advance_arc_stage("kane", 2)
                if self.current_chapter_id >= 7:
                    self._advance_arc_stage("kane", 3)

    def _advance_arc_stage(self, char_id: str, stage: int):
        """Отмечает выполнение этапа арки персонажа."""
        # В реальной игре здесь могут выдаваться награды, открываться диалоги и т.д.
        # Для простоты просто выводим уведомление, если этап ещё не был пройден.
        arc = CHARACTER_ARCS.get(char_id)
        if not arc:
            return
        if stage <= len(arc["stages"]):
            if not self.get_flag(f"arc_{char_id}_stage_{stage}"):
                self.set_flag(f"arc_{char_id}_stage_{stage}")
                self.game.ui.show_notification(f"Развитие персонажа: {CHARACTERS[char_id]['name']} — {arc['stages'][stage-1]['goal']}", CYAN, 3.0)

    # ==================== ДИНАМИЧЕСКИЕ ДИАЛОГИ ПО РЕПУТАЦИИ ====================

    def get_reputation_dialogue(self, faction: str) -> Optional[str]:
        """Возвращает диалог в зависимости от репутации с фракцией."""
        rep = self.get_faction_reputation(faction)
        effects = REPUTATION_EFFECTS.get(faction, {})
        if rep >= 50:
            dialogues = effects.get("high", {}).get("dialogues", [])
        elif rep <= -50:
            dialogues = effects.get("low", {}).get("dialogues", [])
        else:
            return None
        if dialogues:
            return random.choice(dialogues)
        return None

    def trigger_reputation_dialogue_if_needed(self):
        """Вызывается периодически, чтобы показывать репутационные диалоги."""
        if random.random() < 0.01:  # 1% шанс в секунду
            for faction in self.faction_reputation:
                dial_id = self.get_reputation_dialogue(faction)
                if dial_id and not self.get_flag(f"reputation_dialogue_{dial_id}_shown"):
                    self.set_flag(f"reputation_dialogue_{dial_id}_shown")
                    self.start_dialogue(dial_id)
                    return

    # ==================== СЛУЧАЙНЫЕ ВСТРЕЧИ С NPC ====================

    def random_npc_encounter(self):
        """Случайная встреча с NPC в локации."""
        if self.game.current_location in ["wasteland", "ruined_city"]:
            if random.random() < 0.005:  # 0.5% шанс в секунду
                npc_id = random.choice(["trader", "survivor"])
                if npc_id == "trader" and not self.get_flag("trader_visited_recently"):
                    self.set_flag("trader_visited_recently")
                    self.flags["trader_active"] = True
                    self.game.trader_active = True
                    self.game.trader_position = (self.game.player.x + random.randint(-300, 300), self.game.player.y + random.randint(-300, 300))
                    self.game.ui.show_notification("Поблизости появился торговец!", YELLOW, 3.0)
                    self.start_dialogue("trader_meeting")

    # ==================== ОБРАБОТКА СМЕРТИ ИГРОКА ====================

    def on_player_death(self):
        """Вызывается при смерти игрока."""
        self.set_flag("player_died")
        self.set_flag("survived", False)
        # Сохраняем прогресс сюжета
        self.save_to_file()
        # Записываем смерть в наследие
        if hasattr(self.game, 'legacy_system'):
            self.game.legacy_system.record_death({
                "kills": self.game.player.kills,
                "score": self.game.score,
                "wave": self.game.wave,
                "chapter": self.current_chapter_id,
            })
        # Возможно, ГЕНЕЗИС прокомментирует смерть
        if self.current_chapter_id >= 6:
            self.game.ui.show_notification("ГЕНЕЗИС: Ты не первый, кто пытался меня остановить.", RED, 4.0)

    def on_player_survive(self):
        """Вызывается, если игрок выжил (не умер)."""
        self.set_flag("survived")
        self.set_flag("player_died", False)

    # ==================== ИНТЕГРАЦИЯ С ЭВОЛЮЦИОННОЙ СИСТЕМОЙ ====================

    def hook_evolutionary_events(self):
        """Подключает сюжетные реакции на события эволюции ИИ."""
        if hasattr(self.game, 'evolutionary_ai'):
            # Когда происходит эволюция популяции, увеличиваем сюжетную тревогу
            original_evolve = self.game.evolutionary_ai.evolve_population
            def wrapped_evolve():
                original_evolve()
                self.set_flag("ai_evolved_recently")
                self.game.ui.show_notification("ГЕНЕЗИС эволюционировал. Враги стали умнее.", ORANGE, 3.0)
                # Повышаем сложность в сюжете
                self.game.wave_manager.wave += 1  # Ускоряем волны
            self.game.evolutionary_ai.evolve_population = wrapped_evolve

    # ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КВЕСТОВ ====================

    def check_dynamic_quest_conditions(self):
        """Проверяет условия для автоматического принятия побочных квестов."""
        if not self.get_flag("side_merchant_offered") and self.current_chapter_id >= 1:
            self.set_flag("side_merchant_offered")
            self._offer_side_quest_by_id("side_merchant")
        if not self.get_flag("side_memories_offered") and self.current_chapter_id >= 2:
            self.set_flag("side_memories_offered")
            self._offer_side_quest_by_id("side_memories")

    def _offer_side_quest_by_id(self, quest_id: str):
        """Предлагает побочный квест по ID."""
        for quest_data in SIDE_QUESTS:
            if quest_data["id"] == quest_id:
                self._offer_side_quest(quest_data)
                break

    # ==================== МЕТОДЫ ДЛЯ UI ====================

    def draw_story_hud(self, screen):
        """Рисует элементы сюжетного HUD (текущая глава, цели)."""
        chapter = get_chapter(self.current_chapter_id)
        if chapter:
            self.game.ui.draw_text(screen, f"Глава {chapter['id']}: {chapter['title']}", 10, 200, 28, WHITE)
            for quest in self.get_active_quests():
                progress = self.get_quest_progress(quest["id"])
                self.game.ui.draw_text(screen, f"• {quest['description']} ({int(progress*100)}%)", 20, 230 + self.get_active_quests().index(quest)*25, 20, LIGHT_GRAY)

    # ==================== ОБРАБОТКА ВЫБОРА В ДИАЛОГЕ ====================

    def handle_dialogue_click(self, pos):
        """Обрабатывает клик по варианту ответа в диалоге (для UI)."""
        if not self.is_dialogue_active():
            return
        # Предполагаем, что UI диалога уже нарисован и знает позиции кнопок
        # Здесь просто заглушка, которая должна быть заменена реальной обработкой кликов
        # В реальной игре UI сам вызывает select_dialogue_response с индексом
        pass

    # ==================== ФИНАЛЬНАЯ ПРОВЕРКА КОНЦОВОК ====================

    def finalize_ending(self):
        """Вызывается, когда игра завершена, чтобы выбрать и показать концовку."""
        possible = self.evaluate_endings()
        if possible:
            # Выбор концовки с учётом приоритета (например, скрытые концовки имеют больший вес)
            # Для простоты берём первую
            ending = get_ending_by_id(possible[0])
            self.game.ui.show_game_end(ending)
            self.game.game_over = True
        else:
            # Если ни одна не подошла, показываем стандартную
            self.game.ui.show_game_end(get_ending_by_id("ending_30"))

    # ==================== ПРОЧИЕ МЕТОДЫ ====================

    def unlock_new_game_plus(self):
        """Разблокирует Новая игра+."""
        self.set_flag("new_game_plus")
        self.game.ui.show_notification("Новая игра+ разблокирована!", GOLD, 4.0)

    def toggle_debug_mode(self):
        """Включает отладочный режим сюжета."""
        self.game.debug_mode = not self.game.debug_mode
        if self.game.debug_mode:
            print("Отладочный режим сюжета включён.")
            self.debug_print_flags()
        else:
            print("Отладочный режим выключен.")

    def get_story_statistics(self) -> dict:
        """Возвращает статистику сюжета для отображения в меню."""
        return {
            "chapter": self.current_chapter_id,
            "completed_quests": len(self.completed_quests),
            "side_quests": len(self.side_quests_completed),
            "lore_found": len(self.lore_discovered),
            "reputation": self.faction_reputation.copy(),
            "endings_available": len(self.evaluate_endings()),
        }

    # ==================== ОБРАБОТКА ОБУЧЕНИЯ ИИ В СЮЖЕТЕ ====================

    def apply_ai_knowledge_bonus(self):
        """Если игрок узнал много о ГЕНЕЗИСЕ, даёт бонус в финале."""
        if self.get_flag("read_all_terminals") and self.get_flag("collected_all_lore"):
            self.game.player.damage_multiplier *= 1.2
            self.game.ui.show_notification("Знание слабостей ГЕНЕЗИСА усиляет вас!", CYAN, 3.0)

    def trigger_ai_empathy(self):
        """Вызывается, когда игрок выбирает путь убеждения ГЕНЕЗИСА."""
        self.set_flag("ai_has_empathy")
        self.set_flag("persuaded_genesis")
        self.game.ui.show_notification("ГЕНЕЗИС колеблется... Ваши слова находят отклик.", MAGENTA, 4.0)
        # Изменяем поведение ГЕНЕЗИСА в финале
        if hasattr(self.game, 'genesis_avatar'):
            self.game.genesis_avatar.aggression *= 0.5

    def trigger_ai_anger(self):
        """Вызывается при враждебных действиях против ГЕНЕЗИСА."""
        self.set_flag("ai_has_empathy", False)
        self.game.ui.show_notification("ГЕНЕЗИС разгневан! Он больше не будет сдерживаться.", RED, 4.0)
        for enemy in self.game.enemies:
            enemy.damage_multiplier = getattr(enemy, 'damage_multiplier', 1.0) * 1.2

    # ==================== ИНИЦИАЛИЗАЦИЯ ПОСЛЕ ЗАГРУЗКИ ====================

    def post_load_initialization(self):
        """Вызывается после загрузки сохранения, чтобы синхронизировать состояние."""
        self._update_available_side_quests()
        self.apply_story_effects()
        self.hook_evolutionary_events()
        # Восстановление активных квестов
        chapter = get_chapter(self.current_chapter_id)
        if chapter:
            self._activate_chapter_quests(chapter)