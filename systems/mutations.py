# systems/mutations.py
import random
from typing import Dict, List, Tuple, Optional
from settings import *


class Mutation:
    """Мутация"""

    def __init__(self, mutation_id: str, name: str, description: str,
                 positive_effect: Dict, negative_effect: Dict):
        self.id = mutation_id
        self.name = name
        self.description = description
        self.positive = positive_effect
        self.negative = negative_effect
        self.active = False

    def apply(self, player):
        """Применение мутации"""
        self.active = True

        # Применение положительных эффектов
        if 'damage' in self.positive:
            player.damage_multiplier *= self.positive['damage']
        if 'speed' in self.positive:
            player.speed *= self.positive['speed']
        if 'hp' in self.positive:
            player.max_hp += self.positive['hp']
            player.hp += self.positive['hp']
        if 'fire_rate' in self.positive:
            player.fire_rate *= self.positive['fire_rate']
        if 'regen' in self.positive:
            player.regen_rate += self.positive['regen']

        # Применение отрицательных эффектов
        if 'hp_drain' in self.negative:
            player.hp_drain += self.negative['hp_drain']
        if 'speed_penalty' in self.negative:
            player.speed *= self.negative['speed_penalty']
        if 'energy_drain' in self.negative:
            player.energy_drain += self.negative['energy_drain']

    def remove(self, player):
        """Снятие мутации"""
        self.active = False
        # Обратное применение эффектов (упрощённо)
        if 'damage' in self.positive:
            player.damage_multiplier /= self.positive['damage']
        if 'speed' in self.positive:
            player.speed /= self.positive['speed']
        if 'speed_penalty' in self.negative:
            player.speed /= self.negative['speed_penalty']


class MutationSystem:
    """Система мутаций"""

    def __init__(self, game):
        self.game = game
        self.active_mutations = []
        self.available_mutations = []
        self._initialize_mutations()

    def _initialize_mutations(self):
        """Инициализация мутаций"""
        self.available_mutations = [
            Mutation('cyber_arm', 'Кибер-рука',
                     'Увеличенный урон, но расход энергии',
                     {'damage': 1.5}, {'energy_drain': 2}),

            Mutation('adrenal_glands', 'Адреналиновые железы',
                     'Повышенная скорость, но сниженное HP',
                     {'speed': 1.3}, {'hp_drain': 1}),

            Mutation('regen_skin', 'Регенерирующая кожа',
                     'Регенерация, но слабость к огню',
                     {'regen': 5}, {'fire_vulnerability': 2}),

            Mutation('night_vision', 'Ночное зрение',
                     'Лучшая видимость, но чувствительность к свету',
                     {'vision': 2}, {'light_sensitivity': 1.5}),

            Mutation('titan_bones', 'Титановые кости',
                     'Больше HP, но медленнее',
                     {'hp': 50}, {'speed_penalty': 0.85}),

            Mutation('quantum_reflexes', 'Квантовые рефлексы',
                     'Быстрая стрельба, но больше отдача',
                     {'fire_rate': 0.6}, {'recoil': 2}),

            Mutation('nano_blood', 'Нано-кровь',
                     'Лечение, но уязвимость к ЭМИ',
                     {'regen': 10}, {'emp_vulnerability': 3}),
        ]

    def apply_mutation(self, mutation_id: str) -> bool:
        """Применение мутации"""
        for mutation in self.available_mutations:
            if mutation.id == mutation_id and not mutation.active:
                mutation.apply(self.game.player)
                self.active_mutations.append(mutation)
                return True
        return False

    def remove_mutation(self, mutation_id: str) -> bool:
        """Снятие мутации"""
        for mutation in self.active_mutations:
            if mutation.id == mutation_id:
                mutation.remove(self.game.player)
                self.active_mutations.remove(mutation)
                return True
        return False

    def get_random_mutation(self) -> Optional[Mutation]:
        """Получение случайной мутации"""
        available = [m for m in self.available_mutations if not m.active]
        if available:
            return random.choice(available)
        return None

    def update(self, dt: float):
        """Обновление мутаций"""
        for mutation in self.active_mutations:
            # Применение постоянных эффектов
            if 'hp_drain' in mutation.negative:
                self.game.player.hp -= mutation.negative['hp_drain'] * dt
            if 'energy_drain' in mutation.negative:
                self.game.player.energy = max(0, self.game.player.energy -
                                              mutation.negative['energy_drain'] * dt)

    def can_get_mutation(self) -> bool:
        """Проверяет, можно ли получить новую мутацию."""
        max_mutations = 3 + self.game.player.level // 5  # 3 базово + 1 за каждые 5 уровней
        if len(self.active_mutations) >= max_mutations:
            return False
        return True

    def get_cannot_reason(self) -> str:
        """Возвращает причину, почему нельзя получить мутацию."""
        max_mutations = 3 + self.game.player.level // 5
        if len(self.active_mutations) >= max_mutations:
            return f"Максимум мутаций: {max_mutations}. Повысьте уровень!"
        return "Мутации недоступны"

    def pay_mutation_cost(self, cost: int) -> bool:
        """Списывает ресурсы за мутацию."""
        if self.game.player.scrap >= cost:
            self.game.player.scrap -= cost
            return True
        return False