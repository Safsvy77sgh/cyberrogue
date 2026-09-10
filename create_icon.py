# create_icon.py
import pygame
import sys

pygame.init()

# Иконка 512x512
icon = pygame.Surface((512, 512))
icon.fill((30, 30, 50))
pygame.draw.circle(icon, (0, 255, 255), (256, 256), 200)
pygame.draw.circle(icon, (255, 255, 255), (256, 256), 200, 5)
pygame.draw.circle(icon, (255, 255, 255), (256, 256), 50)

# Шестиугольный глаз
import math
points = []
for i in range(6):
    angle = i * math.pi / 3 - math.pi / 6
    x = 256 + math.cos(angle) * 80
    y = 256 + math.sin(angle) * 80
    points.append((x, y))
pygame.draw.polygon(icon, (0, 255, 255), points, 5)

pygame.image.save(icon, "icon.png")

# Заставка 1080x1920 (портретная)
presplash = pygame.Surface((1080, 1920))
presplash.fill((10, 10, 20))
font = pygame.font.Font(None, 120)
text = font.render("ПЕРЕГРУЗКА", True, (0, 255, 255))
text2 = font.render("Последний Протокол", True, (255, 255, 255))
presplash.blit(text, (540 - text.get_width()//2, 800))
presplash.blit(text2, (540 - text2.get_width()//2, 950))
pygame.image.save(presplash, "presplash.png")

print("Иконки созданы!")
pygame.quit()