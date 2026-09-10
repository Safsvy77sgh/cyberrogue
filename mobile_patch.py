"""
Mobile touch controls patch for "Overload: Last Protocol".

USAGE:
    import mobile_patch
    mobile_patch.patch_game(game)  # Только для мобильных устройств!
"""

import pygame
import math
from typing import Tuple, Dict, Any, Optional

# ---------- Touch UI state ----------
_touch_state = {
    'move_joystick': {'active': False, 'base': (0, 0), 'current': (0, 0), 'touch_id': None},
    'aim_joystick': {'active': False, 'base': (0, 0), 'current': (0, 0), 'touch_id': None},
    'shoot_pressed': False,
    'dash_pressed': False,
    'wall_pressed': False,
    'repair_pressed': False,
    'reload_pressed': False,
    'weapon_next': False,
    'weapon_prev': False,
    'pause_pressed': False,
    'shop_pressed': False,
    'craft_pressed': False,
}

_touch_buttons = {}
_screen_size = (0, 0)
_patched_games = set()
_patched_game_class = False

# Button layout constants
_BTN_SIZE = 60
_MARGIN = 20
_JOYSTICK_RADIUS = 60


def patch_game(game=None):
    """
    Apply mobile touch controls to the running game.
    Call this ONLY on mobile devices!
    """
    global _patched_game_class

    if game is not None:
        # Проверяем, не патчили ли уже эту игру
        if id(game) in _patched_games:
            print(f"Игра уже пропатчена, пропускаем")
            return True

        _patched_games.add(id(game))
        _patch_game_instance(game)
        print("Мобильное управление применено к экземпляру игры")
        return True

    # Патчим класс Game (только если явно вызвано)
    if not _patched_game_class:
        try:
            from systems.game import Game
            _patch_game_class(Game)
            _patched_game_class = True
            print("Мобильное управление применено к классу Game")
            return True
        except ImportError:
            print("Класс Game не найден для патча")
            return False
        except Exception as e:
            print(f"Ошибка патча: {e}")
            return False

    return True


def _patch_game_instance(game):
    """Патчит конкретный экземпляр игры."""
    # Проверяем, не пропатчен ли уже
    if hasattr(game, '_mobile_patched'):
        print(f"Игра {id(game)} уже пропатчена")
        return

    game._mobile_patched = True

    # Сохраняем оригинальные методы
    game._original_handle_events = game.handle_events
    game._original_update = game.update
    game._original_draw = game.draw
    game._original_handle_keydown = game.handle_keydown

    # Инициализируем UI
    _init_touch_ui(game.screen.get_width(), game.screen.get_height())

    # Создаём новые методы
    def mobile_handle_events():
        _mobile_handle_events(game)

    def mobile_update(dt):
        _mobile_update(game, dt)

    def mobile_draw():
        _mobile_draw(game)

    # Применяем патчи
    game.handle_events = mobile_handle_events
    game.update = mobile_update
    game.draw = mobile_draw

    # Добавляем флаг мобильного режима
    game.mobile_mode = True
    game._needs_input_restore = False
    game._original_input_functions = {}

    print(f"Мобильное управление активировано для {game.__class__.__name__}")


def _patch_game_class(game_cls):
    """Патчит класс Game для всех будущих экземпляров."""
    if game_cls is None:
        return

    # Проверяем, не пропатчен ли уже класс
    if hasattr(game_cls, '_mobile_patched_class'):
        return

    game_cls._mobile_patched_class = True

    # Сохраняем оригинальные методы
    game_cls._original_handle_events = game_cls.handle_events
    game_cls._original_update = game_cls.update
    game_cls._original_draw = game_cls.draw
    game_cls._original_handle_keydown = game_cls.handle_keydown

    def mobile_handle_events(self):
        _mobile_handle_events(self)

    def mobile_update(self, dt):
        _mobile_update(self, dt)

    def mobile_draw(self):
        _mobile_draw(self)

    game_cls.handle_events = mobile_handle_events
    game_cls.update = mobile_update
    game_cls.draw = mobile_draw


def _init_touch_ui(width, height):
    """Инициализирует расположение кнопок на экране."""
    global _screen_size, _touch_buttons
    _screen_size = (width, height)
    _touch_buttons = {}

    # Джойстик движения (нижний левый угол)
    _touch_buttons['move_base'] = (int(width * 0.15), int(height * 0.75))

    # Джойстик прицеливания (нижний правый угол)
    _touch_buttons['aim_base'] = (int(width * 0.85), int(height * 0.75))

    # Кнопки действий (правая сторона)
    _touch_buttons['shoot'] = (width - _MARGIN - _BTN_SIZE, height - _MARGIN - _BTN_SIZE)
    _touch_buttons['dash'] = (width - _MARGIN - _BTN_SIZE * 2 - 10, height - _MARGIN - _BTN_SIZE)
    _touch_buttons['wall'] = (width - _MARGIN - _BTN_SIZE, height - _MARGIN - _BTN_SIZE * 2 - 10)
    _touch_buttons['repair'] = (width - _MARGIN - _BTN_SIZE * 2 - 10, height - _MARGIN - _BTN_SIZE * 2 - 10)
    _touch_buttons['reload'] = (width - _MARGIN - _BTN_SIZE * 3 - 20, height - _MARGIN - _BTN_SIZE)

    # Верхние кнопки
    _touch_buttons['pause'] = (_MARGIN, _MARGIN)
    _touch_buttons['shop'] = (_MARGIN + _BTN_SIZE + 10, _MARGIN)
    _touch_buttons['craft'] = (_MARGIN + _BTN_SIZE * 2 + 20, _MARGIN)
    _touch_buttons['weapon_prev'] = (width - _MARGIN - _BTN_SIZE, _MARGIN)
    _touch_buttons['weapon_next'] = (width - _MARGIN - _BTN_SIZE * 2 - 10, _MARGIN)


def _mobile_handle_events(game):
    """Обрабатывает события с учётом мобильного ввода."""
    # Вызываем оригинальный обработчик
    if hasattr(game, '_original_handle_events'):
        game._original_handle_events()

    # Обрабатываем сенсорные события
    _process_touch_events(game)

    # Обработка кнопок
    if _touch_state['pause_pressed']:
        game.paused = not game.paused
        _touch_state['pause_pressed'] = False

    if _touch_state['shop_pressed']:
        game.shop_open = not game.shop_open
        _touch_state['shop_pressed'] = False

    if _touch_state['craft_pressed']:
        game.crafting_open = not game.crafting_open
        _touch_state['craft_pressed'] = False


def _mobile_update(game, dt):
    """Обновляет игру с учётом мобильного ввода."""
    # Переопределяем ввод
    _override_input_from_touch(game)

    # Вызываем оригинальное обновление
    if hasattr(game, '_original_update'):
        game._original_update(dt)

    # Восстанавливаем ввод
    _restore_input(game)

    # Сбрасываем одноразовые кнопки
    _touch_state['weapon_next'] = False
    _touch_state['weapon_prev'] = False


def _mobile_draw(game):
    """Отрисовывает игру и мобильные контролы."""
    # Вызываем оригинальную отрисовку
    if hasattr(game, '_original_draw'):
        game._original_draw()

    # Рисуем мобильные контролы поверх
    _draw_touch_controls(game)


def _process_touch_events(game):
    """Обрабатывает сенсорные события."""
    global _touch_state

    for event in pygame.event.get():
        # Обработка касаний
        if event.type == pygame.FINGERDOWN:
            x = event.x * _screen_size[0]
            y = event.y * _screen_size[1]
            _handle_touch_down(x, y, event.finger_id)

        elif event.type == pygame.FINGERMOTION:
            x = event.x * _screen_size[0]
            y = event.y * _screen_size[1]
            _handle_touch_move(x, y, event.finger_id)

        elif event.type == pygame.FINGERUP:
            _handle_touch_up(event.finger_id)

        # Обработка мыши для тестирования
        elif event.type == pygame.MOUSEBUTTONDOWN:
            _handle_touch_down(event.pos[0], event.pos[1], 1000 + event.button)

        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[0]:
                _handle_touch_move(event.pos[0], event.pos[1], 1001)

        elif event.type == pygame.MOUSEBUTTONUP:
            _handle_touch_up(1000 + event.button)


def _handle_touch_down(x, y, touch_id):
    """Обрабатывает нажатие."""
    global _touch_state

    pos = (x, y)

    # Проверяем кнопки
    for btn_name, btn_pos in _touch_buttons.items():
        if btn_name.endswith('_base'):
            continue
        btn_rect = pygame.Rect(btn_pos[0], btn_pos[1], _BTN_SIZE, _BTN_SIZE)
        if btn_rect.collidepoint(pos):
            _touch_state[btn_name + '_pressed'] = True
            return

    # Проверяем джойстики
    move_base = _touch_buttons.get('move_base')
    if move_base and math.hypot(x - move_base[0], y - move_base[1]) < _JOYSTICK_RADIUS * 1.5:
        if _touch_state['move_joystick']['touch_id'] is None:
            _touch_state['move_joystick'].update({
                'active': True,
                'base': (x, y),
                'current': (x, y),
                'touch_id': touch_id
            })
            return

    aim_base = _touch_buttons.get('aim_base')
    if aim_base and math.hypot(x - aim_base[0], y - aim_base[1]) < _JOYSTICK_RADIUS * 1.5:
        if _touch_state['aim_joystick']['touch_id'] is None:
            _touch_state['aim_joystick'].update({
                'active': True,
                'base': (x, y),
                'current': (x, y),
                'touch_id': touch_id
            })
            return


def _handle_touch_move(x, y, touch_id):
    """Обрабатывает движение пальца."""
    global _touch_state

    if _touch_state['move_joystick']['touch_id'] == touch_id:
        _touch_state['move_joystick']['current'] = (x, y)

    if _touch_state['aim_joystick']['touch_id'] == touch_id:
        _touch_state['aim_joystick']['current'] = (x, y)


def _handle_touch_up(touch_id):
    """Обрабатывает отпускание."""
    global _touch_state

    if _touch_state['move_joystick']['touch_id'] == touch_id:
        _touch_state['move_joystick'].update({
            'active': False,
            'base': (0, 0),
            'current': (0, 0),
            'touch_id': None
        })

    if _touch_state['aim_joystick']['touch_id'] == touch_id:
        _touch_state['aim_joystick'].update({
            'active': False,
            'base': (0, 0),
            'current': (0, 0),
            'touch_id': None
        })

    # Сбрасываем кнопки
    for btn_name in list(_touch_state.keys()):
        if btn_name.endswith('_pressed'):
            _touch_state[btn_name] = False


def _override_input_from_touch(game):
    """Переопределяет ввод с клавиатуры/мыши на сенсорный."""
    global _touch_state

    # Сохраняем оригинальные функции
    if not hasattr(game, '_original_input_functions') or not game._original_input_functions:
        game._original_input_functions = {
            'key_get_pressed': pygame.key.get_pressed,
            'mouse_get_pressed': pygame.mouse.get_pressed,
            'mouse_get_pos': pygame.mouse.get_pos,
        }

    # Получаем вектор движения
    move_js = _touch_state['move_joystick']
    aim_js = _touch_state['aim_joystick']

    dx = dy = 0
    if move_js['active']:
        dx = move_js['current'][0] - move_js['base'][0]
        dy = move_js['current'][1] - move_js['base'][1]

    aim_dx = aim_dy = 0
    if aim_js['active']:
        aim_dx = aim_js['current'][0] - aim_js['base'][0]
        aim_dy = aim_js['current'][1] - aim_js['base'][1]

    # Симулируем позицию мыши
    if abs(aim_dx) > 10 or abs(aim_dy) > 10:
        mouse_pos = (game.player.x + aim_dx * 5, game.player.y + aim_dy * 5)
    else:
        mouse_pos = (game.player.x + 100, game.player.y)

    # Симулируем клавиши
    keys_state = {}
    threshold = 20

    if abs(dx) > threshold or abs(dy) > threshold:
        if abs(dx) > abs(dy):
            if dx > 0:
                keys_state[pygame.K_d] = True
                keys_state[pygame.K_RIGHT] = True
            else:
                keys_state[pygame.K_a] = True
                keys_state[pygame.K_LEFT] = True
        else:
            if dy > 0:
                keys_state[pygame.K_s] = True
                keys_state[pygame.K_DOWN] = True
            else:
                keys_state[pygame.K_w] = True
                keys_state[pygame.K_UP] = True

    # Кнопки мыши
    if _touch_state['shoot_pressed']:
        mouse_buttons = (True, False, False)
    elif _touch_state['dash_pressed']:
        mouse_buttons = (False, False, True)
    else:
        mouse_buttons = (False, False, False)

    # Подменяем функции
    def fake_key_get_pressed():
        class KeyState:
            def __getitem__(self, key):
                return keys_state.get(key, False)

        return KeyState()

    def fake_mouse_get_pressed():
        return mouse_buttons

    def fake_mouse_get_pos():
        return mouse_pos

    pygame.key.get_pressed = fake_key_get_pressed
    pygame.mouse.get_pressed = fake_mouse_get_pressed
    pygame.mouse.get_pos = fake_mouse_get_pos

    # Переключение оружия
    if _touch_state['weapon_next']:
        weapons_list = list(game.player.weapons)
        if weapons_list:
            current_idx = weapons_list.index(
                game.player.current_weapon) if game.player.current_weapon in weapons_list else 0
            next_idx = (current_idx + 1) % len(weapons_list)
            game.player.current_weapon = weapons_list[next_idx]
            game.player.reloading = False
        _touch_state['weapon_next'] = False

    if _touch_state['weapon_prev']:
        weapons_list = list(game.player.weapons)
        if weapons_list:
            current_idx = weapons_list.index(
                game.player.current_weapon) if game.player.current_weapon in weapons_list else 0
            prev_idx = (current_idx - 1) % len(weapons_list)
            game.player.current_weapon = weapons_list[prev_idx]
            game.player.reloading = False
        _touch_state['weapon_prev'] = False


def _restore_input(game):
    """Восстанавливает оригинальные функции ввода."""
    if hasattr(game, '_original_input_functions') and game._original_input_functions:
        pygame.key.get_pressed = game._original_input_functions['key_get_pressed']
        pygame.mouse.get_pressed = game._original_input_functions['mouse_get_pressed']
        pygame.mouse.get_pos = game._original_input_functions['mouse_get_pos']


def _draw_touch_controls(game):
    """Отрисовывает мобильные контролы."""
    global _touch_state, _touch_buttons

    screen = game.screen
    if not screen:
        return

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

    # Джойстики
    move_js = _touch_state['move_joystick']
    move_base = _touch_buttons.get('move_base', (100, 400))

    if move_js['active']:
        pygame.draw.circle(overlay, (100, 100, 100, 100), move_js['base'], _JOYSTICK_RADIUS, 3)
        pygame.draw.circle(overlay, (200, 200, 200, 150), move_js['current'], 30)
    else:
        pygame.draw.circle(overlay, (80, 80, 80, 80), move_base, _JOYSTICK_RADIUS, 2)
        pygame.draw.circle(overlay, (80, 80, 80, 80), move_base, 20, 1)

    aim_js = _touch_state['aim_joystick']
    aim_base = _touch_buttons.get('aim_base', (700, 400))

    if aim_js['active']:
        pygame.draw.circle(overlay, (100, 100, 100, 100), aim_js['base'], _JOYSTICK_RADIUS, 3)
        pygame.draw.circle(overlay, (200, 200, 200, 150), aim_js['current'], 30)
    else:
        pygame.draw.circle(overlay, (80, 80, 80, 80), aim_base, _JOYSTICK_RADIUS, 2)
        pygame.draw.circle(overlay, (80, 80, 80, 80), aim_base, 20, 1)

    # Кнопки
    font = pygame.font.Font(None, 20)

    for btn_name, btn_pos in _touch_buttons.items():
        if btn_name.endswith('_base'):
            continue

        rect = pygame.Rect(btn_pos[0], btn_pos[1], _BTN_SIZE, _BTN_SIZE)

        if _touch_state.get(btn_name + '_pressed', False):
            color = (200, 200, 200, 200)
        else:
            color = (100, 100, 100, 128)

        pygame.draw.rect(overlay, color, rect, border_radius=10)
        pygame.draw.rect(overlay, (255, 255, 255, 200), rect, 2, border_radius=10)

        labels = {
            'shoot': 'ОГОНЬ',
            'dash': 'РЫВОК',
            'wall': 'СТЕНА',
            'repair': 'РЕМОНТ',
            'reload': 'ПЕРЕЗ.',
            'pause': 'ПАУЗА',
            'shop': 'МАГАЗ.',
            'craft': 'КРАФТ',
            'weapon_prev': '<',
            'weapon_next': '>',
        }

        label = labels.get(btn_name, btn_name[:4])
        text = font.render(label, True, (255, 255, 255))
        text_rect = text.get_rect(center=(rect.centerx, rect.centery))
        overlay.blit(text, text_rect)

    screen.blit(overlay, (0, 0))

# НЕ вызываем patch_game() автоматически!
# main.py вызовет его только на мобильных устройствах