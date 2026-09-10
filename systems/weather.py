# systems/weather.py
import random
import math
import pygame
from typing import List, Dict, Tuple, Optional
from settings import *


class WeatherSystem:
    """Система динамической погоды с сюжетными эффектами."""

    def __init__(self):
        self.current_weather = 'clear'
        self.weather_timer = 0
        self.weather_duration = 30.0
        self.particles = []
        self.intensity = 0.0
        self.target_intensity = 0.0
        self.acid_damage_cooldown = 0.0

        # Туман
        self.fog_particles = []
        self.fog_alpha = 0.0
        self.fog_target_alpha = 0.0

        # Капли на экране (для дождя)
        self.screen_drops = []  # Капли на "стекле"
        self._init_screen_drops()

        # Сюжетные флаги
        self.story_weather_locked = False
        self.story_weather_type = None
        self.story_weather_duration = 0.0

        self.weather_effects = {
            'clear': {'speed_multiplier': 1.0, 'visibility': 1.0, 'damage': 0},
            'rain': {'speed_multiplier': 0.95, 'visibility': 0.85, 'damage': 0},
            'acid_rain': {'speed_multiplier': 0.9, 'visibility': 0.75, 'damage': 3},
            'fog': {'speed_multiplier': 1.0, 'visibility': 0.5, 'damage': 0},
            'lightning_storm': {'speed_multiplier': 0.9, 'visibility': 0.7, 'damage': 0},
        }

    def _init_screen_drops(self):
        """Инициализация капель на экране (эффект стекла)."""
        self.screen_drops = []
        for _ in range(30):
            self.screen_drops.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'size': random.uniform(1, 3),
                'alpha': 0,
            })

    def set_story_weather(self, weather_type: str, duration: float = 30.0):
        """Установка сюжетной погоды (не меняется случайно)."""
        self.story_weather_locked = True
        self.story_weather_type = weather_type
        self.story_weather_duration = duration
        self._set_weather(weather_type, duration)

    def clear_story_weather(self):
        """Снятие сюжетной погоды."""
        self.story_weather_locked = False
        self.story_weather_type = None
        self.story_weather_duration = 0.0
        self.current_weather = 'clear'
        self.weather_timer = 0
        self.particles.clear()
        self.target_intensity = 0.0

    def _set_weather(self, weather_type: str, duration: float):
        """Внутренняя установка погоды."""
        self.current_weather = weather_type
        self.weather_timer = duration
        self.target_intensity = random.uniform(0.5, 1.0)

        # Очистка частиц
        self.particles.clear()

        # Создание частиц
        if weather_type == 'rain':
            for _ in range(150):
                self.particles.append({
                    'x': random.randint(0, SCREEN_WIDTH),
                    'y': random.randint(-SCREEN_HEIGHT, 0),
                    'vx': random.uniform(-30, 30),
                    'vy': random.uniform(400, 700),
                    'length': random.uniform(10, 25),
                    'type': 'rain'
                })
        elif weather_type == 'acid_rain':
            for _ in range(120):
                self.particles.append({
                    'x': random.randint(0, SCREEN_WIDTH),
                    'y': random.randint(-SCREEN_HEIGHT, 0),
                    'vx': random.uniform(-20, 20),
                    'vy': random.uniform(300, 500),
                    'length': random.uniform(8, 18),
                    'type': 'acid'
                })
        elif weather_type == 'fog':
            for _ in range(40):
                self.particles.append({
                    'x': random.randint(0, SCREEN_WIDTH),
                    'y': random.randint(0, SCREEN_HEIGHT),
                    'vx': random.uniform(-10, 10),
                    'vy': random.uniform(-3, 3),
                    'radius': random.uniform(60, 150),
                    'alpha': random.uniform(30, 80),
                    'type': 'fog'
                })
        elif weather_type == 'lightning_storm':
            for _ in range(80):
                self.particles.append({
                    'x': random.randint(0, SCREEN_WIDTH),
                    'y': random.randint(-SCREEN_HEIGHT, 0),
                    'vx': random.uniform(-40, 40),
                    'vy': random.uniform(500, 800),
                    'length': random.uniform(5, 15),
                    'type': 'rain'
                })

    def update(self, dt: float, game):
        """Обновление погоды."""
        # Сюжетная погода
        if self.story_weather_locked:
            self.story_weather_duration -= dt
            if self.story_weather_duration <= 0:
                self.clear_story_weather()
                return
        else:
            self.weather_timer -= dt
            if self.weather_timer <= 0:
                self.change_weather()

        # Плавное изменение интенсивности
        self.intensity += (self.target_intensity - self.intensity) * dt * 0.5

        # Обновление частиц
        self.update_particles(dt, game)

        # Применение эффектов
        self.apply_effects(dt, game)

        # Обновление капель на экране
        self._update_screen_drops(dt)

    def _update_screen_drops(self, dt: float):
        """Обновление капель на экране."""
        for drop in self.screen_drops:
            if self.current_weather in ('rain', 'acid_rain', 'lightning_storm'):
                # Капли появляются и исчезают
                drop['alpha'] += dt * 50
                if drop['alpha'] > 150:
                    drop['alpha'] = 150
                # Медленно стекают вниз
                drop['y'] += dt * 20
                if drop['y'] > SCREEN_HEIGHT:
                    drop['y'] = random.randint(-10, 0)
                    drop['x'] = random.randint(0, SCREEN_WIDTH)
                    drop['alpha'] = 0
            else:
                # Капли исчезают
                drop['alpha'] -= dt * 100
                if drop['alpha'] < 0:
                    drop['alpha'] = 0

    def change_weather(self):
        """Случайная смена погоды."""
        # Сюжетная погода не меняется случайно
        if self.story_weather_locked:
            return

        weather_types = ['clear', 'rain', 'fog']
        if random.random() < 0.15:
            weather_types = ['clear', 'rain', 'acid_rain', 'fog', 'lightning_storm']

        new_weather = random.choice(weather_types)
        duration = random.uniform(20, 50)
        self._set_weather(new_weather, duration)

    def update_particles(self, dt: float, game):
        """Обновление частиц погоды."""
        if self.acid_damage_cooldown > 0:
            self.acid_damage_cooldown -= dt

        for particle in self.particles[:]:
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt

            # Сброс вышедших за экран
            if particle['type'] in ('rain', 'acid'):
                if particle['y'] > SCREEN_HEIGHT:
                    particle['y'] = random.randint(-50, -10)
                    particle['x'] = random.randint(0, SCREEN_WIDTH)
            elif particle['type'] == 'fog':
                if particle['x'] > SCREEN_WIDTH + particle['radius']:
                    particle['x'] = -particle['radius']
                elif particle['x'] < -particle['radius']:
                    particle['x'] = SCREEN_WIDTH + particle['radius']
                if particle['y'] > SCREEN_HEIGHT:
                    particle['y'] = 0
                elif particle['y'] < 0:
                    particle['y'] = SCREEN_HEIGHT

            # Урон от кислотного дождя
            if particle['type'] == 'acid':
                if (self.acid_damage_cooldown <= 0 and game.player.alive and
                        math.hypot(particle['x'] - game.player.x,
                                   particle['y'] - game.player.y) < game.player.radius + 5):
                    game.player.take_damage(1)
                    self.acid_damage_cooldown = 0.5  # Урон не чаще 2 раз в секунду

    def apply_effects(self, dt: float, game):
        """Применение эффектов погоды."""
        effects = self.weather_effects.get(self.current_weather, {})

        # Молнии
        if self.current_weather == 'lightning_storm':
            if random.random() < dt * 0.8:
                self.strike_lightning(game)

    def strike_lightning(self, game):
        """Удар молнии."""
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, SCREEN_HEIGHT // 3)

        # Урон врагам
        for enemy in game.enemies:
            if enemy.alive:
                dist = math.hypot(x - enemy.x, y - enemy.y)
                if dist < 80:
                    enemy.take_damage(30)

        # Урон игроку (редко)
        if game.player.alive:
            dist = math.hypot(x - game.player.x, y - game.player.y)
            if dist < 50:
                game.player.take_damage(15)

        # Визуальные эффекты
        game.spawn_particles(x, y, 25, CYAN)
        game.spawn_sparks(x, y, 15)

        # Добавляем молнию в эффекты
        game.lightning_effects.append({
            'start': (x, 0),
            'end': (x, y),
            'life': 0.3,
            'color': CYAN,
        })

    def draw(self, screen: pygame.Surface):
        """Отрисовка частиц погоды."""
        for particle in self.particles:
            if particle['type'] == 'rain':
                # Капля дождя
                end_x = particle['x'] + particle['vx'] * 0.03
                end_y = particle['y'] + particle['length']
                pygame.draw.line(screen, (120, 160, 220),
                                 (particle['x'], particle['y']),
                                 (end_x, end_y), 1)
            elif particle['type'] == 'acid':
                # Кислотная капля — зелёная
                end_x = particle['x'] + particle['vx'] * 0.03
                end_y = particle['y'] + particle['length']
                pygame.draw.line(screen, (100, 220, 100),
                                 (particle['x'], particle['y']),
                                 (end_x, end_y), 2)
            elif particle['type'] == 'fog':
                # Туман — мягкие круги
                fog_surf = pygame.Surface((int(particle['radius'] * 2), int(particle['radius'] * 2)), pygame.SRCALPHA)
                pygame.draw.circle(fog_surf, (200, 200, 210, int(particle['alpha'])),
                                   (int(particle['radius']), int(particle['radius'])),
                                   int(particle['radius']))
                screen.blit(fog_surf, (particle['x'] - particle['radius'], particle['y'] - particle['radius']))

    def draw_overlay(self, screen: pygame.Surface):
        """Отрисовка оверлея погоды (ЛЁГКИЙ, не заливает экран)."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        if self.current_weather == 'rain':
            overlay.fill((30, 40, 70, int(25 * self.intensity)))
        elif self.current_weather == 'acid_rain':
            overlay.fill((30, 70, 30, int(30 * self.intensity)))
        elif self.current_weather == 'fog':
            overlay.fill((180, 180, 190, int(40 * self.intensity)))
        elif self.current_weather == 'lightning_storm':
            overlay.fill((30, 30, 60, int(20 * self.intensity)))

        screen.blit(overlay, (0, 0))

        # Капли на экране (эффект стекла)
        for drop in self.screen_drops:
            if drop['alpha'] > 0:
                drop_surf = pygame.Surface((int(drop['size'] * 3), int(drop['size'] * 6)), pygame.SRCALPHA)
                pygame.draw.ellipse(drop_surf, (200, 210, 230, int(drop['alpha'])),
                                    drop_surf.get_rect())
                screen.blit(drop_surf, (drop['x'], drop['y']))

    def get_visibility_multiplier(self) -> float:
        """Множитель видимости (для врагов)."""
        effects = self.weather_effects.get(self.current_weather, {})
        return effects.get('visibility', 1.0)

    def get_speed_multiplier(self) -> float:
        """Множитель скорости (для игрока)."""
        effects = self.weather_effects.get(self.current_weather, {})
        return effects.get('speed_multiplier', 1.0)