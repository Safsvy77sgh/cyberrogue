# systems/achievement.py
from typing import Dict, List, Callable, Optional
from settings import *
import pygame


class Achievement:
    """Достижение"""

    def __init__(self, achievement_id: str, title: str, description: str,
                 condition: Callable, reward: Dict = None, secret: bool = False):
        self.id = achievement_id
        self.title = title
        self.description = description
        self.condition = condition
        self.reward = reward or {}
        self.secret = secret
        self.unlocked = False
        self.unlock_time = None


class AchievementManager:
    """Менеджер достижений"""

    def __init__(self, game):
        self.game = game
        self.achievements = {}
        self.new_achievements = []
        self.total_achievements = 0
        self.unlocked_count = 0
        self._register_achievements()

    def _register_achievements(self):
        """Регистрация всех достижений"""

        # Боевые достижения
        self._add_achievement('first_blood', 'Первая кровь',
                              'Уничтожьте первого врага',
                              lambda g: g.player.kills >= 1,
                              {'exp': 10})

        self._add_achievement('killer_10', 'Десяток',
                              'Уничтожьте 10 врагов',
                              lambda g: g.player.kills >= 10,
                              {'exp': 50})

        self._add_achievement('killer_50', 'Полтинник',
                              'Уничтожьте 50 врагов',
                              lambda g: g.player.kills >= 50,
                              {'exp': 200})

        self._add_achievement('killer_100', 'Сотня',
                              'Уничтожьте 100 врагов',
                              lambda g: g.player.kills >= 100,
                              {'weapon': 'laser'})

        self._add_achievement('killer_500', 'Мясник',
                              'Уничтожьте 500 врагов',
                              lambda g: g.player.kills >= 500,
                              {'exp': 1000})

        self._add_achievement('killer_1000', 'Истребитель',
                              'Уничтожьте 1000 врагов',
                              lambda g: g.player.kills >= 1000,
                              {'exp': 5000})

        # Достижения за выживание
        self._add_achievement('survivor_5', 'Выживший',
                              'Достигните 5 волны',
                              lambda g: g.wave >= 5,
                              {'exp': 50})

        self._add_achievement('survivor_10', 'Стойкий',
                              'Достигните 10 волны',
                              lambda g: g.wave >= 10,
                              {'exp': 150})

        self._add_achievement('survivor_20', 'Неубиваемый',
                              'Достигните 20 волны',
                              lambda g: g.wave >= 20,
                              {'exp': 500})

        self._add_achievement('survivor_50', 'Легенда',
                              'Достигните 50 волны',
                              lambda g: g.wave >= 50,
                              {'exp': 2000})

        # Достижения за боссов
        self._add_achievement('boss_killer_1', 'Убийца боссов',
                              'Уничтожьте первого босса',
                              lambda g: g.session_stats.get('bosses_killed', 0) >= 1,
                              {'exp': 100})

        self._add_achievement('boss_killer_10', 'Истребитель боссов',
                              'Уничтожьте 10 боссов',
                              lambda g: g.session_stats.get('bosses_killed', 0) >= 10,
                              {'exp': 500})

        # Достижения за комбо
        self._add_achievement('combo_10', 'Комбо x10',
                              'Достигните комбо 10',
                              lambda g: g.player.max_combo >= 10,
                              {'exp': 50})

        self._add_achievement('combo_50', 'Комбо x50',
                              'Достигните комбо 50',
                              lambda g: g.player.max_combo >= 50,
                              {'exp': 200})

        self._add_achievement('combo_100', 'Комбо x100',
                              'Достигните комбо 100',
                              lambda g: g.player.max_combo >= 100,
                              {'exp': 1000})

        # Достижения за коллекционирование
        self._add_achievement('collector_10', 'Коллекционер',
                              'Соберите 10 предметов',
                              lambda g: g.player.pickups_collected >= 10,
                              {'exp': 30})

        self._add_achievement('collector_100', 'Собиратель',
                              'Соберите 100 предметов',
                              lambda g: g.player.pickups_collected >= 100,
                              {'exp': 300})

        # Достижения за крафт
        self._add_achievement('crafter_1', 'Мастер',
                              'Создайте первый предмет',
                              lambda g: g.crafted_items >= 1,
                              {'exp': 30})

        self._add_achievement('crafter_50', 'Кузнец',
                              'Создайте 50 предметов',
                              lambda g: g.crafted_items >= 50,
                              {'exp': 500})

        # Достижения за исследование
        self._add_achievement('explorer_1', 'Исследователь',
                              'Откройте новую локацию',
                              lambda g: len(g.unlocked_locations) > 1,
                              {'exp': 50})

        self._add_achievement('explorer_all', 'Картограф',
                              'Откройте все локации',
                              lambda g: len(g.unlocked_locations) >= 8,
                              {'exp': 500})

        # Секретные достижения
        self._add_achievement('secret_1', '???',
                              'Секретное достижение',
                              lambda g: g.player.hp == 1 and g.player.kills >= 100,
                              {'exp': 1000}, secret=True)

        self._add_achievement('secret_2', '???',
                              'Секретное достижение',
                              lambda g: g.player.scrap >= 1000,
                              {'exp': 500}, secret=True)

        self._add_achievement('secret_3', '???',
                              'Секретное достижение',
                              lambda g: g.time_elapsed >= 3600,
                              {'exp': 2000}, secret=True)

        self.total_achievements = len(self.achievements)

    def _add_achievement(self, achievement_id: str, title: str, description: str,
                         condition: Callable, reward: Dict = None, secret: bool = False):
        """Добавление достижения"""
        achievement = Achievement(achievement_id, title, description, condition, reward, secret)
        self.achievements[achievement_id] = achievement

    def check_achievements(self):
        """Проверка всех достижений"""
        for ach_id, achievement in self.achievements.items():
            if not achievement.unlocked and achievement.condition(self.game):
                self._unlock_achievement(achievement)

    def _unlock_achievement(self, achievement: Achievement):
        """Разблокировка достижения"""
        achievement.unlocked = True
        achievement.unlock_time = self.game.time_elapsed
        self.unlocked_count += 1
        self.new_achievements.append(achievement)

        # Применение награды
        if 'exp' in achievement.reward:
            self.game.player.add_exp(achievement.reward['exp'])
        if 'weapon' in achievement.reward:
            self.game.player.add_weapon(achievement.reward['weapon'])

        # Звук
        if hasattr(self.game, 'sound_manager'):
            self.game.sound_manager.play('achievement')

        # Уведомление
        self.game.ui.show_notification(f"Достижение: {achievement.title}", YELLOW, 3.0)

    def unlock_achievement(self, achievement_id: str):
        """Разблокировать достижение по ID (публичный метод)"""
        if achievement_id in self.achievements:
            achievement = self.achievements[achievement_id]
            if not achievement.unlocked:
                self._unlock_achievement(achievement)

    def draw_achievements(self, screen: pygame.Surface):
        """Отрисовка новых достижений"""
        y = 150
        for achievement in self.new_achievements[:5]:
            # Фон
            rect = pygame.Rect(SCREEN_WIDTH - 350, y, 330, 70)
            pygame.draw.rect(screen, (40, 40, 50), rect)
            pygame.draw.rect(screen, YELLOW, rect, 2)

            # Текст
            font_title = pygame.font.Font(None, 24)
            font_desc = pygame.font.Font(None, 18)

            title = font_title.render(achievement.title, True, YELLOW)
            desc = font_desc.render(achievement.description, True, WHITE)

            screen.blit(title, (rect.x + 10, rect.y + 10))
            screen.blit(desc, (rect.x + 10, rect.y + 40))

            y += 80

    def get_completion_percentage(self) -> float:
        """Получение процента завершения"""
        if self.total_achievements == 0:
            return 0
        return (self.unlocked_count / self.total_achievements) * 100