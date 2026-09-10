# systems/__init__.py

from systems.game import Game
from systems.collision import CollisionSystem
from systems.wave_manager import RoomManager
from systems.achievement import AchievementManager
from systems.save_system import SaveSystem
from systems.shop import Shop
from systems.story import StoryManager
from systems.quest import QuestManager, Quest, QuestObjective
from systems.dialogue import DialogueManager
from systems.ui import UI
from systems.effects import EffectSystem, EffectData, EffectInstance
from systems.crafting import CraftingSystem, CraftingRecipe
from systems.crafting_extended import CraftingSystemExtended, CraftingMaterial, CraftingRecipeExtended
from systems.portal import Portal
from systems.editor import Editor
from systems.synergy import SynergySystem
from systems.procedural_generation import ProceduralGenerator
from systems.building import BuildingSystem, Building
from systems.weather import WeatherSystem
from systems.stealth import StealthSystem
from systems.allies import AllySystem, Ally
from systems.vehicles import VehicleSystem, Vehicle
from systems.economy import EconomySystem
from systems.mutations import MutationSystem, Mutation
from systems.reputation import ReputationSystem
from systems.time_system import TimeSystem
from systems.events import EventSystem, GameEvent
from systems.legacy import LegacySystem
from systems.adaptive_enemies import AdaptiveEnemySystem, AdaptiveEnemyController
from systems.evolutionary_ai import EvolutionaryAIManager, AIIndividual, BehaviorGene, SituationalRule
from systems.coop import CoopSystem, CoopPlayer
from systems.weapons_extended import WeaponManager, Weapon
from systems.protection import ProtectionManager, Protection
from systems.minions import MinionManager, Minion

__all__ = [
    'Game',
    'CollisionSystem',
    'RoomManager',
    'AchievementManager',
    'SaveSystem',
    'Shop',
    'StoryManager',
    'QuestManager',
    'Quest',
    'QuestObjective',
    'DialogueManager',
    'UI',
    'EffectSystem',
    'EffectData',
    'EffectInstance',
    'CraftingSystem',
    'CraftingRecipe',
    'CraftingSystemExtended',
    'CraftingMaterial',
    'CraftingRecipeExtended',
    'Portal',
    'Editor',
    'SynergySystem',
    'ProceduralGenerator',
    'BuildingSystem',
    'Building',
    'WeatherSystem',
    'StealthSystem',
    'AllySystem',
    'Ally',
    'VehicleSystem',
    'Vehicle',
    'EconomySystem',
    'MutationSystem',
    'Mutation',
    'ReputationSystem',
    'TimeSystem',
    'EventSystem',
    'GameEvent',
    'LegacySystem',
    'AdaptiveEnemySystem',
    'AdaptiveEnemyController',
    'EvolutionaryAIManager',
    'AIIndividual',
    'BehaviorGene',
    'SituationalRule',
    'CoopSystem',
    'CoopPlayer',
    'WeaponManager',
    'Weapon',
    'ProtectionManager',
    'Protection',
    'MinionManager',
    'Minion',
]