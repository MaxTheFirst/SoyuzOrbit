# visualize.py (улучшенная версия)

import pygame
import pandas as pd
import config
import sys

# --- НОВЫЕ И УЛУЧШЕННЫЕ НАСТРОЙКИ ВИЗУАЛИЗАЦИИ ---
FULLSCREEN = False  # Поставьте True для запуска в полноэкранном режиме
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 500
BACKGROUND_COLOR = (10, 20, 30)
BLOCK_COLOR = (100, 150, 255)
SPRING_COLOR = (80, 80, 80)
WALL_COLOR = (200, 200, 200)
TEXT_COLOR = (230, 230, 230)
BLOCK_RADIUS = 5  # Уменьшили радиус блоков
Y_POSITION = SCREEN_HEIGHT // 2
PLAYBACK_SPEED_FPS = 60


def preprocess_data(filename: str) -> pd.DataFrame:
    """Загружает CSV и преобразует его в удобный для анимации формат."""
    print("Loading simulation data...")
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден. Сначала запустите main.py.")
        sys.exit()
    print("Processing data for animation...")
    positions_df = df.pivot_table(index='time', columns='block_index', values='position')
    print("Data ready.")
    return positions_df


def run_animation(positions_df: pd.DataFrame):
    """Основной цикл Pygame для отрисовки анимации."""
    pygame.init()
    pygame.font.init()  # Инициализируем модуль для работы со шрифтами

    # Создаем шрифт для отображения времени
    font = pygame.font.Font(None, 32)  # Используем стандартный шрифт размером 32

    # Настраиваем экран
    flags = pygame.SCALED  # Позволяет корректно работать с разными разрешениями
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    pygame.display.set_caption("Анимация волны в цепочке (Нажмите 'F' для переключения полноэкранного режима)")
    clock = pygame.time.Clock()

    # Рассчитываем масштаб для отображения
    total_chain_length = (config.NUM_BLOCKS + 1) * config.BLOCK_SPACING
    padding = 80  # Увеличили отступы по бокам

    # Масштаб рассчитывается на основе текущего размера окна (важно для полноэкранного режима)
    effective_screen_width = screen.get_width()
    scale = (effective_screen_width - 2 * padding) / total_chain_length

    running = True
    frame_iterator = positions_df.iterrows()

    while running:
        try:
            timestamp, positions = next(frame_iterator)
        except StopIteration:
            print("Animation finished.")
            break

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Новая функция: переключение полноэкранного режима по клавише F
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                    # Пересчитываем масштаб после изменения размера окна
                    effective_screen_width = screen.get_width()
                    scale = (effective_screen_width - 2 * padding) / total_chain_length

        # --- Отрисовка ---
        screen.fill(BACKGROUND_COLOR)

        # Подготавливаем текст с временем
        time_surface = font.render(f"Time: {timestamp:.2f} s", True, TEXT_COLOR)

        # Отрисовываем стены
        left_wall_x = padding
        right_wall_x = padding + int(total_chain_length * scale)
        pygame.draw.line(screen, WALL_COLOR, (left_wall_x, Y_POSITION - 40), (left_wall_x, Y_POSITION + 40), 4)
        pygame.draw.line(screen, WALL_COLOR, (right_wall_x, Y_POSITION - 40), (right_wall_x, Y_POSITION + 40), 4)

        # Сохраняем экранные координаты всех блоков
        screen_positions = [padding + int(p * scale) for p in positions]

        # Сначала рисуем все пружины
        # Пружина от левой стены до первого блока
        pygame.draw.line(screen, SPRING_COLOR, (left_wall_x, Y_POSITION), (screen_positions[0], Y_POSITION), 1)
        # Пружины между блоками
        for i in range(len(screen_positions) - 1):
            pygame.draw.line(screen, SPRING_COLOR, (screen_positions[i], Y_POSITION),
                             (screen_positions[i + 1], Y_POSITION), 1)
        # Пружина от последнего блока до правой стены
        pygame.draw.line(screen, SPRING_COLOR, (screen_positions[-1], Y_POSITION), (right_wall_x, Y_POSITION), 1)

        # Затем рисуем все блоки поверх пружин
        for x_pos in screen_positions:
            pygame.draw.circle(screen, BLOCK_COLOR, (x_pos, Y_POSITION), BLOCK_RADIUS)

        # Выводим текст поверх всего
        screen.blit(time_surface, (20, 20))

        # Обновляем дисплей
        pygame.display.flip()
        clock.tick(PLAYBACK_SPEED_FPS)

    pygame.quit()


if __name__ == "__main__":
    animation_data = preprocess_data(config.CSV_FILENAME)
    run_animation(animation_data)