# mobile_controls.py
import pygame
import math
from typing import Tuple, Optional
from settings import *


class VirtualJoystick:
    def __init__(self, x: float, y: float, radius: float = 60):
        self.base_x = x
        self.base_y = y
        self.radius = radius
        self.knob_x = x
        self.knob_y = y
        self.knob_radius = radius * 0.4
        self.active = False
        self.touch_id = None
        self.dx = 0.0  # -1..1
        self.dy = 0.0  # -1..1

    def handle_touch_down(self, pos: Tuple[float, float], touch_id) -> bool:
        """Проверяет, попал ли палец по джойстику."""
        dist = math.hypot(pos[0] - self.base_x, pos[1] - self.base_y)
        if dist < self.radius * 1.5 and self.touch_id is None:
            self.touch_id = touch_id
            self.active = True
            self.update_knob(pos)
            return True
        return False

    def handle_touch_move(self, pos: Tuple[float, float], touch_id) -> bool:
        """Обновляет позицию джойстика."""
        if touch_id == self.touch_id and self.active:
            self.update_knob(pos)
            return True
        return False

    def handle_touch_up(self, touch_id) -> bool:
        """Отпускает джойстик."""
        if touch_id == self.touch_id:
            self.touch_id = None
            self.active = False
            self.knob_x = self.base_x
            self.knob_y = self.base_y
            self.dx = 0.0
            self.dy = 0.0
            return True
        return False

    def update_knob(self, pos: Tuple[float, float]):
        """Обновляет позицию ручки джойстика."""
        dx = pos[0] - self.base_x
        dy = pos[1] - self.base_y
        dist = math.hypot(dx, dy)

        if dist > self.radius:
            # Ограничиваем ручку радиусом
            dx = dx / dist * self.radius
            dy = dy / dist * self.radius
            dist = self.radius

        self.knob_x = self.base_x + dx
        self.knob_y = self.base_y + dy

        # Нормализуем значения (-1..1)
        if dist > 10:  # Мёртвая зона
            self.dx = dx / self.radius
            self.dy = dy / self.radius
        else:
            self.dx = 0.0
            self.dy = 0.0

    def draw(self, surface: pygame.Surface):
        """Отрисовка джойстика."""
        if not self.active:
            # Неактивный джойстик
            pygame.draw.circle(surface, (60, 60, 70, 128),
                               (int(self.base_x), int(self.base_y)),
                               self.radius, 2)
            pygame.draw.circle(surface, (80, 80, 90, 128),
                               (int(self.knob_x), int(self.knob_y)),
                               int(self.knob_radius))
        else:
            # Активный джойстик
            pygame.draw.circle(surface, (100, 200, 255, 180),
                               (int(self.base_x), int(self.base_y)),
                               self.radius, 2)
            pygame.draw.circle(surface, (100, 200, 255, 200),
                               (int(self.knob_x), int(self.knob_y)),
                               int(self.knob_radius))


class VirtualButton:
    def __init__(self, x: float, y: float, radius: float = 30,
                 text: str = "", color: Tuple[int, int, int] = (100, 100, 120)):
        self.x = x
        self.y = y
        self.radius = radius
        self.text = text
        self.color = color
        self.pressed = False
        self.touch_id = None

    def handle_touch_down(self, pos: Tuple[float, float], touch_id) -> bool:
        """Проверяет нажатие на кнопку."""
        dist = math.hypot(pos[0] - self.x, pos[1] - self.y)
        if dist < self.radius * 1.5 and self.touch_id is None:
            self.touch_id = touch_id
            self.pressed = True
            return True
        return False

    def handle_touch_move(self, pos: Tuple[float, float], touch_id) -> bool:
        """Обновляет состояние кнопки при движении пальца."""
        if touch_id == self.touch_id:
            dist = math.hypot(pos[0] - self.x, pos[1] - self.y)
            self.pressed = dist < self.radius * 1.5
            return True
        return False

    def handle_touch_up(self, touch_id) -> bool:
        """Отпускает кнопку."""
        if touch_id == self.touch_id:
            self.touch_id = None
            self.pressed = False
            return True
        return False

    def draw(self, surface: pygame.Surface):
        """Отрисовка кнопки."""
        alpha = 200 if self.pressed else 128
        color = (min(255, self.color[0] + 50),
                 min(255, self.color[1] + 50),
                 min(255, self.color[2] + 50)) if self.pressed else self.color

        # Полупрозрачный круг
        surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color, alpha),
                           (self.radius, self.radius), self.radius)
        pygame.draw.circle(surf, (255, 255, 255, 200),
                           (self.radius, self.radius), self.radius, 2)

        # Текст кнопки
        if self.text:
            font = pygame.font.Font(None, 24)
            text_surf = font.render(self.text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(self.radius, self.radius))
            surf.blit(text_surf, text_rect)

        surface.blit(surf, (int(self.x - self.radius), int(self.y - self.radius)))


class MobileControls:
    """Менеджер мобильного управления."""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_mobile = self._detect_mobile()

        # Джойстик движения (левый нижний угол)
        self.move_joystick = VirtualJoystick(
            screen_width * 0.15,
            screen_height * 0.75,
            radius=60
        )

        # Джойстик атаки (правый нижний угол)
        self.attack_joystick = VirtualJoystick(
            screen_width * 0.85,
            screen_height * 0.75,
            radius=60
        )

        # Кнопки действий
        button_radius = 35
        button_y = screen_height * 0.35

        self.dash_button = VirtualButton(
            screen_width * 0.75, button_y,
            button_radius, "Д", (200, 150, 50)
        )

        self.wall_button = VirtualButton(
            screen_width * 0.75, button_y + button_radius * 2.5,
            button_radius, "С", (100, 150, 250)
        )

        self.interact_button = VirtualButton(
            screen_width * 0.75, button_y + button_radius * 5,
            button_radius, "Е", (100, 200, 100)
        )

        self.shop_button = VirtualButton(
            screen_width * 0.75, button_y + button_radius * 7.5,
            button_radius, "М", (200, 100, 200)
        )

        # Кнопка паузы (верхний правый угол)
        self.pause_button = VirtualButton(
            screen_width * 0.95, screen_height * 0.05,
            25, "||", (150, 150, 150)
        )

        # Состояния
        self.touches = {}  # touch_id -> (x, y)
        self.button_states = {
            'dash': False,
            'wall': False,
            'interact': False,
            'shop': False,
            'pause': False
        }

    def _detect_mobile(self) -> bool:
        """Определяет, запущена ли игра на мобильном устройстве."""
        try:
            # Пытаемся определить платформу
            import platform
            system = platform.system().lower()
            if 'android' in system or 'ios' in system:
                return True

            # Проверяем окружение pygame
            if hasattr(pygame, 'TOUCH'):
                return True

            # Проверяем размер экрана (если очень маленький - вероятно, телефон)
            if self.screen_width < 800 or self.screen_height < 600:
                return True

            # Проверяем наличие сенсорного ввода
            if hasattr(pygame, 'FINGERDOWN'):
                return True

        except:
            pass

        return False

    def handle_event(self, event: pygame.event.Event):
        """Обрабатывает события сенсорного ввода."""
        if not self.is_mobile:
            return

        if event.type == pygame.FINGERDOWN:
            # Конвертируем координаты из нормализованных в пиксельные
            x = event.x * self.screen_width
            y = event.y * self.screen_height
            touch_id = event.finger_id
            self.touches[touch_id] = (x, y)
            self._process_touch_down(x, y, touch_id)

        elif event.type == pygame.FINGERMOTION:
            x = event.x * self.screen_width
            y = event.y * self.screen_height
            touch_id = event.finger_id
            self.touches[touch_id] = (x, y)
            self._process_touch_move(x, y, touch_id)

        elif event.type == pygame.FINGERUP:
            touch_id = event.finger_id
            if touch_id in self.touches:
                del self.touches[touch_id]
            self._process_touch_up(touch_id)

        # Также обрабатываем мышь для тестирования на ПК
        elif event.type == pygame.MOUSEBUTTONDOWN and self.is_mobile:
            x, y = event.pos
            touch_id = 1000 + event.button  # Имитация touch_id
            self.touches[touch_id] = (x, y)
            self._process_touch_down(x, y, touch_id)

        elif event.type == pygame.MOUSEMOTION and self.is_mobile:
            for touch_id, pos in list(self.touches.items()):
                if touch_id >= 1000:  # Только мышиные касания
                    self._process_touch_move(pos[0], pos[1], touch_id)

        elif event.type == pygame.MOUSEBUTTONUP and self.is_mobile:
            for touch_id in [1001, 1002, 1003]:
                if touch_id in self.touches:
                    del self.touches[touch_id]
                    self._process_touch_up(touch_id)

    def _process_touch_down(self, x: float, y: float, touch_id: int):
        """Обрабатывает нажатие."""
        pos = (x, y)

        # Проверяем кнопки в порядке приоритета
        if self.pause_button.handle_touch_down(pos, touch_id):
            self.button_states['pause'] = True
        elif self.dash_button.handle_touch_down(pos, touch_id):
            self.button_states['dash'] = True
        elif self.wall_button.handle_touch_down(pos, touch_id):
            self.button_states['wall'] = True
        elif self.interact_button.handle_touch_down(pos, touch_id):
            self.button_states['interact'] = True
        elif self.shop_button.handle_touch_down(pos, touch_id):
            self.button_states['shop'] = True
        elif self.move_joystick.handle_touch_down(pos, touch_id):
            pass  # Джойстик движения
        elif self.attack_joystick.handle_touch_down(pos, touch_id):
            pass  # Джойстик атаки

    def _process_touch_move(self, x: float, y: float, touch_id: int):
        """Обрабатывает движение пальца."""
        pos = (x, y)

        # Обновляем все элементы управления
        self.move_joystick.handle_touch_move(pos, touch_id)
        self.attack_joystick.handle_touch_move(pos, touch_id)
        self.dash_button.handle_touch_move(pos, touch_id)
        self.wall_button.handle_touch_move(pos, touch_id)
        self.interact_button.handle_touch_move(pos, touch_id)
        self.shop_button.handle_touch_move(pos, touch_id)
        self.pause_button.handle_touch_move(pos, touch_id)

    def _process_touch_up(self, touch_id: int):
        """Обрабатывает отпускание."""
        self.move_joystick.handle_touch_up(touch_id)
        self.attack_joystick.handle_touch_up(touch_id)

        if self.dash_button.handle_touch_up(touch_id):
            self.button_states['dash'] = False
        if self.wall_button.handle_touch_up(touch_id):
            self.button_states['wall'] = False
        if self.interact_button.handle_touch_up(touch_id):
            self.button_states['interact'] = False
        if self.shop_button.handle_touch_up(touch_id):
            self.button_states['shop'] = False
        if self.pause_button.handle_touch_up(touch_id):
            self.button_states['pause'] = False

    def get_movement(self) -> Tuple[float, float]:
        """Возвращает вектор движения (-1..1, -1..1)."""
        if self.is_mobile:
            return self.move_joystick.dx, self.move_joystick.dy
        return 0.0, 0.0

    def get_aim(self) -> Tuple[float, float]:
        """Возвращает вектор прицеливания (-1..1, -1..1)."""
        if self.is_mobile:
            return self.attack_joystick.dx, self.attack_joystick.dy
        return 0.0, 0.0

    def is_attacking(self) -> bool:
        """Проверяет, идёт ли атака."""
        if self.is_mobile:
            return (abs(self.attack_joystick.dx) > 0.3 or
                    abs(self.attack_joystick.dy) > 0.3)
        return False

    def draw(self, surface: pygame.Surface):
        """Отрисовка всех элементов управления."""
        if not self.is_mobile:
            return

        # Полупрозрачный фон для кнопок (только если активны)
        self.move_joystick.draw(surface)
        self.attack_joystick.draw(surface)
        self.dash_button.draw(surface)
        self.wall_button.draw(surface)
        self.interact_button.draw(surface)
        self.shop_button.draw(surface)
        self.pause_button.draw(surface)