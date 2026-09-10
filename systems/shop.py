# systems/shop.py
import pygame
from settings import *


class Shop:
    def __init__(self, game):
        self.game = game
        self.items = [
            {'name': 'Скорострельность', 'cost': 1000, 'type': 'fire_rate',
             'description': '-10% к времени перезарядки'},
            {'name': 'Максимальное HP', 'cost': 500, 'type': 'max_hp', 'description': '+20 к максимальному HP'},
            {'name': 'Полное восстановление', 'cost': 300, 'type': 'heal', 'description': 'Восстановить всё HP'},
            {'name': 'Скорость движения', 'cost': 600, 'type': 'speed', 'description': '+50 к скорости'},
            {'name': 'Урон', 'cost': 800, 'type': 'damage', 'description': '+10 к урону'},
            {'name': 'Дробовик', 'cost': 1500, 'type': 'weapon_shotgun', 'description': 'Новое оружие'},
            {'name': 'Лазер', 'cost': 2000, 'type': 'weapon_laser', 'description': 'Мощное оружие'}
        ]

    def buy_item(self, index: int) -> bool:
        if index >= len(self.items):
            return False

        item = self.items[index]
        if self.game.score < item['cost']:
            return False

        self.game.score -= item['cost']
        self._apply_item(item['type'])
        if self.game.sound_manager:
            self.game.sound_manager.play('pickup')
        return True

    def _apply_item(self, type_: str):
        player = self.game.player
        if type_ == 'fire_rate':
            player.fire_rate = max(0.15, player.fire_rate - 0.03)
        elif type_ == 'max_hp':
            player.max_hp += 20
            player.hp = min(player.max_hp, player.hp + 20)
        elif type_ == 'heal':
            player.heal(player.max_hp)
        elif type_ == 'speed':
            player.permanent_speed_boost += 50
        elif type_ == 'damage':
            player.permanent_damage_boost += 10
        elif type_ == 'weapon_shotgun':
            player.weapons.append('shotgun')
            player.current_weapon = 'shotgun'
        elif type_ == 'weapon_laser':
            player.weapons.append('laser')
            player.current_weapon = 'laser'

    def draw(self, screen: pygame.Surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        font_large = pygame.font.Font(None, 60)
        title = font_large.render("МАГАЗИН", True, YELLOW)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        font = pygame.font.Font(None, 30)
        y = 150
        for i, item in enumerate(self.items):
            can_buy = self.game.score >= item['cost']
            color = WHITE if can_buy else GRAY
            text = f"{i + 1}. {item['name']} - {item['cost']} очков ({item['description']})"
            rendered = font.render(text, True, color)
            screen.blit(rendered, (SCREEN_WIDTH // 2 - 400, y))
            y += 40

        hint = font.render("Нажмите B для закрытия. Нажмите 1-7 для покупки.", True, LIGHT_GRAY)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))