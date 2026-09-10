# systems/ui.py
import pygame
import math
from settings import *


class UI:
    def __init__(self, game):
        self.game = game
        self.notifications = []
        self.chapter_title = None
        self.chapter_title_timer = 0
        self.boss_hp_display = 0
        self.combo_display = 0
        self.combo_scale = 1.0
        self.current_dialogue = None
        self.pulse_timer = 0
        self.damage_flash_timer = 0
        self.damage_flash_alpha = 0
        self.heal_flash_timer = 0
        self.heal_flash_alpha = 0
        self.quest_progress_display = 0
        self.show_quest_progress = False
        self.quest_progress_timer = 0
        self.touch_buttons = []
        self.is_mobile = False
        self.screen_width = SCREEN_WIDTH
        self.screen_height = SCREEN_HEIGHT

        # Для анимации уведомлений
        self.notification_slide_offset = {}

        # Инициализация мобильных кнопок
        if self.is_mobile:
            self._init_touch_buttons()

    def _detect_mobile(self) -> bool:
        """Определяет, запущена ли игра на мобильном устройстве"""
        try:
            # Проверяем наличие сенсорного экрана
            import pygame.touch
            return pygame.touch.get_num_devices() > 0
        except:
            return False

    def _init_touch_buttons(self):
        """Создание кнопок для мобильного управления"""
        button_size = 60
        margin = 20
        bottom_y = self.screen_height - button_size - margin

        # Джойстик движения (левый нижний угол)
        self.touch_buttons.append({
            'id': 'joystick',
            'rect': pygame.Rect(margin, bottom_y - button_size, button_size * 2, button_size * 2),
            'type': 'joystick',
            'color': (100, 100, 100, 128)
        })

        # Кнопка стрельбы (правый нижний угол)
        self.touch_buttons.append({
            'id': 'shoot',
            'rect': pygame.Rect(self.screen_width - button_size - margin, bottom_y, button_size, button_size),
            'type': 'button',
            'color': (255, 100, 100, 128),
            'key': pygame.K_SPACE
        })

        # Кнопка рывка
        self.touch_buttons.append({
            'id': 'dash',
            'rect': pygame.Rect(self.screen_width - button_size * 2 - margin - 10, bottom_y, button_size, button_size),
            'type': 'button',
            'color': (100, 100, 255, 128),
            'key': pygame.K_LSHIFT
        })

        # Кнопка способности
        self.touch_buttons.append({
            'id': 'ability',
            'rect': pygame.Rect(self.screen_width - button_size - margin, bottom_y - button_size - 10, button_size,
                                button_size),
            'type': 'button',
            'color': (255, 255, 100, 128),
            'key': pygame.K_e
        })

        # Кнопка паузы (верхний правый угол)
        self.touch_buttons.append({
            'id': 'pause',
            'rect': pygame.Rect(self.screen_width - button_size - margin, margin, button_size // 2, button_size // 2),
            'type': 'button',
            'color': (200, 200, 200, 128),
            'key': pygame.K_ESCAPE
        })

    def handle_touch_input(self, event):
        """Обработка сенсорного ввода для мобильных устройств"""
        if not self.is_mobile or not self.touch_buttons:
            return

        if event.type == pygame.FINGERDOWN:
            # Конвертируем координаты пальца в экранные
            x = int(event.x * self.screen_width)
            y = int(event.y * self.screen_height)

            for button in self.touch_buttons:
                if button['rect'].collidepoint(x, y):
                    if button['type'] == 'button':
                        # Симулируем нажатие клавиши
                        key_event = pygame.event.Event(pygame.KEYDOWN, {'key': button['key']})
                        pygame.event.post(key_event)
                    elif button['type'] == 'joystick':
                        # Сохраняем позицию джойстика
                        button['active'] = True
                        button['start_pos'] = (x, y)
                        button['current_pos'] = (x, y)

        elif event.type == pygame.FINGERUP:
            x = int(event.x * self.screen_width)
            y = int(event.y * self.screen_height)

            for button in self.touch_buttons:
                if button['rect'].collidepoint(x, y):
                    if button['type'] == 'button':
                        key_event = pygame.event.Event(pygame.KEYUP, {'key': button['key']})
                        pygame.event.post(key_event)
                    elif button['type'] == 'joystick':
                        button['active'] = False
                        button['current_pos'] = button['start_pos']

        elif event.type == pygame.FINGERMOTION:
            x = int(event.x * self.screen_width)
            y = int(event.y * self.screen_height)

            for button in self.touch_buttons:
                if button['type'] == 'joystick' and button.get('active', False):
                    button['current_pos'] = (x, y)

    def show_notification(self, text: str, color: tuple = WHITE, duration: float = 2.0, icon: str = None):
        """Показать уведомление с иконкой"""
        notification_id = len(self.notifications)
        self.notifications.append({
            'text': text,
            'color': color,
            'timer': duration,
            'max_timer': duration,
            'icon': icon,
            'id': notification_id,
            'slide_x': SCREEN_WIDTH
        })
        self.notification_slide_offset[notification_id] = SCREEN_WIDTH

    def show_floor_notification(self, floor: int):
        """Показать уведомление о новом этаже"""
        self.chapter_title = f"Этаж {floor}"
        self.chapter_title_timer = 3.0
        self.show_notification(f"Этаж {floor}", MAGENTA, 3.0, "floor")

    def show_room_notification(self, current: int, total: int):
        """Показать уведомление о прогрессе комнат"""
        self.show_notification(f"Комната {current}/{total}", CYAN, 2.0, "room")

    def show_chapter_title(self, title: str):
        """Показать заголовок главы"""
        self.chapter_title = title
        self.chapter_title_timer = 4.0

    def show_chapter_complete(self, title: str):
        """Показать уведомление о завершении главы"""
        self.show_notification(f"Глава завершена: {title}", GREEN, 3.0)

    def show_quest(self, title: str):
        """Показать уведомление о новом задании"""
        self.show_notification(f"Новое задание: {title}", CYAN, 3.0)

    def show_quest_complete(self, title: str):
        """Показать уведомление о выполнении задания"""
        self.show_notification(f"Задание выполнено: {title}", GREEN, 3.0)

    def show_quest_progress(self, progress: float, title: str):
        """Показать прогресс квеста на экране"""
        self.quest_progress_display = progress
        self.show_quest_progress = True
        self.quest_progress_timer = 3.0

    def show_damage_flash(self, intensity: float = 1.0):
        """Показать красную вспышку при получении урона"""
        self.damage_flash_timer = 0.3
        self.damage_flash_alpha = min(1.0, 0.5 * intensity)

    def show_heal_flash(self, intensity: float = 1.0):
        """Показать зелёную вспышку при лечении"""
        self.heal_flash_timer = 0.3
        self.heal_flash_alpha = min(1.0, 0.3 * intensity)

    def show_dialogue(self, dialogue_data: dict):
        """Store dialogue data for rendering."""
        self.current_dialogue = dialogue_data
        # Автоматически ставим игру на паузу
        if hasattr(self.game, 'in_dialogue'):
            self.game.in_dialogue = True

    def hide_dialogue(self):
        """Clear current dialogue."""
        self.current_dialogue = None
        # Снимаем паузу
        if hasattr(self.game, 'in_dialogue'):
            self.game.in_dialogue = False

    def update(self, dt: float):
        """Обновление UI элементов"""
        self.pulse_timer += dt

        # Обновление вспышек
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= dt
            self.damage_flash_alpha = max(0, self.damage_flash_alpha - dt * 2)
        if self.heal_flash_timer > 0:
            self.heal_flash_timer -= dt
            self.heal_flash_alpha = max(0, self.heal_flash_alpha - dt * 2)

        # Обновление прогресса квеста
        if self.quest_progress_timer > 0:
            self.quest_progress_timer -= dt
            if self.quest_progress_timer <= 0:
                self.show_quest_progress = False

        # Обновление уведомлений
        for notif in self.notifications[:]:
            notif['timer'] -= dt

            # Анимация скольжения
            target_x = SCREEN_WIDTH - 350
            current_x = self.notification_slide_offset.get(notif['id'], SCREEN_WIDTH)

            if current_x > target_x:
                # Скольжение влево
                current_x = max(target_x, current_x - 800 * dt)
                self.notification_slide_offset[notif['id']] = current_x
            elif notif['timer'] < 0.5 and notif['timer'] > 0:
                # Скольжение вправо при исчезновении
                current_x = min(SCREEN_WIDTH, current_x + 800 * dt)
                self.notification_slide_offset[notif['id']] = current_x

            if notif['timer'] <= 0:
                self.notifications.remove(notif)
                if notif['id'] in self.notification_slide_offset:
                    del self.notification_slide_offset[notif['id']]

        # Обновление заголовка главы
        if self.chapter_title:
            self.chapter_title_timer -= dt
            if self.chapter_title_timer <= 0:
                self.chapter_title = None

        # Плавный переход здоровья босса
        if self.game.enemies:
            boss = self._find_boss()
            if boss:
                target_hp = boss.hp / boss.max_hp
                self.boss_hp_display += (target_hp - self.boss_hp_display) * min(1, dt * 3)

        # Плавный переход комбо
        if self.game.player and hasattr(self.game.player, 'combo_multiplier'):
            target_combo = self.game.player.combo_multiplier
            self.combo_display += (target_combo - self.combo_display) * min(1, dt * 5)

            # Анимация масштаба при увеличении комбо
            if target_combo > self.combo_display:
                self.combo_scale = 1.3
            else:
                self.combo_scale = max(1.0, self.combo_scale - dt * 2)

    def draw(self, screen: pygame.Surface):
        """Отрисовка всех UI элементов"""
        self.draw_hud(screen)
        self.draw_boss_bar(screen)
        self.draw_low_hp_warning(screen)
        self.draw_combo_indicator(screen)
        self.draw_notifications(screen)
        self.draw_chapter_title(screen)
        self.draw_flash_effects(screen)
        self.draw_quest_progress(screen)
        self.draw_touch_controls(screen)
        self.draw_dialogue(screen)

    def draw_hud(self, screen: pygame.Surface):
        """Отрисовка HUD элементов"""
        font_small = pygame.font.Font(None, 24)
        font_medium = pygame.font.Font(None, 30)
        font_large = pygame.font.Font(None, 36)

        # Верхний левый угол - Счёт и прогресс
        y_offset = 10

        # Счёт с иконкой
        score_icon = "★"
        score_text = f"{score_icon} {self.game.score}"
        score_surface = font_medium.render(score_text, True, YELLOW)
        screen.blit(score_surface, (10, y_offset))
        y_offset += 35

        # Этаж и прогресс комнат
        if hasattr(self.game, 'room_manager') and self.game.room_manager:
            # Этаж
            if hasattr(self.game.room_manager, 'floor'):
                floor_text = f"Этаж: {self.game.room_manager.floor}"
                floor_surface = font_medium.render(floor_text, True, WHITE)
                screen.blit(floor_surface, (10, y_offset))
                y_offset += 30

            # Прогресс комнат
            if hasattr(self.game.room_manager, 'cleared_rooms'):
                cleared = self.game.room_manager.cleared_rooms
                total = getattr(self.game.room_manager, 'total_rooms',
                                len(self.game.current_rooms) if hasattr(self.game, 'current_rooms') else 0)
                if total > 0:
                    room_text = f"Комнаты: {cleared}/{total}"
                    room_surface = font_medium.render(room_text, True, CYAN)
                    screen.blit(room_surface, (10, y_offset))
                    y_offset += 30

        # Оружие и патроны
        if self.game.player and hasattr(self.game.player, 'current_weapon'):
            weapon = self.game.player.current_weapon
            if weapon:
                if isinstance(weapon, str):
                    weapon_name = weapon
                else:
                    weapon_name = getattr(weapon, 'name', str(weapon))

                weapon_text = weapon_name
                if hasattr(self.game.player, 'ammo') and self.game.player.ammo is not None:
                    weapon_text += f" | {self.game.player.ammo}"
                weapon_surface = font_medium.render(weapon_text, True, ORANGE)
                screen.blit(weapon_surface, (10, y_offset))
                y_offset += 30

        # Нижний левый угол - Бары
        y_bottom = SCREEN_HEIGHT - 90
        bar_width = 200 if not self.is_mobile else 150

        # HP бар
        if self.game.player:
            hp_ratio = max(0, min(1, self.game.player.hp / self.game.player.max_hp))
            hp_color = self._get_hp_color(hp_ratio)
            self._draw_bar(screen, 10, y_bottom, bar_width, 20, hp_ratio, hp_color, bg_color=(40, 40, 40))
            hp_text = font_small.render(f"HP: {self.game.player.hp}/{self.game.player.max_hp}", True, WHITE)
            screen.blit(hp_text, (15, y_bottom + 2))
            y_bottom += 25

            # Энергия бар
            if hasattr(self.game.player, 'energy'):
                energy_ratio = max(0, min(1, self.game.player.energy / 100))
                self._draw_bar(screen, 10, y_bottom, bar_width, 10, energy_ratio, YELLOW, bg_color=(40, 40, 40))
                y_bottom += 15

            # EXP бар
            if hasattr(self.game.player, 'exp') and hasattr(self.game.player, 'exp_to_next'):
                exp_ratio = max(0, min(1, self.game.player.exp / self.game.player.exp_to_next))
                self._draw_bar(screen, 10, y_bottom, bar_width - 50, 5, exp_ratio, CYAN, bg_color=(40, 40, 40))

                # Уровень
                level_text = f"Ур. {self.game.player.level}"
                level_surface = font_small.render(level_text, True, WHITE)
                screen.blit(level_surface, (10, y_bottom + 8))
                y_bottom += 25

            # Очки навыков с пульсацией
            if hasattr(self.game.player, 'skill_points') and self.game.player.skill_points > 0:
                pulse = (math.sin(self.pulse_timer * 3) + 1) / 2
                sp_color = self._lerp_color(MAGENTA, PURPLE, pulse)
                sp_text = f"✦ Очки навыков: {self.game.player.skill_points}"
                sp_surface = font_medium.render(sp_text, True, sp_color)
                screen.blit(sp_surface, (10, y_bottom))

        # Верхний правый угол - Валюта и кнопки
        x_right = SCREEN_WIDTH - 10

        if hasattr(self.game, 'economy_system') and self.game.economy_system:
            credits_text = f"¤ {self.game.economy_system.credits}"
            credits_surface = font_medium.render(credits_text, True, YELLOW)
            screen.blit(credits_surface, (x_right - credits_surface.get_width(), 10))

        # Кнопки (только для десктопа)
        if not self.is_mobile:
            if hasattr(self.game, 'settings_button_rect'):
                self._draw_button(screen, "⚙", self.game.settings_button_rect, WHITE)
            if hasattr(self.game, 'help_button_rect'):
                self._draw_button(screen, "?", self.game.help_button_rect, WHITE)

    def draw_boss_bar(self, screen: pygame.Surface):
        """Отрисовка полосы здоровья босса"""
        boss = self._find_boss()
        if not boss:
            return

        # Параметры бара (адаптивные)
        bar_width = min(400, SCREEN_WIDTH - 100)
        bar_height = 25 if not self.is_mobile else 20
        bar_x = SCREEN_WIDTH // 2 - bar_width // 2
        bar_y = 10

        # Имя босса
        font = pygame.font.Font(None, 30 if not self.is_mobile else 24)
        boss_name = getattr(boss, 'name', 'БОСС')
        name_surface = font.render(boss_name, True, RED)
        screen.blit(name_surface, (bar_x, bar_y - 25))

        # Фаза
        if hasattr(boss, 'phase'):
            phase_text = f"Фаза {boss.phase}"
            phase_surface = font.render(phase_text, True, ORANGE)
            screen.blit(phase_surface, (bar_x + bar_width - phase_surface.get_width(), bar_y - 25))

        # Фон бара
        pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))

        # Здоровье с плавным переходом
        hp_width = int(bar_width * self.boss_hp_display)
        pygame.draw.rect(screen, RED, (bar_x, bar_y, hp_width, bar_height))

        # Граница
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

        # Текст здоровья
        hp_text = f"{int(self.boss_hp_display * boss.max_hp)}/{boss.max_hp}"
        hp_surface = font.render(hp_text, True, WHITE)
        screen.blit(hp_surface, (bar_x + bar_width // 2 - hp_surface.get_width() // 2, bar_y))

    def draw_low_hp_warning(self, screen: pygame.Surface):
        """Отрисовка красной виньетки при низком HP"""
        if not self.game.player:
            return

        hp_ratio = self.game.player.hp / self.game.player.max_hp

        if hp_ratio < 0.3:
            pulse = (math.sin(self.pulse_timer * 4) + 1) / 2
            intensity = (0.3 - hp_ratio) * 3 * (0.5 + 0.5 * pulse)
            intensity = min(1.0, intensity)

            vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            # Рисуем градиентную виньетку
            for i in range(10):
                alpha = int(15 * intensity * (i + 1))
                pygame.draw.rect(vignette, (255, 0, 0, alpha),
                                 (i * 10, i * 10, SCREEN_WIDTH - i * 20, SCREEN_HEIGHT - i * 20),
                                 10)
            screen.blit(vignette, (0, 0))

    def draw_combo_indicator(self, screen: pygame.Surface):
        """Отрисовка индикатора комбо"""
        if not self.game.player or not hasattr(self.game.player, 'combo_multiplier'):
            return

        if self.game.player.combo_multiplier <= 1:
            return

        font = pygame.font.Font(None, 50 if not self.is_mobile else 40)
        px = self.game.player.x
        py = self.game.player.y - 40

        scale = self.combo_scale
        combo_text = f"x{self.game.player.combo_multiplier}"

        if self.game.player.combo_multiplier >= 5:
            color = MAGENTA
        elif self.game.player.combo_multiplier >= 3:
            color = ORANGE
        else:
            color = YELLOW

        combo_surface = font.render(combo_text, True, color)

        if scale != 1.0:
            scaled_width = int(combo_surface.get_width() * scale)
            scaled_height = int(combo_surface.get_height() * scale)
            combo_surface = pygame.transform.scale(combo_surface, (scaled_width, scaled_height))

        shadow_surface = font.render(combo_text, True, BLACK)
        shadow_surface = pygame.transform.scale(shadow_surface,
                                                (combo_surface.get_width(), combo_surface.get_height()))
        screen.blit(shadow_surface, (px - combo_surface.get_width() // 2 + 2,
                                     py - combo_surface.get_height() // 2 + 2))
        screen.blit(combo_surface, (px - combo_surface.get_width() // 2,
                                    py - combo_surface.get_height() // 2))

    def draw_notifications(self, screen: pygame.Surface):
        """Отрисовка уведомлений с фоном"""
        font_size = 30 if not self.is_mobile else 24
        font = pygame.font.Font(None, font_size)

        for notif in self.notifications:
            text_surface = font.render(notif['text'], True, notif['color'])

            x = self.notification_slide_offset.get(notif['id'], SCREEN_WIDTH)
            y = 100 + (notif['id'] % 5) * 50

            bg_width = text_surface.get_width() + 40
            bg_height = 40
            bg_surface = pygame.Surface((bg_width, bg_height))
            bg_surface.set_alpha(200)
            bg_surface.fill((20, 20, 30))
            screen.blit(bg_surface, (x - bg_width, y - bg_height // 2))

            pygame.draw.rect(screen, notif['color'],
                             (x - bg_width, y - bg_height // 2, bg_width, bg_height), 2)

            if notif['icon']:
                icon_symbol = self._get_icon_symbol(notif['icon'])
                icon_surface = font.render(icon_symbol, True, notif['color'])
                screen.blit(icon_surface, (x - bg_width + 10, y - icon_surface.get_height() // 2))
                text_x = x - bg_width + 40
            else:
                text_x = x - bg_width + 20

            screen.blit(text_surface, (text_x, y - text_surface.get_height() // 2))

    def draw_chapter_title(self, screen: pygame.Surface):
        """Отрисовка заголовка главы"""
        if not self.chapter_title:
            return

        font_size = 72 if not self.is_mobile else 48
        font = pygame.font.Font(None, font_size)
        text_surface = font.render(self.chapter_title, True, WHITE)

        alpha = min(1.0, self.chapter_title_timer)
        text_surface.set_alpha(int(255 * alpha))

        x = SCREEN_WIDTH // 2 - text_surface.get_width() // 2
        y = SCREEN_HEIGHT // 3

        shadow_surface = font.render(self.chapter_title, True, BLACK)
        shadow_surface.set_alpha(int(150 * alpha))
        screen.blit(shadow_surface, (x + 3, y + 3))
        screen.blit(text_surface, (x, y))

    def draw_flash_effects(self, screen: pygame.Surface):
        """Отрисовка вспышек при уроне/лечении"""
        if self.damage_flash_alpha > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash.set_alpha(int(self.damage_flash_alpha * 255))
            flash.fill(RED)
            screen.blit(flash, (0, 0))

        if self.heal_flash_alpha > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash.set_alpha(int(self.heal_flash_alpha * 255))
            flash.fill(GREEN)
            screen.blit(flash, (0, 0))

    def draw_quest_progress(self, screen: pygame.Surface):
        """Отрисовка прогресса квеста"""
        if not self.show_quest_progress:
            return

        font = pygame.font.Font(None, 36 if not self.is_mobile else 28)
        text = f"Прогресс: {int(self.quest_progress_display * 100)}%"
        text_surface = font.render(text, True, CYAN)

        x = SCREEN_WIDTH // 2 - text_surface.get_width() // 2
        y = SCREEN_HEIGHT - 150

        # Фон
        bg_width = text_surface.get_width() + 40
        bg_height = 50
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(200)
        bg_surface.fill((20, 20, 30))
        screen.blit(bg_surface, (x - 20, y - 10))

        # Прогресс-бар
        bar_width = text_surface.get_width()
        bar_height = 10
        bar_x = x
        bar_y = y + 30

        pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int(bar_width * self.quest_progress_display)
        pygame.draw.rect(screen, CYAN, (bar_x, bar_y, fill_width, bar_height))
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

        screen.blit(text_surface, (x, y))

    def draw_touch_controls(self, screen: pygame.Surface):
        """Отрисовка мобильных кнопок управления"""
        if not self.is_mobile:
            return

        for button in self.touch_buttons:
            if button['type'] == 'button':
                # Полупрозрачная кнопка
                button_surface = pygame.Surface((button['rect'].width, button['rect'].height), pygame.SRCALPHA)
                button_surface.fill(button['color'])
                screen.blit(button_surface, button['rect'])

                # Иконка на кнопке
                font = pygame.font.Font(None, 30)
                icon_text = self._get_button_icon(button['id'])
                icon_surface = font.render(icon_text, True, WHITE)
                icon_x = button['rect'].x + button['rect'].width // 2 - icon_surface.get_width() // 2
                icon_y = button['rect'].y + button['rect'].height // 2 - icon_surface.get_height() // 2
                screen.blit(icon_surface, (icon_x, icon_y))

            elif button['type'] == 'joystick':
                # Джойстик
                joystick_surface = pygame.Surface((button['rect'].width, button['rect'].height), pygame.SRCALPHA)
                pygame.draw.circle(joystick_surface, button['color'],
                                   (button['rect'].width // 2, button['rect'].height // 2),
                                   button['rect'].width // 2)
                screen.blit(joystick_surface, button['rect'])

                # Позиция пальца на джойстике
                if button.get('active', False) and 'current_pos' in button:
                    dx = button['current_pos'][0] - button['start_pos'][0]
                    dy = button['current_pos'][1] - button['start_pos'][1]
                    # Ограничиваем расстояние
                    max_dist = button['rect'].width // 2
                    dist = math.hypot(dx, dy)
                    if dist > max_dist:
                        dx = dx * max_dist / dist
                        dy = dy * max_dist / dist

                    stick_x = button['rect'].x + button['rect'].width // 2 + dx
                    stick_y = button['rect'].y + button['rect'].height // 2 + dy
                    pygame.draw.circle(screen, WHITE, (int(stick_x), int(stick_y)), 20)
                    pygame.draw.circle(screen, (200, 200, 200), (int(stick_x), int(stick_y)), 20, 2)

    def _get_button_icon(self, button_id: str) -> str:
        """Возвращает иконку для мобильной кнопки"""
        icons = {
            'shoot': '●',  # Стрельба
            'dash': '➤',  # Рывок
            'ability': '✦',  # Способность
            'pause': '⏸',  # Пауза
        }
        return icons.get(button_id, '?')

    def draw_dialogue(self, screen: pygame.Surface):
        """Draw dialogue box if active."""
        if not hasattr(self, 'current_dialogue') or not self.current_dialogue:
            return

        # Адаптивный размер диалогового окна
        if self.is_mobile:
            box = pygame.Rect(20, SCREEN_HEIGHT - 300, SCREEN_WIDTH - 40, 280)
        else:
            box = pygame.Rect(50, SCREEN_HEIGHT - 250, SCREEN_WIDTH - 100, 200)

        # Полупрозрачный фон
        bg_surface = pygame.Surface((box.width, box.height))
        bg_surface.set_alpha(230)
        bg_surface.fill((20, 20, 30))
        screen.blit(bg_surface, box)
        pygame.draw.rect(screen, WHITE, box, 2)

        # Кнопка закрытия
        close_button = pygame.Rect(box.x + box.width - 30, box.y, 30, 30)
        pygame.draw.rect(screen, (60, 60, 60), close_button)
        pygame.draw.rect(screen, WHITE, close_button, 2)
        close_font = pygame.font.Font(None, 24)
        close_text = close_font.render("X", True, WHITE)
        screen.blit(close_text, (close_button.x + 10, close_button.y + 5))

        # Имя говорящего
        font_name = pygame.font.Font(None, 30 if not self.is_mobile else 24)
        speaker = self.current_dialogue.get('speaker', '')
        name_text = font_name.render(speaker, True, CYAN)
        screen.blit(name_text, (box.x + 20, box.y + 20))

        # Текст диалога
        font_text = pygame.font.Font(None, 24 if not self.is_mobile else 20)
        text = self.current_dialogue.get('text', '')

        # Перенос текста по словам
        words = text.split()
        lines = []
        current_line = ""
        max_width = box.width - 40

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if font_text.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        # Отрисовка текста
        y = box.y + 60
        for line in lines[:4]:  # Максимум 4 строки
            text_surf = font_text.render(line, True, WHITE)
            screen.blit(text_surf, (box.x + 20, y))
            y += 25

        # Ответы
        responses = self.current_dialogue.get('responses', [])
        y = box.y + 120 if not self.is_mobile else box.y + 170
        for i, response in enumerate(responses):
            response_text = f"{i + 1}. {response['text']}"
            response_surf = font_text.render(response_text, True, YELLOW)
            screen.blit(response_surf, (box.x + 40, y))
            y += 30

        # Подсказка
        hint_font = pygame.font.Font(None, 20 if not self.is_mobile else 16)
        hint_text = hint_font.render("ESC/X - закрыть | 1-4 - выбрать ответ", True, LIGHT_GRAY)
        screen.blit(hint_text, (box.x + 20, box.y + box.height - 30))

    def _get_hp_color(self, ratio: float) -> tuple:
        """Возвращает цвет HP бара с градиентом"""
        if ratio > 0.5:
            # Зелёный -> Жёлтый
            t = (ratio - 0.5) * 2
            return self._lerp_color(YELLOW, GREEN, t)
        elif ratio > 0.25:
            # Жёлтый -> Оранжевый
            t = (ratio - 0.25) * 4
            return self._lerp_color(ORANGE, YELLOW, t)
        else:
            # Оранжевый -> Красный
            t = ratio * 4
            return self._lerp_color(RED, ORANGE, t)

    def _draw_bar(self, screen: pygame.Surface, x: int, y: int, width: int, height: int,
                  ratio: float, color: tuple, bg_color: tuple = BLACK):
        """Вспомогательный метод для отрисовки полос"""
        ratio = max(0.0, min(1.0, ratio))

        # Фон с закруглёнными углами
        pygame.draw.rect(screen, bg_color, (x, y, width, height), border_radius=3)

        # Заполнение
        fill_width = int(width * ratio)
        if fill_width > 0:
            pygame.draw.rect(screen, color, (x, y, fill_width, height), border_radius=3)

        # Граница
        pygame.draw.rect(screen, WHITE, (x, y, width, height), 1, border_radius=3)

    def _draw_button(self, screen: pygame.Surface, symbol: str, rect: pygame.Rect, color: tuple):
        """Отрисовка кнопки"""
        font = pygame.font.Font(None, 36)
        text_surface = font.render(symbol, True, color)

        # Кнопка с эффектом наведения
        mouse_pos = pygame.mouse.get_pos()
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (60, 60, 60), rect, border_radius=5)
        else:
            pygame.draw.rect(screen, (40, 40, 40), rect, border_radius=5)

        pygame.draw.rect(screen, color, rect, 2, border_radius=5)

        text_x = rect.x + rect.width // 2 - text_surface.get_width() // 2
        text_y = rect.y + rect.height // 2 - text_surface.get_height() // 2
        screen.blit(text_surface, (text_x, text_y))

    def _find_boss(self):
        """Поиск босса среди врагов"""
        for enemy in self.game.enemies:
            if hasattr(enemy, 'is_boss') and enemy.is_boss:
                return enemy
        return None

    def _get_icon_symbol(self, icon_type: str) -> str:
        """Получение символа иконки"""
        icons = {
            'floor': '◆',
            'room': '▣',
            'boss': '☠',
            'reward': '★',
            'warning': '⚠',
            'info': 'ℹ'
        }
        return icons.get(icon_type, '•')

    def _lerp_color(self, color1: tuple, color2: tuple, t: float) -> tuple:
        """Интерполяция цветов"""
        return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))