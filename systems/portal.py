import pygame
import math
from settings import *


class Portal:
    def __init__(self, x, y, destination, color=PURPLE, bidirectional=False):
        self.x = x
        self.y = y
        self.radius = 30
        self.destination = destination
        self.color = color
        self.bidirectional = bidirectional
        self.active = True
        self.animation = 0

    def update(self, dt):
        self.animation += dt * 2

    def draw(self, screen):
        # Пульсирующий круг
        pulse = int(100 + 50 * math.sin(self.animation))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius, 3)
        pygame.draw.circle(screen, (self.color[0], self.color[1], self.color[2], pulse),
                           (int(self.x), int(self.y)), self.radius - 5, 2)

    def contains(self, x, y, radius=0):
        dist = math.hypot(x - self.x, y - self.y)
        return dist < self.radius + radius