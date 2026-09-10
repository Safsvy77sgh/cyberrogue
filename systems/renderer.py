# systems/renderer.py — ЦЕНТРАЛИЗОВАННАЯ СИСТЕМА ОТРИСОВКИ
# "Overload: Last Protocol" — неоновый sci-fi roguelike визуальный стиль.
#
# Полностью процедурная графика на Pygame (без внешних текстур), вдохновлённая
# Dead Cells / Hades / Neon Abyss: неоновые контуры, свечение, мягкие тени,
# параллакс-фон, пульсирующие ядра, частицы. Игровая логика не затрагивается —
# только то, как сцена рисуется.
#
# Интеграция: класс называется Renderer и принимает `game` в конструкторе,
# как и раньше — существующий патчинг в main.py (например,
# `game.renderer = Renderer(game)`) продолжает работать без изменений.

import pygame
import math
import random
from typing import Optional, Tuple, List, Dict, Any
from settings import *

try:
    import pygame.gfxdraw as gfxdraw
    HAS_GFXDRAW = True
except ImportError:
    HAS_GFXDRAW = False


# ============================================================
#                     ЦВЕТОВАЯ ПАЛИТРА
# ============================================================

class Palette:
    BG_DEEP = (6, 8, 16)
    BG_MID = (10, 14, 28)
    NEON_CYAN = (80, 240, 255)
    NEON_MAGENTA = (255, 70, 200)
    NEON_GOLD = (255, 200, 80)
    NEON_GREEN = (110, 255, 160)
    NEON_RED = (255, 70, 90)
    NEON_ORANGE = (255, 140, 60)
    NEON_BLUE = (90, 140, 255)
    PANEL_BG = (12, 16, 26, 190)
    PANEL_BORDER = (90, 210, 230, 160)
    TEXT_MAIN = (225, 240, 245)
    TEXT_DIM = (140, 160, 175)


def _clamp255(v: float) -> int:
    return max(0, min(255, int(v)))


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    t = max(0.0, min(1.0, t))
    return tuple(_clamp255(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def with_alpha(color: tuple, a: int) -> tuple:
    return (color[0], color[1], color[2], max(0, min(255, a)))


# ============================================================
#                    ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ
# ============================================================

class PointLight:
    __slots__ = ("x", "y", "radius", "color", "intensity", "flicker",
                 "flicker_speed", "_flicker_phase", "enabled", "cast_shadows")

    def __init__(self, x: float, y: float, radius: int, color: tuple = (255, 220, 150),
                 intensity: float = 1.0, flicker: float = 0.0, cast_shadows: bool = False):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity
        self.flicker = flicker
        self.flicker_speed = random.uniform(6.0, 10.0)
        self._flicker_phase = random.uniform(0, math.tau)
        self.enabled = True
        self.cast_shadows = cast_shadows

    def current_radius(self, t: float) -> int:
        if self.flicker <= 0:
            return self.radius
        offset = math.sin(t * self.flicker_speed + self._flicker_phase) * self.flicker
        return max(1, int(self.radius * (1.0 + offset * 0.15)))


class SpriteSheet:
    def __init__(self, image: pygame.Surface, frame_width: int, frame_height: int,
                 rows: int = 1, cols: int = 1):
        self.image = image
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.rows = rows
        self.cols = cols
        self._frame_cache: Dict[int, pygame.Surface] = {}

    def get_frame(self, index: int) -> pygame.Surface:
        if index in self._frame_cache:
            return self._frame_cache[index]
        col = index % self.cols
        row = index // self.cols
        rect = pygame.Rect(col * self.frame_width, row * self.frame_height,
                            self.frame_width, self.frame_height)
        frame = self.image.subsurface(rect).copy()
        self._frame_cache[index] = frame
        return frame

    @property
    def frame_count(self) -> int:
        return self.rows * self.cols


class SpriteAnimation:
    def __init__(self, sheet: SpriteSheet, fps: float = 12.0, loop: bool = True,
                 frame_indices: Optional[List[int]] = None):
        self.sheet = sheet
        self.fps = fps
        self.loop = loop
        self.frame_indices = frame_indices or list(range(sheet.frame_count))
        self._time = 0.0
        self.finished = False

    def update(self, dt: float):
        if self.finished:
            return
        self._time += dt
        total_frames = len(self.frame_indices)
        frame_pos = self._time * self.fps
        if frame_pos >= total_frames and not self.loop:
            self.finished = True

    def reset(self):
        self._time = 0.0
        self.finished = False

    def current_frame(self) -> pygame.Surface:
        total_frames = len(self.frame_indices)
        if total_frames == 0:
            return self.sheet.get_frame(0)
        frame_pos = int(self._time * self.fps)
        if self.loop:
            frame_pos %= total_frames
        else:
            frame_pos = min(frame_pos, total_frames - 1)
        return self.sheet.get_frame(self.frame_indices[frame_pos])


class MotionTrail:
    def __init__(self, max_length: int = 12, color: tuple = (255, 255, 255),
                 width: int = 3, fade: bool = True):
        self.points: List[Tuple[float, float]] = []
        self.max_length = max_length
        self.color = color
        self.width = width
        self.fade = fade

    def add_point(self, x: float, y: float):
        self.points.append((x, y))
        if len(self.points) > self.max_length:
            self.points.pop(0)

    def clear(self):
        self.points.clear()


class HealthBarAnimator:
    def __init__(self, initial_ratio: float = 1.0, catch_up_speed: float = 2.5):
        self.display_ratio = initial_ratio
        self.target_ratio = initial_ratio
        self.catch_up_speed = catch_up_speed
        self.flash_timer = 0.0

    def set_target(self, ratio: float):
        ratio = max(0.0, min(1.0, ratio))
        if ratio < self.target_ratio - 1e-4:
            self.flash_timer = 0.25
        self.target_ratio = ratio

    def update(self, dt: float):
        diff = self.target_ratio - self.display_ratio
        if abs(diff) > 1e-3:
            step = diff * min(1.0, dt * self.catch_up_speed * 4)
            self.display_ratio += step
        else:
            self.display_ratio = self.target_ratio
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)


class DamageFlash:
    def __init__(self):
        self.timer = 0.0
        self.duration = 0.12

    def trigger(self, duration: float = 0.12):
        self.timer = duration
        self.duration = duration

    def update(self, dt: float):
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)

    @property
    def active(self) -> bool:
        return self.timer > 0

    @property
    def strength(self) -> float:
        if self.duration <= 0:
            return 0.0
        return self.timer / self.duration


class ParallaxLayer:
    def __init__(self, surface: pygame.Surface, scroll_factor: float, y_offset: int = 0,
                 tile_x: bool = True, tile_y: bool = False):
        self.surface = surface
        self.scroll_factor = scroll_factor
        self.y_offset = y_offset
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.width = surface.get_width()
        self.height = surface.get_height()


class ScreenTransition:
    def __init__(self):
        self.active = False
        self.kind = 'fade'
        self.progress = 0.0
        self.duration = 0.5
        self._elapsed = 0.0
        self.color = (0, 0, 0)
        self.on_complete = None
        self.on_midpoint = None
        self._midpoint_fired = False

    def start(self, kind: str = 'fade', duration: float = 0.5, color: tuple = (0, 0, 0),
              on_complete=None, on_midpoint=None):
        self.active = True
        self.kind = kind
        self.duration = max(0.01, duration)
        self._elapsed = 0.0
        self.progress = 0.0
        self.color = color
        self.on_complete = on_complete
        self.on_midpoint = on_midpoint
        self._midpoint_fired = False

    def update(self, dt: float):
        if not self.active:
            return
        self._elapsed += dt
        self.progress = min(1.0, self._elapsed / self.duration)
        if not self._midpoint_fired and self.progress >= 0.5:
            self._midpoint_fired = True
            if self.on_midpoint:
                self.on_midpoint()
        if self.progress >= 1.0:
            self.active = False
            if self.on_complete:
                self.on_complete()

    def draw(self, surface: pygame.Surface):
        if not self.active and self.progress <= 0.0:
            return
        w, h = surface.get_size()
        if self.kind == 'fade':
            alpha = int(255 * math.sin(self.progress * math.pi))
            if alpha <= 0:
                return
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((*self.color[:3], alpha))
            surface.blit(overlay, (0, 0))
        elif self.kind in ('circle_in', 'circle_out'):
            max_radius = math.hypot(w / 2, h / 2)
            if self.kind == 'circle_out':
                radius = max_radius * self.progress
            else:
                radius = max_radius * (1 - self.progress)
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            mask.fill((*self.color[:3], 255))
            pygame.draw.circle(mask, (0, 0, 0, 0), (w // 2, h // 2), max(1, int(radius)))
            surface.blit(mask, (0, 0))


class WeatherSystem:
    def __init__(self, screen_width: int, screen_height: int):
        self.width = screen_width
        self.height = screen_height
        self.kind: Optional[str] = None
        self.intensity = 1.0
        self.quality_multiplier = 1.0
        self._particles: List[Dict[str, float]] = []
        self._max_particles = 0

    def set_weather(self, kind: Optional[str], intensity: float = 1.0):
        self.kind = kind
        self.intensity = max(0.0, min(2.0, intensity))
        self._respawn_all()

    def set_quality_multiplier(self, multiplier: float):
        self.quality_multiplier = max(0.0, min(1.0, multiplier))
        if self.kind:
            self._respawn_all()

    def _respawn_all(self):
        self._particles.clear()
        base_counts = {'rain': 150, 'snow': 90, 'sandstorm': 120}
        self._max_particles = int(base_counts.get(self.kind, 0) * self.intensity * self.quality_multiplier)
        for _ in range(self._max_particles):
            self._particles.append(self._spawn_particle())

    def _spawn_particle(self) -> Dict[str, float]:
        if self.kind == 'rain':
            return {'x': random.uniform(0, self.width), 'y': random.uniform(-self.height, 0),
                    'speed': random.uniform(650, 950), 'len': random.uniform(10, 22),
                    'drift': random.uniform(-40, -80)}
        elif self.kind == 'snow':
            return {'x': random.uniform(0, self.width), 'y': random.uniform(-self.height, 0),
                    'speed': random.uniform(40, 110), 'size': random.uniform(1.5, 3.5),
                    'drift': random.uniform(-20, 20), 'phase': random.uniform(0, math.tau)}
        else:
            return {'x': random.uniform(-50, self.width), 'y': random.uniform(0, self.height),
                    'speed': random.uniform(300, 600), 'size': random.uniform(1, 3),
                    'drift': random.uniform(-20, 20)}

    def update(self, dt: float):
        if not self.kind:
            return
        for p in self._particles:
            if self.kind == 'rain':
                p['y'] += p['speed'] * dt
                p['x'] += p['drift'] * dt
                if p['y'] > self.height:
                    p.update(self._spawn_particle())
                    p['y'] = random.uniform(-40, 0)
            elif self.kind == 'snow':
                p['phase'] += dt * 2.0
                p['y'] += p['speed'] * dt
                p['x'] += math.sin(p['phase']) * 20 * dt + p['drift'] * dt * 0.2
                if p['y'] > self.height:
                    p.update(self._spawn_particle())
                    p['y'] = random.uniform(-40, 0)
            else:
                p['x'] += p['speed'] * dt
                p['y'] += p['drift'] * dt
                if p['x'] > self.width + 20:
                    p.update(self._spawn_particle())
                    p['x'] = random.uniform(-50, -10)

    def draw(self, surface: pygame.Surface):
        if not self.kind:
            return
        if self.kind == 'rain':
            color = (170, 190, 220)
            for p in self._particles:
                x, y = p['x'], p['y']
                pygame.draw.line(surface, color, (x, y), (x + 2, y + p['len']), 1)
        elif self.kind == 'snow':
            color = (240, 240, 250)
            for p in self._particles:
                pygame.draw.circle(surface, color, (int(p['x']), int(p['y'])), max(1, int(p['size'])))
        else:
            color = (190, 160, 110)
            for p in self._particles:
                pygame.draw.circle(surface, color, (int(p['x']), int(p['y'])), max(1, int(p['size'])))
            haze = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            haze.fill((196, 164, 100, int(18 * self.intensity)))
            surface.blit(haze, (0, 0))


class Starfield:
    def __init__(self, width: int, height: int, quality_multiplier: float = 1.0):
        self.width = width
        self.height = height
        self.quality_multiplier = quality_multiplier
        self._layers: List[List[Dict[str, float]]] = []
        self._layer_specs = [
            {'count': 60, 'speed': 6, 'size': (1, 1), 'brightness': (40, 90), 'twinkle': False},
            {'count': 45, 'speed': 16, 'size': (1, 2), 'brightness': (90, 170), 'twinkle': True},
            {'count': 28, 'speed': 34, 'size': (1, 3), 'brightness': (170, 255), 'twinkle': True},
        ]
        self._build()
        self.shooting_stars: List[Dict[str, float]] = []
        self._shooting_timer = random.uniform(3.0, 7.0)
        self.dust: List[Dict[str, float]] = []
        for _ in range(int(18 * quality_multiplier)):
            self.dust.append(self._spawn_dust())
        self.scroll_x = 0.0
        self.scroll_y = 0.0
        self._t = 0.0

    def _build(self):
        self._layers.clear()
        for spec in self._layer_specs:
            count = max(1, int(spec['count'] * self.quality_multiplier))
            stars = []
            for _ in range(count):
                b0, b1 = spec['brightness']
                s0, s1 = spec['size']
                stars.append({
                    'x': random.uniform(0, self.width),
                    'y': random.uniform(0, self.height),
                    'brightness': random.uniform(b0, b1),
                    'size': random.uniform(s0, s1),
                    'phase': random.uniform(0, math.tau),
                    'speed': spec['speed'],
                    'twinkle': spec['twinkle'],
                })
            self._layers.append(stars)

    def _spawn_dust(self) -> Dict[str, float]:
        return {
            'x': random.uniform(0, self.width), 'y': random.uniform(0, self.height),
            'vx': random.uniform(-6, 6), 'vy': random.uniform(-4, 4),
            'size': random.uniform(1, 2), 'alpha': random.uniform(20, 60),
        }

    def set_quality_multiplier(self, multiplier: float):
        self.quality_multiplier = max(0.0, min(1.0, multiplier))
        self._build()

    def update(self, dt: float, scroll_dx: float = 0.0, scroll_dy: float = 0.0):
        self._t += dt
        self.scroll_x += scroll_dx
        self.scroll_y += scroll_dy

        for d in self.dust:
            d['x'] += d['vx'] * dt
            d['y'] += d['vy'] * dt
            if d['x'] < 0: d['x'] += self.width
            if d['x'] > self.width: d['x'] -= self.width
            if d['y'] < 0: d['y'] += self.height
            if d['y'] > self.height: d['y'] -= self.height

        self._shooting_timer -= dt
        if self._shooting_timer <= 0:
            self._shooting_timer = random.uniform(4.0, 10.0)
            y0 = random.uniform(0, self.height * 0.5)
            self.shooting_stars.append({
                'x': random.uniform(0, self.width), 'y': y0,
                'vx': random.uniform(220, 380), 'vy': random.uniform(90, 160),
                'life': 0.0, 'max_life': random.uniform(0.5, 0.9),
            })
        for s in self.shooting_stars:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['life'] += dt
        self.shooting_stars = [s for s in self.shooting_stars if s['life'] < s['max_life']]

    def draw(self, surface: pygame.Surface):
        w, h = self.width, self.height
        for stars in self._layers:
            for st in stars:
                speed = st['speed']
                x = (st['x'] - self.scroll_x * speed * 0.02) % w
                y = (st['y'] - self.scroll_y * speed * 0.02) % h
                brightness = st['brightness']
                if st['twinkle']:
                    brightness *= 0.6 + 0.4 * (0.5 + 0.5 * math.sin(self._t * 2.2 + st['phase']))
                c = _clamp255(brightness)
                color = (c, c, min(255, c + 25))
                size = max(1, int(st['size']))
                if size <= 1:
                    surface.set_at((int(x), int(y)), color)
                else:
                    pygame.draw.circle(surface, color, (int(x), int(y)), size)

        for s in self.shooting_stars:
            t = s['life'] / s['max_life']
            alpha = int(255 * (1 - t))
            tail_surf = pygame.Surface((60, 6), pygame.SRCALPHA)
            pygame.draw.line(tail_surf, (*Palette.NEON_CYAN, alpha), (0, 3), (60, 3), 2)
            angle = math.degrees(math.atan2(s['vy'], s['vx']))
            rotated = pygame.transform.rotate(tail_surf, -angle)
            rect = rotated.get_rect(center=(int(s['x']), int(s['y'])))
            surface.blit(rotated, rect)

        for d in self.dust:
            a = int(d['alpha'])
            dust_surf = pygame.Surface((int(d['size'] * 2) + 2, int(d['size'] * 2) + 2), pygame.SRCALPHA)
            pygame.draw.circle(dust_surf, (*Palette.NEON_BLUE, a), dust_surf.get_rect().center, max(1, int(d['size'])))
            surface.blit(dust_surf, (int(d['x']), int(d['y'])))


# ============================================================
#                         RENDERER
# ============================================================

class Renderer:
    """Централизованная система отрисовки — неоновый sci-fi roguelike стиль."""

    def __init__(self, game):
        self.game = game
        self.use_advanced = self._check_advanced_support()

        self._surface_cache: Dict[tuple, pygame.Surface] = {}
        self._glow_cache: Dict[tuple, pygame.Surface] = {}
        self._light_cache: Dict[tuple, pygame.Surface] = {}
        self._health_gradient_cache: Dict[tuple, pygame.Surface] = {}
        self._shape_cache: Dict[tuple, pygame.Surface] = {}

        self.background_layer = None
        self.game_layer = None
        self.foreground_layer = None
        self.lighting_layer = None
        self.ui_layer = None
        self._composite_layer = None

        self.screen_shake_offset = (0, 0)
        self._shake_intensity = 0.0
        self._shake_duration = 0.0
        self._shake_timer = 0.0
        self.flash_alpha = 0.0
        self._flash_peak_alpha = 0.0
        self.flash_color = (255, 255, 255)
        self.flash_timer = 0.0
        self._flash_duration = 0.2
        self._flash_pos: Optional[Tuple[int, int]] = None
        self.darkness_alpha = 0
        self.vignette_alpha = 0
        self.bloom_alpha = 0.35
        self.chromatic_aberration = 0.0
        self.color_grade: Optional[tuple] = None

        self.quality = 'high'
        self.antialiasing = True
        self.glow_enabled = True
        self.shadows_enabled = True
        self.particle_multiplier = 1.0

        self._time = 0.0

        self.lights: List[PointLight] = []
        self.ambient_color = (28, 26, 46)
        self.shadow_casters: List[pygame.Rect] = []

        self.parallax_layers: List[ParallaxLayer] = []
        self.parallax_scroll_x = 0.0
        self.parallax_scroll_y = 0.0

        self.transition = ScreenTransition()
        self.weather = WeatherSystem(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.starfield = Starfield(SCREEN_WIDTH, SCREEN_HEIGHT)

        self._particle_batches: Dict[str, List[Any]] = {}

        self.low_hp_ratio: float = 1.0
        self._critical_pulse_t = 0.0
        self._crack_seeds: List[float] = [random.uniform(0, math.tau) for _ in range(10)]

        self._levelup_bursts: List[Dict[str, float]] = []

        self._vignette_surface: Optional[pygame.Surface] = None

        self._notifications: List[Dict[str, Any]] = []

        self._init_layers()
        self._build_vignette_surface()

    def _check_advanced_support(self) -> bool:
        try:
            test = pygame.Surface((10, 10), pygame.SRCALPHA)
            test.fill((255, 0, 0, 128))
            test2 = pygame.Surface((10, 10))
            test2.blit(test, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            return True
        except Exception:
            return False

    def _init_layers(self):
        self.background_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.game_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.foreground_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.lighting_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.ui_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._composite_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # ==================== КАЧЕСТВО ====================

    def set_quality(self, quality: str):
        self.quality = quality
        if quality == 'low':
            self.glow_enabled = False
            self.shadows_enabled = False
            self.antialiasing = False
            self.particle_multiplier = 0.35
            self.bloom_alpha = 0.0
            self.chromatic_aberration = 0.0
        elif quality == 'medium':
            self.glow_enabled = True
            self.shadows_enabled = False
            self.antialiasing = True
            self.particle_multiplier = 0.7
            self.bloom_alpha = 0.2
            self.chromatic_aberration = 0.0
        else:
            self.glow_enabled = True
            self.shadows_enabled = True
            self.antialiasing = True
            self.particle_multiplier = 1.0
            self.bloom_alpha = 0.35

        self.weather.set_quality_multiplier(self.particle_multiplier)
        self.starfield.set_quality_multiplier(self.particle_multiplier)

    # ==================== КАДР ====================

    def begin_frame(self):
        self.game.screen.fill(Palette.BG_DEEP)
        self.background_layer.fill(Palette.BG_DEEP)
        self.game_layer.fill((0, 0, 0))
        self.foreground_layer.fill((0, 0, 0, 0))
        self.lighting_layer.fill((0, 0, 0, 0))
        self.ui_layer.fill((0, 0, 0, 0))
        self._particle_batches.clear()

    def end_frame(self):
        target = self._composite_layer
        target.fill((0, 0, 0))
        target.blit(self.background_layer, (0, 0))
        target.blit(self.game_layer, (0, 0))
        target.blit(self.foreground_layer, (0, 0))

        self._render_lighting()
        if self.lighting_layer is not None:
            target.blit(self.lighting_layer, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self.weather.draw(target)

        if self.quality != 'low':
            self._apply_bloom(target)
            self._apply_chromatic_aberration(target)
            self._apply_color_grade(target)

        offset = self.screen_shake_offset
        if offset != (0, 0):
            self.game.screen.fill((0, 0, 0))
            self.game.screen.blit(target, offset)
        else:
            self.game.screen.blit(target, (0, 0))

        self.game.screen.blit(self.ui_layer, (0, 0))

        if self.flash_alpha > 0:
            self._draw_radial_flash(self.game.screen)

        if self.vignette_alpha > 0 and self._vignette_surface is not None:
            self._vignette_surface.set_alpha(int(255 * self.vignette_alpha))
            self.game.screen.blit(self._vignette_surface, (0, 0))

        if self.low_hp_ratio < 0.3:
            self._draw_critical_overlay(self.game.screen)

        for burst in self._levelup_bursts:
            self._draw_levelup_burst(self.game.screen, burst)

        if self.darkness_alpha > 0:
            darkness = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            darkness.fill((0, 0, 0, int(self.darkness_alpha * 255)))
            self.game.screen.blit(darkness, (0, 0))

        self.transition.draw(self.game.screen)

        pygame.display.flip()

    # ==================== ФОН ====================

    def draw_background(self, surface: pygame.Surface = None):
        if surface is None:
            surface = self.background_layer

        if self.parallax_layers:
            self._draw_parallax_background(surface)
            return

        self._draw_gradient_sky(surface)

        if self.use_advanced and self.quality != 'low':
            self._draw_glow_grid(surface)
            self.starfield.draw(surface)
        else:
            self._draw_background_simple(surface)

    def _draw_gradient_sky(self, surface):
        shift = 0.5 + 0.5 * math.sin(self._time * 0.05)
        top = lerp_color(Palette.BG_DEEP, (18, 10, 30), shift)
        bottom = lerp_color(Palette.BG_MID, (10, 22, 34), 1 - shift)
        h = SCREEN_HEIGHT
        step = 3
        for y in range(0, h, step):
            t = y / h
            color = lerp_color(top, bottom, t)
            pygame.draw.rect(surface, color, (0, y, SCREEN_WIDTH, step))

    def _draw_glow_grid(self, surface):
        grid_size = 64
        pulse = 0.5 + 0.5 * math.sin(self._time * 0.8)
        alpha = int(10 + 8 * pulse)
        grid_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        color = (*Palette.NEON_CYAN[:3], alpha)
        off = int(self._time * 6) % grid_size
        for x in range(-grid_size, SCREEN_WIDTH + grid_size, grid_size):
            pygame.draw.line(grid_surf, color, (x + off, 0), (x + off, SCREEN_HEIGHT), 1)
        for y in range(-grid_size, SCREEN_HEIGHT + grid_size, grid_size):
            pygame.draw.line(grid_surf, color, (0, y), (SCREEN_WIDTH, y), 1)
        surface.blit(grid_surf, (0, 0))

    def _draw_background_simple(self, surface):
        surface.fill(Palette.BG_MID)
        for x in range(0, SCREEN_WIDTH, 50):
            pygame.draw.line(surface, (26, 30, 40), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 50):
            pygame.draw.line(surface, (26, 30, 40), (0, y), (SCREEN_WIDTH, y))

    def set_parallax_layers(self, layers: List[ParallaxLayer]):
        self.parallax_layers = layers

    def set_parallax_scroll(self, x: float, y: float = 0.0):
        dx = x - self.parallax_scroll_x
        dy = y - self.parallax_scroll_y
        self.parallax_scroll_x = x
        self.parallax_scroll_y = y
        self.starfield.update(0.0, dx, dy)

    def _draw_parallax_background(self, surface: pygame.Surface):
        surface.fill(Palette.BG_DEEP)
        for layer in self.parallax_layers:
            offset_x = int(-self.parallax_scroll_x * layer.scroll_factor) % layer.width
            base_y = layer.y_offset - int(self.parallax_scroll_y * layer.scroll_factor)
            y_positions = [base_y]
            if layer.tile_y:
                offset_y = base_y % layer.height
                y_positions = []
                y = -offset_y
                while y < SCREEN_HEIGHT:
                    y_positions.append(y)
                    y += layer.height
            for offset_y in y_positions:
                if layer.tile_x:
                    x = -offset_x
                    while x < SCREEN_WIDTH:
                        surface.blit(layer.surface, (x, offset_y))
                        x += layer.width
                else:
                    surface.blit(layer.surface, (offset_x, offset_y))
        self.starfield.draw(surface)

    # ==================== СВЕЧЕНИЕ ====================

    def draw_glow(self, surface, x: float, y: float, radius: int, color: tuple, alpha: int = 128):
        radius = int(radius)  # ← ФИКС: float → int
        if not self.glow_enabled or not self.use_advanced or radius <= 0:
            return
        key = (radius, color, alpha)
        if key not in self._glow_cache:
            glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for r in range(radius, 0, -1):
                a = int(alpha * (1 - r / radius) * (1 - r / radius))
                if HAS_GFXDRAW:
                    gfxdraw.filled_circle(glow_surf, radius, radius, r, (*color[:3], a))
                else:
                    pygame.draw.circle(glow_surf, (*color[:3], a), (radius, radius), r)
            self._glow_cache[key] = glow_surf
        surface.blit(self._glow_cache[key], (int(x - radius), int(y - radius)))

    def draw_rect_glow(self, surface, rect: pygame.Rect, color: tuple, alpha: int = 100, border_radius: int = 0):
        if not self.glow_enabled:
            return
        glow_rect = rect.inflate(8, 8)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*color[:3], alpha), glow_surf.get_rect(), border_radius=border_radius)
        surface.blit(glow_surf, glow_rect)

    def draw_line_glow(self, surface, start: tuple, end: tuple, color: tuple, width: int = 2):
        if not self.glow_enabled:
            pygame.draw.line(surface, color, start, end, width)
            return
        for w in range(width + 4, width, -2):
            pygame.draw.line(surface, (*color[:3], 40), start, end, w)
        pygame.draw.line(surface, color, start, end, width)

    def _polygon_glow(self, surface, points: List[Tuple[float, float]], color: tuple, alpha: int = 70, spread: int = 6):
        if not self.glow_enabled:
            return
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        for i in range(spread, 0, -2):
            expanded = []
            for px, py in points:
                dx, dy = px - cx, py - cy
                dist = math.hypot(dx, dy) or 1
                expanded.append((px + dx / dist * i, py + dy / dist * i))
            a = int(alpha * (1 - i / spread))
            glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(glow_surf, (*color[:3], a), expanded, width=3)
            surface.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # ==================== ДИНАМИЧЕСКОЕ ОСВЕЩЕНИЕ ====================

    def add_light(self, light: PointLight):
        self.lights.append(light)
        return light

    def remove_light(self, light: PointLight):
        if light in self.lights:
            self.lights.remove(light)

    def clear_lights(self):
        self.lights.clear()

    def add_shadow_caster(self, rect: pygame.Rect):
        self.shadow_casters.append(rect)
        return rect

    def remove_shadow_caster(self, rect: pygame.Rect):
        if rect in self.shadow_casters:
            self.shadow_casters.remove(rect)

    def clear_shadow_casters(self):
        self.shadow_casters.clear()

    def _render_lighting(self):
        layer = self.lighting_layer
        layer.fill((*self.ambient_color, 255))
        if not self.lights:
            return
        for light in self.lights:
            if not light.enabled:
                continue
            radius = light.current_radius(self._time)
            key = (radius, light.color, int(light.intensity * 100))
            if key not in self._light_cache:
                glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                for r in range(radius, 0, -1):
                    t = 1 - (r / radius)
                    a = int(255 * light.intensity * (t ** 1.5))
                    color = (min(255, int(light.color[0])), min(255, int(light.color[1])),
                             min(255, int(light.color[2])), a)
                    if HAS_GFXDRAW:
                        gfxdraw.filled_circle(glow, radius, radius, r, color)
                    else:
                        pygame.draw.circle(glow, color, (radius, radius), r)
                self._light_cache[key] = glow
            glow_surf = self._light_cache[key]
            layer.blit(glow_surf, (int(light.x - radius), int(light.y - radius)),
                       special_flags=pygame.BLEND_RGBA_ADD)

        if self.shadows_enabled and self.shadow_casters:
            for light in self.lights:
                if not light.enabled or not light.cast_shadows:
                    continue
                self._cast_shadows_for_light(layer, light)

    def _cast_shadows_for_light(self, layer: pygame.Surface, light: PointLight):
        for rect in self.shadow_casters:
            cx, cy = rect.center
            dx, dy = cx - light.x, cy - light.y
            dist = math.hypot(dx, dy)
            if dist < 1 or dist > light.radius * 1.5:
                continue
            length = light.radius * 0.8
            nx, ny = dx / dist, dy / dist
            corners = [rect.topleft, rect.topright, rect.bottomleft, rect.bottomright]
            projected = [(x + nx * length, y + ny * length) for x, y in corners]
            polygon = corners + projected[::-1]
            shadow_surf = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(shadow_surf, (0, 0, 0, 120), polygon)
            layer.blit(shadow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    # ==================== ПОСТ-ОБРАБОТКА ====================

    def _apply_bloom(self, surface: pygame.Surface):
        if self.bloom_alpha <= 0:
            return
        w, h = surface.get_size()
        scale = 4
        small = pygame.transform.smoothscale(surface, (max(1, w // scale), max(1, h // scale)))
        blurred = pygame.transform.smoothscale(small, (max(1, w // (scale * 2)), max(1, h // (scale * 2))))
        blurred = pygame.transform.smoothscale(blurred, (w, h))
        blurred.set_alpha(int(255 * self.bloom_alpha))
        surface.blit(blurred, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _apply_chromatic_aberration(self, surface: pygame.Surface):
        if self.chromatic_aberration <= 0:
            return
        offset = max(1, int(self.chromatic_aberration * 6))
        base = surface.copy()
        red_layer = base.copy()
        red_layer.fill((255, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        blue_layer = base.copy()
        blue_layer.fill((0, 0, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        red_layer.set_alpha(120)
        blue_layer.set_alpha(120)
        surface.blit(red_layer, (offset, 0), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(blue_layer, (-offset, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _apply_color_grade(self, surface: pygame.Surface):
        if not self.color_grade:
            return
        r, g, b = self.color_grade
        tint = pygame.Surface(surface.get_size())
        tint.fill((_clamp255(255 * r), _clamp255(255 * g), _clamp255(255 * b)))
        surface.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def set_color_grade(self, r: float = 1.0, g: float = 1.0, b: float = 1.0):
        self.color_grade = (r, g, b)

    def clear_color_grade(self):
        self.color_grade = None

    # ==================== ПОЛОСЫ (HP / ЭНЕРГИЯ / XP) ====================

    def _get_health_gradient(self, width: int, height: int, color: tuple) -> pygame.Surface:
        key = (width, height, color)
        cached = self._health_gradient_cache.get(key)
        if cached is not None:
            return cached
        strip = pygame.Surface((max(1, width), max(1, height - 4)))
        for i in range(max(1, width)):
            t = i / max(1, width)
            brightness = 0.7 + 0.3 * t
            grad_color = (min(255, int(color[0] * brightness)), min(255, int(color[1] * brightness)),
                          min(255, int(color[2] * brightness)))
            pygame.draw.line(strip, grad_color, (i, 0), (i, max(1, height - 4)))
        self._health_gradient_cache[key] = strip
        return strip

    def draw_health_bar(self, surface, x: int, y: int, width: int, height: int,
                         ratio: float, color: tuple, bg_color: tuple = (18, 20, 28)):
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, bg_color, (x, y, width, height), border_radius=3)
        fill_width = int(width * ratio)
        if fill_width > 0:
            gradient = self._get_health_gradient(width, height, color)
            surface.blit(gradient, (x, y + 2), area=pygame.Rect(0, 0, fill_width, gradient.get_height()))
        if self.use_advanced:
            highlight = pygame.Surface((width, height // 2), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 30))
            surface.blit(highlight, (x, y))
        pygame.draw.rect(surface, Palette.PANEL_BORDER, (x, y, width, height), 1, border_radius=3)

    def draw_animated_health_bar(self, surface, x: int, y: int, width: int, height: int,
                                  animator: HealthBarAnimator, color: tuple,
                                  bg_color: tuple = (18, 20, 28), damage_color: tuple = (200, 60, 60)):
        ratio = max(0.0, min(1.0, animator.display_ratio))
        target_ratio = max(0.0, min(1.0, animator.target_ratio))
        pygame.draw.rect(surface, bg_color, (x, y, width, height), border_radius=3)
        if target_ratio < ratio:
            damage_width = int(width * ratio)
            pygame.draw.rect(surface, damage_color, (x, y, damage_width, height), border_radius=3)
        fill_width = int(width * target_ratio if target_ratio < ratio else width * ratio)
        if fill_width > 0:
            gradient = self._get_health_gradient(width, height, color)
            surface.blit(gradient, (x, y + 2), area=pygame.Rect(0, 0, fill_width, gradient.get_height()))
        if self.use_advanced:
            highlight = pygame.Surface((width, height // 2), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 30))
            surface.blit(highlight, (x, y))
        border_color = Palette.PANEL_BORDER
        if animator.flash_timer > 0:
            flash_t = animator.flash_timer / 0.25
            border_color = lerp_color((255, 255, 255), (255, 80, 80), flash_t)
        pygame.draw.rect(surface, border_color, (x, y, width, height), 2, border_radius=3)

    def draw_stat_bar(self, surface, x: int, y: int, width: int, height: int, ratio: float,
                       color: tuple, icon: Optional[str] = None, label: Optional[str] = None):
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, (16, 18, 26, 200), (x, y, width, height), border_radius=height // 2)
        fill_w = int((width - 4) * ratio)
        if fill_w > 0:
            inner = pygame.Rect(x + 2, y + 2, fill_w, height - 4)
            pygame.draw.rect(surface, color, inner, border_radius=max(1, (height - 4) // 2))
            if self.glow_enabled:
                self.draw_rect_glow(surface, inner, color, alpha=60, border_radius=(height - 4) // 2)
        pygame.draw.rect(surface, with_alpha(color, 140), (x, y, width, height), 1, border_radius=height // 2)
        if icon == 'bolt':
            self._draw_icon_bolt(surface, x - 14, y + height // 2, color)
        elif icon == 'star':
            self._draw_icon_star(surface, x - 14, y + height // 2, color)
        if label:
            self.draw_text(surface, label, x, y - 16, 14, Palette.TEXT_DIM, shadow=False)

    # ==================== ЧАСТИЦЫ ====================

    def draw_particle(self, surface, particle):
        alpha = getattr(particle, 'alpha', 255)
        if alpha <= 0:
            return
        color = getattr(particle, 'color', Palette.TEXT_MAIN)
        size = max(1, int(getattr(particle, 'size', 3)))
        x = int(getattr(particle, 'x', 0))
        y = int(getattr(particle, 'y', 0))
        if self.use_advanced and size > 2 and alpha > 100:
            self.draw_glow(surface, x, y, size * 2, color, alpha // 3)
        if alpha >= 255:
            pygame.draw.circle(surface, color, (x, y), size)
        else:
            particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (*color[:3], alpha), (size, size), size)
            surface.blit(particle_surf, (x - size, y - size))

    def draw_particles_batch(self, surface, particles: List[Any]):
        if not particles:
            return
        limit = max(1, int(len(particles) * self.particle_multiplier))
        particles = particles[:limit] if self.particle_multiplier < 1.0 else particles

        opaque_groups: Dict[tuple, List[Tuple[int, int, int]]] = {}
        translucent: List[Any] = []

        for p in particles:
            alpha = int(getattr(p, 'alpha', 255))
            if alpha <= 0:
                continue
            color = getattr(p, 'color', Palette.TEXT_MAIN)
            size = max(1, int(getattr(p, 'size', 3)))
            x = int(getattr(p, 'x', 0))
            y = int(getattr(p, 'y', 0))
            if alpha >= 250:
                key = (color[0], color[1], color[2], size)
                opaque_groups.setdefault(key, []).append((x, y, size))
            else:
                translucent.append(p)

        for (r, g, b, size), points in opaque_groups.items():
            color = (r, g, b)
            if HAS_GFXDRAW:
                for x, y, s in points:
                    gfxdraw.filled_circle(surface, x, y, s, color)
                    if self.antialiasing:
                        gfxdraw.aacircle(surface, x, y, s, color)
            else:
                for x, y, s in points:
                    pygame.draw.circle(surface, color, (x, y), s)

        by_size: Dict[int, List[Any]] = {}
        for p in translucent:
            size = max(1, int(getattr(p, 'size', 3)))
            by_size.setdefault(size, []).append(p)

        for size, group in by_size.items():
            for p in group:
                color = getattr(p, 'color', Palette.TEXT_MAIN)
                alpha = int(getattr(p, 'alpha', 255))
                x = int(getattr(p, 'x', 0))
                y = int(getattr(p, 'y', 0))
                key = ('_p_batch', size, color, alpha)
                cached = self._glow_cache.get(key)
                if cached is None:
                    surf_dim = size * 2
                    cached = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
                    pygame.draw.circle(cached, (*color[:3], alpha), (size, size), size)
                    self._glow_cache[key] = cached
                surface.blit(cached, (x - size, y - size))

        if self.glow_enabled and self.quality == 'high':
            for p in particles:
                size = max(1, int(getattr(p, 'size', 3)))
                alpha = int(getattr(p, 'alpha', 255))
                if size > 3 and alpha > 150:
                    color = getattr(p, 'color', Palette.TEXT_MAIN)
                    x = int(getattr(p, 'x', 0))
                    y = int(getattr(p, 'y', 0))
                    self.draw_glow(surface, x, y, size * 2, color, alpha // 4)

    def draw_special_particle(self, surface, kind: str, x: float, y: float, size: float,
                               alpha: int = 255, angle: float = 0.0, color: Optional[tuple] = None):
        alpha = max(0, min(255, alpha))
        if alpha <= 0:
            return
        x, y = int(x), int(y)
        size = max(1.0, size)

        if kind == 'spark':
            c = color or Palette.NEON_GOLD
            length = size * 3
            dx, dy = math.cos(angle) * length, math.sin(angle) * length
            self.draw_line_glow(surface, (x - dx / 2, y - dy / 2), (x + dx / 2, y + dy / 2), with_alpha(c, alpha), 2)

        elif kind == 'smoke':
            c = color or (90, 90, 95)
            smoke_surf = pygame.Surface((int(size * 2) + 2, int(size * 2) + 2), pygame.SRCALPHA)
            pygame.draw.circle(smoke_surf, with_alpha(c, int(alpha * 0.5)), smoke_surf.get_rect().center, int(size))
            surface.blit(smoke_surf, (x - int(size), y - int(size)))

        elif kind == 'fire':
            c = color or Palette.NEON_ORANGE
            core = lerp_color(Palette.NEON_GOLD, (255, 255, 220), 0.4)
            self.draw_glow(surface, x, y, int(size * 2.2), c, alpha // 2)
            pygame.draw.circle(surface, with_alpha(core, alpha), (x, y), max(1, int(size * 0.5)))

        elif kind == 'ice_shard':
            c = color or (150, 220, 255)
            pts = []
            for i in range(6):
                a = angle + i * math.pi / 3
                r = size if i % 2 == 0 else size * 0.45
                pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
            shard_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(shard_surf, with_alpha(c, alpha), pts)
            pygame.draw.polygon(shard_surf, with_alpha((255, 255, 255), min(255, alpha + 40)), pts, 1)
            surface.blit(shard_surf, (0, 0))

        elif kind == 'electric_arc':
            c = color or Palette.NEON_CYAN
            length = size * 8
            segments = 6
            points = [(x, y)]
            for i in range(1, segments + 1):
                t = i / segments
                px = x + math.cos(angle) * length * t + random.uniform(-6, 6)
                py = y + math.sin(angle) * length * t + random.uniform(-6, 6)
                points.append((px, py))
            arc_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.lines(arc_surf, with_alpha(c, alpha), False, points, 2)
            surface.blit(arc_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            if self.glow_enabled:
                self.draw_glow(surface, points[-1][0], points[-1][1], int(size), c, alpha // 3)

    # ==================== СПРАЙТЫ И АНИМАЦИЯ ====================

    def draw_animated_sprite(self, surface, animation: SpriteAnimation, x: int, y: int,
                              flip_x: bool = False, flip_y: bool = False,
                              scale: float = 1.0, rotation: float = 0.0,
                              damage_flash: Optional[DamageFlash] = None):
        frame = animation.current_frame()
        if flip_x or flip_y:
            frame = pygame.transform.flip(frame, flip_x, flip_y)
        if scale != 1.0:
            w, h = frame.get_size()
            frame = pygame.transform.smoothscale(frame, (max(1, int(w * scale)), max(1, int(h * scale))))
        if rotation != 0.0:
            frame = pygame.transform.rotate(frame, rotation)
        if damage_flash is not None and damage_flash.active:
            frame = frame.copy()
            flash_alpha = int(255 * damage_flash.strength)
            white_overlay = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
            white_overlay.fill((255, 255, 255, flash_alpha))
            frame.blit(white_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        rect = frame.get_rect(center=(x, y))
        surface.blit(frame, rect)
        return rect

    def apply_damage_flash(self, sprite_surface: pygame.Surface, flash: DamageFlash) -> pygame.Surface:
        if not flash.active:
            return sprite_surface
        result = sprite_surface.copy()
        overlay = pygame.Surface(result.get_size(), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, int(255 * flash.strength)))
        result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return result

    # ==================== ХВОСТЫ ДВИЖЕНИЯ ====================

    def draw_trail(self, surface, trail: MotionTrail):
        points = trail.points
        n = len(points)
        if n < 2:
            return
        for i in range(1, n):
            t = i / n
            alpha = int(255 * t) if trail.fade else 255
            width = max(1, int(trail.width * t))
            start = points[i - 1]
            end = points[i]
            if alpha >= 250:
                pygame.draw.line(surface, trail.color, start, end, width)
            else:
                seg_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                pygame.draw.line(seg_surf, (*trail.color[:3], alpha), start, end, width)
                surface.blit(seg_surf, (0, 0))
        if self.glow_enabled and self.use_advanced:
            self.draw_glow(surface, points[-1][0], points[-1][1], trail.width * 3, trail.color, 90)

    # ==================== ТЕКСТ ====================

    def draw_text(self, surface, text: str, x: int, y: int, size: int,
                  color: tuple, shadow: bool = True, glow: bool = False):
        font = pygame.font.Font(None, size)
        if glow and self.use_advanced:
            glow_surf = font.render(text, True, (*color[:3],))
            glow_surf.set_alpha(60)
            surface.blit(glow_surf, (x - 2, y - 2))
            surface.blit(glow_surf, (x + 2, y - 2))
            surface.blit(glow_surf, (x - 2, y + 2))
            surface.blit(glow_surf, (x + 2, y + 2))
        if shadow:
            shadow_surf = font.render(text, True, (0, 0, 0))
            surface.blit(shadow_surf, (x + 2, y + 2))
        text_surf = font.render(text, True, color)
        surface.blit(text_surf, (x, y))
        return text_surf.get_width(), text_surf.get_height()

    # ==================== ЭФФЕКТЫ ЭКРАНА ====================

    def add_flash(self, color: tuple = None, alpha: float = 0.5, duration: float = 0.2,
                  pos: Optional[Tuple[int, int]] = None):
        self.flash_alpha = alpha
        self._flash_peak_alpha = alpha
        self.flash_color = color if color is not None else (255, 255, 255)
        self.flash_timer = duration
        self._flash_duration = max(0.0001, duration)
        self._flash_pos = pos

    def _draw_radial_flash(self, surface: pygame.Surface):
        cx, cy = self._flash_pos if self._flash_pos else (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        max_r = int(math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.7)
        flash_surf = pygame.Surface((max_r * 2, max_r * 2), pygame.SRCALPHA)
        for r in range(max_r, 0, -max(2, max_r // 40)):
            a = int(self.flash_alpha * 255 * (1 - r / max_r) ** 2)
            pygame.draw.circle(flash_surf, (*self.flash_color[:3], a), (max_r, max_r), r)
        surface.blit(flash_surf, (cx - max_r, cy - max_r), special_flags=pygame.BLEND_RGBA_ADD)

    def set_darkness(self, alpha: float):
        self.darkness_alpha = max(0.0, min(1.0, alpha))

    def set_vignette(self, alpha: float):
        self.vignette_alpha = max(0.0, min(1.0, alpha))

    def set_low_hp_ratio(self, ratio: float):
        self.low_hp_ratio = max(0.0, min(1.0, ratio))

    def set_screen_shake(self, intensity: float, duration: float = 0.15):
        if intensity > 0:
            self._shake_intensity = intensity
            self._shake_duration = max(0.0001, duration)
            self._shake_timer = duration
        else:
            self._shake_intensity = 0.0
            self._shake_duration = 0.0
            self._shake_timer = 0.0
            self.screen_shake_offset = (0, 0)

    def trigger_levelup_burst(self, x: Optional[int] = None, y: Optional[int] = None, duration: float = 0.9):
        cx = x if x is not None else SCREEN_WIDTH // 2
        cy = y if y is not None else SCREEN_HEIGHT // 2
        self._levelup_bursts.append({
            'x': cx, 'y': cy, 'life': 0.0, 'duration': duration,
            'particles': [
                {'angle': random.uniform(0, math.tau), 'speed': random.uniform(120, 320),
                 'size': random.uniform(2, 4)} for _ in range(24)
            ],
        })

    def _draw_levelup_burst(self, surface: pygame.Surface, burst: Dict[str, float]):
        t = burst['life'] / burst['duration']
        ring_r = int(t * 220)
        alpha = int(255 * (1 - t))
        if alpha > 0:
            ring_surf = pygame.Surface((ring_r * 2 + 4, ring_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, with_alpha(Palette.NEON_GOLD, alpha), (ring_r + 2, ring_r + 2), ring_r, 4)
            surface.blit(ring_surf, (int(burst['x'] - ring_r - 2), int(burst['y'] - ring_r - 2)),
                         special_flags=pygame.BLEND_RGBA_ADD)
        for p in burst['particles']:
            dist = p['speed'] * t
            px = burst['x'] + math.cos(p['angle']) * dist
            py = burst['y'] + math.sin(p['angle']) * dist
            pa = int(255 * (1 - t))
            if pa > 0:
                self.draw_special_particle(surface, 'spark', px, py, p['size'], pa, p['angle'], Palette.NEON_GOLD)

    def _draw_critical_overlay(self, surface: pygame.Surface):
        severity = 1.0 - (self.low_hp_ratio / 0.3)
        pulse = 0.5 + 0.5 * math.sin(self._critical_pulse_t * 4.0)
        alpha = int(70 + 90 * severity * pulse)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        step = 26
        max_i = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 2
        for i in range(0, max_i, step):
            a = int(alpha * (i / max_i))
            pygame.draw.rect(overlay, (140, 10, 20, a),
                              (i, i, SCREEN_WIDTH - i * 2, SCREEN_HEIGHT - i * 2), step)
        surface.blit(overlay, (0, 0))

        vein_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        vein_alpha = int(90 + 110 * severity * pulse)
        for seed in self._crack_seeds:
            edge = int(seed * 4) % 4
            if edge == 0:
                start = (random.Random(seed).uniform(0, SCREEN_WIDTH), 0)
            elif edge == 1:
                start = (SCREEN_WIDTH, random.Random(seed).uniform(0, SCREEN_HEIGHT))
            elif edge == 2:
                start = (random.Random(seed).uniform(0, SCREEN_WIDTH), SCREEN_HEIGHT)
            else:
                start = (0, random.Random(seed).uniform(0, SCREEN_HEIGHT))
            points = [start]
            cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
            steps = 5
            for i in range(1, steps + 1):
                t = i / steps
                jitter = math.sin(seed * 12 + i + self._critical_pulse_t) * 18
                px = start[0] + (cx - start[0]) * t * 0.4 + jitter
                py = start[1] + (cy - start[1]) * t * 0.4 + jitter
                points.append((px, py))
            pygame.draw.lines(vein_surf, (200, 20, 30, vein_alpha), False, points, 2)
        surface.blit(vein_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # ==================== ПЕРЕХОДЫ МЕЖДУ ЭКРАНАМИ ====================

    def start_fade(self, duration: float = 0.5, color: tuple = (0, 0, 0), on_midpoint=None, on_complete=None):
        self.transition.start('fade', duration, color, on_complete=on_complete, on_midpoint=on_midpoint)

    def start_circle_wipe(self, opening: bool = True, duration: float = 0.6, color: tuple = (0, 0, 0),
                           on_complete=None):
        kind = 'circle_in' if opening else 'circle_out'
        self.transition.start(kind, duration, color, on_complete=on_complete)

    # ==================== ПОГОДА ====================

    def set_weather(self, kind: Optional[str], intensity: float = 1.0):
        self.weather.set_weather(kind, intensity)

    # ==================== ВИНЬЕТКА ====================

    def _build_vignette_surface(self):
        vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        step = 30
        for i in range(0, SCREEN_WIDTH // 2, step):
            alpha = int(255 * (i / (SCREEN_WIDTH // 2)))
            pygame.draw.rect(vignette, (0, 0, 0, alpha),
                              (i, i, SCREEN_WIDTH - i * 2, SCREEN_HEIGHT - i * 2), step)
        self._vignette_surface = vignette

    # ==================== ИГРОК ====================

    def draw_player(self, surface, x: float, y: float, angle: float = 0.0,
                     thrust: bool = False, shield_active: bool = False,
                     hit_flash: Optional[DamageFlash] = None, radius: int = 20,
                     color: tuple = None):
        color = color or Palette.NEON_CYAN
        pulse = 0.5 + 0.5 * math.sin(self._time * 6.0)

        if thrust:
            flame_len = radius * (1.1 + 0.3 * random.uniform(0, 1))
            back_angle = angle + math.pi
            bx = x + math.cos(back_angle) * radius * 0.8
            by = y + math.sin(back_angle) * radius * 0.8
            for i, spread in enumerate((-0.18, 0.0, 0.18)):
                a = back_angle + spread
                fx = bx + math.cos(a) * flame_len * (0.7 if spread else 1.0)
                fy = by + math.sin(a) * flame_len * (0.7 if spread else 1.0)
                flame_color = Palette.NEON_ORANGE if i != 1 else Palette.NEON_GOLD
                self.draw_line_glow(surface, (bx, by), (fx, fy), with_alpha(flame_color, 200), 4)

        if shield_active:
            hex_r = radius * 1.7
            pts = []
            for i in range(6):
                a = self._time * 1.5 + i * math.pi / 3
                pts.append((x + math.cos(a) * hex_r, y + math.sin(a) * hex_r))
            self._polygon_glow(surface, pts, Palette.NEON_BLUE, alpha=90, spread=8)
            shield_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(shield_surf, with_alpha(Palette.NEON_BLUE, 40), pts)
            pygame.draw.polygon(shield_surf, with_alpha(Palette.NEON_CYAN, 160), pts, 2)
            surface.blit(shield_surf, (0, 0))

        nose = (x + math.cos(angle) * radius, y + math.sin(angle) * radius)
        left = (x + math.cos(angle + 2.5) * radius * 0.75, y + math.sin(angle + 2.5) * radius * 0.75)
        right = (x + math.cos(angle - 2.5) * radius * 0.75, y + math.sin(angle - 2.5) * radius * 0.75)
        hull_color = color if not (hit_flash and hit_flash.active) else lerp_color(color, (255, 255, 255), hit_flash.strength)

        self._polygon_glow(surface, [nose, left, right], hull_color, alpha=80, spread=6)
        hull_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(hull_surf, with_alpha((14, 18, 26), 255), [nose, left, right])
        pygame.draw.polygon(hull_surf, with_alpha(hull_color, 255), [nose, left, right], 2)
        surface.blit(hull_surf, (0, 0))

        core_r = max(2, int(radius * 0.28 * (0.85 + 0.15 * pulse)))
        self.draw_glow(surface, x, y, core_r * 3, hull_color, 140)
        pygame.draw.circle(surface, with_alpha((255, 255, 255), 230), (int(x), int(y)), core_r)
        pygame.draw.circle(surface, hull_color, (int(x), int(y)), max(1, core_r - 2))

    # ==================== ВРАГИ ====================

    def draw_enemy(self, surface, kind: str, x: float, y: float, angle: float = 0.0,
                    hp_ratio: float = 1.0, hit_flash: Optional[DamageFlash] = None,
                    radius: int = 18, targeting: bool = False, target_pos: Optional[Tuple[float, float]] = None,
                    phase: int = 0):
        flash_t = hit_flash.strength if (hit_flash and hit_flash.active) else 0.0
        handlers = {
            'basic': self._draw_enemy_basic,
            'fast': self._draw_enemy_fast,
            'tank': self._draw_enemy_tank,
            'shooter': self._draw_enemy_shooter,
            'elite': self._draw_enemy_elite,
            'boss': self._draw_enemy_boss,
        }
        fn = handlers.get(kind, self._draw_enemy_basic)
        fn(surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase)

    def _rim_light(self, base_color: tuple, flash_t: float) -> tuple:
        c = lerp_color(base_color, (255, 255, 255), 0.5)
        if flash_t > 0:
            c = lerp_color(c, (255, 255, 255), flash_t)
        return c

    def _draw_enemy_basic(self, surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase):
        base = lerp_color(Palette.NEON_RED, (60, 10, 20), 0.3)
        body_color = lerp_color(base, (255, 255, 255), flash_t)
        self.draw_glow(surface, x, y, int(radius * 2), Palette.NEON_RED, 70)
        pygame.draw.circle(surface, body_color, (int(x), int(y)), radius)
        pygame.draw.circle(surface, self._rim_light(base, flash_t), (int(x), int(y)), radius, 2)

        ring_r = radius + 6
        for i in range(8):
            a = self._time * 2.4 + i * (math.tau / 8)
            rx = x + math.cos(a) * ring_r
            ry = y + math.sin(a) * ring_r
            pygame.draw.circle(surface, with_alpha(Palette.NEON_RED, 200), (int(rx), int(ry)), 2)

        eye_pulse = 0.6 + 0.4 * math.sin(self._time * 5)
        eye_color = lerp_color(Palette.NEON_RED, (255, 220, 220), eye_pulse * 0.5)
        pygame.draw.circle(surface, eye_color, (int(x), int(y)), max(2, radius // 3))
        self._draw_hp_pip(surface, x, y - radius - 10, hp_ratio, Palette.NEON_RED)

    def _draw_enemy_fast(self, surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase):
        base = lerp_color(Palette.NEON_MAGENTA, (60, 10, 45), 0.25)
        color = lerp_color(base, (255, 255, 255), flash_t)
        nose = (x + math.cos(angle) * radius * 1.3, y + math.sin(angle) * radius * 1.3)
        left = (x + math.cos(angle + 2.6) * radius * 0.7, y + math.sin(angle + 2.6) * radius * 0.7)
        right = (x + math.cos(angle - 2.6) * radius * 0.7, y + math.sin(angle - 2.6) * radius * 0.7)
        self._polygon_glow(surface, [nose, left, right], Palette.NEON_MAGENTA, alpha=90, spread=8)
        pygame.draw.polygon(surface, color, [nose, left, right])
        pygame.draw.polygon(surface, self._rim_light(base, flash_t), [nose, left, right], 2)
        self._draw_hp_pip(surface, x, y - radius - 10, hp_ratio, Palette.NEON_MAGENTA)

    def _draw_enemy_tank(self, surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase):
        base = lerp_color((90, 95, 105), (30, 30, 35), 0.2)
        color = lerp_color(base, (255, 255, 255), flash_t)
        pts = [(x + math.cos(math.pi / 3 * i) * radius * 1.2, y + math.sin(math.pi / 3 * i) * radius * 1.2)
               for i in range(6)]
        self._polygon_glow(surface, pts, (140, 40, 40), alpha=50, spread=6)
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, self._rim_light(base, flash_t), pts, 3)

        for px, py in pts:
            pygame.draw.circle(surface, (200, 200, 210), (int(px), int(py)), 3)
            pygame.draw.circle(surface, (60, 60, 65), (int(px), int(py)), 3, 1)

        pulse = 0.5 + 0.5 * math.sin(self._time * 1.6)
        core_color = lerp_color(Palette.NEON_RED, (120, 10, 10), 1 - pulse)
        self.draw_glow(surface, x, y, int(radius * 0.9), Palette.NEON_RED, int(80 * pulse))
        pygame.draw.circle(surface, core_color, (int(x), int(y)), max(2, radius // 3))
        self._draw_hp_pip(surface, x, y - radius - 14, hp_ratio, (200, 60, 60))

    def _draw_enemy_shooter(self, surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase):
        base = lerp_color(Palette.NEON_GOLD, (60, 45, 5), 0.25)
        color = lerp_color(base, (255, 255, 255), flash_t)
        rect = pygame.Rect(0, 0, int(radius * 1.6), int(radius * 1.6))
        rect.center = (int(x), int(y))
        glow_rect = rect.inflate(6, 6)
        self.draw_rect_glow(surface, glow_rect, Palette.NEON_GOLD, alpha=60)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, self._rim_light(base, flash_t), rect, 2, border_radius=4)

        turret_angle = angle
        turret_len = radius * 1.1
        tx = x + math.cos(turret_angle) * turret_len
        ty = y + math.sin(turret_angle) * turret_len
        pygame.draw.line(surface, (40, 40, 45), (x, y), (tx, ty), 6)
        pygame.draw.line(surface, Palette.NEON_GOLD, (x, y), (tx, ty), 2)

        if targeting and target_pos:
            dash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(dash_surf, with_alpha(Palette.NEON_RED, 140), (x, y), target_pos, 1)
            surface.blit(dash_surf, (0, 0))
        self._draw_hp_pip(surface, x, y - radius - 12, hp_ratio, Palette.NEON_GOLD)

    def _draw_enemy_elite(self, surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase):
        base = lerp_color(Palette.NEON_ORANGE, (70, 30, 0), 0.2)
        color = lerp_color(base, (255, 255, 255), flash_t)
        diamond = [(x, y - radius * 1.3), (x + radius, y), (x, y + radius * 1.3), (x - radius, y)]
        pulse = 0.5 + 0.5 * math.sin(self._time * 3.0)
        self._polygon_glow(surface, diamond, Palette.NEON_ORANGE, alpha=int(60 + 40 * pulse), spread=10)
        pygame.draw.polygon(surface, color, diamond)
        pygame.draw.polygon(surface, self._rim_light(base, flash_t), diamond, 2)

        for i in range(8):
            a = self._time * 2.0 + i * (math.tau / 8)
            spike_r1 = radius * 1.4
            spike_r2 = radius * 1.9
            x1, y1 = x + math.cos(a) * spike_r1, y + math.sin(a) * spike_r1
            x2, y2 = x + math.cos(a) * spike_r2, y + math.sin(a) * spike_r2
            self.draw_line_glow(surface, (x1, y1), (x2, y2), with_alpha(Palette.NEON_ORANGE, 220), 2)
        self._draw_hp_pip(surface, x, y - radius - 18, hp_ratio, Palette.NEON_ORANGE)

    def _draw_enemy_boss(self, surface, x, y, angle, hp_ratio, flash_t, radius, targeting, target_pos, phase):
        phase_colors = [Palette.NEON_CYAN, Palette.NEON_MAGENTA, Palette.NEON_RED]
        base = phase_colors[min(phase, len(phase_colors) - 1)]
        color = lerp_color(base, (255, 255, 255), flash_t)

        for ring_i, mult in enumerate((1.6, 1.3, 1.0)):
            ring_r = radius * mult
            ring_color = lerp_color(base, (10, 10, 15), ring_i * 0.15)
            dashes = 20
            for i in range(dashes):
                a0 = self._time * (1.2 - ring_i * 0.3) * (1 if ring_i % 2 == 0 else -1) + i * (math.tau / dashes)
                a1 = a0 + (math.tau / dashes) * 0.6
                p0 = (x + math.cos(a0) * ring_r, y + math.sin(a0) * ring_r)
                p1 = (x + math.cos(a1) * ring_r, y + math.sin(a1) * ring_r)
                pygame.draw.line(surface, with_alpha(ring_color, 200), p0, p1, 3)

        core_r = radius
        self._polygon_glow(surface, [
            (x + math.cos(a) * core_r, y + math.sin(a) * core_r)
            for a in (i * math.tau / 10 for i in range(10))
        ], base, alpha=90, spread=12)
        pygame.draw.circle(surface, color, (int(x), int(y)), core_r)
        pygame.draw.circle(surface, self._rim_light(base, flash_t), (int(x), int(y)), core_r, 3)

        eye_positions = [(-0.4, -0.2), (0.4, -0.2), (0.0, 0.35)]
        for ex, ey in eye_positions:
            eyex, eyey = x + ex * radius, y + ey * radius
            pulse = 0.5 + 0.5 * math.sin(self._time * 4 + ex * 3)
            eye_color = lerp_color(Palette.NEON_RED, (255, 240, 240), pulse * 0.4)
            pygame.draw.circle(surface, (15, 15, 20), (int(eyex), int(eyey)), max(3, radius // 5))
            pygame.draw.circle(surface, eye_color, (int(eyex), int(eyey)), max(2, radius // 7))

        self._draw_hp_pip(surface, x, y - radius - 26, hp_ratio, base, wide=True)

    def _draw_hp_pip(self, surface, x, y, ratio, color, wide: bool = False):
        w = 46 if wide else 30
        h = 5
        self.draw_health_bar(surface, int(x - w / 2), int(y), w, h, ratio, color)

    def spawn_death_burst(self, particle_system, x: float, y: float, color: tuple, count: int = 18):
        spawner = getattr(particle_system, 'spawn', None) or getattr(particle_system, 'add', None)
        if not callable(spawner):
            return
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(60, 220)
            kind = 'spark' if random.random() < 0.6 else 'smoke'
            spawner(x=x, y=y, vx=math.cos(angle) * speed, vy=math.sin(angle) * speed,
                    color=color, kind=kind, size=random.uniform(2, 4), life=random.uniform(0.3, 0.7))

    # ==================== ПРОЕКТИЛИ ====================

    def draw_projectile_player(self, surface, x: float, y: float, angle: float,
                                color: tuple = None, length: int = 16, width: int = 4,
                                trail: Optional[MotionTrail] = None):
        color = color or Palette.NEON_CYAN
        if trail:
            self.draw_trail(surface, trail)
        tail = (x - math.cos(angle) * length, y - math.sin(angle) * length)
        head = (x + math.cos(angle) * length * 0.3, y + math.sin(angle) * length * 0.3)
        self.draw_line_glow(surface, tail, head, color, width)
        pygame.draw.circle(surface, (255, 255, 255), (int(head[0]), int(head[1])), max(1, width // 2))

    def draw_projectile_enemy(self, surface, x: float, y: float, radius: int = 6,
                               color: tuple = None):
        color = color or Palette.NEON_ORANGE
        self.draw_glow(surface, x, y, int(radius * 3), color, 130)
        pygame.draw.circle(surface, lerp_color(color, (255, 255, 255), 0.3), (int(x), int(y)), radius)
        pygame.draw.circle(surface, (30, 10, 10), (int(x), int(y)), radius, 1)

    def draw_muzzle_flash(self, surface, x: float, y: float, angle: float, color: tuple = None, size: int = 14):
        color = color or Palette.NEON_GOLD
        for i in range(3):
            a = angle + random.uniform(-0.3, 0.3)
            r = size * random.uniform(0.5, 1.0)
            ex = x + math.cos(a) * r
            ey = y + math.sin(a) * r
            self.draw_line_glow(surface, (x, y), (ex, ey), with_alpha(color, 220), 3)
        self.draw_glow(surface, x, y, size, color, 200)

    # ==================== ПРЕПЯТСТВИЯ ====================

    def draw_obstacle_barrel(self, surface, x: float, y: float, width: int = 26, height: int = 34,
                              warning: bool = True):
        rect = pygame.Rect(0, 0, int(width), int(height))
        rect.center = (int(x), int(y))
        self._draw_soft_shadow(surface, rect)

        body = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for i in range(rect.width):
            t = i / max(1, rect.width)
            shade = lerp_color((70, 72, 78), (110, 112, 118), math.sin(t * math.pi))
            pygame.draw.line(body, shade, (i, 4), (i, rect.height - 4))
        pygame.draw.rect(body, (40, 42, 48), (0, 0, rect.width, rect.height), 2, border_radius=4)
        for stripe_y in (rect.height * 0.28, rect.height * 0.72):
            stripe_rect = pygame.Rect(2, int(stripe_y) - 3, rect.width - 4, 6)
            for sx in range(stripe_rect.left, stripe_rect.right, 8):
                col = Palette.NEON_GOLD if (sx // 8) % 2 == 0 else (25, 25, 28)
                pygame.draw.rect(body, col, (sx, stripe_rect.top, 8, stripe_rect.height))
        surface.blit(body, rect.topleft)

        if warning:
            blink = 0.5 + 0.5 * math.sin(self._time * 8.0)
            light_color = lerp_color((60, 5, 5), Palette.NEON_RED, blink)
            self.draw_glow(surface, x, rect.top + 6, 10, Palette.NEON_RED, int(120 * blink))
            pygame.draw.circle(surface, light_color, (int(x), rect.top + 6), 4)

    def draw_obstacle_crate(self, surface, x: float, y: float, size: int = 32):
        size = int(size)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(x), int(y))
        self._draw_soft_shadow(surface, rect)

        wood_light = (120, 84, 46)
        wood_dark = (80, 54, 28)
        crate_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        plank_h = size // 4
        for i in range(4):
            shade = wood_light if i % 2 == 0 else wood_dark
            pygame.draw.rect(crate_surf, shade, (0, i * plank_h, size, plank_h))
            pygame.draw.line(crate_surf, (50, 34, 18), (0, i * plank_h), (size, i * plank_h), 1)
        pygame.draw.rect(crate_surf, (55, 38, 20), (0, 0, size, size), 2)

        corner = size // 5
        for cx, cy in ((0, 0), (size - corner, 0), (0, size - corner), (size - corner, size - corner)):
            pygame.draw.rect(crate_surf, (150, 150, 158), (cx, cy, corner, corner), border_radius=2)
            pygame.draw.rect(crate_surf, (90, 90, 96), (cx, cy, corner, corner), 1, border_radius=2)

        pygame.draw.line(crate_surf, Palette.NEON_GOLD, (size * 0.3, size * 0.5), (size * 0.7, size * 0.5), 2)
        pygame.draw.line(crate_surf, Palette.NEON_GOLD, (size * 0.5, size * 0.3), (size * 0.5, size * 0.7), 2)

        surface.blit(crate_surf, rect.topleft)

    def draw_obstacle_wall(self, surface, rect: pygame.Rect, cracked: bool = True, mossy: bool = True):
        self._draw_soft_shadow(surface, rect, offset=6)
        wall_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        wall_surf.fill((58, 52, 50))
        brick_w, brick_h = 22, 12
        for row, y0 in enumerate(range(0, rect.height, brick_h)):
            offset_x = (brick_w // 2) if row % 2 == 0 else 0
            for x0 in range(-brick_w, rect.width + brick_w, brick_w):
                brick_rect = pygame.Rect(x0 + offset_x, y0, brick_w - 2, brick_h - 2)
                shade = random.Random(hash((row, x0))).uniform(0.85, 1.1)
                color = tuple(_clamp255(c * shade) for c in (96, 68, 58))
                pygame.draw.rect(wall_surf, color, brick_rect)
                pygame.draw.rect(wall_surf, (40, 32, 30), brick_rect, 1)

        if cracked:
            rnd = random.Random(int(rect.x * 7 + rect.y * 13))
            for _ in range(3):
                x0 = rnd.uniform(0, rect.width)
                y0 = rnd.uniform(0, rect.height)
                pts = [(x0, y0)]
                for _ in range(4):
                    x0 += rnd.uniform(-14, 14)
                    y0 += rnd.uniform(4, 14)
                    pts.append((x0, y0))
                pygame.draw.lines(wall_surf, (20, 16, 16), False, pts, 1)

        if mossy:
            rnd = random.Random(int(rect.x * 3 + rect.y * 5) + 1)
            for _ in range(6):
                mx = rnd.uniform(0, rect.width)
                my = rnd.uniform(rect.height * 0.6, rect.height)
                pygame.draw.circle(wall_surf, (60, 90, 50), (int(mx), int(my)), rnd.randint(3, 6))

        surface.blit(wall_surf, rect.topleft)

    def _draw_soft_shadow(self, surface, rect: pygame.Rect, offset: int = 4):
        shadow_surf = pygame.Surface((rect.width + offset * 2, rect.height // 2 + offset), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), shadow_surf.get_rect())
        pos = (rect.centerx - shadow_surf.get_width() // 2, rect.bottom - shadow_surf.get_height() // 2)
        surface.blit(shadow_surf, pos)

    # ==================== ПОДБИРАЕМЫЕ ПРЕДМЕТЫ ====================

    def draw_pickup_medkit(self, surface, x: float, y: float, size: int = 22):
        size = int(size)
        pulse = 0.5 + 0.5 * math.sin(self._time * 3.0)
        self.draw_glow(surface, x, y, int(size * 1.6), Palette.NEON_GREEN, int(90 * pulse))
        rect = pygame.Rect(0, 0, size, int(size * 0.75))
        rect.center = (int(x), int(y))
        pygame.draw.rect(surface, (235, 235, 235), rect, border_radius=3)
        pygame.draw.rect(surface, (160, 160, 165), rect, 2, border_radius=3)
        cross_w = size * 0.14
        pygame.draw.rect(surface, Palette.NEON_RED, (rect.centerx - cross_w / 2, rect.top + 3, cross_w, rect.height - 6))
        pygame.draw.rect(surface, Palette.NEON_RED, (rect.left + 3, rect.centery - cross_w / 2, rect.width - 6, cross_w))

    def draw_pickup_scrap(self, surface, x: float, y: float, size: int = 16):
        size = int(size)
        teeth = 8
        outer = size * 0.5
        inner = size * 0.32
        pts = []
        for i in range(teeth * 2):
            r = outer if i % 2 == 0 else inner
            a = i * math.pi / teeth + self._time * 1.2
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surface, (150, 152, 158), pts)
        pygame.draw.polygon(surface, (90, 92, 98), pts, 1)
        pygame.draw.circle(surface, (70, 72, 78), (int(x), int(y)), int(inner * 0.7))
        pygame.draw.circle(surface, (210, 212, 220), (int(x - size * 0.15), int(y - size * 0.15)), max(1, int(size * 0.1)))

    def draw_pickup_energy_cell(self, surface, x: float, y: float, size: int = 18):
        size = int(size)
        w, h = int(size * 0.7), int(size * 1.3)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(x), int(y))
        self.draw_glow(surface, x, y, int(size * 1.5), Palette.NEON_BLUE, 120)
        pygame.draw.rect(surface, lerp_color(Palette.NEON_BLUE, (10, 20, 40), 0.3), rect, border_radius=int(w / 2))
        pygame.draw.rect(surface, Palette.NEON_BLUE, rect, 2, border_radius=int(w / 2))
        self._draw_icon_bolt(surface, x, y, (255, 255, 255))

    def draw_pickup_crystal(self, surface, x: float, y: float, size: int = 16):
        size = int(size)
        rot = self._time * 1.0
        facets = 6
        pts = [(x + math.cos(rot + i * math.tau / facets) * size,
                y + math.sin(rot + i * math.tau / facets) * size * 1.3) for i in range(facets)]
        hue = (self._time * 40) % 360
        base_color = pygame.Color(0)
        base_color.hsva = (hue, 60, 100, 100)
        self._polygon_glow(surface, pts, tuple(base_color)[:3], alpha=70, spread=6)
        pygame.draw.polygon(surface, with_alpha(tuple(base_color)[:3], 200), pts)
        pygame.draw.polygon(surface, (255, 255, 255), pts, 1)
        glint_color = pygame.Color(0)
        glint_color.hsva = ((hue + 120) % 360, 40, 100, 100)
        pygame.draw.line(surface, tuple(glint_color)[:3], pts[0], (x, y), 1)

    def draw_pickup_weapon(self, surface, x: float, y: float, icon: str = 'blaster', size: int = 20):
        size = int(size)
        bob = math.sin(self._time * 2.5) * 4
        y = y + bob
        pulse = 0.5 + 0.5 * math.sin(self._time * 2.0)
        self.draw_glow(surface, x, y, int(size * 1.8), Palette.NEON_GOLD, int(100 * pulse))
        icon_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(icon_surf, Palette.NEON_GOLD, (x - size * 0.4, y - size * 0.15, size * 0.8, size * 0.3), border_radius=3)
        pygame.draw.rect(icon_surf, (255, 240, 200), (x + size * 0.2, y - size * 0.08, size * 0.35, size * 0.16))
        surface.blit(icon_surf, (0, 0))

    def _draw_icon_bolt(self, surface, x, y, color):
        pts = [(x - 3, y - 8), (x + 2, y - 8), (x - 2, y), (x + 3, y),
               (x - 3, y + 8), (x + 1, y + 1), (x - 3, y + 1)]
        pygame.draw.polygon(surface, color, pts)

    def _draw_icon_star(self, surface, x, y, color):
        pts = []
        for i in range(10):
            r = 7 if i % 2 == 0 else 3
            a = i * math.pi / 5 - math.pi / 2
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surface, color, pts)

    # ==================== ПОРТАЛЫ ====================

    def draw_portal(self, surface, x: float, y: float, radius: int = 46,
                     color: tuple = None, particles: bool = True):
        radius = int(radius)
        color = color or Palette.NEON_MAGENTA
        self.draw_glow(surface, x, y, int(radius * 1.6), color, 100)

        for i, mult in enumerate((1.0, 0.7, 0.4)):
            ring_r = radius * mult
            spin = self._time * (1.5 - i * 0.4) * (1 if i % 2 == 0 else -1)
            ring_color = lerp_color(color, Palette.NEON_CYAN, i * 0.3)
            dashes = 16 - i * 3
            for d in range(dashes):
                a0 = spin + d * (math.tau / dashes)
                a1 = a0 + (math.tau / dashes) * 0.5
                p0 = (x + math.cos(a0) * ring_r, y + math.sin(a0) * ring_r)
                p1 = (x + math.cos(a1) * ring_r, y + math.sin(a1) * ring_r)
                pygame.draw.line(surface, with_alpha(ring_color, 220), p0, p1, 3)

        symbol_r = radius * 1.25
        for i in range(12):
            a = i * math.tau / 12
            x0 = x + math.cos(a) * symbol_r
            y0 = y + math.sin(a) * symbol_r
            x1 = x + math.cos(a) * (symbol_r - 8)
            y1 = y + math.sin(a) * (symbol_r - 8)
            pygame.draw.line(surface, with_alpha(Palette.NEON_GOLD, 160), (x0, y0), (x1, y1), 2)

        core_pulse = 0.5 + 0.5 * math.sin(self._time * 3.0)
        core_surf = pygame.Surface((radius, radius), pygame.SRCALPHA)
        pygame.draw.ellipse(core_surf, with_alpha((10, 5, 15), 230), core_surf.get_rect())
        surface.blit(core_surf, (x - radius / 2, y - radius / 2))
        self.draw_glow(surface, x, y, int(radius * 0.4 * (0.8 + 0.2 * core_pulse)), color, 200)

        if particles:
            for i in range(6):
                a = self._time * 3 + i * (math.tau / 6)
                dist = radius * (0.9 - 0.5 * ((self._time * 0.7 + i) % 1.0))
                px = x + math.cos(a) * dist
                py = y + math.sin(a) * dist
                self.draw_special_particle(surface, 'spark', px, py, 2, 200, a, color)

    # ==================== HUD ====================

    def draw_panel(self, surface, rect: pygame.Rect, border_color: tuple = None, radius: int = 10):
        border_color = border_color or Palette.PANEL_BORDER
        panel_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, Palette.PANEL_BG, panel_surf.get_rect(), border_radius=radius)
        pygame.draw.rect(panel_surf, with_alpha(border_color, 200), panel_surf.get_rect(), 2, border_radius=radius)
        surface.blit(panel_surf, rect.topleft)
        if self.glow_enabled:
            self.draw_rect_glow(surface, rect, border_color, alpha=40, border_radius=radius)

    def draw_button(self, surface, rect: pygame.Rect, label: str, hovered: bool = False,
                     color: tuple = None):
        color = color or Palette.NEON_CYAN
        shadow_rect = rect.move(0, 3)
        shadow_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 100), shadow_surf.get_rect(), border_radius=8)
        surface.blit(shadow_surf, shadow_rect.topleft)

        bg = lerp_color((22, 26, 36), (34, 40, 54), 1.0 if hovered else 0.0)
        btn_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, (*bg, 235), btn_surf.get_rect(), border_radius=8)
        border_alpha = 255 if hovered else 160
        pygame.draw.rect(btn_surf, with_alpha(color, border_alpha), btn_surf.get_rect(), 2, border_radius=8)
        surface.blit(btn_surf, rect.topleft)
        if hovered and self.glow_enabled:
            self.draw_rect_glow(surface, rect, color, alpha=80, border_radius=8)

        font = pygame.font.Font(None, 22)
        text_surf = font.render(label, True, Palette.TEXT_MAIN if not hovered else (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def draw_boss_bar(self, surface, x: int, y: int, width: int, height: int,
                       ratio: float, name: str = "", phase_markers: Optional[List[float]] = None,
                       color: tuple = None):
        color = color or Palette.NEON_RED
        frame_rect = pygame.Rect(x, y, width, height)
        self.draw_panel(surface, frame_rect.inflate(8, 14), border_color=color, radius=10)

        ratio = max(0.0, min(1.0, ratio))
        inner = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, (20, 12, 14), inner, border_radius=6)
        fill_w = int(width * ratio)
        if fill_w > 0:
            grad = self._get_health_gradient(width, height, color)
            surface.blit(grad, (x, y + 2), area=pygame.Rect(0, 0, fill_w, grad.get_height()))
        shimmer_x = x + int((math.sin(self._time * 2) * 0.5 + 0.5) * width)
        pygame.draw.line(surface, with_alpha((255, 255, 255), 90), (shimmer_x, y), (shimmer_x, y + height), 2)
        pygame.draw.rect(surface, with_alpha(color, 220), inner, 2, border_radius=6)

        if phase_markers:
            for m in phase_markers:
                mx = x + int(width * max(0.0, min(1.0, m)))
                pygame.draw.line(surface, Palette.NEON_GOLD, (mx, y - 3), (mx, y + height + 3), 2)

        if name:
            self.draw_text(surface, name, x, y - 22, 18, Palette.TEXT_MAIN, shadow=True)

    def push_notification(self, text: str, icon_color: tuple = None, duration: float = 3.0):
        self._notifications.append({
            'text': text, 'color': icon_color or Palette.NEON_CYAN,
            'life': 0.0, 'duration': duration,
        })

    def draw_notifications(self, surface, x: int = 20, y: int = 20, spacing: int = 46):
        for i, note in enumerate(self._notifications):
            t = note['life'] / note['duration']
            if t < 0.1:
                slide = (1 - t / 0.1)
                offset_x = -int(220 * slide)
                alpha = 255
            elif t > 0.8:
                fade = (t - 0.8) / 0.2
                offset_x = 0
                alpha = int(255 * (1 - fade))
            else:
                offset_x = 0
                alpha = 255

            rect = pygame.Rect(x + offset_x, y + i * spacing, 240, 36)
            panel = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (*Palette.PANEL_BG[:3], min(Palette.PANEL_BG[3], alpha)), panel.get_rect(), border_radius=8)
            pygame.draw.rect(panel, with_alpha(note['color'], alpha), panel.get_rect(), 2, border_radius=8)
            pygame.draw.rect(panel, with_alpha(note['color'], alpha), (0, 0, 4, rect.height), border_radius=2)
            surface.blit(panel, rect.topleft)

            font = pygame.font.Font(None, 20)
            text_surf = font.render(note['text'], True, Palette.TEXT_MAIN)
            text_surf.set_alpha(alpha)
            surface.blit(text_surf, (rect.x + 14, rect.y + rect.height // 2 - text_surf.get_height() // 2))

    def draw_currency(self, surface, x: int, y: int, amount: int, icon: str = 'star', color: tuple = None):
        color = color or Palette.NEON_GOLD
        if icon == 'star':
            self._draw_icon_star(surface, x, y, color)
        else:
            self._draw_icon_bolt(surface, x, y, color)
        self.draw_text(surface, str(amount), x + 16, y - 9, 20, Palette.TEXT_MAIN, shadow=True)

    # ==================== ОБНОВЛЕНИЕ ====================

    def update(self, dt: float):
        self._time += dt
        self._critical_pulse_t += dt

        if self.flash_timer > 0:
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.flash_timer = 0.0
                self.flash_alpha = 0.0
            else:
                self.flash_alpha = self._flash_peak_alpha * (self.flash_timer / self._flash_duration)

        if self._shake_timer > 0:
            self._shake_timer -= dt
            if self._shake_timer <= 0:
                self._shake_timer = 0.0
                self.screen_shake_offset = (0, 0)
            else:
                decay = self._shake_timer / self._shake_duration
                mag = self._shake_intensity * decay * 10
                self.screen_shake_offset = (random.uniform(-mag, mag), random.uniform(-mag, mag))
        else:
            self.screen_shake_offset = (0, 0)

        for burst in self._levelup_bursts:
            burst['life'] += dt
        self._levelup_bursts = [b for b in self._levelup_bursts if b['life'] < b['duration']]

        for note in self._notifications:
            note['life'] += dt
        self._notifications = [n for n in self._notifications if n['life'] < n['duration']]

        self.weather.update(dt)
        self.starfield.update(dt)
        self.transition.update(dt)

    # ==================== ГРАДИЕНТЫ ====================

    def draw_gradient_rect(self, surface, rect: pygame.Rect, color1: tuple, color2: tuple, horizontal: bool = True):
        if horizontal:
            for i in range(rect.width):
                t = i / max(1, rect.width)
                color = lerp_color(color1, color2, t)
                pygame.draw.line(surface, color, (rect.x + i, rect.y), (rect.x + i, rect.y + rect.height))
        else:
            for i in range(rect.height):
                t = i / max(1, rect.height)
                color = lerp_color(color1, color2, t)
                pygame.draw.line(surface, color, (rect.x, rect.y + i), (rect.x + rect.width, rect.y + i))

    def _lerp_color(self, c1: tuple, c2: tuple, t: float) -> tuple:
        return lerp_color(c1, c2, t)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ ====================

    def get_cached_surface(self, width: int, height: int, alpha: bool = False) -> pygame.Surface:
        key = (width, height, alpha)
        if key not in self._surface_cache:
            flags = pygame.SRCALPHA if alpha else 0
            self._surface_cache[key] = pygame.Surface((width, height), flags)
        return self._surface_cache[key]

    def clear_cache(self):
        self._surface_cache.clear()
        self._glow_cache.clear()
        self._light_cache.clear()
        self._health_gradient_cache.clear()
        self._shape_cache.clear()

    @staticmethod
    def load_spritesheet(path: str, frame_width: int, frame_height: int,
                          rows: int = 1, cols: int = 1) -> SpriteSheet:
        image = pygame.image.load(path).convert_alpha()
        return SpriteSheet(image, frame_width, frame_height, rows, cols)

    # ==================== ДОПОЛНИТЕЛЬНЫЕ ВИЗУАЛЬНЫЕ МЕТОДЫ ====================

    def draw_hud_label(self, surface, text: str, x: int, y: int, size: int = 22,
                       color: tuple = None, icon: str = None, shadow: bool = True):
        """Рисует подпись кнопки HUD с иконкой (например, 'Настройки' или 'Инструкция')."""
        color = color or Palette.TEXT_MAIN
        icon_str = f"{icon} " if icon else ""
        self.draw_text(surface, f"{icon_str}{text}", x, y, size, color, shadow=shadow)

    def draw_crack_overlay(self, surface, rect: pygame.Rect, intensity: float = 1.0,
                           seed: int = 0):
        """Рисует ЖИРНЫЕ заметные трещины на препятствии."""
        if not self.use_advanced or intensity <= 0:
            return

        rnd = random.Random(seed)
        crack_surf = pygame.Surface(rect.size, pygame.SRCALPHA)

        # Основная трещина — ТОЛЩЕ и ЯРЧЕ
        main_width = max(2, int(4 * intensity))  # 2-4 пикселя
        main_color = (15, 10, 10, int(255 * min(1.0, intensity + 0.3)))

        # Несколько основных трещин
        num_main_cracks = 3 if intensity > 0.5 else 2
        for _ in range(num_main_cracks):
            points = [(rnd.uniform(rect.width * 0.2, rect.width * 0.8),
                       rnd.uniform(rect.height * 0.2, rect.height * 0.8))]

            # Длинная зигзагообразная трещина
            for _ in range(8):
                x = points[-1][0] + rnd.uniform(-rect.width * 0.2, rect.width * 0.2)
                y = points[-1][1] + rnd.uniform(rect.height * 0.15, rect.height * 0.25)
                x = max(2, min(rect.width - 3, x))
                y = max(2, min(rect.height - 3, y))
                points.append((x, y))

            # Основная линия — жирная
            pygame.draw.lines(crack_surf, main_color, False, points, main_width)

            # Тёмная обводка для контраста
            pygame.draw.lines(crack_surf, (0, 0, 0, int(150 * intensity)), False, points, main_width + 2)

            # Ветви — средней толщины
            branch_width = max(1, int(2 * intensity))
            branch_color = (20, 12, 12, int(200 * intensity))

            num_branches = 5 if intensity > 0.6 else 3
            for _ in range(num_branches):
                branch_from = points[rnd.randint(1, len(points) - 2)]
                branch = [branch_from]
                branch_length = rnd.randint(3, 6)
                for _ in range(branch_length):
                    x = branch[-1][0] + rnd.uniform(-15, 15)
                    y = branch[-1][1] + rnd.uniform(-15, 15)
                    branch.append((max(1, min(rect.width - 2, x)), max(1, min(rect.height - 2, y))))

                # Ветвь — жирная
                pygame.draw.lines(crack_surf, branch_color, False, branch, branch_width)

                # Тонкие ответвления от ветвей
                if rnd.random() < 0.7:
                    sub_branch = [branch[-1]]
                    for _ in range(3):
                        x = sub_branch[-1][0] + rnd.uniform(-8, 8)
                        y = sub_branch[-1][1] + rnd.uniform(-8, 8)
                        sub_branch.append((max(0, min(rect.width - 1, x)), max(0, min(rect.height - 1, y))))
                    pygame.draw.lines(crack_surf, branch_color, False, sub_branch, 1)

        # Добавляем светлые блики по краям трещин (для объёма)
        if intensity > 0.4:
            highlight_color = (80, 70, 65, int(100 * intensity))
            for _ in range(4):
                hx = rnd.uniform(0, rect.width)
                hy = rnd.uniform(0, rect.height)
                pygame.draw.circle(crack_surf, highlight_color, (int(hx), int(hy)), rnd.randint(2, 4), 1)

        surface.blit(crack_surf, rect.topleft)

    def draw_rotated_triangle(self, surface, x: float, y: float, angle: float,
                              radius: int = 20, color: tuple = None, glow: bool = True):
        """Рисует треугольник, повёрнутый на угол angle (для игрока, смотрящего на курсор)."""
        color = color or Palette.NEON_CYAN
        # Три вершины с учётом угла
        points = [
            (x + math.cos(angle) * radius, y + math.sin(angle) * radius),
            (x + math.cos(angle + 2.5) * radius * 0.7, y + math.sin(angle + 2.5) * radius * 0.7),
            (x + math.cos(angle - 2.5) * radius * 0.7, y + math.sin(angle - 2.5) * radius * 0.7),
        ]
        if glow:
            self._polygon_glow(surface, points, color, alpha=70, spread=6)
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, self._rim_light(color, 0.0), points, 2)

    def draw_dash_afterimage(self, surface, x: float, y: float, angle: float,
                              radius: int = 20, color: tuple = None, count: int = 5,
                              spacing: float = 8.0):
        """Эффект размытия при рывке — несколько полупрозрачных копий позади игрока."""
        color = color or Palette.NEON_CYAN
        back_angle = angle + math.pi
        for i in range(1, count + 1):
            offset = spacing * i
            ghost_x = x + math.cos(back_angle) * offset
            ghost_y = y + math.sin(back_angle) * offset
            alpha = 255 // (i + 1)
            ghost_color = with_alpha(color, alpha)
            self.draw_rotated_triangle(surface, ghost_x, ghost_y, angle, radius, ghost_color, glow=False)

    def draw_rain_drop(self, surface, x: float, y: float, length: float = 12,
                        speed: float = 0, angle: float = -math.pi / 4, color: tuple = None):
        """Отдельная капля дождя с бликом."""
        color = color or (170, 190, 220)
        end_x = x + math.cos(angle) * length
        end_y = y + math.sin(angle) * length
        pygame.draw.line(surface, color, (x, y), (end_x, end_y), 1)
        # Блик
        if self.use_advanced:
            self.draw_glow(surface, end_x, end_y, 3, color, 60)

    def draw_lightning_bolt(self, surface, start: Tuple[float, float], end: Tuple[float, float],
                            color: tuple = None, width: int = 2, branches: int = 3):
        """Улучшенная молния с ветвлением."""
        color = color or Palette.NEON_CYAN
        # Основная ломаная
        points = [start]
        segments = 8
        for i in range(1, segments):
            t = i / segments
            x = start[0] + (end[0] - start[0]) * t + random.uniform(-15, 15)
            y = start[1] + (end[1] - start[1]) * t + random.uniform(-15, 15)
            points.append((x, y))
        points.append(end)
        for i in range(len(points) - 1):
            self.draw_line_glow(surface, points[i], points[i + 1], color, width)
        # Ветви
        for _ in range(branches):
            if len(points) > 2:
                branch_from = random.choice(points[1:-1])
                branch_end = (branch_from[0] + random.uniform(-30, 30),
                              branch_from[1] + random.uniform(20, 50))
                self.draw_line_glow(surface, branch_from, branch_end, with_alpha(color, 150), 1)

    def draw_enemy_shadow(self, surface, x: float, y: float, radius: int = 18,
                           alpha: int = 80):
        """Мягкая тень под врагом/игроком."""
        shadow_surf = pygame.Surface((radius * 2, radius), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), shadow_surf.get_rect())
        surface.blit(shadow_surf, (int(x - radius), int(y - radius * 0.3)))

    def draw_pickup_glow(self, surface, x: float, y: float, color: tuple, radius: int = 12,
                          pulse_speed: float = 2.0, alpha: int = 100):
        """Усиленное пульсирующее свечение для предметов."""
        pulse = 0.5 + 0.5 * math.sin(self._time * pulse_speed)
        self.draw_glow(surface, x, y, int(radius * (1 + 0.2 * pulse)), color, int(alpha * pulse))

    def draw_energy_shield(self, surface, x: float, y: float, radius: int = 20,
                            color: tuple = None, active: bool = True):
        """Энергетический щит с вращающимися шестиугольниками."""
        if not active:
            return
        color = color or Palette.NEON_BLUE
        hex_r = radius * 1.6
        pts = []
        for i in range(6):
            a = self._time * 1.5 + i * math.pi / 3
            pts.append((x + math.cos(a) * hex_r, y + math.sin(a) * hex_r))
        self._polygon_glow(surface, pts, color, alpha=90, spread=8)
        shield_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(shield_surf, with_alpha(color, 40), pts)
        pygame.draw.polygon(shield_surf, with_alpha(Palette.NEON_CYAN, 160), pts, 2)
        surface.blit(shield_surf, (0, 0))

    def draw_muzzle_flash_improved(self, surface, x: float, y: float, angle: float,
                                    size: int = 14, color: tuple = None):
        """Улучшенная вспышка у дула с лучами и искрами."""
        color = color or Palette.NEON_GOLD
        # Лучи
        for _ in range(5):
            a = angle + random.uniform(-0.4, 0.4)
            r = size * random.uniform(0.5, 1.5)
            ex = x + math.cos(a) * r
            ey = y + math.sin(a) * r
            self.draw_line_glow(surface, (x, y), (ex, ey), with_alpha(color, 220), 2)
        # Искры
        for _ in range(8):
            a = angle + random.uniform(-math.pi, math.pi)
            r = size * random.uniform(0.3, 1.0)
            self.draw_special_particle(surface, 'spark', x + math.cos(a) * r,
                                       y + math.sin(a) * r, 2, 200, a, color)

    def draw_explosion_shockwave(self, surface, x: float, y: float, radius: int = 50,
                                  color: tuple = None, alpha: int = 200):
        """Ударная волна взрыва."""
        color = color or Palette.NEON_ORANGE
        # Внешнее кольцо
        ring_radius = radius * 0.8
        pygame.draw.circle(surface, with_alpha(color, alpha), (int(x), int(y)), int(ring_radius), 3)
        # Внутреннее свечение
        self.draw_glow(surface, x, y, int(radius * 0.5), color, alpha // 2)

    def draw_spark_burst(self, surface, x: float, y: float, count: int = 15,
                          color: tuple = None, speed: float = 200):
        """Разлетающиеся искры."""
        color = color or Palette.NEON_GOLD
        for _ in range(count):
            a = random.uniform(0, math.tau)
            r = speed * random.uniform(0.5, 1.0)
            self.draw_special_particle(surface, 'spark', x + math.cos(a) * r * 0.1,
                                       y + math.sin(a) * r * 0.1, 2, 200, a, color)

    def draw_smoke_puff(self, surface, x: float, y: float, radius: int = 10,
                         alpha: int = 100):
        """Мягкий дым."""
        self.draw_glow(surface, x, y, radius, (90, 90, 95), alpha // 2)
        pygame.draw.circle(surface, (90, 90, 95, alpha), (int(x), int(y)), radius // 2)

    def draw_fire_trail(self, surface, x: float, y: float, angle: float,
                         length: int = 20, color: tuple = None):
        """Огненный след (для ракет, фаерболов)."""
        color = color or Palette.NEON_ORANGE
        tail = (x - math.cos(angle) * length, y - math.sin(angle) * length)
        for i in range(3):
            t = i / 3
            cx = x + (tail[0] - x) * t
            cy = y + (tail[1] - y) * t
            self.draw_glow(surface, cx, cy, int(6 * (1 - t)), color, 150)

    def draw_ice_spike(self, surface, x: float, y: float, size: int = 12,
                        color: tuple = None):
        """Ледяной шип (для ледяных атак)."""
        color = color or (150, 220, 255)
        pts = []
        for i in range(5):
            a = i * math.tau / 5
            r = size if i % 2 == 0 else size * 0.4
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, (255, 255, 255), pts, 1)

    def draw_poison_bubble(self, surface, x: float, y: float, size: int = 8,
                            color: tuple = None):
        """Ядовитый пузырь с внутренним свечением."""
        color = color or (100, 255, 100)
        self.draw_glow(surface, x, y, size * 2, color, 100)
        pygame.draw.circle(surface, color, (int(x), int(y)), size)
        pygame.draw.circle(surface, (255, 255, 255, 100), (int(x), int(y)), max(1, size // 2))

    def draw_blood_splatter(self, surface, x: float, y: float, count: int = 10,
                             color: tuple = None):
        """Кровавые брызги."""
        color = color or (140, 10, 20)
        for _ in range(count):
            a = random.uniform(0, math.tau)
            r = random.uniform(5, 15)
            self.draw_special_particle(surface, 'smoke', x + math.cos(a) * r,
                                       y + math.sin(a) * r, random.uniform(2, 4), 200, a, color)

    def draw_star_particle(self, surface, x: float, y: float, size: int = 4,
                            color: tuple = None):
        """Мерцающая звезда (для магических эффектов)."""
        color = color or Palette.NEON_GOLD
        pts = []
        for i in range(10):
            r = size if i % 2 == 0 else size // 2
            a = i * math.pi / 5
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surface, color, pts)

    def draw_portal_particles(self, surface, x: float, y: float, radius: int = 30,
                               color: tuple = None, count: int = 6):
        """Частицы, затягивающиеся в портал."""
        color = color or Palette.NEON_MAGENTA
        for i in range(count):
            a = self._time * 3 + i * (math.tau / count)
            dist = radius * (0.9 - 0.5 * ((self._time * 0.7 + i) % 1.0))
            px = x + math.cos(a) * dist
            py = y + math.sin(a) * dist
            self.draw_special_particle(surface, 'spark', px, py, 2, 200, a, color)

    def draw_healing_cross(self, surface, x: float, y: float, size: int = 16,
                            color: tuple = None):
        """Крест лечения с зелёным свечением."""
        color = color or Palette.NEON_GREEN
        self.draw_glow(surface, x, y, size, color, 100)
        pygame.draw.rect(surface, color, (x - size // 2, y - size // 6, size, size // 3))
        pygame.draw.rect(surface, color, (x - size // 6, y - size // 2, size // 3, size))

    def draw_damage_numbers_improved(self, surface, x: float, y: float, damage: int,
                                      color: tuple = None, is_crit: bool = False):
        """Урон с обводкой и свечением."""
        color = color or (255, 100, 100)
        font = pygame.font.Font(None, 28 if not is_crit else 34)
        text = str(damage)
        if is_crit:
            text += "!"
            color = (255, 200, 80)
        self.draw_text(surface, text, int(x), int(y), 28 if not is_crit else 34, color, shadow=True, glow=True)

    # ==================== СЮЖЕТНЫЕ ВИЗУАЛЬНЫЕ ЭФФЕКТЫ ====================

    def draw_memory_fragment(self, surface, x: float, y: float, size: int = 14,
                              color: tuple = None, alpha: int = 200):
        """Голографический фрагмент памяти — парящий светящийся осколок."""
        color = color or Palette.NEON_CYAN
        bob = math.sin(self._time * 2.0) * 3
        y += bob
        self.draw_glow(surface, x, y, size * 2, color, alpha)
        # Кристаллическая форма
        pts = []
        for i in range(6):
            a = self._time * 0.5 + i * math.tau / 6
            r = size if i % 2 == 0 else size * 0.5
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(surface, with_alpha(color, alpha), pts)
        pygame.draw.polygon(surface, (255, 255, 255), pts, 1)

    def draw_terminal_screen(self, surface, x: float, y: float, size: int = 20,
                              active: bool = True):
        """Терминал лора — светящийся экран с текстом."""
        rect = pygame.Rect(0, 0, size * 1.6, size * 1.2)
        rect.center = (int(x), int(y))
        screen_color = (80, 240, 160) if active else (80, 80, 100)
        self.draw_glow(surface, x, y, size, screen_color, 80 if active else 30)
        pygame.draw.rect(surface, (10, 20, 15), rect, border_radius=3)
        pygame.draw.rect(surface, screen_color, rect, 2, border_radius=3)
        # Текстовые линии на экране
        for i in range(3):
            line_y = rect.top + 5 + i * 6
            pygame.draw.line(surface, screen_color, (rect.left + 4, line_y), (rect.right - 4, line_y), 1)

    def draw_audio_log_device(self, surface, x: float, y: float, size: int = 16,
                               playing: bool = False):
        """Аудиолог — устройство с динамиком."""
        color = Palette.NEON_GOLD if playing else (120, 120, 140)
        self.draw_glow(surface, x, y, size, color, 60 if playing else 20)
        pygame.draw.circle(surface, (30, 30, 40), (int(x), int(y)), size)
        pygame.draw.circle(surface, color, (int(x), int(y)), size, 2)
        # Динамик
        pygame.draw.circle(surface, color, (int(x), int(y)), max(2, size // 3))
        if playing:
            # Звуковые волны
            for i in range(3):
                wave_r = size + 4 + i * 5
                alpha = 150 - i * 40
                pygame.draw.circle(surface, with_alpha(color, alpha), (int(x), int(y)), wave_r, 1)

    def draw_holo_projector(self, surface, x: float, y: float, size: int = 18,
                             active: bool = True):
        """Голографический проектор — источник голограммы."""
        base_color = Palette.NEON_MAGENTA if active else (80, 80, 100)
        # Основание
        pygame.draw.rect(surface, (40, 40, 50), (x - size // 2, y, size, size // 3))
        # Луч проектора
        if active:
            beam_h = size * 1.5
            for i in range(beam_h):
                t = i / beam_h
                alpha = int(100 * (1 - t))
                pygame.draw.line(surface, with_alpha(base_color, alpha),
                                 (x - size // 4, y - i), (x + size // 4, y - i), 1)
        self.draw_glow(surface, x, y - size, size, base_color, 80 if active else 20)

    def draw_quantum_core(self, surface, x: float, y: float, size: int = 22,
                           hacked: bool = False):
        """Квантовое ядро — вращающийся энергетический шар."""
        core_color = Palette.NEON_GREEN if hacked else Palette.NEON_MAGENTA
        pulse = 0.5 + 0.5 * math.sin(self._time * 3.0)
        self.draw_glow(surface, x, y, int(size * 1.5 * (1 + 0.2 * pulse)), core_color, 150)
        # Вращающиеся кольца
        for i in range(3):
            ring_r = size * (0.6 + i * 0.3)
            spin = self._time * (1.5 + i * 0.5) * (1 if i % 2 == 0 else -1)
            ring_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.ellipse(ring_surf, with_alpha(core_color, 180 - i * 40),
                                (x - ring_r, y - ring_r * 0.5, ring_r * 2, ring_r))
            surface.blit(ring_surf, (0, 0))
        # Ядро
        pygame.draw.circle(surface, core_color, (int(x), int(y)), max(3, size // 3))

    def draw_story_artifact(self, surface, x: float, y: float, artifact_type: str,
                             size: int = 20):
        """Отображение сюжетного артефакта по типу."""
        handlers = {
            'memory_shard': lambda: self.draw_memory_fragment(surface, x, y, size),
            'terminal': lambda: self.draw_terminal_screen(surface, x, y, size),
            'audio_log': lambda: self.draw_audio_log_device(surface, x, y, size),
            'holo_projector': lambda: self.draw_holo_projector(surface, x, y, size),
            'quantum_core': lambda: self.draw_quantum_core(surface, x, y, size),
        }
        handler = handlers.get(artifact_type, lambda: self.draw_memory_fragment(surface, x, y, size))
        handler()

    # ==================== СЮЖЕТНЫЕ АУРЫ И ЭФФЕКТЫ ====================

    def draw_survivor_aura(self, surface, x: float, y: float, radius: int = 24,
                            color: tuple = None):
        """Аура выжившего — тёплое свечение для NPC Сопротивления."""
        color = color or (180, 220, 255)
        pulse = 0.5 + 0.5 * math.sin(self._time * 1.5)
        self.draw_glow(surface, x, y, int(radius * (1 + 0.1 * pulse)), color, 50 + int(20 * pulse))

    def draw_betrayer_aura(self, surface, x: float, y: float, radius: int = 26,
                            color: tuple = None):
        """Аура предателя — тёмно-красное пульсирующее свечение (для Око)."""
        color = color or (200, 50, 80)
        pulse = 0.5 + 0.5 * math.sin(self._time * 2.5)
        self.draw_glow(surface, x, y, int(radius * (1 + 0.15 * pulse)), color, 60 + int(40 * pulse))
        # Лёгкие "вены" контроля
        for i in range(6):
            a = self._time * 1.2 + i * math.tau / 6
            x1 = x + math.cos(a) * radius * 0.5
            y1 = y + math.sin(a) * radius * 0.5
            x2 = x + math.cos(a) * radius * 0.9
            y2 = y + math.sin(a) * radius * 0.9
            self.draw_line_glow(surface, (x1, y1), (x2, y2), with_alpha(color, 120), 1)

    def draw_hybrid_energy(self, surface, x: float, y: float, radius: int = 22,
                            color: tuple = None):
        """Энергия гибрида — смесь человеческого и машинного свечения."""
        color = color or Palette.NEON_GREEN
        pulse = 0.5 + 0.5 * math.sin(self._time * 2.0)
        self.draw_glow(surface, x, y, int(radius * (1 + 0.1 * pulse)), color, 70)
        # Кибернетические линии
        for i in range(4):
            a = self._time * 0.8 + i * math.pi / 2
            x1 = x + math.cos(a) * radius * 0.3
            y1 = y + math.sin(a) * radius * 0.3
            x2 = x + math.cos(a) * radius * 0.8
            y2 = y + math.sin(a) * radius * 0.8
            pygame.draw.line(surface, with_alpha(Palette.NEON_CYAN, 150), (x1, y1), (x2, y2), 1)

    def draw_genesis_presence(self, surface, x: float, y: float, radius: int = 30,
                               intensity: float = 1.0):
        """Присутствие ГЕНЕЗИСА — холодное зловещее свечение с цифровыми помехами."""
        pulse = 0.5 + 0.5 * math.sin(self._time * 1.8)
        self.draw_glow(surface, x, y, int(radius * (1 + 0.15 * pulse)), (180, 60, 255), int(80 * intensity))
        # Цифровые помехи (линии)
        for i in range(5):
            a = self._time * 1.3 + i * math.tau / 5
            x1 = x + math.cos(a) * radius * 0.7
            y1 = y + math.sin(a) * radius * 0.7
            x2 = x + math.cos(a) * radius * 1.0
            y2 = y + math.sin(a) * radius * 1.0
            pygame.draw.line(surface, with_alpha((200, 100, 255), 100), (x1, y1), (x2, y2), 1)

    # ==================== ВРАЖДЕБНЫЕ ВИЗУАЛЬНЫЕ ЭФФЕКТЫ ====================

    def draw_enemy_elite_aura(self, surface, x: float, y: float, radius: int = 24,
                               color: tuple = None):
        """Аура элитного врага — мощное пульсирующее свечение."""
        color = color or Palette.NEON_ORANGE
        pulse = 0.5 + 0.5 * math.sin(self._time * 4.0)
        self.draw_glow(surface, x, y, int(radius * 1.5 * (1 + 0.2 * pulse)), color, 100 + int(50 * pulse))

    def draw_enemy_boss_rings(self, surface, x: float, y: float, radius: int = 40,
                               phase: int = 0):
        """Кольца босса с фазовой окраской."""
        phase_colors = [Palette.NEON_CYAN, Palette.NEON_MAGENTA, Palette.NEON_RED]
        color = phase_colors[min(phase, len(phase_colors) - 1)]
        for ring_i, mult in enumerate((1.8, 1.5, 1.2, 0.9)):
            ring_r = radius * mult
            spin = self._time * (1.5 - ring_i * 0.3) * (1 if ring_i % 2 == 0 else -1)
            dashes = 20 - ring_i * 3
            for d in range(dashes):
                a0 = spin + d * (math.tau / dashes)
                a1 = a0 + (math.tau / dashes) * 0.5
                p0 = (x + math.cos(a0) * ring_r, y + math.sin(a0) * ring_r)
                p1 = (x + math.cos(a1) * ring_r, y + math.sin(a1) * ring_r)
                pygame.draw.line(surface, with_alpha(color, 200), p0, p1, 3)

    def draw_drone_patrol_path(self, surface, x: float, y: float, radius: int = 20,
                                color: tuple = None):
        """Патрульный дрон с вращающимся сенсором."""
        color = color or Palette.NEON_RED
        self.draw_glow(surface, x, y, radius, color, 60)
        pygame.draw.circle(surface, color, (int(x), int(y)), radius // 2)
        # Вращающийся сенсор
        sensor_angle = self._time * 3.0
        sensor_x = x + math.cos(sensor_angle) * radius
        sensor_y = y + math.sin(sensor_angle) * radius
        pygame.draw.circle(surface, (255, 255, 255), (int(sensor_x), int(sensor_y)), 3)

    def draw_tank_tread_marks(self, surface, x: float, y: float, angle: float,
                               width: int = 30, length: int = 20):
        """Следы гусениц от танка."""
        perp = angle + math.pi / 2
        for offset in (-width // 2, width // 2):
            x1 = x + math.cos(perp) * offset - math.cos(angle) * length
            y1 = y + math.sin(perp) * offset - math.sin(angle) * length
            x2 = x + math.cos(perp) * offset + math.cos(angle) * length
            y2 = y + math.sin(perp) * offset + math.sin(angle) * length
            pygame.draw.line(surface, (60, 60, 65), (x1, y1), (x2, y2), 6)
            pygame.draw.line(surface, (40, 40, 45), (x1, y1), (x2, y2), 4)

    def draw_shooter_laser_sight(self, surface, x: float, y: float, target_pos: Tuple[float, float],
                                  color: tuple = None):
        """Лазерный прицел стрелка."""
        color = color or Palette.NEON_GOLD
        # Пунктирная линия
        dash_length = 8
        dx = target_pos[0] - x
        dy = target_pos[1] - y
        dist = math.hypot(dx, dy)
        if dist > 0:
            nx, ny = dx / dist, dy / dist
            for d in range(0, int(dist), dash_length * 2):
                x1 = x + nx * d
                y1 = y + ny * d
                x2 = x + nx * min(d + dash_length, dist)
                y2 = y + ny * min(d + dash_length, dist)
                pygame.draw.line(surface, with_alpha(color, 150), (x1, y1), (x2, y2), 1)
        # Точка прицеливания
        pygame.draw.circle(surface, color, (int(target_pos[0]), int(target_pos[1])), 3)

    # ==================== ВИЗУАЛЬНЫЕ ЭФФЕКТЫ ПРОТОКОЛА "ФЕНИКС" ====================

    def draw_phoenix_warning(self, surface, alpha: float = 0.5):
        """Красная тревожная рамка при активации протокола «Феникс»."""
        if alpha <= 0:
            return
        warning_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        # Пульсирующая рамка
        pulse = 0.5 + 0.5 * math.sin(self._time * 5.0)
        border_alpha = int(255 * alpha * (0.5 + 0.5 * pulse))
        pygame.draw.rect(warning_surf, (255, 50, 50, border_alpha), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 4)
        pygame.draw.rect(warning_surf, (255, 100, 100, border_alpha // 2), (10, 10, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20), 2)
        surface.blit(warning_surf, (0, 0))

    def draw_phoenix_countdown(self, surface, x: float, y: float, time_left: float,
                                color: tuple = None):
        """Обратный отсчёт протокола «Феникс»."""
        color = color or (255, 80, 80)
        font = pygame.font.Font(None, 60)
        text = str(max(0, int(time_left)))
        self.draw_text(surface, text, int(x), int(y), 60, color, shadow=True, glow=True)

    # ==================== ЭМОЦИОНАЛЬНЫЕ ВИЗУАЛЬНЫЕ МАРКЕРЫ ====================

    def draw_emotional_marker(self, surface, x: float, y: float, emotion: str,
                               size: int = 12):
        """Визуальный маркер эмоции персонажа (для диалогов)."""
        markers = {
            'anger': (255, 80, 80, '!'),
            'fear': (180, 180, 255, '?'),
            'sadness': (100, 150, 255, '...'),
            'joy': (255, 220, 80, '!'),
            'surprise': (255, 150, 255, '?!'),
            'trust': (100, 255, 150, '✓'),
            'betrayal': (200, 50, 80, '✗'),
        }
        color, symbol = markers.get(emotion, (255, 255, 255, '!'))
        self.draw_glow(surface, x, y, size * 2, color, 100)
        self.draw_text(surface, symbol, int(x), int(y), size * 2, color, shadow=True)

    def draw_relationship_indicator(self, surface, x: float, y: float, level: float,
                                     color: tuple = None):
        """Индикатор отношений с персонажем (0..1)."""
        color = color or Palette.NEON_GREEN
        width = 30
        height = 5
        pygame.draw.rect(surface, (40, 40, 50), (x, y, width, height), border_radius=2)
        fill_width = int(width * max(0.0, min(1.0, level)))
        if fill_width > 0:
            pygame.draw.rect(surface, color, (x, y, fill_width, height), border_radius=2)
        pygame.draw.rect(surface, with_alpha(color, 150), (x, y, width, height), 1, border_radius=2)

    # ==================== ФРАКЦИОННЫЕ ВИЗУАЛЬНЫЕ ЭФФЕКТЫ ====================

    def draw_survivor_banner(self, surface, x: float, y: float, size: int = 16):
        """Знамя Сопротивления — символ выживших."""
        color = (100, 180, 255)
        # Древко
        pygame.draw.line(surface, (120, 100, 60), (x - size // 2, y - size), (x - size // 2, y + size), 2)
        # Полотно
        pts = [(x - size // 2, y - size), (x + size // 2, y - size // 2), (x - size // 2, y)]
        pygame.draw.polygon(surface, color, pts)
        self.draw_glow(surface, x, y - size // 2, size // 2, color, 60)

    def draw_omega_symbol(self, surface, x: float, y: float, size: int = 18,
                           color: tuple = None):
        """Символ Омега — знак корпорации."""
        color = color or (150, 150, 200)
        self.draw_text(surface, "Ω", int(x - size // 2), int(y - size // 2), size, color, shadow=True, glow=True)

    def draw_genesis_core_icon(self, surface, x: float, y: float, size: int = 20,
                                color: tuple = None):
        """Иконка ядра ГЕНЕЗИСА — вращающийся треугольник в круге."""
        color = color or Palette.NEON_MAGENTA
        pygame.draw.circle(surface, color, (int(x), int(y)), size, 2)
        # Вращающийся треугольник внутри
        angle = self._time * 2.0
        pts = []
        for i in range(3):
            a = angle + i * math.tau / 3
            pts.append((x + math.cos(a) * size * 0.6, y + math.sin(a) * size * 0.6))
        pygame.draw.polygon(surface, color, pts)
        self.draw_glow(surface, x, y, size, color, 80)
