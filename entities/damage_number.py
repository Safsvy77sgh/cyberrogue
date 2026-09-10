# entities/damage_number.py
import pygame
import random
import math
from typing import Tuple
from settings import *


class DamageNumber:
    def __init__(self, x: float, y: float, damage: int,
                 color: Tuple[int, int, int] = YELLOW,
                 is_crit: bool = False, is_heal: bool = False,
                 is_energy: bool = False):
        # Позиция
        self.x = x + random.uniform(-10, 10)
        self.y = y
        self.start_y = y

        # Текст
        self.text = str(damage)
        if is_heal:
            self.text = "+" + self.text
        elif is_energy:
            self.text = "⚡" + self.text

        # Цвет и стиль
        self.color = color
        self.is_crit = is_crit
        self.is_heal = is_heal
        self.is_energy = is_energy

        # Движение
        self.vy = -80
        self.vx = random.uniform(-20, 20)
        self.float_offset = random.uniform(0, 2 * math.pi)
        self.float_speed = 3.0

        # Жизнь
        self.life = 0.8
        self.max_life = 0.8

        # Шрифт
        if is_crit:
            self.font_size = 36
        elif is_heal:
            self.font_size = 28
        else:
            self.font_size = 24

        self.font = pygame.font.Font(None, self.font_size)

        # Эффекты
        self.scale = 1.0
        self.scale_speed = 2.0 if is_crit else 1.0

    def update(self, dt: float) -> bool:
        """Обновление числа"""
        # Движение
        self.y += self.vy * dt
        self.x += self.vx * dt
        self.vy *= 0.95
        self.vx *= 0.95

        # Покачивание
        self.float_offset += dt * self.float_speed

        # Масштабирование
        self.scale = max(0.5, self.scale - self.scale_speed * dt)

        # Жизнь
        self.life -= dt
        return self.life > 0

    def draw(self, screen: pygame.Surface):
        """Отрисовка числа"""
        alpha = max(0, self.life / self.max_life)

        # Создание текста
        text_surf = self.font.render(self.text, True, self.color)

        # Масштабирование
        if self.scale != 1.0:
            new_width = int(text_surf.get_width() * self.scale)
            new_height = int(text_surf.get_height() * self.scale)
            text_surf = pygame.transform.scale(text_surf, (new_width, new_height))

        # Прозрачность
        text_surf.set_alpha(int(255 * alpha))

        # Позиция с учётом покачивания
        x_offset = math.sin(self.float_offset) * 5
        draw_x = self.x - text_surf.get_width() // 2 + x_offset
        draw_y = self.y - text_surf.get_height() // 2

        # Отрисовка
        screen.blit(text_surf, (draw_x, draw_y))

        # Дополнительные эффекты для критов
        if self.is_crit:
            # Обводка
            outline_surf = self.font.render(self.text, True, WHITE)
            if self.scale != 1.0:
                new_width = int(outline_surf.get_width() * self.scale)
                new_height = int(outline_surf.get_height() * self.scale)
                outline_surf = pygame.transform.scale(outline_surf, (new_width, new_height))
            outline_surf.set_alpha(int(255 * alpha))

            # Смещённая обводка
            screen.blit(outline_surf, (draw_x - 1, draw_y - 1))
            screen.blit(outline_surf, (draw_x + 1, draw_y + 1))
            screen.blit(outline_surf, (draw_x - 1, draw_y + 1))
            screen.blit(outline_surf, (draw_x + 1, draw_y - 1))