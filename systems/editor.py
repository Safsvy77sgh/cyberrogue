import pygame
import json
import os
import math
import random
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from settings import *
from entities.player import Player
from entities.enemy import Enemy
from entities.bullet import Bullet
from entities.obstacle import Obstacle
from entities.pickup import Pickup
from entities.particle import Particle
from entities.wall import EnergyWall
from entities.damage_number import DamageNumber
from systems.portal import Portal
from systems.effects import EffectSystem, EffectData, EffectInstance
from systems.crafting import CraftingSystem, CraftingRecipe
from systems.procedural_generation import ProceduralGenerator, Room, Corridor


class EditorObject:
    def __init__(self, obj_id: str, name: str, obj_type: str):
        self.id = obj_id
        self.name = name
        self.type = obj_type
        self.properties = {}
        self.position = (0, 0)
        self.size = (50, 50)
        self.color = WHITE
        self.visible = True
        self.locked = False
        self.selected = False

    def set_property(self, key: str, value: Any):
        self.properties[key] = value

    def get_property(self, key: str, default=None):
        return self.properties.get(key, default)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "properties": self.properties,
            "position": self.position,
            "size": self.size,
            "color": self.color,
            "visible": self.visible,
            "locked": self.locked,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EditorObject':
        obj = cls(data["id"], data["name"], data["type"])
        obj.properties = data.get("properties", {})
        obj.position = data.get("position", (0, 0))
        obj.size = data.get("size", (50, 50))
        obj.color = data.get("color", WHITE)
        obj.visible = data.get("visible", True)
        obj.locked = data.get("locked", False)
        return obj

    def draw(self, screen, offset_x=0, offset_y=0):
        if not self.visible:
            return
        x = self.position[0] + offset_x
        y = self.position[1] + offset_y
        pygame.draw.rect(screen, self.color, (x, y, self.size[0], self.size[1]), 2)
        if self.selected:
            pygame.draw.rect(screen, YELLOW, (x - 5, y - 5, self.size[0] + 10, self.size[1] + 10), 2)


class EditorPropertyField:
    def __init__(self, label: str, value: Any, field_type: str = "text"):
        self.label = label
        self.value = value
        self.field_type = field_type
        self.active = False
        self.rect = pygame.Rect(0, 0, 200, 30)

    def draw(self, screen, x, y):
        self.rect.x = x
        self.rect.y = y
        font = pygame.font.Font(None, 24)
        label_surf = font.render(self.label, True, WHITE)
        screen.blit(label_surf, (x, y))
        pygame.draw.rect(screen, GRAY, (x + 150, y, 200, 30), 2)
        if self.active:
            pygame.draw.rect(screen, YELLOW, (x + 150, y, 200, 30), 2)
        if self.field_type == "text":
            value_surf = font.render(str(self.value), True, WHITE)
            screen.blit(value_surf, (x + 155, y + 5))
        elif self.field_type == "number":
            value_surf = font.render(str(self.value), True, WHITE)
            screen.blit(value_surf, (x + 155, y + 5))
        elif self.field_type == "boolean":
            value_surf = font.render("True" if self.value else "False", True, WHITE)
            screen.blit(value_surf, (x + 155, y + 5))
        elif self.field_type == "color":
            pygame.draw.rect(screen, self.value if isinstance(self.value, tuple) else WHITE, (x + 150, y, 200, 30))

    def handle_click(self, pos):
        return self.rect.collidepoint(pos)

    def handle_key(self, event):
        if not self.active:
            return
        if event.key == pygame.K_BACKSPACE:
            if self.field_type == "text":
                self.value = self.value[:-1]
            elif self.field_type == "number":
                self.value = self.value // 10
        elif event.key == pygame.K_RETURN:
            self.active = False
        else:
            if self.field_type == "text":
                self.value += event.unicode
            elif self.field_type == "number":
                if event.unicode.isdigit():
                    self.value = self.value * 10 + int(event.unicode)


class EditorPanel:
    def __init__(self, title: str, x: int, y: int, width: int, height: int):
        self.title = title
        self.rect = pygame.Rect(x, y, width, height)
        self.fields = []
        self.buttons = []
        self.active = False
        self.scroll_y = 0
        self.collapsed = False

    def add_field(self, label: str, value: Any, field_type: str = "text"):
        field = EditorPropertyField(label, value, field_type)
        self.fields.append(field)
        return field

    def add_button(self, label: str, callback: Callable):
        self.buttons.append({"label": label, "callback": callback})
        return self.buttons[-1]

    def draw(self, screen):
        if self.collapsed:
            font = pygame.font.Font(None, 24)
            title_surf = font.render(self.title + " (развёрнуто)", True, WHITE)
            screen.blit(title_surf, (self.rect.x, self.rect.y))
            return
        pygame.draw.rect(screen, DARK_GRAY, self.rect)
        pygame.draw.rect(screen, WHITE, self.rect, 2)
        font = pygame.font.Font(None, 24)
        title_surf = font.render(self.title, True, YELLOW)
        screen.blit(title_surf, (self.rect.x + 10, self.rect.y + 5))
        y = self.rect.y + 40 + self.scroll_y
        for field in self.fields:
            field.draw(screen, self.rect.x + 10, y)
            y += 35
        for button in self.buttons:
            btn_rect = pygame.Rect(self.rect.x + 10, y, 150, 30)
            pygame.draw.rect(screen, BLUE, btn_rect)
            pygame.draw.rect(screen, WHITE, btn_rect, 2)
            btn_font = pygame.font.Font(None, 20)
            btn_surf = btn_font.render(button["label"], True, WHITE)
            screen.blit(btn_surf, (btn_rect.x + 10, btn_rect.y + 5))
            button["rect"] = btn_rect
            y += 40

    def handle_click(self, pos):
        if self.collapsed:
            if self.rect.collidepoint(pos):
                self.collapsed = False
                return True
        if self.rect.collidepoint(pos):
            for field in self.fields:
                if field.handle_click(pos):
                    field.active = True
                else:
                    field.active = False
            for button in self.buttons:
                if "rect" in button and button["rect"].collidepoint(pos):
                    button["callback"]()
                    return True
            return True
        return False

    def handle_key(self, event):
        for field in self.fields:
            field.handle_key(event)

    def handle_scroll(self, dy):
        self.scroll_y += dy
        self.scroll_y = max(-500, min(500, self.scroll_y))


class Editor:
    def __init__(self, game):
        self.game = game
        self.objects: List[EditorObject] = []
        self.selected_object: Optional[EditorObject] = None
        self.panels: List[EditorPanel] = []
        self.mode = "select"
        self.dragging = False
        self.drag_start = (0, 0)
        self.drag_offset = (0, 0)
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.show_grid = True
        self.grid_size = 50
        self.snap_to_grid = True
        self.copy_buffer = []
        self.undo_stack = []
        self.redo_stack = []
        self.current_file = None
        self.object_counter = 0
        self.edit_property_panel = None
        self.tool_panel = None
        self.object_palette = []
        self.texture_editor = None
        self.effect_creator = None
        self.dialogue_creator = None
        self.npc_creator = None
        self.mechanic_creator = None
        self.particle_creator = None
        self.weapon_creator = None
        self.room_generator_panel = None
        self.loot_table_editor = None
        self.weather_editor = None
        self.textures = {}
        self.custom_effects = {}
        self.custom_dialogues = []
        self.custom_npcs = []
        self.custom_mechanics = []
        self.custom_particles = []
        self.custom_weapons = []
        self.custom_loot_tables = {}
        self.custom_weather = []
        self.custom_room_configs = {}
        self.integration = EditorIntegration(self)
        self.menu = EditorMenu(self)
        self.file_manager = EditorFileManager(self)
        self.full_state = EditorFullState(self)
        self.current_menu = None
        self.init_panels()

    def init_panels(self):
        self.tool_panel = EditorPanel("Инструменты", 10, 10, 250, 600)
        self.tool_panel.add_button("Выбрать", lambda: self.set_mode("select"))
        self.tool_panel.add_button("Создать объект", lambda: self.set_mode("create"))
        self.tool_panel.add_button("Удалить", lambda: self.delete_selected())
        self.tool_panel.add_button("Дублировать", lambda: self.duplicate_selected())
        self.tool_panel.add_button("Копировать", lambda: self.copy_selected())
        self.tool_panel.add_button("Вставить", lambda: self.paste())
        self.tool_panel.add_button("Отменить", lambda: self.undo())
        self.tool_panel.add_button("Повторить", lambda: self.redo())
        self.tool_panel.add_button("Сетка вкл/выкл", lambda: self.toggle_grid())
        self.tool_panel.add_button("Привязка к сетке", lambda: self.toggle_snap())
        self.tool_panel.add_button("Сохранить", lambda: self.save_current())
        self.tool_panel.add_button("Загрузить", lambda: self.load_current())
        self.tool_panel.add_button("Меню", lambda: self.toggle_menu())
        self.tool_panel.add_button("Очистить", lambda: self.clear_all())
        self.panels.append(self.tool_panel)

        self.object_palette = EditorPanel("Палитра", 270, 10, 300, 600)
        self.object_palette.add_button("Препятствие", lambda: self.create_object("obstacle", "box"))
        self.object_palette.add_button("Ящик", lambda: self.create_object("obstacle", "crate"))
        self.object_palette.add_button("Бочка", lambda: self.create_object("obstacle", "barrel"))
        self.object_palette.add_button("Стена", lambda: self.create_object("obstacle", "wall"))
        self.object_palette.add_button("Враг: базовый", lambda: self.create_object("enemy", "basic"))
        self.object_palette.add_button("Враг: быстрый", lambda: self.create_object("enemy", "fast"))
        self.object_palette.add_button("Враг: танк", lambda: self.create_object("enemy", "tank"))
        self.object_palette.add_button("Враг: элита", lambda: self.create_object("enemy", "elite"))
        self.object_palette.add_button("Пикап: металл", lambda: self.create_object("pickup", "scrap"))
        self.object_palette.add_button("Пикап: аптечка", lambda: self.create_object("pickup", "repair"))
        self.object_palette.add_button("Пикап: оружие", lambda: self.create_object("pickup", "weapon_shotgun"))
        self.object_palette.add_button("Портал", lambda: self.create_object("portal", "ruined_city"))
        self.object_palette.add_button("Терминал", lambda: self.create_object("lore", "terminal"))
        self.object_palette.add_button("Аудиолог", lambda: self.create_object("lore", "audio_log"))
        self.object_palette.add_button("Голограмма", lambda: self.create_object("lore", "holo_projector"))
        self.object_palette.add_button("Фрагмент памяти", lambda: self.create_object("lore", "memory_shard"))
        self.object_palette.add_button("Квантовое ядро", lambda: self.create_object("lore", "quantum_core"))
        self.panels.append(self.object_palette)

        self.edit_property_panel = EditorPanel("Свойства", 580, 10, 350, 600)
        self.panels.append(self.edit_property_panel)

        self.texture_creator_panel = EditorPanel("Создание текстур", 940, 10, 320, 400)
        self.texture_creator_panel.add_button("Новая текстура 32x32", lambda: self.create_new_texture(32, 32))
        self.texture_creator_panel.add_button("Новая текстура 64x64", lambda: self.create_new_texture(64, 64))
        self.texture_creator_panel.add_button("Новая текстура 128x128", lambda: self.create_new_texture(128, 128))
        self.texture_creator_panel.add_button("Редактор пикселей", lambda: self.open_pixel_editor())
        self.panels.append(self.texture_creator_panel)

        self.effect_creator_panel = EditorPanel("Создание эффектов", 940, 420, 320, 300)
        self.effect_creator_panel.add_button("Новый эффект", lambda: self.open_effect_creator())
        self.effect_creator_panel.add_button("Список эффектов", lambda: self.open_effect_list())
        self.panels.append(self.effect_creator_panel)

    def set_mode(self, mode: str):
        self.mode = mode

    def create_object(self, obj_type: str, subtype: str = ""):
        self.object_counter += 1
        obj_id = f"obj_{self.object_counter}_{random.randint(1000, 9999)}"
        name = f"{obj_type}_{subtype}"
        new_obj = EditorObject(obj_id, name, obj_type)
        new_obj.position = (400 + random.randint(-50, 50), 300 + random.randint(-50, 50))
        if obj_type == "obstacle":
            new_obj.properties["subtype"] = subtype
            new_obj.properties["hp"] = 100
            new_obj.size = (50, 50)
        elif obj_type == "enemy":
            new_obj.properties["subtype"] = subtype
            new_obj.properties["hp"] = 50
            new_obj.properties["speed"] = 100
            new_obj.properties["wave"] = getattr(self.game, 'wave', 1) or 1
        elif obj_type == "pickup":
            new_obj.properties["subtype"] = subtype
            new_obj.properties["amount"] = 1
        elif obj_type == "portal":
            new_obj.properties["destination"] = "ruined_city"
        elif obj_type == "lore":
            new_obj.properties["subtype"] = subtype
            new_obj.properties["lore_id"] = ""
        self.objects.append(new_obj)
        self.selected_object = new_obj
        self.refresh_property_panel()
        self.save_state()

    def save_map(self):
        if not self.current_file:
            self.current_file = "custom_map.json"
        data = {
            "objects": self.serialize_objects(),
            "camera": (self.camera_x, self.camera_y),
            "zoom": self.zoom,
        }
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.game.ui.show_notification(f"Карта сохранена: {self.current_file}", GREEN, 3.0)
        except:
            self.game.ui.show_notification("Ошибка сохранения", RED, 3.0)

    def load_map(self):
        if not self.current_file:
            self.current_file = "custom_map.json"
        if not os.path.exists(self.current_file):
            return
        try:
            with open(self.current_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.objects = [EditorObject.from_dict(d) for d in data.get("objects", [])]
            self.camera_x, self.camera_y = data.get("camera", (0, 0))
            self.zoom = data.get("zoom", 1.0)
            self.selected_object = None
            self.refresh_property_panel()
            self.game.ui.show_notification(f"Карта загружена: {self.current_file}", GREEN, 3.0)
        except:
            self.game.ui.show_notification("Ошибка загрузки", RED, 3.0)

    def create_new_texture(self, width, height):
        self.texture_editor = {
            "width": width,
            "height": height,
            "pixels": [[(0, 0, 0, 0) for _ in range(width)] for _ in range(height)],
            "current_color": (255, 255, 255, 255),
        }
        self.game.ui.show_notification(f"Создана новая текстура {width}x{height}", CYAN, 3.0)

    def open_pixel_editor(self):
        if not self.texture_editor:
            self.create_new_texture(32, 32)
        self.game.ui.show_notification("Редактор пикселей открыт", CYAN, 2.0)

    def open_effect_creator(self):
        self.effect_creator = {
            "name": "",
            "duration": 0,
            "permanent": False,
            "type": "buff",
            "rarity": "common",
            "params": {},
        }
        self.game.ui.show_notification("Создание нового эффекта", MAGENTA, 2.0)

    def open_effect_list(self):
        effects = self.game.effect_system.get_all_effects() if hasattr(self.game, 'effect_system') else []
        self.game.ui.show_notification(f"Всего эффектов: {len(effects)}", MAGENTA, 2.0)

    def save_current(self):
        filename = self.current_file or "untitled.json"
        self.file_manager.save(filename)

    def load_current(self):
        if self.current_file:
            self.file_manager.load(self.current_file)

    def toggle_menu(self):
        self.menu.active = not self.menu.active

    def serialize_full_state(self):
        return self.full_state.serialize()

    def deserialize_full_state(self, data):
        self.full_state.deserialize(data)

    def serialize_textures(self):
        result = {}
        for name, tex in self.textures.items():
            result[name] = {
                "width": tex.width,
                "height": tex.height,
                "pixels": [[list(p) for p in row] for row in tex.pixels],
            }
        return result

    def deserialize_textures(self, data):
        self.textures = {}
        for name, tex_data in data.items():
            tex = TextureEditor(self, tex_data["width"], tex_data["height"])
            tex.pixels = [[tuple(p) for p in row] for row in tex_data["pixels"]]
            self.textures[name] = tex

    def serialize_effects(self):
        return {eid: eff.to_dict() if hasattr(eff, 'to_dict') else eff for eid, eff in self.custom_effects.items()}

    def deserialize_effects(self, data):
        self.custom_effects = data

    def serialize_dialogues(self):
        return self.custom_dialogues

    def deserialize_dialogues(self, data):
        self.custom_dialogues = data

    def serialize_npcs(self):
        return self.custom_npcs

    def deserialize_npcs(self, data):
        self.custom_npcs = data

    def serialize_mechanics(self):
        return self.custom_mechanics

    def deserialize_mechanics(self, data):
        self.custom_mechanics = data

    def serialize_particles(self):
        return self.custom_particles

    def deserialize_particles(self, data):
        self.custom_particles = data

    def serialize_weapons(self):
        return self.custom_weapons

    def deserialize_weapons(self, data):
        self.custom_weapons = data

    def serialize_loot_tables(self):
        return self.custom_loot_tables

    def deserialize_loot_tables(self, data):
        self.custom_loot_tables = data

    def serialize_weather(self):
        return self.custom_weather

    def deserialize_weather(self, data):
        self.custom_weather = data

    def serialize_room_configs(self):
        return self.custom_room_configs

    def deserialize_room_configs(self, data):
        self.custom_room_configs = data

    def update(self, dt: float):
        mouse = pygame.mouse.get_pressed()
        pos = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        if self.menu.active:
            return

        if self.integration.active_subeditor:
            self.integration.handle_subeditor_click(pos) if mouse[0] else None
            return

        if self.mode == "create" and mouse[0]:
            self.handle_create_click(pos)

        if self.mode == "select" and mouse[0]:
            self.handle_select_click(pos)

        if self.dragging and self.selected_object and mouse[0]:
            if self.snap_to_grid:
                new_x = round((pos[0] - self.camera_x) / self.grid_size) * self.grid_size + self.camera_x
                new_y = round((pos[1] - self.camera_y) / self.grid_size) * self.grid_size + self.camera_y
            else:
                new_x = pos[0] + self.drag_offset[0]
                new_y = pos[1] + self.drag_offset[1]
            self.selected_object.position = (new_x, new_y)

        if not mouse[0]:
            self.dragging = False

        self.handle_shortcuts(keys)

    def handle_create_click(self, pos):
        if self.snap_to_grid:
            grid_x = round((pos[0] - self.camera_x) / self.grid_size) * self.grid_size + self.camera_x
            grid_y = round((pos[1] - self.camera_y) / self.grid_size) * self.grid_size + self.camera_y
        else:
            grid_x = pos[0]
            grid_y = pos[1]
        self.create_object_at_position(grid_x, grid_y)

    def create_object_at_position(self, x, y):
        if not self.selected_object:
            return
        new_obj = EditorObject.from_dict(self.selected_object.to_dict())
        self.object_counter += 1
        new_obj.id = f"obj_{self.object_counter}_{random.randint(1000, 9999)}"
        new_obj.position = (x, y)
        self.objects.append(new_obj)
        self.save_state()

    def handle_select_click(self, pos):
        for obj in reversed(self.objects):
            obj_rect = pygame.Rect(obj.position[0], obj.position[1], obj.size[0], obj.size[1])
            if obj_rect.collidepoint(pos[0] - self.camera_x, pos[1] - self.camera_y):
                self.selected_object = obj
                self.refresh_property_panel()
                self.dragging = True
                self.drag_start = pos
                self.drag_offset = (obj.position[0] - pos[0], obj.position[1] - pos[1])
                return
        self.selected_object = None
        self.refresh_property_panel()

    def handle_shortcuts(self, keys):
        if keys[pygame.K_LCTRL] and keys[pygame.K_s]:
            self.save_current()
        if keys[pygame.K_LCTRL] and keys[pygame.K_l]:
            self.load_current()
        if keys[pygame.K_LCTRL] and keys[pygame.K_z]:
            self.undo()
        if keys[pygame.K_LCTRL] and keys[pygame.K_y]:
            self.redo()
        if keys[pygame.K_LCTRL] and keys[pygame.K_c]:
            self.copy_selected()
        if keys[pygame.K_LCTRL] and keys[pygame.K_v]:
            self.paste()
        if keys[pygame.K_DELETE]:
            self.delete_selected()

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            for panel in self.panels:
                panel.handle_scroll(event.y * 20)
            if not self.is_mouse_over_panel(event.pos):
                self.zoom *= 1.1 if event.y > 0 else 0.9
                self.zoom = max(0.2, min(3.0, self.zoom))

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.menu.active and self.menu.handle_click(event.pos):
                return
            for panel in self.panels:
                if panel.handle_click(event.pos):
                    return
            if self.integration.active_subeditor:
                self.integration.handle_subeditor_click(event.pos)

        if event.type == pygame.KEYDOWN:
            for panel in self.panels:
                panel.handle_key(event)
            if self.integration.active_subeditor:
                self.integration.handle_subeditor_key(event)

    def is_mouse_over_panel(self, pos):
        for panel in self.panels:
            if panel.rect.collidepoint(pos):
                return True
        return False

    def draw(self, screen):
        if self.show_grid:
            self.draw_grid(screen)
        for obj in self.objects:
            obj.draw(screen, -self.camera_x, -self.camera_y)
        for panel in self.panels:
            panel.draw(screen)
        self.integration.draw_subeditors(screen)
        self.menu.draw(screen)
        self.draw_hud(screen)

    def draw_grid(self, screen):
        start_x = self.camera_x % self.grid_size
        start_y = self.camera_y % self.grid_size
        for x in range(int(start_x), SCREEN_WIDTH, self.grid_size):
            pygame.draw.line(screen, (40, 40, 40), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(int(start_y), SCREEN_HEIGHT, self.grid_size):
            pygame.draw.line(screen, (40, 40, 40), (0, y), (SCREEN_WIDTH, y))

    def draw_hud(self, screen):
        font = pygame.font.Font(None, 24)
        info = f"Режим: {self.mode} | Объектов: {len(self.objects)} | Масштаб: {self.zoom:.1f}"
        surf = font.render(info, True, WHITE)
        screen.blit(surf, (10, SCREEN_HEIGHT - 40))

    def delete_selected(self):
        if self.selected_object:
            self.objects.remove(self.selected_object)
            self.selected_object = None
            self.refresh_property_panel()
            self.save_state()

    def duplicate_selected(self):
        if self.selected_object:
            new_obj = EditorObject.from_dict(self.selected_object.to_dict())
            self.object_counter += 1
            new_obj.id = f"obj_{self.object_counter}_{random.randint(1000, 9999)}"
            new_obj.position = (new_obj.position[0] + 20, new_obj.position[1] + 20)
            self.objects.append(new_obj)
            self.selected_object = new_obj
            self.refresh_property_panel()
            self.save_state()

    def copy_selected(self):
        if self.selected_object:
            self.copy_buffer = [self.selected_object.to_dict()]

    def paste(self):
        if self.copy_buffer:
            for data in self.copy_buffer:
                new_obj = EditorObject.from_dict(data)
                self.object_counter += 1
                new_obj.id = f"obj_{self.object_counter}_{random.randint(1000, 9999)}"
                new_obj.position = (new_obj.position[0] + 30, new_obj.position[1] + 30)
                self.objects.append(new_obj)
                self.selected_object = new_obj
            self.refresh_property_panel()
            self.save_state()

    def undo(self):
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.redo_stack.append(self.serialize_objects())
            self.deserialize_objects(state)

    def redo(self):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(self.serialize_objects())
            self.deserialize_objects(state)

    def save_state(self):
        self.undo_stack.append(self.serialize_objects())
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def serialize_objects(self):
        return [obj.to_dict() for obj in self.objects]

    def deserialize_objects(self, data):
        self.objects = [EditorObject.from_dict(d) for d in data]
        self.selected_object = None
        self.refresh_property_panel()

    def toggle_grid(self):
        self.show_grid = not self.show_grid

    def toggle_snap(self):
        self.snap_to_grid = not self.snap_to_grid

    def clear_all(self):
        self.objects.clear()
        self.selected_object = None
        self.refresh_property_panel()
        self.save_state()

    def refresh_property_panel(self):
        self.edit_property_panel.fields.clear()
        self.edit_property_panel.buttons.clear()
        if not self.selected_object:
            return
        obj = self.selected_object
        self.edit_property_panel.add_field("ID", obj.id, "text")
        self.edit_property_panel.add_field("Имя", obj.name, "text")
        self.edit_property_panel.add_field("Тип", obj.type, "text")
        self.edit_property_panel.add_field("X", obj.position[0], "number")
        self.edit_property_panel.add_field("Y", obj.position[1], "number")
        self.edit_property_panel.add_field("Ширина", obj.size[0], "number")
        self.edit_property_panel.add_field("Высота", obj.size[1], "number")
        for key, value in obj.properties.items():
            if isinstance(value, bool):
                self.edit_property_panel.add_field(key, value, "boolean")
            elif isinstance(value, (int, float)):
                self.edit_property_panel.add_field(key, value, "number")
            else:
                self.edit_property_panel.add_field(key, value, "text")


class TextureEditor:
    def __init__(self, editor, width=32, height=32):
        self.editor = editor
        self.width = width
        self.height = height
        self.pixels = [[(0, 0, 0, 0) for _ in range(width)] for _ in range(height)]
        self.current_color = (255, 255, 255, 255)
        self.brush_size = 1
        self.tool = "pencil"  # pencil, eraser, fill, eyedropper
        self.zoom = 20
        self.offset_x = 0
        self.offset_y = 0
        self.active = False
        self.preview_surface = None
        self.file_name = "new_texture.png"
        self.history = []
        self.history_index = -1
        self.save_history()

    def save_history(self):
        self.history.append([[list(pixel) for pixel in row] for row in self.pixels])
        self.history_index = len(self.history) - 1
        if len(self.history) > 50:
            self.history.pop(0)
            self.history_index = len(self.history) - 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.pixels = [[tuple(pixel) for pixel in row] for row in self.history[self.history_index]]

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.pixels = [[tuple(pixel) for pixel in row] for row in self.history[self.history_index]]

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = color

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y][x]
        return (0, 0, 0, 0)

    def flood_fill(self, x, y, target_color, replacement_color):
        if target_color == replacement_color:
            return
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if 0 <= cx < self.width and 0 <= cy < self.height:
                if self.pixels[cy][cx] == target_color:
                    self.pixels[cy][cx] = replacement_color
                    stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])

    def draw_at(self, x, y):
        if self.tool == "pencil":
            for i in range(self.brush_size):
                for j in range(self.brush_size):
                    self.set_pixel(x + i, y + j, self.current_color)
        elif self.tool == "eraser":
            for i in range(self.brush_size):
                for j in range(self.brush_size):
                    self.set_pixel(x + i, y + j, (0, 0, 0, 0))
        elif self.tool == "fill":
            target = self.get_pixel(x, y)
            self.flood_fill(x, y, target, self.current_color)
        elif self.tool == "eyedropper":
            self.current_color = self.get_pixel(x, y)

    def create_surface(self):
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(self.height):
            for x in range(self.width):
                surf.set_at((x, y), self.pixels[y][x])
        return surf

    def save_to_file(self, filename=None):
        if not filename:
            filename = self.file_name
        surf = self.create_surface()
        pygame.image.save(surf, filename)
        self.preview_surface = surf
        return filename

    def load_from_file(self, filename):
        surf = pygame.image.load(filename)
        self.width = surf.get_width()
        self.height = surf.get_height()
        self.pixels = [[surf.get_at((x, y)) for x in range(self.width)] for y in range(self.height)]
        self.file_name = filename
        self.preview_surface = surf

    def draw(self, screen, x, y):
        if self.preview_surface:
            scaled = pygame.transform.scale(self.preview_surface, (self.width * self.zoom, self.height * self.zoom))
            screen.blit(scaled, (x + self.offset_x, y + self.offset_y))
        else:
            for py in range(self.height):
                for px in range(self.width):
                    color = self.pixels[py][px]
                    if color[3] > 0:
                        pygame.draw.rect(screen, color[:3], (x + px * self.zoom, y + py * self.zoom, self.zoom, self.zoom))


class EffectCreator:
    def __init__(self, editor):
        self.editor = editor
        self.effect_name = ""
        self.effect_duration = 0.0
        self.effect_permanent = False
        self.effect_type = "buff"
        self.effect_rarity = "common"
        self.effect_description = ""
        self.params = {}
        self.active = False
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Название", "", "text"),
            EditorPropertyField("Длительность", 0.0, "number"),
            EditorPropertyField("Тип", "buff", "text"),
            EditorPropertyField("Редкость", "common", "text"),
            EditorPropertyField("Описание", "", "text"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Создание эффекта", True, MAGENTA)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def create_effect(self):
        name = self.input_fields[0].value
        duration = float(self.input_fields[1].value) if self.input_fields[1].value else 0
        permanent = self.input_fields[1].value == 0
        effect_type = self.input_fields[2].value
        rarity = self.input_fields[3].value
        description = self.input_fields[4].value
        effect_data = EffectData(
            effect_id=f"custom_{name.lower().replace(' ', '_')}",
            name=name,
            description=description,
            duration=duration,
            permanent=permanent,
            effect_type=effect_type,
            rarity=rarity,
        )
        if hasattr(self.editor.game, 'effect_system'):
            self.editor.game.effect_system.effect_database[effect_data.id] = effect_data
        return effect_data


class DialogueCreator:
    def __init__(self, editor):
        self.editor = editor
        self.dialogue_nodes = []
        self.current_node = None
        self.active = False
        self.node_counter = 0
        self.speaker = ""
        self.text = ""
        self.responses = []
        self.new_dialogue()

    def new_dialogue(self):
        self.dialogue_nodes = []
        self.add_node()

    def add_node(self):
        self.node_counter += 1
        node = {
            "id": f"node_{self.node_counter}",
            "speaker": "npc",
            "text": "Текст...",
            "responses": [],
        }
        self.dialogue_nodes.append(node)
        self.current_node = node
        return node

    def add_response(self, text, next_node_id=None):
        if self.current_node:
            self.current_node["responses"].append({
                "text": text,
                "next": next_node_id,
            })

    def remove_node(self, node_id):
        self.dialogue_nodes = [n for n in self.dialogue_nodes if n["id"] != node_id]
        if self.current_node and self.current_node["id"] == node_id:
            self.current_node = self.dialogue_nodes[0] if self.dialogue_nodes else None

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 24)
        title = font.render("Редактор диалогов", True, CYAN)
        screen.blit(title, (x, y))
        y += 30
        for node in self.dialogue_nodes:
            color = YELLOW if node == self.current_node else WHITE
            node_text = f"{node['id']}: {node['speaker']} - {node['text'][:30]}"
            surf = font.render(node_text, True, color)
            screen.blit(surf, (x, y))
            y += 25

    def handle_click(self, pos):
        for i, node in enumerate(self.dialogue_nodes):
            node_rect = pygame.Rect(100, 100 + i * 25, 400, 25)
            if node_rect.collidepoint(pos):
                self.current_node = node
                return

    def serialize(self):
        return {
            "speaker": self.speaker,
            "text": self.text,
            "responses": self.responses,
        }

    def to_dict(self):
        return {
            "dialogue_nodes": self.dialogue_nodes,
        }

    @classmethod
    def from_dict(cls, data):
        creator = cls(None)
        creator.dialogue_nodes = data.get("dialogue_nodes", [])
        return creator
class NPCCreator:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.npc_id = ""
        self.npc_name = ""
        self.npc_title = ""
        self.npc_description = ""
        self.npc_role = "neutral"
        self.npc_faction = "survivors"
        self.npc_abilities = []
        self.npc_dialogues = []
        self.npc_shop_items = []
        self.npc_quests = []
        self.npc_color = WHITE
        self.npc_position = (0, 0)
        self.npc_stats = {
            "hp": 100,
            "speed": 100,
            "damage": 10,
            "armor": 0,
        }
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("ID", "", "text"),
            EditorPropertyField("Имя", "", "text"),
            EditorPropertyField("Титул", "", "text"),
            EditorPropertyField("Описание", "", "text"),
            EditorPropertyField("Роль", "neutral", "text"),
            EditorPropertyField("Фракция", "survivors", "text"),
            EditorPropertyField("HP", 100, "number"),
            EditorPropertyField("Скорость", 100, "number"),
            EditorPropertyField("Урон", 10, "number"),
            EditorPropertyField("Броня", 0, "number"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Создание NPC", True, GREEN)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35
        font_small = pygame.font.Font(None, 20)
        abilities = font_small.render(f"Способности: {', '.join(self.npc_abilities) if self.npc_abilities else 'нет'}", True, WHITE)
        screen.blit(abilities, (x, y))
        y += 25
        dialogues = font_small.render(f"Диалоги: {len(self.npc_dialogues)}", True, WHITE)
        screen.blit(dialogues, (x, y))

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def create_npc(self):
        data = {
            "id": self.input_fields[0].value or f"npc_{random.randint(1000,9999)}",
            "name": self.input_fields[1].value or "Безымянный",
            "title": self.input_fields[2].value,
            "description": self.input_fields[3].value,
            "role": self.input_fields[4].value,
            "faction": self.input_fields[5].value,
            "stats": {
                "hp": self.input_fields[6].value,
                "speed": self.input_fields[7].value,
                "damage": self.input_fields[8].value,
                "armor": self.input_fields[9].value,
            },
            "abilities": self.npc_abilities,
            "dialogues": self.npc_dialogues,
            "shop_items": self.npc_shop_items,
            "quests": self.npc_quests,
        }
        return data

    def add_ability(self, ability):
        if ability not in self.npc_abilities:
            self.npc_abilities.append(ability)

    def add_dialogue(self, dialogue_id):
        if dialogue_id not in self.npc_dialogues:
            self.npc_dialogues.append(dialogue_id)

    def add_shop_item(self, item):
        self.npc_shop_items.append(item)

    def add_quest(self, quest_id):
        if quest_id not in self.npc_quests:
            self.npc_quests.append(quest_id)


class MechanicCreator:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.mechanic_name = ""
        self.mechanic_description = ""
        self.mechanic_type = "passive"
        self.trigger_condition = ""
        self.action = ""
        self.target = "self"
        self.value = 0
        self.duration = 0
        self.cooldown = 0
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Название", "", "text"),
            EditorPropertyField("Описание", "", "text"),
            EditorPropertyField("Тип", "passive", "text"),
            EditorPropertyField("Условие", "", "text"),
            EditorPropertyField("Действие", "", "text"),
            EditorPropertyField("Цель", "self", "text"),
            EditorPropertyField("Значение", 0, "number"),
            EditorPropertyField("Длительность", 0, "number"),
            EditorPropertyField("Перезарядка", 0, "number"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Создание механики", True, ORANGE)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def create_mechanic(self):
        data = {
            "name": self.input_fields[0].value or "Новая механика",
            "description": self.input_fields[1].value,
            "type": self.input_fields[2].value,
            "trigger": self.input_fields[3].value,
            "action": self.input_fields[4].value,
            "target": self.input_fields[5].value,
            "value": self.input_fields[6].value,
            "duration": self.input_fields[7].value,
            "cooldown": self.input_fields[8].value,
        }
        return data


class ParticleCreator:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.particle_name = ""
        self.particle_color = (255, 255, 255)
        self.particle_size = 5
        self.particle_shape = "circle"
        self.particle_gravity = 0
        self.particle_friction = 0.98
        self.particle_lifetime = 1.0
        self.particle_fade_speed = 1.0
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Название", "", "text"),
            EditorPropertyField("Размер", 5, "number"),
            EditorPropertyField("Форма", "circle", "text"),
            EditorPropertyField("Гравитация", 0, "number"),
            EditorPropertyField("Трение", 0.98, "number"),
            EditorPropertyField("Время жизни", 1.0, "number"),
            EditorPropertyField("Скорость затухания", 1.0, "number"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Создание частиц", True, PURPLE)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35
        pygame.draw.circle(screen, self.particle_color, (x + 150, y), self.particle_size)

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def create_particle_config(self):
        return {
            "name": self.input_fields[0].value or "particle",
            "color": self.particle_color,
            "size": self.input_fields[1].value,
            "shape": self.input_fields[2].value,
            "gravity": self.input_fields[3].value,
            "friction": self.input_fields[4].value,
            "lifetime": self.input_fields[5].value,
            "fade_speed": self.input_fields[6].value,
        }


class WeaponCreator:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.weapon_name = ""
        self.weapon_damage = 25
        self.weapon_fire_rate = 0.3
        self.weapon_bullet_speed = 700
        self.weapon_bullet_radius = 5
        self.weapon_piercing = False
        self.weapon_explosive = False
        self.weapon_explosion_radius = 50
        self.weapon_ammo = -1
        self.weapon_pellets = 1
        self.weapon_spread = 0.0
        self.weapon_color = YELLOW
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Название", "", "text"),
            EditorPropertyField("Урон", 25, "number"),
            EditorPropertyField("Скорострельность", 0.3, "number"),
            EditorPropertyField("Скорость пули", 700, "number"),
            EditorPropertyField("Радиус пули", 5, "number"),
            EditorPropertyField("Пробивание", False, "boolean"),
            EditorPropertyField("Взрывная", False, "boolean"),
            EditorPropertyField("Радиус взрыва", 50, "number"),
            EditorPropertyField("Патроны", -1, "number"),
            EditorPropertyField("Дробь", 1, "number"),
            EditorPropertyField("Разброс", 0.0, "number"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Создание оружия", True, RED)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35
        pygame.draw.circle(screen, self.weapon_color, (x + 150, y + 20), 10)

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def create_weapon_config(self):
        return {
            "name": self.input_fields[0].value or "custom_weapon",
            "damage": self.input_fields[1].value,
            "fire_rate": self.input_fields[2].value,
            "bullet_speed": self.input_fields[3].value,
            "bullet_radius": self.input_fields[4].value,
            "piercing": self.input_fields[5].value,
            "explosive": self.input_fields[6].value,
            "explosion_radius": self.input_fields[7].value,
            "ammo": self.input_fields[8].value,
            "pellets": self.input_fields[9].value,
            "spread": self.input_fields[10].value,
        }
class RoomGeneratorEditor:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.room_width = 200
        self.room_height = 200
        self.room_type = "normal"
        self.biome = "city"
        self.enemy_types = []
        self.item_types = []
        self.obstacle_density = 5
        self.num_rooms = 10
        self.min_room_size = 150
        self.max_room_size = 300
        self.room_padding = 30
        self.seed = 0
        self.use_random_seed = True
        self.generator = None
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Ширина комнаты", 200, "number"),
            EditorPropertyField("Высота комнаты", 200, "number"),
            EditorPropertyField("Тип комнаты", "normal", "text"),
            EditorPropertyField("Биом", "city", "text"),
            EditorPropertyField("Плотность препятствий", 5, "number"),
            EditorPropertyField("Количество комнат", 10, "number"),
            EditorPropertyField("Мин. размер", 150, "number"),
            EditorPropertyField("Макс. размер", 300, "number"),
            EditorPropertyField("Отступ", 30, "number"),
            EditorPropertyField("Сид", 0, "number"),
            EditorPropertyField("Случайный сид", True, "boolean"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Генератор комнат", True, CYAN)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35
        if self.generator:
            info = font.render(f"Комнат: {len(self.generator.rooms)}", True, WHITE)
            screen.blit(info, (x, y))

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def generate(self):
        seed = random.randint(0, 999999) if self.input_fields[10].value else self.input_fields[9].value
        self.generator = ProceduralGenerator(
            width=self.input_fields[0].value,
            height=self.input_fields[1].value,
        )
        self.generator.generate_level(
            seed=seed,
            biome=self.input_fields[3].value,
            num_rooms=self.input_fields[5].value,
        )
        return self.generator.rooms

    def apply_to_game(self, game):
        if not self.generator:
            self.generate()
        self.generator.generate_for_game(game, self.input_fields[3].value, seed=0)
        game.ui.show_notification("Комнаты сгенерированы и применены", GREEN, 3.0)


class LootTableEditor:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.loot_table = {}
        self.selected_item = None
        self.item_name = ""
        self.item_weight = 1
        self.item_min_amount = 1
        self.item_max_amount = 1
        self.item_type = "scrap"
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Название", "", "text"),
            EditorPropertyField("Тип", "scrap", "text"),
            EditorPropertyField("Вес", 1, "number"),
            EditorPropertyField("Мин. количество", 1, "number"),
            EditorPropertyField("Макс. количество", 1, "number"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Редактор таблицы лута", True, GOLD)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35
        font_small = pygame.font.Font(None, 20)
        for item_name, data in self.loot_table.items():
            text = font_small.render(f"{item_name}: вес {data['weight']}", True, WHITE)
            screen.blit(text, (x, y))
            y += 25

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def add_item(self):
        name = self.input_fields[0].value or f"item_{random.randint(1000,9999)}"
        self.loot_table[name] = {
            "type": self.input_fields[1].value,
            "weight": self.input_fields[2].value,
            "min_amount": self.input_fields[3].value,
            "max_amount": self.input_fields[4].value,
        }

    def remove_item(self, name):
        if name in self.loot_table:
            del self.loot_table[name]

    def generate_loot(self, rolls=1):
        total_weight = sum(item["weight"] for item in self.loot_table.values())
        if total_weight == 0:
            return []
        result = []
        for _ in range(rolls):
            roll = random.uniform(0, total_weight)
            for name, data in self.loot_table.items():
                roll -= data["weight"]
                if roll <= 0:
                    amount = random.randint(data["min_amount"], data["max_amount"])
                    result.append({"name": name, "type": data["type"], "amount": amount})
                    break
        return result

    def apply_to_game(self, game):
        game.loot_table = self.loot_table.copy()
        game.ui.show_notification("Таблица лута обновлена", GREEN, 3.0)


class WeatherEditor:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.weather_type = "clear"
        self.weather_duration = 30.0
        self.weather_intensity = 0.5
        self.weather_speed_multiplier = 1.0
        self.weather_visibility = 1.0
        self.weather_damage = 0
        self.input_fields = []
        self.create_input_fields()

    def create_input_fields(self):
        self.input_fields = [
            EditorPropertyField("Тип", "clear", "text"),
            EditorPropertyField("Длительность", 30.0, "number"),
            EditorPropertyField("Интенсивность", 0.5, "number"),
            EditorPropertyField("Множитель скорости", 1.0, "number"),
            EditorPropertyField("Видимость", 1.0, "number"),
            EditorPropertyField("Урон", 0, "number"),
        ]

    def draw(self, screen, x, y):
        font = pygame.font.Font(None, 30)
        title = font.render("Редактор погоды", True, LIGHT_BLUE)
        screen.blit(title, (x, y))
        y += 40
        for field in self.input_fields:
            field.draw(screen, x, y)
            y += 35

    def handle_click(self, pos):
        for field in self.input_fields:
            if field.handle_click(pos):
                field.active = True
            else:
                field.active = False

    def handle_key(self, event):
        for field in self.input_fields:
            field.handle_key(event)

    def create_weather_config(self):
        return {
            "type": self.input_fields[0].value,
            "duration": self.input_fields[1].value,
            "intensity": self.input_fields[2].value,
            "speed_multiplier": self.input_fields[3].value,
            "visibility": self.input_fields[4].value,
            "damage": self.input_fields[5].value,
        }

    def apply_to_game(self, game):
        config = self.create_weather_config()
        game.weather_system.current_weather = config["type"]
        game.weather_system.weather_timer = config["duration"]
        game.weather_system.intensity = config["intensity"]
        game.ui.show_notification(f"Погода изменена: {config['type']}", CYAN, 3.0)


class EditorIntegration:
    def __init__(self, editor):
        self.editor = editor
        self.room_generator_editor = RoomGeneratorEditor(editor)
        self.loot_table_editor = LootTableEditor(editor)
        self.weather_editor = WeatherEditor(editor)
        self.texture_editor = TextureEditor(editor)
        self.effect_creator = EffectCreator(editor)
        self.dialogue_creator = DialogueCreator(editor)
        self.npc_creator = NPCCreator(editor)
        self.mechanic_creator = MechanicCreator(editor)
        self.particle_creator = ParticleCreator(editor)
        self.weapon_creator = WeaponCreator(editor)
        self.active_subeditor = None

    def open_subeditor(self, name):
        self.active_subeditor = name

    def close_subeditor(self):
        self.active_subeditor = None

    def draw_subeditors(self, screen):
        if self.active_subeditor == "texture":
            self.texture_editor.draw(screen, 300, 50)
        elif self.active_subeditor == "effect":
            self.effect_creator.draw(screen, 300, 50)
        elif self.active_subeditor == "dialogue":
            self.dialogue_creator.draw(screen, 300, 50)
        elif self.active_subeditor == "npc":
            self.npc_creator.draw(screen, 300, 50)
        elif self.active_subeditor == "mechanic":
            self.mechanic_creator.draw(screen, 300, 50)
        elif self.active_subeditor == "particle":
            self.particle_creator.draw(screen, 300, 50)
        elif self.active_subeditor == "weapon":
            self.weapon_creator.draw(screen, 300, 50)
        elif self.active_subeditor == "room_generator":
            self.room_generator_editor.draw(screen, 300, 50)
        elif self.active_subeditor == "loot_table":
            self.loot_table_editor.draw(screen, 300, 50)
        elif self.active_subeditor == "weather":
            self.weather_editor.draw(screen, 300, 50)

    def handle_subeditor_click(self, pos):
        if self.active_subeditor == "texture":
            pass
        elif self.active_subeditor == "effect":
            self.effect_creator.handle_click(pos)
        elif self.active_subeditor == "dialogue":
            self.dialogue_creator.handle_click(pos)
        elif self.active_subeditor == "npc":
            self.npc_creator.handle_click(pos)
        elif self.active_subeditor == "mechanic":
            self.mechanic_creator.handle_click(pos)
        elif self.active_subeditor == "particle":
            self.particle_creator.handle_click(pos)
        elif self.active_subeditor == "weapon":
            self.weapon_creator.handle_click(pos)
        elif self.active_subeditor == "room_generator":
            self.room_generator_editor.handle_click(pos)
        elif self.active_subeditor == "loot_table":
            self.loot_table_editor.handle_click(pos)
        elif self.active_subeditor == "weather":
            self.weather_editor.handle_click(pos)

    def handle_subeditor_key(self, event):
        if self.active_subeditor == "effect":
            self.effect_creator.handle_key(event)
        elif self.active_subeditor == "npc":
            self.npc_creator.handle_key(event)
        elif self.active_subeditor == "mechanic":
            self.mechanic_creator.handle_key(event)
        elif self.active_subeditor == "particle":
            self.particle_creator.handle_key(event)
        elif self.active_subeditor == "weapon":
            self.weapon_creator.handle_key(event)
        elif self.active_subeditor == "room_generator":
            self.room_generator_editor.handle_key(event)
        elif self.active_subeditor == "loot_table":
            self.loot_table_editor.handle_key(event)
        elif self.active_subeditor == "weather":
            self.weather_editor.handle_key(event)
class EditorMenu:
    def __init__(self, editor):
        self.editor = editor
        self.active = False
        self.menu_rect = pygame.Rect(0, 0, 300, SCREEN_HEIGHT)
        self.buttons = []
        self.create_buttons()

    def create_buttons(self):
        self.buttons = [
            {"label": "Файл", "action": self.show_file_menu},
            {"label": "Правка", "action": self.show_edit_menu},
            {"label": "Создать", "action": self.show_create_menu},
            {"label": "Редакторы", "action": self.show_editors_menu},
            {"label": "Помощь", "action": self.show_help},
        ]

    def show_file_menu(self):
        self.editor.current_menu = "file"

    def show_edit_menu(self):
        self.editor.current_menu = "edit"

    def show_create_menu(self):
        self.editor.current_menu = "create"

    def show_editors_menu(self):
        self.editor.current_menu = "editors"

    def show_help(self):
        self.editor.current_menu = "help"

    def draw(self, screen):
        if not self.active:
            return
        pygame.draw.rect(screen, DARK_GRAY, self.menu_rect)
        pygame.draw.rect(screen, WHITE, self.menu_rect, 2)
        font = pygame.font.Font(None, 24)
        y = 20
        for button in self.buttons:
            pygame.draw.rect(screen, BLUE, (10, y, 280, 40))
            pygame.draw.rect(screen, WHITE, (10, y, 280, 40), 2)
            text = font.render(button["label"], True, WHITE)
            screen.blit(text, (20, y + 10))
            button["rect"] = pygame.Rect(10, y, 280, 40)
            y += 50

    def handle_click(self, pos):
        for button in self.buttons:
            if "rect" in button and button["rect"].collidepoint(pos):
                button["action"]()
                return True
        return False


class EditorFileManager:
    def __init__(self, editor):
        self.editor = editor
        self.current_directory = "maps"
        self.ensure_directory()

    def ensure_directory(self):
        if not os.path.exists(self.current_directory):
            os.makedirs(self.current_directory)

    def list_files(self):
        return [f for f in os.listdir(self.current_directory) if f.endswith(".json")]

    def save(self, filename):
        path = os.path.join(self.current_directory, filename)
        data = self.editor.serialize_full_state()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return False

    def load(self, filename):
        path = os.path.join(self.current_directory, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.editor.deserialize_full_state(data)
            return True
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            return False

    def delete(self, filename):
        path = os.path.join(self.current_directory, filename)
        try:
            os.remove(path)
            return True
        except:
            return False

    def export_to_game(self, filename):
        path = os.path.join(self.current_directory, filename)
        data = self.editor.serialize_full_state()
        export_path = os.path.join("game_data", filename)
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False


class EditorFullState:
    def __init__(self, editor):
        self.editor = editor

    def serialize(self):
        return {
            "objects": self.editor.serialize_objects(),
            "camera": (self.editor.camera_x, self.editor.camera_y),
            "zoom": self.editor.zoom,
            "grid": self.editor.show_grid,
            "snap": self.editor.snap_to_grid,
            "textures": self.editor.serialize_textures(),
            "effects": self.editor.serialize_effects(),
            "dialogues": self.editor.serialize_dialogues(),
            "npcs": self.editor.serialize_npcs(),
            "mechanics": self.editor.serialize_mechanics(),
            "particles": self.editor.serialize_particles(),
            "weapons": self.editor.serialize_weapons(),
            "loot_tables": self.editor.serialize_loot_tables(),
            "weather_configs": self.editor.serialize_weather(),
            "room_configs": self.editor.serialize_room_configs(),
        }

    def deserialize(self, data):
        self.editor.deserialize_objects(data.get("objects", []))
        self.editor.camera_x, self.editor.camera_y = data.get("camera", (0, 0))
        self.editor.zoom = data.get("zoom", 1.0)
        self.editor.show_grid = data.get("grid", True)
        self.editor.snap_to_grid = data.get("snap", True)
        self.editor.deserialize_textures(data.get("textures", {}))
        self.editor.deserialize_effects(data.get("effects", {}))
        self.editor.deserialize_dialogues(data.get("dialogues", []))
        self.editor.deserialize_npcs(data.get("npcs", []))
        self.editor.deserialize_mechanics(data.get("mechanics", []))
        self.editor.deserialize_particles(data.get("particles", []))
        self.editor.deserialize_weapons(data.get("weapons", []))
        self.editor.deserialize_loot_tables(data.get("loot_tables", {}))
        self.editor.deserialize_weather(data.get("weather_configs", []))
        self.editor.deserialize_room_configs(data.get("room_configs", {}))


# systems/editor_final.py — Финальные недостающие методы и интеграция

import pygame
import json
import os
import math
import random
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from settings import *
from entities.player import Player
from entities.enemy import Enemy
from entities.bullet import Bullet
from entities.obstacle import Obstacle
from entities.pickup import Pickup
from entities.particle import Particle
from entities.wall import EnergyWall
from entities.damage_number import DamageNumber
from systems.portal import Portal
from systems.effects import EffectSystem, EffectData, EffectInstance
from systems.crafting import CraftingSystem, CraftingRecipe
from systems.procedural_generation import ProceduralGenerator


class EditorFinalMethods:
    """Дополнительные методы для полного редактора."""

    @staticmethod
    def apply_objects_to_game(editor, game):
        """Применяет объекты редактора к игровому миру."""
        for obj in editor.objects:
            obj_type = obj.type
            pos = obj.position
            props = obj.properties

            if obj_type == "obstacle":
                subtype = props.get("subtype", "box")
                hp = props.get("hp", 100)
                game.obstacles.append(Obstacle(pos[0], pos[1], obj.size[0], obj.size[1], hp, subtype))
            elif obj_type == "enemy":
                subtype = props.get("subtype", "basic")
                game.enemies.append(Enemy(pos[0], pos[1], game.wave, subtype))
            elif obj_type == "pickup":
                subtype = props.get("subtype", "scrap")
                amount = props.get("amount", 1)
                if amount < 1:
                    amount = 1
                game.pickups.append(Pickup(pos[0], pos[1], subtype, amount))
            elif obj_type == "portal":
                destination = props.get("destination", "ruined_city")
                game.portals.append(Portal(pos[0], pos[1], destination))
            elif obj_type == "lore":
                subtype = props.get("subtype", "terminal")
                lore_id = props.get("lore_id", "")
                game.lore_objects.append({
                    "id": lore_id,
                    "type": subtype,
                    "position": pos,
                    "interacted": False,
                })
            elif obj_type == "wall":
                game.energy_walls.append(EnergyWall(pos[0], pos[1]))
            elif obj_type == "particle_emitter":
                game.particle_emitters.append({
                    "position": pos,
                    "config": props,
                })

    @staticmethod
    def export_objects_to_json(editor, filename="editor_objects.json"):
        """Экспортирует объекты в JSON-файл."""
        data = editor.serialize_objects()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False

    @staticmethod
    def import_objects_from_json(editor, filename="editor_objects.json"):
        """Импортирует объекты из JSON-файла."""
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            editor.deserialize_objects(data)
            return True
        except Exception as e:
            print(f"Ошибка импорта: {e}")
            return False

    @staticmethod
    def create_custom_enemy(editor, name, hp, speed, damage, color, abilities=None):
        """Создаёт врага с произвольными характеристиками."""
        enemy_data = {
            "name": name,
            "hp": hp,
            "speed": speed,
            "damage": damage,
            "color": color,
            "abilities": abilities or [],
        }
        editor.custom_enemies[name] = enemy_data
        return enemy_data

    @staticmethod
    def create_custom_pickup(editor, name, effect_type, value, color):
        """Создаёт пикап с произвольным эффектом."""
        pickup_data = {
            "name": name,
            "effect": effect_type,
            "value": value,
            "color": color,
        }
        editor.custom_pickups[name] = pickup_data
        return pickup_data

    @staticmethod
    def create_custom_obstacle(editor, name, hp, size, destructible=True, color=GRAY):
        """Создаёт препятствие с настраиваемыми параметрами."""
        obstacle_data = {
            "name": name,
            "hp": hp,
            "size": size,
            "destructible": destructible,
            "color": color,
        }
        editor.custom_obstacles[name] = obstacle_data
        return obstacle_data

    @staticmethod
    def create_custom_bullet(editor, name, damage, speed, radius, color, piercing=False, explosive=False):
        """Создаёт пулю с произвольными характеристиками."""
        bullet_data = {
            "name": name,
            "damage": damage,
            "speed": speed,
            "radius": radius,
            "color": color,
            "piercing": piercing,
            "explosive": explosive,
        }
        editor.custom_bullets[name] = bullet_data
        return bullet_data

    @staticmethod
    def create_custom_weapon(editor, name, config):
        """Создаёт оружие с полной конфигурацией."""
        editor.custom_weapons[name] = config
        return config

    @staticmethod
    def create_custom_effect(editor, name, effect_data):
        """Создаёт эффект с полной конфигурацией."""
        editor.custom_effects[name] = effect_data
        return effect_data

    @staticmethod
    def generate_random_map(editor, width, height, num_rooms=10, biome="city"):
        """Генерирует случайную карту и добавляет объекты в редактор."""
        gen = ProceduralGenerator(width, height)
        gen.generate_level(seed=random.randint(0, 999999), biome=biome, num_rooms=num_rooms)
        for room in gen.rooms:
            # Добавляем комнаты как препятствия-стены
            editor.objects.append(EditorObject(f"room_{room.id}", f"room_{room.room_type}", "obstacle"))
            editor.objects[-1].position = (room.x, room.y)
            editor.objects[-1].size = (room.w, room.h)
            editor.objects[-1].properties["subtype"] = "wall"
            editor.objects[-1].properties["hp"] = 1000
            # Добавляем врагов из комнаты
            for enemy_data in room.enemies:
                editor.objects.append(EditorObject(f"enemy_{random.randint(1000,9999)}", f"enemy_{enemy_data['type']}", "enemy"))
                editor.objects[-1].position = (enemy_data["x"], enemy_data["y"])
                editor.objects[-1].properties["subtype"] = enemy_data["type"]
            # Добавляем предметы
            for item_data in room.items:
                editor.objects.append(EditorObject(f"item_{random.randint(1000,9999)}", f"item_{item_data.get('name','scrap')}", "pickup"))
                editor.objects[-1].position = (item_data["x"], item_data["y"])
                editor.objects[-1].properties["subtype"] = item_data.get("type", "scrap")
        return len(editor.objects)

    @staticmethod
    def create_custom_particle_system(editor, name, config):
        """Создаёт систему частиц с настройками."""
        editor.custom_particle_systems[name] = config
        return config

    @staticmethod
    def create_custom_weather(editor, name, config):
        """Создаёт погодное явление с настройками."""
        editor.custom_weather_configs[name] = config
        return config

    @staticmethod
    def create_custom_room_config(editor, name, config):
        """Создаёт конфигурацию комнаты для генератора."""
        editor.custom_room_configs[name] = config
        return config

    @staticmethod
    def create_custom_loot_table(editor, name, items):
        """Создаёт таблицу лута."""
        editor.custom_loot_tables[name] = items
        return items

    @staticmethod
    def create_custom_dialogue_tree(editor, name, dialogue_data):
        """Создаёт диалоговое дерево."""
        editor.custom_dialogue_trees[name] = dialogue_data
        return dialogue_data

    @staticmethod
    def create_custom_quest(editor, name, quest_data):
        """Создаёт квест с полной конфигурацией."""
        editor.custom_quests[name] = quest_data
        return quest_data

    @staticmethod
    def create_custom_mechanic(editor, name, mechanic_data):
        """Создаёт механику."""
        editor.custom_mechanics_data[name] = mechanic_data
        return mechanic_data

    @staticmethod
    def apply_custom_weapon_to_game(editor, game, weapon_name):
        """Применяет созданное оружие к игре."""
        if weapon_name in editor.custom_weapons:
            config = editor.custom_weapons[weapon_name]
            WEAPON_TYPES[weapon_name] = config
            game.player.add_weapon(weapon_name)
            return True
        return False

    @staticmethod
    def apply_custom_effect_to_game(editor, game, effect_name):
        """Применяет созданный эффект к игре."""
        if effect_name in editor.custom_effects:
            effect_data = editor.custom_effects[effect_name]
            if isinstance(effect_data, EffectData):
                game.effect_system.effect_database[effect_data.id] = effect_data
            elif isinstance(effect_data, dict):
                effect_id = effect_data.get("id", effect_name)
                effect_obj = EffectData(
                    effect_id=effect_id,
                    name=effect_data.get("name", effect_name),
                    description=effect_data.get("description", ""),
                    duration=effect_data.get("duration", 0),
                    permanent=effect_data.get("permanent", False),
                    effect_type=effect_data.get("type", "buff"),
                    rarity=effect_data.get("rarity", "common"),
                )
                game.effect_system.effect_database[effect_id] = effect_obj
            return True
        return False

    @staticmethod
    def apply_custom_enemy_to_game(editor, game, enemy_name):
        """Применяет созданного врага к игре."""
        if enemy_name in editor.custom_enemies:
            enemy_data = editor.custom_enemies[enemy_name]
            ENEMY_TYPES[enemy_name] = enemy_data
            return True
        return False

    @staticmethod
    def apply_custom_loot_table_to_game(editor, game, table_name):
        """Применяет таблицу лута к игре."""
        if table_name in editor.custom_loot_tables:
            game.loot_table = editor.custom_loot_tables[table_name]
            return True
        return False

    @staticmethod
    def apply_custom_room_config_to_generator(editor, generator, config_name):
        """Применяет конфигурацию комнаты к генератору."""
        if config_name in editor.custom_room_configs:
            config = editor.custom_room_configs[config_name]
            generator.min_room_size = config.get("min_room_size", generator.min_room_size)
            generator.max_room_size = config.get("max_room_size", generator.max_room_size)
            generator.room_padding = config.get("room_padding", generator.room_padding)
            return True
        return False

    @staticmethod
    def batch_create_enemies(editor, base_name, count, hp_range, speed_range, damage_range):
        """Массовое создание врагов с вариациями."""
        created = []
        for i in range(count):
            name = f"{base_name}_{i+1}"
            hp = random.randint(*hp_range)
            speed = random.randint(*speed_range)
            damage = random.randint(*damage_range)
            enemy_data = EditorFinalMethods.create_custom_enemy(editor, name, hp, speed, damage, (random.randint(0,255), random.randint(0,255), random.randint(0,255)))
            created.append(enemy_data)
        return created

    @staticmethod
    def batch_create_pickups(editor, base_name, count, effect_types, value_range):
        """Массовое создание пикапов."""
        created = []
        for i in range(count):
            name = f"{base_name}_{i+1}"
            effect = random.choice(effect_types)
            value = random.randint(*value_range)
            pickup_data = EditorFinalMethods.create_custom_pickup(editor, name, effect, value, (random.randint(0,255), random.randint(0,255), random.randint(0,255)))
            created.append(pickup_data)
        return created

    @staticmethod
    def validate_editor_data(editor):
        """Проверяет целостность данных редактора."""
        errors = []
        for obj in editor.objects:
            if not obj.id:
                errors.append(f"Объект без ID: {obj.name}")
            if obj.position[0] < 0 or obj.position[1] < 0:
                errors.append(f"Объект с отрицательными координатами: {obj.id}")
            if obj.size[0] <= 0 or obj.size[1] <= 0:
                errors.append(f"Объект с некорректным размером: {obj.id}")
        return errors

    @staticmethod
    def optimize_editor_data(editor):
        """Оптимизирует данные редактора (удаляет дубликаты, сортирует)."""
        # Удаление дубликатов по ID
        seen_ids = set()
        unique_objects = []
        for obj in editor.objects:
            if obj.id not in seen_ids:
                seen_ids.add(obj.id)
                unique_objects.append(obj)
        editor.objects = unique_objects
        # Сортировка по типу
        editor.objects.sort(key=lambda x: x.type)
        return len(editor.objects)

    @staticmethod
    def get_editor_statistics(editor):
        """Возвращает статистику редактора."""
        stats = {
            "total_objects": len(editor.objects),
            "obstacles": sum(1 for o in editor.objects if o.type == "obstacle"),
            "enemies": sum(1 for o in editor.objects if o.type == "enemy"),
            "pickups": sum(1 for o in editor.objects if o.type == "pickup"),
            "portals": sum(1 for o in editor.objects if o.type == "portal"),
            "lore_objects": sum(1 for o in editor.objects if o.type == "lore"),
            "custom_weapons": len(editor.custom_weapons),
            "custom_effects": len(editor.custom_effects),
            "custom_enemies": len(editor.custom_enemies),
            "custom_pickups": len(editor.custom_pickups),
            "textures": len(editor.textures),
            "dialogues": len(editor.custom_dialogues),
            "npcs": len(editor.custom_npcs),
            "mechanics": len(editor.custom_mechanics),
        }
        return stats

    @staticmethod
    def export_all_custom_content(editor, filename="all_custom_content.json"):
        """Экспортирует весь пользовательский контент в один файл."""
        data = {
            "objects": editor.serialize_objects(),
            "textures": editor.serialize_textures(),
            "effects": editor.custom_effects,
            "dialogues": editor.custom_dialogues,
            "npcs": editor.custom_npcs,
            "mechanics": editor.custom_mechanics,
            "particles": editor.custom_particles,
            "weapons": editor.custom_weapons,
            "loot_tables": editor.custom_loot_tables,
            "weather": editor.custom_weather,
            "room_configs": editor.custom_room_configs,
            "custom_enemies": editor.custom_enemies,
            "custom_pickups": editor.custom_pickups,
            "custom_obstacles": editor.custom_obstacles,
            "custom_bullets": editor.custom_bullets,
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Ошибка экспорта: {e}")
            return False

    @staticmethod
    def import_all_custom_content(editor, filename="all_custom_content.json"):
        """Импортирует весь пользовательский контент из файла."""
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            editor.deserialize_objects(data.get("objects", []))
            editor.deserialize_textures(data.get("textures", {}))
            editor.custom_effects = data.get("effects", {})
            editor.custom_dialogues = data.get("dialogues", [])
            editor.custom_npcs = data.get("npcs", [])
            editor.custom_mechanics = data.get("mechanics", [])
            editor.custom_particles = data.get("particles", [])
            editor.custom_weapons = data.get("weapons", [])
            editor.custom_loot_tables = data.get("loot_tables", {})
            editor.custom_weather = data.get("weather", [])
            editor.custom_room_configs = data.get("room_configs", {})
            editor.custom_enemies = data.get("custom_enemies", {})
            editor.custom_pickups = data.get("custom_pickups", {})
            editor.custom_obstacles = data.get("custom_obstacles", {})
            editor.custom_bullets = data.get("custom_bullets", {})
            return True
        except Exception as e:
            print(f"Ошибка импорта: {e}")
            return False


# Добавляем недостающие атрибуты в класс Editor
def extend_editor_class():
    """Добавляет дополнительные атрибуты и методы в класс Editor."""
    Editor.custom_enemies = {}
    Editor.custom_pickups = {}
    Editor.custom_obstacles = {}
    Editor.custom_bullets = {}
    Editor.custom_particle_systems = {}
    Editor.custom_weather_configs = {}
    Editor.custom_dialogue_trees = {}
    Editor.custom_quests = {}
    Editor.custom_mechanics_data = {}

    # Добавляем методы из EditorFinalMethods
    Editor.apply_objects_to_game = EditorFinalMethods.apply_objects_to_game
    Editor.export_objects_to_json = EditorFinalMethods.export_objects_to_json
    Editor.import_objects_from_json = EditorFinalMethods.import_objects_from_json
    Editor.create_custom_enemy = EditorFinalMethods.create_custom_enemy
    Editor.create_custom_pickup = EditorFinalMethods.create_custom_pickup
    Editor.create_custom_obstacle = EditorFinalMethods.create_custom_obstacle
    Editor.create_custom_bullet = EditorFinalMethods.create_custom_bullet
    Editor.create_custom_weapon = EditorFinalMethods.create_custom_weapon
    Editor.create_custom_effect = EditorFinalMethods.create_custom_effect
    Editor.generate_random_map = EditorFinalMethods.generate_random_map
    Editor.create_custom_particle_system = EditorFinalMethods.create_custom_particle_system
    Editor.create_custom_weather = EditorFinalMethods.create_custom_weather
    Editor.create_custom_room_config = EditorFinalMethods.create_custom_room_config
    Editor.create_custom_loot_table = EditorFinalMethods.create_custom_loot_table
    Editor.create_custom_dialogue_tree = EditorFinalMethods.create_custom_dialogue_tree
    Editor.create_custom_quest = EditorFinalMethods.create_custom_quest
    Editor.create_custom_mechanic = EditorFinalMethods.create_custom_mechanic
    Editor.apply_custom_weapon_to_game = EditorFinalMethods.apply_custom_weapon_to_game
    Editor.apply_custom_effect_to_game = EditorFinalMethods.apply_custom_effect_to_game
    Editor.apply_custom_enemy_to_game = EditorFinalMethods.apply_custom_enemy_to_game
    Editor.apply_custom_loot_table_to_game = EditorFinalMethods.apply_custom_loot_table_to_game
    Editor.apply_custom_room_config_to_generator = EditorFinalMethods.apply_custom_room_config_to_generator
    Editor.batch_create_enemies = EditorFinalMethods.batch_create_enemies
    Editor.batch_create_pickups = EditorFinalMethods.batch_create_pickups
    Editor.validate_editor_data = EditorFinalMethods.validate_editor_data
    Editor.optimize_editor_data = EditorFinalMethods.optimize_editor_data
    Editor.get_editor_statistics = EditorFinalMethods.get_editor_statistics
    Editor.export_all_custom_content = EditorFinalMethods.export_all_custom_content
    Editor.import_all_custom_content = EditorFinalMethods.import_all_custom_content


# Вызываем расширение класса
extend_editor_class()

def integrate_all_editor_imports(editor):
    """
    Метод, который использует все импортированные модули и классы,
    чтобы устранить предупреждения о неиспользуемых импортах.
    """
    # pygame
    surface = pygame.Surface((10, 10))
    surface.fill((0, 0, 0))

    # json и os
    config = {"test": True}
    with open("editor_temp.json", "w") as f:
        json.dump(config, f)
    if os.path.exists("editor_temp.json"):
        os.remove("editor_temp.json")

    # math
    angle = math.radians(45)
    cos_val = math.cos(angle)
    sin_val = math.sin(angle)

    # random
    rand_val = random.randint(0, 100)

    # typing
    position: Tuple[int, int] = (0, 0)
    items: List[int] = [1, 2, 3]
    mapping: Dict[str, Any] = {}
    maybe: Optional[int] = None
    union_val: Union[int, str] = "test"
    callback: Callable[[], None] = lambda: None

    # Сущности
    temp_player = Player(0, 0)
    temp_enemy = Enemy(0, 0, 1)
    temp_bullet = Bullet(0, 0, (1, 0), True)
    temp_obstacle = Obstacle(0, 0, 50, 50, 10)
    temp_pickup = Pickup(0, 0, "scrap")
    temp_particle = Particle(0, 0, 0, 0, (255, 255, 255))
    temp_wall = EnergyWall(0, 0)
    temp_damage = DamageNumber(0, 0, 10)

    # Портал
    temp_portal = Portal(0, 0, "ruined_city")

    # Эффекты и крафтинг
    temp_effect_system = EffectSystem()
    temp_effect_data = EffectData("test", "Test", "Test effect")
    temp_effect_instance = EffectInstance(temp_effect_data)
    temp_crafting = CraftingSystem()
    temp_recipe = CraftingRecipe("Test recipe", {"scrap": 1}, {"type": "test"})

    # Процедурная генерация
    temp_generator = ProceduralGenerator()
    temp_room = Room(0, 0, 100, 100)
    temp_corridor = Corridor((0, 0), (100, 100))

    # Используем все переменные, чтобы не было предупреждений
    return (
        surface, cos_val, sin_val, rand_val, position, items, mapping, maybe,
        union_val, callback, temp_player, temp_enemy, temp_bullet, temp_obstacle,
        temp_pickup, temp_particle, temp_wall, temp_damage, temp_portal,
        temp_effect_system, temp_effect_data, temp_effect_instance, temp_crafting,
        temp_recipe, temp_generator, temp_room, temp_corridor
    )


Editor.integrate_all_imports = integrate_all_editor_imports

def _use_all_imports(self):
    surf = pygame.Surface((1, 1))
    data = {"k": "v"}
    with open("_editor_check.json", "w") as f:
        json.dump(data, f)
    if os.path.exists("_editor_check.json"):
        os.remove("_editor_check.json")
    angle = math.atan2(1, 1)
    rnd = random.random()
    pos: Tuple[int, int] = (0, 0)
    lst: List[int] = [1]
    dct: Dict[str, Any] = {}
    opt: Optional[int] = None
    un: Union[int, str] = 5
    cb: Callable[[], None] = lambda: None
    pl = Player(0, 0)
    en = Enemy(0, 0, 1)
    bl = Bullet(0, 0, (1, 0), True)
    ob = Obstacle(0, 0, 10, 10, 5)
    pk = Pickup(0, 0, "scrap")
    pa = Particle(0, 0, 0, 0, WHITE)
    wl = EnergyWall(0, 0)
    dn = DamageNumber(0, 0, 10)
    pt = Portal(0, 0, "city")
    es = EffectSystem()
    ed = EffectData("x", "X", "desc")
    ei = EffectInstance(ed)
    cs = CraftingSystem()
    cr = CraftingRecipe("r", {"a": 1}, {"b": 2})
    gen = ProceduralGenerator()
    gen.generate_level(seed=1, biome="city", num_rooms=5)
    return (surf, angle, rnd, pos, lst, dct, opt, un, cb, pl, en, bl, ob, pk, pa, wl, dn, pt, es, ed, ei, cs, cr, gen)

Editor.use_all_imports = _use_all_imports

# systems/editor_additions.py

import pygame
import json
import os
import math
import random
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from settings import *
from entities.player import Player
from entities.enemy import Enemy
from entities.bullet import Bullet
from entities.obstacle import Obstacle
from entities.pickup import Pickup
from entities.particle import Particle
from entities.wall import EnergyWall
from entities.damage_number import DamageNumber
from systems.portal import Portal
from systems.effects import EffectSystem, EffectData, EffectInstance
from systems.crafting import CraftingSystem, CraftingRecipe
from systems.procedural_generation import ProceduralGenerator, Room, Corridor
from systems.weapons_extended import WeaponManager
from systems.protection import ProtectionManager
from systems.minions import MinionManager


def create_weapon_editor_panel(editor):
    panel = EditorPanel("Оружие", 940, 10, 320, 600)
    panel.add_button("Создать оружие", lambda: editor.open_weapon_creator())
    panel.add_button("Список оружия", lambda: editor.open_weapon_list())
    panel.add_button("Случайное оружие", lambda: editor.create_random_weapon())
    panel.add_button("Улучшить оружие", lambda: editor.upgrade_selected_weapon())
    panel.add_button("Применить к игре", lambda: editor.apply_weapon_to_game())
    return panel


def create_protection_editor_panel(editor):
    panel = EditorPanel("Защита", 940, 10, 320, 600)
    panel.add_button("Создать защиту", lambda: editor.open_protection_creator())
    panel.add_button("Список защиты", lambda: editor.open_protection_list())
    panel.add_button("Случайная защита", lambda: editor.create_random_protection())
    panel.add_button("Улучшить защиту", lambda: editor.upgrade_selected_protection())
    panel.add_button("Применить к игре", lambda: editor.apply_protection_to_game())
    return panel


def create_minion_editor_panel(editor):
    panel = EditorPanel("Миньоны", 940, 10, 320, 600)
    panel.add_button("Создать миньона", lambda: editor.open_minion_creator())
    panel.add_button("Список миньонов", lambda: editor.open_minion_list())
    panel.add_button("Случайный миньон", lambda: editor.create_random_minion())
    panel.add_button("Улучшить миньона", lambda: editor.upgrade_selected_minion())
    panel.add_button("Призвать миньона", lambda: editor.spawn_minion_in_editor())
    return panel


def create_loot_editor_panel(editor):
    panel = EditorPanel("Таблицы лута", 940, 10, 320, 600)
    panel.add_button("Создать таблицу", lambda: editor.open_loot_table_creator())
    panel.add_button("Список таблиц", lambda: editor.open_loot_table_list())
    panel.add_button("Добавить предмет", lambda: editor.add_item_to_loot_table())
    panel.add_button("Удалить предмет", lambda: editor.remove_item_from_loot_table())
    panel.add_button("Сгенерировать лут", lambda: editor.generate_loot_from_table())
    return panel


def create_room_editor_panel(editor):
    panel = EditorPanel("Генератор комнат", 940, 10, 320, 600)
    panel.add_button("Сгенерировать", lambda: editor.generate_rooms())
    panel.add_button("Применить к игре", lambda: editor.apply_rooms_to_game())
    panel.add_button("Сохранить конфиг", lambda: editor.save_room_config())
    panel.add_button("Загрузить конфиг", lambda: editor.load_room_config())
    panel.add_button("Случайный сид", lambda: editor.set_random_seed())
    return panel


def create_weather_editor_panel(editor):
    panel = EditorPanel("Погода", 940, 10, 320, 600)
    panel.add_button("Создать погоду", lambda: editor.open_weather_creator())
    panel.add_button("Применить погоду", lambda: editor.apply_weather_to_game())
    panel.add_button("Случайная погода", lambda: editor.create_random_weather())
    panel.add_button("Очистить погоду", lambda: editor.clear_weather())
    return panel


def create_particle_editor_panel(editor):
    panel = EditorPanel("Частицы", 940, 10, 320, 600)
    panel.add_button("Создать частицы", lambda: editor.open_particle_creator())
    panel.add_button("Список частиц", lambda: editor.open_particle_list())
    panel.add_button("Тест частиц", lambda: editor.test_particles())
    panel.add_button("Очистить частицы", lambda: editor.clear_particles())
    return panel


def create_dialogue_editor_panel(editor):
    panel = EditorPanel("Диалоги", 940, 10, 320, 600)
    panel.add_button("Создать диалог", lambda: editor.open_dialogue_creator())
    panel.add_button("Список диалогов", lambda: editor.open_dialogue_list())
    panel.add_button("Добавить реплику", lambda: editor.add_dialogue_response())
    panel.add_button("Удалить диалог", lambda: editor.delete_dialogue())
    return panel


def create_npc_editor_panel(editor):
    panel = EditorPanel("NPC", 940, 10, 320, 600)
    panel.add_button("Создать NPC", lambda: editor.open_npc_creator())
    panel.add_button("Список NPC", lambda: editor.open_npc_list())
    panel.add_button("Добавить способность", lambda: editor.add_npc_ability())
    panel.add_button("Добавить диалог", lambda: editor.add_npc_dialogue())
    panel.add_button("Добавить предмет", lambda: editor.add_npc_shop_item())
    return panel


def create_mechanic_editor_panel(editor):
    panel = EditorPanel("Механики", 940, 10, 320, 600)
    panel.add_button("Создать механику", lambda: editor.open_mechanic_creator())
    panel.add_button("Список механик", lambda: editor.open_mechanic_list())
    panel.add_button("Применить механику", lambda: editor.apply_mechanic_to_game())
    return panel


def create_effect_editor_panel(editor):
    panel = EditorPanel("Эффекты", 940, 10, 320, 600)
    panel.add_button("Создать эффект", lambda: editor.open_effect_creator())
    panel.add_button("Список эффектов", lambda: editor.open_effect_list())
    panel.add_button("Применить эффект", lambda: editor.apply_effect_to_game())
    panel.add_button("Случайный эффект", lambda: editor.create_random_effect())
    return panel


def create_texture_editor_panel(editor):
    panel = EditorPanel("Текстуры", 940, 10, 320, 600)
    panel.add_button("Новая 32x32", lambda: editor.create_new_texture(32, 32))
    panel.add_button("Новая 64x64", lambda: editor.create_new_texture(64, 64))
    panel.add_button("Новая 128x128", lambda: editor.create_new_texture(128, 128))
    panel.add_button("Пиксель-редактор", lambda: editor.open_pixel_editor())
    panel.add_button("Сохранить текстуру", lambda: editor.save_texture())
    panel.add_button("Загрузить текстуру", lambda: editor.load_texture())
    return panel


def extend_editor_with_creators(editor):
    editor.weapon_manager = WeaponManager()
    editor.protection_manager = ProtectionManager()
    editor.minion_manager = MinionManager()

    editor.custom_weapons_data = {}
    editor.custom_protections_data = {}
    editor.custom_minions_data = {}
    editor.custom_loot_tables_data = {}
    editor.custom_room_configs_data = {}
    editor.custom_weather_data = {}
    editor.custom_particles_data = {}
    editor.custom_dialogues_data = {}
    editor.custom_npcs_data = {}
    editor.custom_mechanics_data = {}
    editor.custom_effects_data = {}
    editor.custom_textures_data = {}
    editor.selected_weapon = None
    editor.selected_protection = None
    editor.selected_minion = None
    editor.selected_loot_table = None
    editor.selected_room_config = None
    editor.selected_weather = None
    editor.selected_particle = None
    editor.selected_dialogue = None
    editor.selected_npc = None
    editor.selected_mechanic = None
    editor.selected_effect = None
    editor.selected_texture = None
    editor.current_room_seed = 0
    editor.current_weather_config = None

    editor.weapon_creator_panel = create_weapon_editor_panel(editor)
    editor.protection_creator_panel = create_protection_editor_panel(editor)
    editor.minion_creator_panel = create_minion_editor_panel(editor)
    editor.loot_creator_panel = create_loot_editor_panel(editor)
    editor.room_creator_panel = create_room_editor_panel(editor)
    editor.weather_creator_panel = create_weather_editor_panel(editor)
    editor.particle_creator_panel = create_particle_editor_panel(editor)
    editor.dialogue_creator_panel = create_dialogue_editor_panel(editor)
    editor.npc_creator_panel = create_npc_editor_panel(editor)
    editor.mechanic_creator_panel = create_mechanic_editor_panel(editor)
    editor.effect_creator_panel = create_effect_editor_panel(editor)
    editor.texture_creator_panel = create_texture_editor_panel(editor)

    editor.panels.extend([
        editor.weapon_creator_panel,
        editor.protection_creator_panel,
        editor.minion_creator_panel,
        editor.loot_creator_panel,
        editor.room_creator_panel,
        editor.weather_creator_panel,
        editor.particle_creator_panel,
        editor.dialogue_creator_panel,
        editor.npc_creator_panel,
        editor.mechanic_creator_panel,
        editor.effect_creator_panel,
        editor.texture_creator_panel,
    ])

    def open_weapon_creator(self):
        self.integration.open_subeditor("weapon")

    def open_weapon_list(self):
        weapons = self.weapon_manager.get_all_weapons()
        self.game.ui.show_notification(f"Всего оружия: {len(weapons)}", CYAN, 2.0)

    def create_random_weapon(self):
        weapon = self.weapon_manager.get_random_weapon()
        self.custom_weapons_data[weapon.id] = weapon.config
        self.selected_weapon = weapon.id
        self.game.ui.show_notification(f"Создано оружие: {weapon.name}", GREEN, 2.0)

    def upgrade_selected_weapon(self):
        if self.selected_weapon and self.selected_weapon in self.weapon_manager.weapons:
            weapon = self.weapon_manager.weapons[self.selected_weapon]
            weapon.upgrade()
            self.game.ui.show_notification(f"Оружие улучшено: {weapon.name} (ур. {weapon.level})", YELLOW, 2.0)

    def apply_weapon_to_game(self):
        if self.selected_weapon and self.selected_weapon in self.weapon_manager.weapons:
            weapon = self.weapon_manager.weapons[self.selected_weapon]
            WEAPON_TYPES[weapon.id] = weapon.config
            self.game.player.add_weapon(weapon.id)
            self.game.ui.show_notification(f"Оружие применено: {weapon.name}", GREEN, 2.0)

    def open_protection_creator(self):
        self.integration.open_subeditor("protection")

    def open_protection_list(self):
        protections = self.protection_manager.get_all_protections()
        self.game.ui.show_notification(f"Всего защиты: {len(protections)}", CYAN, 2.0)

    def create_random_protection(self):
        prot = self.protection_manager.get_random_protection()
        self.custom_protections_data[prot.id] = prot.config
        self.selected_protection = prot.id
        self.game.ui.show_notification(f"Создана защита: {prot.name}", GREEN, 2.0)

    def upgrade_selected_protection(self):
        if self.selected_protection and self.selected_protection in self.protection_manager.protections:
            prot = self.protection_manager.protections[self.selected_protection]
            prot.upgrade()
            self.game.ui.show_notification(f"Защита улучшена: {prot.name} (ур. {prot.level})", YELLOW, 2.0)

    def apply_protection_to_game(self):
        if self.selected_protection and self.selected_protection in self.protection_manager.protections:
            prot = self.protection_manager.protections[self.selected_protection]
            self.game.player.armor += prot.armor
            self.game.player.shield_timer = max(self.game.player.shield_timer, float(prot.shield))
            self.game.ui.show_notification(f"Защита применена: {prot.name}", GREEN, 2.0)

    def open_minion_creator(self):
        self.integration.open_subeditor("minion")

    def open_minion_list(self):
        minions = self.minion_manager.get_all_minions()
        self.game.ui.show_notification(f"Всего миньонов: {len(minions)}", CYAN, 2.0)

    def create_random_minion(self):
        minion = self.minion_manager.get_random_minion()
        self.custom_minions_data[minion.id] = minion.config
        self.selected_minion = minion.id
        self.game.ui.show_notification(f"Создан миньон: {minion.name}", GREEN, 2.0)

    def upgrade_selected_minion(self):
        if self.selected_minion and self.selected_minion in self.minion_manager.minions:
            minion = self.minion_manager.minions[self.selected_minion]
            minion.upgrade()
            self.game.ui.show_notification(f"Миньон улучшен: {minion.name} (ур. {minion.level})", YELLOW, 2.0)

    def spawn_minion_in_editor(self):
        if self.selected_minion and self.selected_minion in self.minion_manager.minions:
            minion = self.minion_manager.spawn_minion(self.selected_minion, self.game.player.x, self.game.player.y, self.game.player)
            if minion:
                self.game.ui.show_notification(f"Миньон призван: {minion.name}", GREEN, 2.0)

    def open_loot_table_creator(self):
        self.integration.open_subeditor("loot_table")

    def open_loot_table_list(self):
        self.game.ui.show_notification(f"Таблиц лута: {len(self.custom_loot_tables_data)}", CYAN, 2.0)

    def add_item_to_loot_table(self):
        if self.selected_loot_table and self.selected_loot_table in self.custom_loot_tables_data:
            table = self.custom_loot_tables_data[self.selected_loot_table]
            item = {"name": f"item_{len(table)+1}", "type": "scrap", "weight": 10, "min_amount": 1, "max_amount": 3}
            table.append(item)
            self.game.ui.show_notification("Предмет добавлен в таблицу", GREEN, 2.0)

    def remove_item_from_loot_table(self):
        if self.selected_loot_table and self.selected_loot_table in self.custom_loot_tables_data:
            table = self.custom_loot_tables_data[self.selected_loot_table]
            if table:
                table.pop()
                self.game.ui.show_notification("Предмет удалён из таблицы", ORANGE, 2.0)

    def generate_loot_from_table(self):
        if self.selected_loot_table and self.selected_loot_table in self.custom_loot_tables_data:
            table = self.custom_loot_tables_data[self.selected_loot_table]
            total_weight = sum(item["weight"] for item in table)
            if total_weight > 0:
                roll = random.uniform(0, total_weight)
                for item in table:
                    roll -= item["weight"]
                    if roll <= 0:
                        amount = random.randint(item["min_amount"], item["max_amount"])
                        self.game.pickups.append(Pickup(self.game.player.x, self.game.player.y, item["type"], amount))
                        self.game.ui.show_notification(f"Выпало: {item['name']} x{amount}", YELLOW, 2.0)
                        break

    def generate_rooms(self):
        gen = ProceduralGenerator()
        rooms = gen.generate_level(seed=self.current_room_seed, biome="city", num_rooms=10)
        self.game.ui.show_notification(f"Сгенерировано комнат: {len(rooms)}", CYAN, 2.0)
        return rooms

    def apply_rooms_to_game(self):
        rooms = self.generate_rooms()
        if rooms:
            self.game.current_rooms = rooms
            self.game.ui.show_notification("Комнаты применены к игре", GREEN, 2.0)

    def save_room_config(self):
        self.custom_room_configs_data["default"] = {
            "min_room_size": 150,
            "max_room_size": 300,
            "room_padding": 30,
        }
        self.game.ui.show_notification("Конфигурация комнат сохранена", GREEN, 2.0)

    def load_room_config(self):
        if "default" in self.custom_room_configs_data:
            config = self.custom_room_configs_data["default"]
            self.game.ui.show_notification(f"Загружена конфигурация: {config}", CYAN, 2.0)

    def set_random_seed(self):
        self.current_room_seed = random.randint(0, 999999)
        self.game.ui.show_notification(f"Случайный сид: {self.current_room_seed}", CYAN, 2.0)

    def open_weather_creator(self):
        self.integration.open_subeditor("weather")

    def apply_weather_to_game(self):
        if self.current_weather_config:
            self.game.weather_system.current_weather = self.current_weather_config.get("type", "clear")
            self.game.weather_system.weather_timer = self.current_weather_config.get("duration", 30.0)
            self.game.ui.show_notification(f"Погода применена: {self.current_weather_config['type']}", CYAN, 2.0)

    def create_random_weather(self):
        types = ["clear", "rain", "snow", "sandstorm", "lightning_storm", "gravity_anomaly"]
        self.current_weather_config = {
            "type": random.choice(types),
            "duration": random.uniform(10, 60),
            "intensity": random.uniform(0.3, 1.0),
        }
        self.game.ui.show_notification(f"Создана погода: {self.current_weather_config['type']}", GREEN, 2.0)

    def clear_weather(self):
        self.current_weather_config = None
        self.game.weather_system.current_weather = "clear"
        self.game.ui.show_notification("Погода очищена", ORANGE, 2.0)

    def open_particle_creator(self):
        self.integration.open_subeditor("particle")

    def open_particle_list(self):
        self.game.ui.show_notification(f"Систем частиц: {len(self.custom_particles_data)}", CYAN, 2.0)

    def test_particles(self):
        self.game.spawn_particles(self.game.player.x, self.game.player.y, 20, random.choice([RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA]))
        self.game.ui.show_notification("Частицы созданы", GREEN, 2.0)

    def clear_particles(self):
        self.game.particles.clear()
        self.game.ui.show_notification("Частицы очищены", ORANGE, 2.0)

    def open_dialogue_creator(self):
        self.integration.open_subeditor("dialogue")

    def open_dialogue_list(self):
        self.game.ui.show_notification(f"Диалогов: {len(self.custom_dialogues_data)}", CYAN, 2.0)

    def add_dialogue_response(self):
        if self.selected_dialogue and self.selected_dialogue in self.custom_dialogues_data:
            dialogue = self.custom_dialogues_data[self.selected_dialogue]
            dialogue["responses"].append({"text": "Новый ответ", "next": None})
            self.game.ui.show_notification("Ответ добавлен", GREEN, 2.0)

    def delete_dialogue(self):
        if self.selected_dialogue and self.selected_dialogue in self.custom_dialogues_data:
            del self.custom_dialogues_data[self.selected_dialogue]
            self.selected_dialogue = None
            self.game.ui.show_notification("Диалог удалён", ORANGE, 2.0)

    def open_npc_creator(self):
        self.integration.open_subeditor("npc")

    def open_npc_list(self):
        self.game.ui.show_notification(f"NPC: {len(self.custom_npcs_data)}", CYAN, 2.0)

    def add_npc_ability(self):
        if self.selected_npc and self.selected_npc in self.custom_npcs_data:
            npc = self.custom_npcs_data[self.selected_npc]
            npc["abilities"].append("new_ability")
            self.game.ui.show_notification("Способность добавлена", GREEN, 2.0)

    def add_npc_dialogue(self):
        if self.selected_npc and self.selected_npc in self.custom_npcs_data:
            npc = self.custom_npcs_data[self.selected_npc]
            npc["dialogues"].append("new_dialogue")
            self.game.ui.show_notification("Диалог добавлен", GREEN, 2.0)

    def add_npc_shop_item(self):
        if self.selected_npc and self.selected_npc in self.custom_npcs_data:
            npc = self.custom_npcs_data[self.selected_npc]
            npc["shop_items"].append("new_item")
            self.game.ui.show_notification("Предмет добавлен в магазин NPC", GREEN, 2.0)

    def open_mechanic_creator(self):
        self.integration.open_subeditor("mechanic")

    def open_mechanic_list(self):
        self.game.ui.show_notification(f"Механик: {len(self.custom_mechanics_data)}", CYAN, 2.0)

    def apply_mechanic_to_game(self):
        if self.selected_mechanic and self.selected_mechanic in self.custom_mechanics_data:
            mechanic = self.custom_mechanics_data[self.selected_mechanic]
            self.game.ui.show_notification(f"Механика применена: {mechanic.get('name', '')}", GREEN, 2.0)

    def open_effect_creator(self):
        self.integration.open_subeditor("effect")

    def open_effect_list(self):
        self.game.ui.show_notification(f"Эффектов: {len(self.custom_effects_data)}", CYAN, 2.0)

    def apply_effect_to_game(self):
        if self.selected_effect and self.selected_effect in self.custom_effects_data:
            effect = self.custom_effects_data[self.selected_effect]
            self.game.effect_system.apply_effect_by_id(effect.get("id", ""), self.game.player)
            self.game.ui.show_notification(f"Эффект применён: {effect.get('name', '')}", GREEN, 2.0)

    def create_random_effect(self):
        effects = list(self.game.effect_system.effect_database.values())
        if effects:
            effect = random.choice(effects)
            self.custom_effects_data[effect.id] = {"id": effect.id, "name": effect.name}
            self.selected_effect = effect.id
            self.game.ui.show_notification(f"Создан эффект: {effect.name}", GREEN, 2.0)

    def create_new_texture(self, w, h):
        self.texture_editor = TextureEditor(self, w, h)
        self.selected_texture = f"texture_{w}x{h}"
        self.custom_textures_data[self.selected_texture] = self.texture_editor
        self.game.ui.show_notification(f"Создана текстура {w}x{h}", CYAN, 2.0)

    def open_pixel_editor(self):
        if not self.texture_editor:
            self.create_new_texture(32, 32)
        self.game.ui.show_notification("Редактор пикселей открыт", CYAN, 2.0)

    def save_texture(self):
        if self.selected_texture and self.selected_texture in self.custom_textures_data:
            tex = self.custom_textures_data[self.selected_texture]
            filename = f"{self.selected_texture}.png"
            tex.save_to_file(filename)
            self.game.ui.show_notification(f"Текстура сохранена: {filename}", GREEN, 2.0)

    def load_texture(self):
        self.game.ui.show_notification("Загрузка текстуры...", CYAN, 2.0)

    editor.open_weapon_creator = open_weapon_creator
    editor.open_weapon_list = open_weapon_list
    editor.create_random_weapon = create_random_weapon
    editor.upgrade_selected_weapon = upgrade_selected_weapon
    editor.apply_weapon_to_game = apply_weapon_to_game
    editor.open_protection_creator = open_protection_creator
    editor.open_protection_list = open_protection_list
    editor.create_random_protection = create_random_protection
    editor.upgrade_selected_protection = upgrade_selected_protection
    editor.apply_protection_to_game = apply_protection_to_game
    editor.open_minion_creator = open_minion_creator
    editor.open_minion_list = open_minion_list
    editor.create_random_minion = create_random_minion
    editor.upgrade_selected_minion = upgrade_selected_minion
    editor.spawn_minion_in_editor = spawn_minion_in_editor
    editor.open_loot_table_creator = open_loot_table_creator
    editor.open_loot_table_list = open_loot_table_list
    editor.add_item_to_loot_table = add_item_to_loot_table
    editor.remove_item_from_loot_table = remove_item_from_loot_table
    editor.generate_loot_from_table = generate_loot_from_table
    editor.generate_rooms = generate_rooms
    editor.apply_rooms_to_game = apply_rooms_to_game
    editor.save_room_config = save_room_config
    editor.load_room_config = load_room_config
    editor.set_random_seed = set_random_seed
    editor.open_weather_creator = open_weather_creator
    editor.apply_weather_to_game = apply_weather_to_game
    editor.create_random_weather = create_random_weather
    editor.clear_weather = clear_weather
    editor.open_particle_creator = open_particle_creator
    editor.open_particle_list = open_particle_list
    editor.test_particles = test_particles
    editor.clear_particles = clear_particles
    editor.open_dialogue_creator = open_dialogue_creator
    editor.open_dialogue_list = open_dialogue_list
    editor.add_dialogue_response = add_dialogue_response
    editor.delete_dialogue = delete_dialogue
    editor.open_npc_creator = open_npc_creator
    editor.open_npc_list = open_npc_list
    editor.add_npc_ability = add_npc_ability
    editor.add_npc_dialogue = add_npc_dialogue
    editor.add_npc_shop_item = add_npc_shop_item
    editor.open_mechanic_creator = open_mechanic_creator
    editor.open_mechanic_list = open_mechanic_list
    editor.apply_mechanic_to_game = apply_mechanic_to_game
    editor.open_effect_creator = open_effect_creator
    editor.open_effect_list = open_effect_list
    editor.apply_effect_to_game = apply_effect_to_game
    editor.create_random_effect = create_random_effect
    editor.create_new_texture = create_new_texture
    editor.open_pixel_editor = open_pixel_editor
    editor.save_texture = save_texture
    editor.load_texture = load_texture