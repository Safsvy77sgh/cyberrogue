# entities/particle.py

import math
import random
import pygame
from typing import Tuple, List, Dict, Optional, Any
from settings import *


class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: Tuple[int, int, int], size: int = 4,
                 gravity: float = 0, friction: float = 0.98,
                 fade_speed: float = 1.0, shape: str = 'circle',
                 lifetime: float = None, rotation: float = None,
                 rotation_speed: float = None, alpha_decay: float = 1.0,
                 scale_decay: float = 0.0, trail: bool = False,
                 glow: bool = False, additive: bool = False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.base_color = color
        self.color = color
        self.size = size
        self.original_size = size
        self.shape = shape
        self.gravity = gravity
        self.friction = friction
        self.fade_speed = fade_speed
        self.alpha_decay = alpha_decay
        self.scale_decay = scale_decay
        self.trail = trail
        self.trail_points = []
        self.glow = glow
        self.additive = additive
        self.rotation = rotation if rotation is not None else random.uniform(0, 360)
        self.rotation_speed = rotation_speed if rotation_speed is not None else random.uniform(-100, 100)
        self.life = lifetime if lifetime is not None else random.uniform(0.3, 1.5)
        self.max_life = self.life
        self.alive = True

    def update(self, dt: float) -> bool:
        if not self.alive:
            return False

        if self.trail:
            self.trail_points.append((self.x, self.y))
            if len(self.trail_points) > 10:
                self.trail_points.pop(0)

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= self.friction
        self.vy *= self.friction
        self.vy += self.gravity * dt
        self.rotation += self.rotation_speed * dt
        self.size = max(0, self.original_size - self.scale_decay * dt)
        self.life -= dt * self.fade_speed

        if self.life <= 0:
            self.alive = False
            return False
        return True

    def get_alpha(self) -> int:
        return max(0, min(255, int(255 * (self.life / self.max_life) * self.alpha_decay)))

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        alpha = self.get_alpha()
        if alpha <= 0:
            return

        color = (self.base_color[0], self.base_color[1], self.base_color[2], alpha)
        draw_size = max(1, int(self.size))

        if self.additive:
            surf = pygame.Surface((draw_size * 4, draw_size * 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (draw_size * 2, draw_size * 2), draw_size)
            screen.blit(surf, (self.x - draw_size * 2, self.y - draw_size * 2), special_flags=pygame.BLEND_ADD)
            return

        if self.glow:
            glow_alpha = alpha // 2
            glow_color = (self.base_color[0], self.base_color[1], self.base_color[2], glow_alpha)
            glow_surf = pygame.Surface((draw_size * 4, draw_size * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (draw_size * 2, draw_size * 2), draw_size * 2)
            screen.blit(glow_surf, (self.x - draw_size * 2, self.y - draw_size * 2))

        if self.trail and len(self.trail_points) > 2:
            for i in range(len(self.trail_points) - 1):
                trail_alpha = int(alpha * (i / len(self.trail_points)))
                trail_color = (self.base_color[0], self.base_color[1], self.base_color[2], trail_alpha)
                pygame.draw.line(screen, trail_color, self.trail_points[i], self.trail_points[i + 1], max(1, draw_size // 2))

        if self.shape == 'circle':
            pygame.draw.circle(screen, color[:3], (int(self.x), int(self.y)), draw_size)
        elif self.shape == 'square':
            rect = pygame.Rect(self.x - draw_size // 2, self.y - draw_size // 2, draw_size, draw_size)
            pygame.draw.rect(screen, color[:3], rect)
        elif self.shape == 'triangle':
            points = [
                (self.x, self.y - draw_size),
                (self.x - draw_size, self.y + draw_size),
                (self.x + draw_size, self.y + draw_size),
            ]
            pygame.draw.polygon(screen, color[:3], points)
        elif self.shape == 'star':
            points = []
            for i in range(10):
                angle = i * math.pi / 5
                radius = draw_size if i % 2 == 0 else draw_size // 2
                points.append((self.x + math.cos(angle) * radius, self.y + math.sin(angle) * radius))
            pygame.draw.polygon(screen, color[:3], points)
        elif self.shape == 'spark':
            angle = math.radians(self.rotation)
            end_x = self.x + math.cos(angle) * self.size * 3
            end_y = self.y + math.sin(angle) * self.size * 3
            pygame.draw.line(screen, color[:3], (self.x, self.y), (end_x, end_y), 1)
        elif self.shape == 'ring':
            pygame.draw.circle(screen, color[:3], (int(self.x), int(self.y)), draw_size, max(1, draw_size // 3))


class ParticleEmitter:
    def __init__(self, x: float, y: float, config: dict = None):
        self.x = x
        self.y = y
        self.config = config or {}
        self.particles = []
        self.emitting = True
        self.emit_rate = self.config.get("emit_rate", 10)
        self.emit_timer = 0
        self.max_particles = self.config.get("max_particles", 100)
        self.duration = self.config.get("duration", -1)
        self.lifetime = self.config.get("lifetime", 1.0)
        self._init_defaults()

    def _init_defaults(self):
        self.config.setdefault("speed_min", 50)
        self.config.setdefault("speed_max", 150)
        self.config.setdefault("size_min", 2)
        self.config.setdefault("size_max", 6)
        self.config.setdefault("color", WHITE)
        self.config.setdefault("color_variance", 0)
        self.config.setdefault("gravity", 0)
        self.config.setdefault("friction", 0.98)
        self.config.setdefault("shape", "circle")
        self.config.setdefault("spread", 360)
        self.config.setdefault("direction", 0)
        self.config.setdefault("glow", False)
        self.config.setdefault("additive", False)
        self.config.setdefault("trail", False)
        self.config.setdefault("fade_speed", 1.0)

    def update(self, dt: float):
        if self.duration > 0:
            self.duration -= dt
            if self.duration <= 0:
                self.emitting = False

        self.emit_timer += dt
        emit_interval = 1.0 / self.emit_rate if self.emit_rate > 0 else 0.1

        if self.emitting and self.emit_timer >= emit_interval and len(self.particles) < self.max_particles:
            self.emit_timer = 0
            self._emit_particle()

        for particle in self.particles[:]:
            if not particle.update(dt):
                self.particles.remove(particle)

    def _emit_particle(self):
        config = self.config
        angle = math.radians(config["direction"] + random.uniform(-config["spread"] / 2, config["spread"] / 2))
        speed = random.uniform(config["speed_min"], config["speed_max"])
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        size = random.randint(config["size_min"], config["size_max"])
        color = config["color"]
        if config["color_variance"] > 0:
            variance = config["color_variance"]
            color = (
                max(0, min(255, color[0] + random.randint(-variance, variance))),
                max(0, min(255, color[1] + random.randint(-variance, variance))),
                max(0, min(255, color[2] + random.randint(-variance, variance))),
            )
        particle = Particle(
            self.x, self.y, vx, vy, color, size,
            gravity=config["gravity"],
            friction=config["friction"],
            shape=config["shape"],
            lifetime=self.lifetime,
            glow=config["glow"],
            additive=config["additive"],
            trail=config["trail"],
            fade_speed=config["fade_speed"],
        )
        self.particles.append(particle)

    def draw(self, screen: pygame.Surface):
        for particle in self.particles:
            particle.draw(screen)

    def is_finished(self) -> bool:
        return not self.emitting and len(self.particles) == 0


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.emitters = []
        self.max_particles = 1000

    def update(self, dt: float):
        for particle in self.particles[:]:
            if not particle.update(dt):
                self.particles.remove(particle)

        for emitter in self.emitters[:]:
            emitter.update(dt)
            if emitter.is_finished():
                self.emitters.remove(emitter)

    def add_particle(self, particle: Particle):
        if len(self.particles) < self.max_particles:
            self.particles.append(particle)

    def add_emitter(self, emitter: ParticleEmitter):
        self.emitters.append(emitter)

    def spawn_particles(self, x: float, y: float, count: int, config: dict = None):
        config = config or {}
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(config.get("speed_min", 50), config.get("speed_max", 200))
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.randint(config.get("size_min", 2), config.get("size_max", 6))
            color = config.get("color", WHITE)
            particle = Particle(
                x, y, vx, vy, color, size,
                gravity=config.get("gravity", 0),
                friction=config.get("friction", 0.98),
                shape=config.get("shape", "circle"),
                lifetime=config.get("lifetime", None),
                glow=config.get("glow", False),
                additive=config.get("additive", False),
                trail=config.get("trail", False),
                fade_speed=config.get("fade_speed", 1.0),
            )
            self.add_particle(particle)

    def spawn_explosion(self, x: float, y: float, radius: int = 100, count: int = 30):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, radius * 2)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            size = random.randint(3, 8)
            color = random.choice([ORANGE, YELLOW, RED, WHITE])
            particle = Particle(x, y, vx, vy, color, size, gravity=100, friction=0.95, lifetime=random.uniform(0.5, 1.5), glow=True, additive=True)
            self.add_particle(particle)

    def spawn_sparks(self, x: float, y: float, count: int = 10):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, YELLOW, 2, gravity=100, friction=0.9, shape='spark', lifetime=0.5)
            self.add_particle(particle)

    def spawn_smoke(self, x: float, y: float, count: int = 5):
        for _ in range(count):
            vx = random.uniform(-20, 20)
            vy = random.uniform(-50, -20)
            size = random.randint(5, 15)
            particle = Particle(x, y, vx, vy, GRAY, size, gravity=-50, friction=0.95, fade_speed=0.5, lifetime=random.uniform(1.0, 2.0), shape='circle')
            self.add_particle(particle)

    def spawn_trail(self, x: float, y: float, color: Tuple[int, int, int] = CYAN):
        for _ in range(3):
            vx = random.uniform(-30, 30)
            vy = random.uniform(-30, 30)
            particle = Particle(x, y, vx, vy, color, 3, friction=0.9, fade_speed=2.0, lifetime=0.3, glow=True)
            self.add_particle(particle)

    def spawn_heal(self, x: float, y: float, count: int = 10):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 50
            particle = Particle(x, y, vx, vy, GREEN, 3, gravity=-30, friction=0.95, lifetime=1.0, glow=True, shape='star')
            self.add_particle(particle)

    def spawn_freeze(self, x: float, y: float, count: int = 15):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 60)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, LIGHT_CYAN, 2, gravity=0, friction=0.98, lifetime=0.8, shape='triangle', glow=True)
            self.add_particle(particle)

    def spawn_burn(self, x: float, y: float, count: int = 12):
        for _ in range(count):
            vx = random.uniform(-40, 40)
            vy = random.uniform(-80, -20)
            color = random.choice([ORANGE, RED, YELLOW])
            particle = Particle(x, y, vx, vy, color, 4, gravity=-100, friction=0.95, lifetime=random.uniform(0.5, 1.0), glow=True, additive=True)
            self.add_particle(particle)

    def spawn_poison(self, x: float, y: float, count: int = 10):
        for _ in range(count):
            vx = random.uniform(-30, 30)
            vy = random.uniform(-30, 30)
            particle = Particle(x, y, vx, vy, DARK_GREEN, 3, gravity=0, friction=0.95, lifetime=1.2, shape='circle', glow=True)
            self.add_particle(particle)

    def spawn_electric(self, x: float, y: float, count: int = 15):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 250)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, YELLOW, 2, gravity=0, friction=0.9, lifetime=0.4, shape='spark', glow=True, additive=True)
            self.add_particle(particle)

    def spawn_teleport(self, x: float, y: float, count: int = 20):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 100)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, PURPLE, 3, gravity=0, friction=0.95, lifetime=0.6, shape='ring', glow=True)
            self.add_particle(particle)

    def spawn_void(self, x: float, y: float, count: int = 20):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, (0, 0, 0), 4, gravity=0, friction=0.9, lifetime=1.0, shape='circle', glow=True, additive=True)
            self.add_particle(particle)

    def spawn_blood(self, x: float, y: float, count: int = 10):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 100)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, DARK_RED, 2, gravity=200, friction=0.95, lifetime=0.8, shape='circle')
            self.add_particle(particle)

    def spawn_level_up(self, x: float, y: float, count: int = 30):
        for i in range(count):
            angle = (i / count) * 2 * math.pi
            speed = 100
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, GOLD, 3, gravity=0, friction=0.95, lifetime=1.5, shape='star', glow=True)
            self.add_particle(particle)

    def spawn_crit(self, x: float, y: float, count: int = 15):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 200)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, WHITE, 3, gravity=0, friction=0.9, lifetime=0.5, shape='spark', glow=True, additive=True)
            self.add_particle(particle)

    def spawn_shield_break(self, x: float, y: float, count: int = 20):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle = Particle(x, y, vx, vy, CYAN, 3, gravity=0, friction=0.95, lifetime=0.7, shape='triangle', glow=True)
            self.add_particle(particle)

    def spawn_item_pickup(self, x: float, y: float, color: Tuple[int, int, int] = YELLOW, count: int = 8):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 30
            particle = Particle(x, y, vx, vy, color, 2, gravity=-50, friction=0.95, lifetime=0.6, shape='star', glow=True)
            self.add_particle(particle)

    def draw(self, screen: pygame.Surface):
        for particle in self.particles:
            particle.draw(screen)
        for emitter in self.emitters:
            emitter.draw(screen)

    def clear(self):
        self.particles.clear()
        self.emitters.clear()


def create_explosion(x: float, y: float, color: Tuple[int, int, int] = ORANGE, count: int = 20) -> List[Particle]:
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(50, 200)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        size = random.randint(3, 8)
        particles.append(Particle(x, y, vx, vy, color, size, gravity=200, friction=0.95))
    return particles


def create_sparks(x: float, y: float, color: Tuple[int, int, int] = YELLOW, count: int = 10) -> List[Particle]:
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(100, 300)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        size = random.randint(2, 4)
        particles.append(Particle(x, y, vx, vy, color, size, gravity=100, friction=0.9, shape='spark'))
    return particles


def create_smoke(x: float, y: float, count: int = 5) -> List[Particle]:
    particles = []
    for _ in range(count):
        vx = random.uniform(-20, 20)
        vy = random.uniform(-50, -20)
        size = random.randint(5, 15)
        particles.append(Particle(x, y, vx, vy, GRAY, size, gravity=-50, friction=0.95, fade_speed=0.5))
    return particles


def create_trail(x: float, y: float, color: Tuple[int, int, int] = CYAN) -> List[Particle]:
    particles = []
    for _ in range(3):
        vx = random.uniform(-30, 30)
        vy = random.uniform(-30, 30)
        size = random.randint(2, 5)
        particles.append(Particle(x, y, vx, vy, color, size, friction=0.9, fade_speed=2.0))
    return particles