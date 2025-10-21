# D2/visualisation_2d_realistic.py
import pygame
import pandas as pd
import numpy as np
import config
from D2.system_builder import build_system_2d
import sys
from typing import Tuple

# --- НАСТРОЙКИ ВИЗУАЛИЗАЦИИ ---
FULLSCREEN = False
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
BACKGROUND_COLOR = (10, 20, 30)
BLOCK_COLOR = (100, 150, 255)
SPRING_COLOR = (80, 80, 80)
WALL_COLOR = (200, 200, 200)
TEXT_COLOR = (230, 230, 230)
PLAYBACK_SPEED_FPS = 60

# --- Размеры сетки ---
NUM_Y = config.NUM_BLOCKS_Y
NUM_X = config.NUM_BLOCKS_X


def preprocess_data_2d_realistic(filename: str) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """
    Загружает CSV и преобразует его в 2 таблицы (DataFrame):
    для X-позиций и Y-позиций.
    Также возвращает сетку равновесных положений.
    """
    print("Loading 2D simulation data for realistic view...")
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден. Сначала запустите main.py.")
        sys.exit()

    print("Pivoting data for x and y positions...")
    # Создаем отдельные таблицы для x и y,
    # где колонки - это MultiIndex (block_y, block_x)
    pos_x_df = df.pivot(index='time', columns=['block_y', 'block_x'], values='pos_x')
    pos_y_df = df.pivot(index='time', columns=['block_y', 'block_x'], values='pos_y')

    print("Building equilibrium grid for world boundaries...")
    # Нам нужно равновесие для расчета "границ" мира
    try:
        (_, _, _,
         equilibrium_positions) = build_system_2d()  # (Y, X, 2)
    except Exception as e:
        print(f"Ошибка при вызове build_system_2d: {e}")
        sys.exit()

    print("Data ready.")
    return pos_x_df, pos_y_df, equilibrium_positions


def run_animation_2d_realistic(pos_x_df: pd.DataFrame, pos_y_df: pd.DataFrame,
                               equilibrium_positions: np.ndarray):
    """Основной цикл Pygame для отрисовки 2D-анимации (вид сверху)."""
    pygame.init()
    pygame.font.init()

    font = pygame.font.Font(None, 32)

    flags = pygame.SCALED | pygame.RESIZABLE
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    pygame.display.set_caption(
        "2D Волна (Реалистичный вид) | ЛКМ+Перемещение - панорама | Колесо мыши - зум | 'Q' - выход")
    clock = pygame.time.Clock()

    # --- Логика камеры (из 1D) ---

    # Рассчитываем общий размер мира
    total_world_width = (NUM_X + 1) * config.DEFAULT_BLOCK_SPACING
    total_world_height = (NUM_Y + 1) * config.DEFAULT_BLOCK_SPACING

    current_zoom = 1.0
    pan_offset_x = 0.0
    pan_offset_y = 0.0
    is_panning = False

    running = True
    animation_finished = False

    pos_x_iterator = pos_x_df.iterrows()
    pos_y_iterator = pos_y_df.iterrows()

    # Загружаем первый кадр
    try:
        timestamp, pos_x_series = next(pos_x_iterator)
        _, pos_y_series = next(pos_y_iterator)
    except StopIteration:
        print("Нет данных для анимации.")
        return

    while running:
        if not animation_finished:
            try:
                timestamp, pos_x_series = next(pos_x_iterator)
                _, pos_y_series = next(pos_y_iterator)
            except StopIteration:
                animation_finished = True
                print("Animation finished. View is now static. Press 'Q' or close window to exit.")

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                pygame.display.toggle_fullscreen()
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    current_zoom *= 1.1
                elif event.y < 0:
                    current_zoom /= 1.1
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                is_panning = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                is_panning = False
            if event.type == pygame.MOUSEMOTION and is_panning:
                pan_offset_x += event.rel[0]
                pan_offset_y += event.rel[1]  # Добавляем панорамирование по Y

        # --- Отрисовка ---
        screen.fill(BACKGROUND_COLOR)

        # --- Расчет масштаба и смещений (из 1D, адаптировано) ---
        effective_screen_width = screen.get_width()
        effective_screen_height = screen.get_height()

        # Масштабируем по меньшей стороне, чтобы все влезло
        base_scale_x = effective_screen_width / total_world_width
        base_scale_y = effective_screen_height / total_world_height
        base_scale = min(base_scale_x, base_scale_y) * 0.9  # 0.9 для отступов

        final_scale = base_scale * current_zoom
        block_radius = max(1, int(3 * current_zoom))

        # Центрирование + панорамирование
        centering_offset_x = (effective_screen_width - (total_world_width * final_scale)) / 2
        centering_offset_y = (effective_screen_height - (total_world_height * final_scale)) / 2
        view_offset_x = centering_offset_x + pan_offset_x
        view_offset_y = centering_offset_y + pan_offset_y

        # --- Функция-хелпер для конвертации мировых координат в экранные ---
        def to_screen(world_x: float, world_y: float) -> Tuple[int, int]:
            screen_x = int(world_x * final_scale + view_offset_x)
            screen_y = int(world_y * final_scale + view_offset_y)
            return screen_x, screen_y

        # --- Сохраняем экранные позиции всех блоков ---
        # Это MultiIndex Series. Преобразуем в (Y, X, 2) массив.
        screen_pos = np.zeros((NUM_Y, NUM_X, 2), dtype=int)

        # (y, x) это MultiIndex (y, x)
        for (y, x), wx in pos_x_series.items():
            wy = pos_y_series[(y, x)]
            screen_pos[y, x] = to_screen(wx, wy)

        # --- Отрисовка ---

        # 1. Стены (рисуем рамку)
        sw_top_left = to_screen(0, 0)
        sw_bottom_right = to_screen(total_world_width, total_world_height)
        pygame.draw.rect(screen, WALL_COLOR,
                         (sw_top_left[0], sw_top_left[1],
                          sw_bottom_right[0] - sw_top_left[0],
                          sw_bottom_right[1] - sw_top_left[1]), 2)

        # 2. Пружины
        # Горизонтальные (Y, X+1)
        for y in range(NUM_Y):
            # Пружина к левой стене (стена на (0, y_eq))
            p_wall = to_screen(0, equilibrium_positions[y, 0, 1])
            p_block = screen_pos[y, 0]
            pygame.draw.line(screen, SPRING_COLOR, p_wall, p_block, 1)

            # Пружины между блоками
            for x in range(NUM_X - 1):
                p1 = screen_pos[y, x]
                p2 = screen_pos[y, x + 1]
                pygame.draw.line(screen, SPRING_COLOR, p1, p2, 1)

            # Пружина к правой стене (стена на (world_width, y_eq))
            p_block = screen_pos[y, -1]
            p_wall = to_screen(total_world_width, equilibrium_positions[y, -1, 1])
            pygame.draw.line(screen, SPRING_COLOR, p_block, p_wall, 1)

        # Вертикальные (Y+1, X)
        for x in range(NUM_X):
            # Пружина к верхней стене (стена на (x_eq, 0))
            p_wall = to_screen(equilibrium_positions[0, x, 0], 0)
            p_block = screen_pos[0, x]
            pygame.draw.line(screen, SPRING_COLOR, p_wall, p_block, 1)

            # Пружины между блоками
            for y in range(NUM_Y - 1):
                p1 = screen_pos[y, x]
                p2 = screen_pos[y + 1, x]
                pygame.draw.line(screen, SPRING_COLOR, p1, p2, 1)

            # Пружина к нижней стене (стена на (x_eq, world_height))
            p_block = screen_pos[-1, x]
            p_wall = to_screen(equilibrium_positions[-1, x, 0], total_world_height)
            pygame.draw.line(screen, SPRING_COLOR, p_block, p_wall, 1)

        # 3. Блоки (рисуем поверх пружин)
        for y in range(NUM_Y):
            for x in range(NUM_X):
                pos = screen_pos[y, x]
                pygame.draw.circle(screen, BLOCK_COLOR, pos, block_radius)

        # --- Текст ---
        time_surface = font.render(f"Time: {timestamp:.2f} s", True, TEXT_COLOR)
        screen.blit(time_surface, (20, 20))

        pygame.display.flip()
        clock.tick(PLAYBACK_SPEED_FPS)

    pygame.quit()