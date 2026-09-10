# main.py — с поддержкой мобильного управления, адаптацией экрана и рендерером
# main.py — добавьте в начало после импортов
import os

# Для Android определяем мобильный режим автоматически
if os.environ.get('ANDROID_ARGUMENT') or os.path.exists('/system/build.prop'):
    MOBILE_MODE = True
else:
    MOBILE_MODE = False
import pygame
import sys
import os
import json
import math

from settings import *
from sounds import SoundManager
from systems.game import Game

# Попытка импорта мобильного патча
try:
    import mobile_patch

    MOBILE_PATCH_AVAILABLE = True
except ImportError:
    MOBILE_PATCH_AVAILABLE = False
    print("Мобильный патч не найден")


# Определяем, запущена ли игра на мобильном устройстве
def is_mobile_device():
    """Определяет, запущена ли игра на мобильном устройстве."""
    # Проверяем наличие сенсорного экрана
    try:
        import pygame.touch
        if pygame.touch.get_num_devices() > 0:
            return True
    except:
        pass

    # Проверяем окружение
    try:
        import platform
        system = platform.system().lower()
        if 'android' in system or 'ios' in system:
            return True
    except:
        pass

    # Проверяем переменные окружения
    if os.environ.get('MOBILE_MODE', '').lower() in ('1', 'true', 'yes'):
        return True

    # По умолчанию - десктоп
    return False


# Определяем режим
MOBILE_MODE = is_mobile_device()

if MOBILE_MODE:
    print("Мобильный режим активирован")
else:
    print("Десктопный режим")

from systems.renderer import Renderer


def get_screen_size():
    """Определяет размер экрана в зависимости от платформы."""
    if MOBILE_MODE:
        try:
            info = pygame.display.Info()
            width = info.current_w
            height = info.current_h
            if width < 100 or height < 100:
                width, height = SCREEN_WIDTH, SCREEN_HEIGHT
            return (width, height)
        except:
            return (SCREEN_WIDTH, SCREEN_HEIGHT)
    return (SCREEN_WIDTH, SCREEN_HEIGHT)


def patch_rendering():
    """Патчит draw-методы. Рендерер рисует КРАСИВО, а оригинал — HP бары и прочее."""
    try:
        from systems.renderer import Renderer
    except ImportError:
        print("Рендерер недоступен — используем обычную отрисовку")
        return

    # --- Player ---
    try:
        from entities.player import Player
        original_player_draw = Player.draw

        def patched_player_draw(self, screen):
            game = getattr(self, 'game', None)
            if game and hasattr(game, 'renderer') and game.renderer:
                renderer = game.renderer
                angle = getattr(self, 'angle', 0)
                thrust = getattr(self, 'moving', False)
                shield = getattr(self, 'shield_timer', 0) > 0
                radius = getattr(self, 'radius', 20)
                # Рендерер рисует корабль
                renderer.draw_player(screen, self.x, self.y, angle, thrust, shield, None, radius)
                # Оригинал рисует HP бар, энергию, щит
                original_player_draw(self, screen)
                return
            original_player_draw(self, screen)

        Player.draw = patched_player_draw
        print("Player.draw патч применён")
    except ImportError:
        print("Player не найден")
    except Exception as e:
        print(f"Ошибка патча Player: {e}")

    # --- Enemy ---
    try:
        from entities.enemy_extended import ExtendedEnemyFinal
        original_enemy_draw = ExtendedEnemyFinal.draw

        def patched_enemy_draw(self, screen):
            game = getattr(self, 'game', None)
            if game and hasattr(game, 'renderer') and game.renderer:
                renderer = game.renderer
                enemy_type = getattr(self, 'type', 'basic')
                if getattr(self, 'is_boss', False):
                    enemy_type = 'boss'
                elif getattr(self, 'is_elite', False):
                    enemy_type = 'elite'
                angle = getattr(self, 'angle', 0)
                hp = getattr(self, 'hp', 1)
                max_hp = getattr(self, 'max_hp', 1)
                hp_ratio = hp / max_hp if max_hp > 0 else 0
                radius = getattr(self, 'radius', 18)
                phase = getattr(self, 'phase', 0)
                # Рендерер рисует красивого врага
                renderer.draw_enemy(screen, enemy_type, self.x, self.y, angle, hp_ratio, None, radius, phase=phase)
                # Оригинал рисует HP бар врага
                original_enemy_draw(self, screen)
                return
            original_enemy_draw(self, screen)

        ExtendedEnemyFinal.draw = patched_enemy_draw
        print("Enemy.draw патч применён")
    except ImportError:
        print("ExtendedEnemyFinal не найден")
    except Exception as e:
        print(f"Ошибка патча Enemy: {e}")

    # --- Bullet ---
    try:
        from entities.bullet import Bullet
        original_bullet_draw = Bullet.draw

        def patched_bullet_draw(self, screen):
            game = getattr(self, 'game', None)
            if game and hasattr(game, 'renderer') and game.renderer:
                renderer = game.renderer
                if getattr(self, 'from_player', True):
                    angle = math.atan2(getattr(self, 'vy', 0), getattr(self, 'vx', 1))
                    renderer.draw_projectile_player(screen, self.x, self.y, angle)
                else:
                    renderer.draw_projectile_enemy(screen, self.x, self.y, getattr(self, 'radius', 6))
                return
            original_bullet_draw(self, screen)

        Bullet.draw = patched_bullet_draw
        print("Bullet.draw патч применён")
    except ImportError:
        print("Bullet не найден")
    except Exception as e:
        print(f"Ошибка патча Bullet: {e}")

    # --- Obstacle ---
    try:
        from entities.obstacle import Obstacle
        original_obstacle_draw = Obstacle.draw

        def patched_obstacle_draw(self, screen):
            game = getattr(self, 'game', None)
            if game and hasattr(game, 'renderer') and game.renderer:
                renderer = game.renderer
                obs_type = getattr(self, 'type', 'box')
                if obs_type == 'barrel':
                    renderer.draw_obstacle_barrel(screen, self.x + self.w // 2, self.y + self.h // 2, self.w, self.h)
                elif obs_type == 'crate' or obs_type == 'box':
                    renderer.draw_obstacle_crate(screen, self.x + self.w // 2, self.y + self.h // 2,
                                                 max(self.w, self.h))
                elif obs_type == 'wall':
                    renderer.draw_obstacle_wall(screen, pygame.Rect(self.x, self.y, self.w, self.h))
                else:
                    renderer.draw_obstacle_crate(screen, self.x + self.w // 2, self.y + self.h // 2,
                                                 max(self.w, self.h))
                return
            original_obstacle_draw(self, screen)

        Obstacle.draw = patched_obstacle_draw
        print("Obstacle.draw патч применён")
    except ImportError:
        print("Obstacle не найден")
    except Exception as e:
        print(f"Ошибка патча Obstacle: {e}")

    # --- Particle ---
    try:
        from entities.particle import Particle
        original_particle_draw = Particle.draw

        def patched_particle_draw(self, screen):
            game = getattr(self, 'game', None)
            if game and hasattr(game, 'renderer') and game.renderer:
                renderer = game.renderer
                renderer.draw_particle(screen, self)
                return
            original_particle_draw(self, screen)

        Particle.draw = patched_particle_draw
        print("Particle.draw патч применён")
    except ImportError:
        print("Particle не найден")
    except Exception as e:
        print(f"Ошибка патча Particle: {e}")

    print("Патчинг отрисовки завершён")


def main():
    pygame.init()

    # Инициализация звука
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        print("Звук инициализирован")
    except pygame.error as e:
        print(f"Звук недоступен: {e}")

    # Определяем размер экрана
    screen_width, screen_height = get_screen_size()
    print(f"Размер экрана: {screen_width}x{screen_height}")

    # Создаём окно
    if MOBILE_MODE:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
        print("Полноэкранный режим для мобильного устройства")
    else:
        screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
        print("Оконный режим (десктоп)")

    pygame.display.set_caption("ПЕРЕГРУЗКА: ПОСЛЕДНИЙ ПРОТОКОЛ")

    # Иконка
    try:
        icon_surface = pygame.Surface((32, 32))
        icon_surface.fill((30, 30, 50))
        pygame.draw.circle(icon_surface, CYAN, (16, 16), 10)
        pygame.draw.circle(icon_surface, WHITE, (16, 16), 10, 2)
        pygame.display.set_icon(icon_surface)
    except Exception as e:
        print(f"Не удалось установить иконку: {e}")

    # Патчим отрисовку до создания игры
    patch_rendering()

    # Создаём менеджер звука
    try:
        sound_manager = SoundManager()
        print("SoundManager создан")
    except Exception as e:
        print(f"Ошибка создания SoundManager: {e}")
        sound_manager = None

    # Создаём игру
    try:
        game = Game(screen)
        print("Игра создана")
    except Exception as e:
        print(f"Ошибка создания игры: {e}")
        pygame.quit()
        sys.exit(1)

    # Привязываем звук
    if sound_manager:
        game.sound_manager = sound_manager

    # Активируем рендерер
    try:
        game.renderer = Renderer(game)
        game.renderer.game = game
        print("Рендерер активирован")
    except Exception as e:
        print(f"Рендерер не активирован: {e}")
        game.renderer = None

    # Инициализируем мобильное управление ТОЛЬКО если мы на мобильном устройстве
    if MOBILE_MODE and MOBILE_PATCH_AVAILABLE:
        try:
            mobile_patch.patch_game(game)
            print("Мобильное управление активировано через mobile_patch")
        except Exception as e:
            print(f"Ошибка мобильного патча: {e}")
    else:
        # На десктопе mobile_mode = False
        game.mobile_mode = False
        game.mobile_controls = None
        print("Обычное управление (клавиатура + мышь)")

    # Запускаем игру
    try:
        game.run()
    except KeyboardInterrupt:
        print("Игра прервана")
    except Exception as e:
        print(f"Ошибка в игровом цикле: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()