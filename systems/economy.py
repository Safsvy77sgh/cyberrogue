# systems/economy.py — УЛУЧШЕННАЯ ЭКОНОМИЧЕСКАЯ СИСТЕМА С БИРЖЕЙ

import random
import math
import json
import os
import pygame
from typing import Dict, List, Tuple, Optional, Any
from settings import *


class EconomySystem:
    """Продвинутая экономическая система с биржей, событиями и зависимостью от мира."""

    def __init__(self, game):
        self.game = game
        self.credits = 0
        self.market_prices = {}
        self.supply_demand = {}
        self.transactions_history = []
        self.price_history = {}
        self.market_events = []
        self.active_events = []
        self.market_sentiment = 0.5  # 0.0 - паника, 1.0 - оптимизм
        self.inflation_rate = 0.0
        self.last_update_time = 0
        self.event_cooldown = random.uniform(45, 90)  # Первое событие через 45-90 сек
        self.stock_market_open = False  # Открыта ли биржа
        self.stock_market_tab = 0  # Вкладка биржи (0 - ресурсы, 1 - оружие, 2 - защита)
        self._initialize_market()
        self._initialize_price_history()

    def _initialize_market(self):
        """Инициализация рынка."""
        self.market_prices = {
            # Ресурсы
            'scrap': 10, 'circuit': 25, 'energy_cell': 50, 'crystal': 100,
            'ai_core': 500, 'plasma_fragment': 150, 'dark_matter': 1000,
            'void_shard': 750, 'quantum_foam': 300, 'nano_swarm': 200,
            'bio_gel': 30, 'mechanical_parts': 15,
            # Оружие
            'weapon_pistol': 100, 'weapon_shotgun': 300, 'weapon_laser': 500,
            'weapon_rocket_launcher': 800, 'weapon_plasma_rifle': 1200,
            'weapon_minigun': 1500, 'weapon_flamethrower': 700,
            'weapon_ice_gun': 650, 'weapon_shock_gun': 700,
            # Защита
            'protection_light_armor': 150, 'protection_medium_armor': 400,
            'protection_heavy_armor': 800, 'protection_energy_shield': 600,
            # Расходники
            'medkit': 50, 'grenade': 75, 'emp_grenade': 150,
            'energy_pack': 60, 'shield_cell': 100,
        }

        self.supply_demand = {}
        for item, base_price in self.market_prices.items():
            self.supply_demand[item] = {
                'supply': random.randint(50, 200),
                'demand': random.randint(30, 150),
                'base_price': base_price,
                'volatility': random.uniform(0.03, 0.15),  # Меньше волатильность
            }

    def _initialize_price_history(self):
        """Инициализация истории цен."""
        for item in self.market_prices:
            self.price_history[item] = [self.market_prices[item]] * 50

    def update(self, dt: float):
        """Обновление экономики."""
        self.last_update_time += dt

        # Таймер событий
        self.event_cooldown -= dt
        if self.event_cooldown <= 0:
            if len(self.active_events) < 2:  # Не больше 2 событий одновременно
                if random.random() < 0.35:  # 35% шанс на событие
                    self._generate_market_event()
            self.event_cooldown = random.uniform(60, 120)  # Реже: 60-120 сек

        # Обновление активных событий
        for event in self.active_events[:]:
            event['duration'] -= dt
            if event['duration'] <= 0:
                self.active_events.remove(event)

        # Обновление настроения
        self._update_market_sentiment(dt)

        # Обновление цен (раз в 2 секунды)
        if self.last_update_time >= 2.0:
            self.last_update_time = 0
            self._update_prices()

        # Инфляция
        self.inflation_rate = max(-0.05, min(0.1, self.inflation_rate + random.uniform(-0.005, 0.005)))

    def _generate_market_event(self):
        """Генерация рыночного события."""
        events = [
            {
                'name': '📉 Дефицит ресурсов',
                'effect': 'supply_shock',
                'duration': random.uniform(20, 40),
                'multiplier': random.uniform(1.3, 1.8),
            },
            {
                'name': '📈 Избыток предложения',
                'effect': 'supply_surge',
                'duration': random.uniform(20, 40),
                'multiplier': random.uniform(0.5, 0.75),
            },
            {
                'name': '🔻 Паника на рынке',
                'effect': 'market_crash',
                'duration': random.uniform(15, 30),
                'multiplier': 0.6,
            },
            {
                'name': '🔺 Экономический бум',
                'effect': 'market_boom',
                'duration': random.uniform(15, 30),
                'multiplier': 1.5,
            },
            {
                'name': '⚔️ Военные закупки',
                'effect': 'weapon_demand',
                'duration': random.uniform(20, 35),
                'multiplier': 1.4,
            },
            {
                'name': '🔬 Научный прорыв',
                'effect': 'tech_advance',
                'duration': random.uniform(25, 45),
                'multiplier': 0.7,
            },
        ]
        event = random.choice(events)
        self.active_events.append(event)
        if self.game and hasattr(self.game, 'ui'):
            self.game.ui.show_notification(f"Событие: {event['name']}", ORANGE, 3.0)

    def _update_market_sentiment(self, dt: float):
        """Обновление настроения рынка."""
        for event in self.active_events:
            if event['effect'] in ('market_crash', 'supply_shock'):
                self.market_sentiment -= 0.05 * dt
            elif event['effect'] in ('market_boom', 'tech_advance'):
                self.market_sentiment += 0.05 * dt
        self.market_sentiment += random.uniform(-0.01, 0.01) * dt
        self.market_sentiment = max(0.0, min(1.0, self.market_sentiment))

    def _update_prices(self):
        """Обновление цен."""
        for item, data in self.supply_demand.items():
            supply = data['supply']
            demand = data['demand']
            base_price = data['base_price']
            volatility = data['volatility']
            current_price = self.market_prices[item]

            # Закон спроса/предложения
            if demand > supply:
                price_pressure = 1 + (demand - supply) / max(1, supply) * 0.05
            elif supply > demand:
                price_pressure = 1 - (supply - demand) / max(1, demand) * 0.05
            else:
                price_pressure = 1.0

            # Настроение
            sentiment_effect = 1 + (self.market_sentiment - 0.5) * 0.15

            # Инфляция
            inflation_effect = 1 + self.inflation_rate

            # События
            event_effect = 1.0
            for event in self.active_events:
                if event['effect'] == 'supply_shock' and item in ('scrap', 'circuit', 'energy_cell', 'crystal', 'ai_core'):
                    event_effect *= event['multiplier']
                elif event['effect'] == 'supply_surge':
                    event_effect *= event['multiplier']
                elif event['effect'] == 'market_crash':
                    event_effect *= event['multiplier']
                elif event['effect'] == 'market_boom':
                    event_effect *= event['multiplier']
                elif event['effect'] == 'weapon_demand' and item.startswith('weapon_'):
                    event_effect *= event['multiplier']
                elif event['effect'] == 'tech_advance' and item in ('circuit', 'energy_cell', 'crystal'):
                    event_effect *= event['multiplier']

            # Случайность
            random_effect = 1 + random.uniform(-volatility, volatility)

            # Новая цена
            new_price = current_price * price_pressure * sentiment_effect * inflation_effect * event_effect * random_effect
            new_price = max(1, int(new_price))
            self.market_prices[item] = new_price

            # История
            self.price_history[item].append(new_price)
            if len(self.price_history[item]) > 100:
                self.price_history[item].pop(0)

            # Изменение спроса/предложения
            self.supply_demand[item]['supply'] += random.randint(-3, 3)
            self.supply_demand[item]['demand'] += random.randint(-2, 2)
            self.supply_demand[item]['supply'] = max(1, self.supply_demand[item]['supply'])
            self.supply_demand[item]['demand'] = max(1, self.supply_demand[item]['demand'])

    def buy(self, item: str, quantity: int = 1) -> bool:
        """Покупка предмета."""
        if item not in self.market_prices:
            return False
        total_cost = self.market_prices[item] * quantity
        if self.credits < total_cost:
            return False
        self.credits -= total_cost
        if item in self.supply_demand:
            self.supply_demand[item]['supply'] = max(1, self.supply_demand[item]['supply'] - quantity)
            self.supply_demand[item]['demand'] += quantity
        self.transactions_history.append({
            'type': 'buy', 'item': item, 'quantity': quantity,
            'price': total_cost, 'time': self.game.time_elapsed if self.game else 0,
        })
        return True

    def sell(self, item: str, quantity: int = 1) -> bool:
        """Продажа предмета."""
        if item not in self.market_prices:
            return False
        sell_price = int(self.market_prices[item] * 0.7)
        total_earnings = sell_price * quantity
        self.credits += total_earnings
        if item in self.supply_demand:
            self.supply_demand[item]['supply'] += quantity
            self.supply_demand[item]['demand'] = max(0, self.supply_demand[item]['demand'] - quantity)
        self.transactions_history.append({
            'type': 'sell', 'item': item, 'quantity': quantity,
            'price': total_earnings, 'time': self.game.time_elapsed if self.game else 0,
        })
        return True

    def get_price(self, item: str) -> int:
        """Получение текущей цены."""
        return self.market_prices.get(item, 0)

    def get_all_prices(self) -> Dict:
        """Получение всех цен."""
        return self.market_prices.copy()

    def get_price_history(self, item: str) -> List[int]:
        """Получение истории цен."""
        return self.price_history.get(item, [])

    def get_price_trend(self, item: str) -> float:
        """Получение тренда цены (-1.0 до 1.0)."""
        history = self.get_price_history(item)
        if len(history) < 10:
            return 0.0
        recent = history[-5:]
        older = history[-15:-5]
        if not older:
            return 0.0
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        if avg_older == 0:
            return 0.0
        return max(-1.0, min(1.0, (avg_recent - avg_older) / avg_older * 10))

    def add_credits(self, amount: int):
        """Добавление кредитов."""
        self.credits += amount

    def remove_credits(self, amount: int) -> bool:
        """Снятие кредитов."""
        if self.credits >= amount:
            self.credits -= amount
            return True
        return False

    def get_market_sentiment(self) -> float:
        """Получение настроения рынка."""
        return self.market_sentiment

    def get_active_events(self) -> List[Dict]:
        """Получение активных событий."""
        return self.active_events

    def get_inflation_rate(self) -> float:
        """Получение уровня инфляции."""
        return self.inflation_rate

    def toggle_stock_market(self):
        """Открыть/закрыть биржу."""
        self.stock_market_open = not self.stock_market_open
        return self.stock_market_open

    def change_tab(self, direction: int):
        """Смена вкладки биржи."""
        self.stock_market_tab = (self.stock_market_tab + direction) % 3

    def get_items_by_tab(self) -> List[str]:
        """Получение предметов по вкладке."""
        if self.stock_market_tab == 0:
            return ['scrap', 'circuit', 'energy_cell', 'crystal', 'ai_core',
                    'plasma_fragment', 'dark_matter', 'void_shard',
                    'quantum_foam', 'nano_swarm', 'bio_gel', 'mechanical_parts']
        elif self.stock_market_tab == 1:
            return [item for item in self.market_prices if item.startswith('weapon_')]
        else:
            return [item for item in self.market_prices if item.startswith('protection_') or item in
                    ('medkit', 'grenade', 'emp_grenade', 'energy_pack', 'shield_cell')]

    # ==================== ОТРИСОВКА ====================

    def draw_market_events(self, screen: pygame.Surface):
        """Отрисовка активных событий мелко в углу экрана."""
        if not self.active_events:
            return
        font = pygame.font.Font(None, 18)
        y = SCREEN_HEIGHT - 100
        for event in self.active_events[:3]:  # Максимум 3 события
            text = f"{event['name']} ({int(event['duration'])}с)"
            surf = font.render(text, True, ORANGE)
            screen.blit(surf, (10, y))
            y += 20

    def draw_stock_market(self, screen: pygame.Surface):
        """Отрисовка биржи."""
        if not self.stock_market_open:
            return

        # Затемнение фона
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # Панель биржи
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 400, 50, 800, 600)
        pygame.draw.rect(screen, (25, 25, 35), panel)
        pygame.draw.rect(screen, WHITE, panel, 2)

        font_title = pygame.font.Font(None, 48)
        title = font_title.render("📊 БИРЖА", True, YELLOW)
        screen.blit(title, (panel.x + 300, panel.y + 20))

        # Кредиты
        font = pygame.font.Font(None, 28)
        credits_text = font.render(f"Кредиты: {self.credits}", True, GREEN)
        screen.blit(credits_text, (panel.x + 20, panel.y + 80))

        # Вкладки
        tabs = ["Ресурсы", "Оружие", "Защита/Расходники"]
        tab_width = 200
        for i, tab_name in enumerate(tabs):
            tab_rect = pygame.Rect(panel.x + 20 + i * tab_width, panel.y + 120, tab_width - 10, 35)
            color = YELLOW if i == self.stock_market_tab else GRAY
            pygame.draw.rect(screen, color, tab_rect, 2)
            tab_text = font.render(tab_name, True, WHITE)
            screen.blit(tab_text, (tab_rect.x + 10, tab_rect.y + 5))

        # Список предметов
        items = self.get_items_by_tab()
        y = panel.y + 170
        for item in items:
            if item not in self.market_prices:
                continue
            price = self.market_prices[item]
            trend = self.get_price_trend(item)

            # Цвет тренда
            if trend > 0.05:
                trend_color = GREEN
                trend_arrow = "▲"
            elif trend < -0.05:
                trend_color = RED
                trend_arrow = "▼"
            else:
                trend_color = WHITE
                trend_arrow = "—"

            item_text = font.render(f"{item}: {price} кр. {trend_arrow}", True, WHITE)
            screen.blit(item_text, (panel.x + 30, y))

            # Кнопки покупки/продажи
            buy_btn = pygame.Rect(panel.x + 550, y - 5, 100, 25)
            sell_btn = pygame.Rect(panel.x + 660, y - 5, 100, 25)
            pygame.draw.rect(screen, GREEN, buy_btn)
            pygame.draw.rect(screen, RED, sell_btn)
            buy_text = font.render("Купить", True, WHITE)
            sell_text = font.render("Продать", True, WHITE)
            screen.blit(buy_text, (buy_btn.x + 15, buy_btn.y))
            screen.blit(sell_text, (sell_btn.x + 10, sell_btn.y))

            y += 35
            if y > panel.y + 550:
                break

        # Подсказка
        hint_font = pygame.font.Font(None, 20)
        hint = hint_font.render("ESC - закрыть | Tab - вкладка | Нажмите на Купить/Продать", True, LIGHT_GRAY)
        screen.blit(hint, (panel.x + 100, panel.y + 570))

    def handle_stock_market_click(self, pos: Tuple[int, int]):
        """Обработка кликов в бирже."""
        if not self.stock_market_open:
            return

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 400, 50, 800, 600)
        if not panel.collidepoint(pos):
            return

        # Вкладки
        tab_width = 200
        for i in range(3):
            tab_rect = pygame.Rect(panel.x + 20 + i * tab_width, panel.y + 120, tab_width - 10, 35)
            if tab_rect.collidepoint(pos):
                self.stock_market_tab = i
                return

        # Предметы
        items = self.get_items_by_tab()
        y = panel.y + 170
        for item in items:
            if item not in self.market_prices:
                continue
            buy_btn = pygame.Rect(panel.x + 550, y - 5, 100, 25)
            sell_btn = pygame.Rect(panel.x + 660, y - 5, 100, 25)
            if buy_btn.collidepoint(pos):
                self.buy(item)
                return
            elif sell_btn.collidepoint(pos):
                self.sell(item)
                return
            y += 35

    def save_to_file(self, filename: str = "economy_save.json"):
        """Сохранение экономики."""
        data = {
            'credits': self.credits,
            'market_prices': self.market_prices,
            'supply_demand': self.supply_demand,
            'transactions_history': self.transactions_history,
            'price_history': self.price_history,
            'market_sentiment': self.market_sentiment,
            'inflation_rate': self.inflation_rate,
            'active_events': self.active_events,
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def load_from_file(self, filename: str = "economy_save.json"):
        """Загрузка экономики."""
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.credits = data.get('credits', 0)
            self.market_prices = data.get('market_prices', self.market_prices)
            self.supply_demand = data.get('supply_demand', self.supply_demand)
            self.transactions_history = data.get('transactions_history', [])
            self.price_history = data.get('price_history', self.price_history)
            self.market_sentiment = data.get('market_sentiment', 0.5)
            self.inflation_rate = data.get('inflation_rate', 0.0)
            self.active_events = data.get('active_events', [])
            return True
        except:
            return False