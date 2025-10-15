# visualize.py (с отображением скорости и ускорения)

import pygame
import pandas as pd
import numpy as np
import config
import sys
from typing import Tuple

# --- НАСТРОЙКИ ВИЗУАЛИЗАЦИИ ---
FULLSCREEN = False
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 500
BACKGROUND_COLOR = (10, 20, 30)
BLOCK_COLOR = (100, 150, 255)
SPRING_COLOR = (80, 80, 80)
WALL_COLOR = (200, 200, 200)
TEXT_COLOR = (230, 230, 230)
Y_POSITION = SCREEN_HEIGHT // 2
PLAYBACK_SPEED_FPS = 60


def preprocess_data(filename: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Загружает CSV и преобразует его в 3 таблицы (DataFrame):
    для позиций, скоростей и ускорений.
    """
    print("Loading simulation data...")
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден. Сначала запустите main.py.")
        sys.exit()

    print("Processing data for animation...")
    positions_df = df.pivot_table(index='time', columns='block_index', values='position')
    velocities_df = df.pivot_table(index='time', columns='block_index', values='velocity')
    accelerations_df = df.pivot_table(index='time', columns='block_index', values='acceleration')
    print("Data ready.")
    return positions_df, velocities_df, accelerations_df


def run_animation(positions_df: pd.DataFrame, spacings: list[float], velocities_df: pd.DataFrame,
                  accelerations_df: pd.DataFrame):
    """Основной цикл Pygame для отрисовки анимации."""
    pygame.init()
    pygame.font.init()

    font = pygame.font.Font(None, 32)

    flags = pygame.SCALED
    if FULLSCREEN:
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    pygame.display.set_caption(
        "Волна | ЛКМ+Перемещение - панорама | Колесо мыши - зум | 'F' - полный экран | 'Q' - выход")
    clock = pygame.time.Clock()

    equilibrium_positions = np.cumsum(spacings[:config.NUM_BLOCKS])

    total_chain_length = sum(spacings)

    current_zoom = config.VISUALIZATION_SCALE
    pan_offset_x = 0.0
    is_panning = False

    running = True
    animation_finished = False

    # Создаем итераторы для всех трех таблиц
    positions_iterator = positions_df.iterrows()
    velocities_iterator = velocities_df.iterrows()
    accelerations_iterator = accelerations_df.iterrows()

    # Загружаем первый кадр для всех
    timestamp, positions = next(positions_iterator)
    _, velocities = next(velocities_iterator)
    _, accelerations = next(accelerations_iterator)

    while running:
        if not animation_finished:
            try:
                timestamp, positions = next(positions_iterator)
                _, velocities = next(velocities_iterator)
                _, accelerations = next(accelerations_iterator)
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

        # --- НОВЫЙ БЛОК: Расчёт всех максимальных значений ---
        displacements = positions.values - equilibrium_positions
        current_amplitude = np.abs(displacements).max()
        current_max_velocity = np.abs(velocities.values).max()
        current_max_acceleration = np.abs(accelerations.values).max()

        # --- Отрисовка ---
        screen.fill(BACKGROUND_COLOR)

        # ... (расчёт масштабов и смещений остаётся прежним) ...
        effective_screen_width = screen.get_width()
        base_padding = 80
        chain_scale = (effective_screen_width - 2 * base_padding) / total_chain_length
        final_scale = chain_scale * current_zoom
        block_radius = max(1, int(5 * current_zoom))
        wall_thickness = max(2, int(4 * current_zoom))
        centering_offset = (effective_screen_width - (total_chain_length * final_scale)) / 2
        view_offset = centering_offset + pan_offset_x

        # --- Подготовка всего текста для вывода ---
        time_surface = font.render(f"Time: {timestamp:.2f} s", True, TEXT_COLOR)
        amplitude_surface = font.render(f"Max Displacement: {current_amplitude:.4f} m", True, TEXT_COLOR)
        velocity_surface = font.render(f"Max Velocity: {current_max_velocity:.4f} m/s", True, TEXT_COLOR)
        acceleration_surface = font.render(f"Max Acceleration: {current_max_acceleration:.4f} m/s²", True, TEXT_COLOR)

        # код отрисовки геометрии остаётся прежним
        left_wall_x = view_offset
        right_wall_x = view_offset + (total_chain_length * final_scale)
        pygame.draw.line(screen, WALL_COLOR, (left_wall_x, Y_POSITION - 20 * current_zoom),
                         (left_wall_x, Y_POSITION + 20 * current_zoom), wall_thickness)
        pygame.draw.line(screen, WALL_COLOR, (right_wall_x, Y_POSITION - 20 * current_zoom),
                         (right_wall_x, Y_POSITION + 20 * current_zoom), wall_thickness)
        screen_positions = [view_offset + (p * final_scale) for p in positions]
        pygame.draw.line(screen, SPRING_COLOR, (left_wall_x, Y_POSITION), (screen_positions[0], Y_POSITION), 1)
        for i in range(len(screen_positions) - 1):
            pygame.draw.line(screen, SPRING_COLOR, (screen_positions[i], Y_POSITION),
                             (screen_positions[i + 1], Y_POSITION), 1)
        pygame.draw.line(screen, SPRING_COLOR, (screen_positions[-1], Y_POSITION), (right_wall_x, Y_POSITION), 1)
        for x_pos in screen_positions:
            pygame.draw.circle(screen, BLOCK_COLOR, (x_pos, Y_POSITION), block_radius)

        # --- Вывод всего текста на экран ---
        screen.blit(time_surface, (20, 20))
        screen.blit(amplitude_surface, (20, 50))
        screen.blit(velocity_surface, (20, 80))
        screen.blit(acceleration_surface, (20, 110))

        pygame.display.flip()
        clock.tick(PLAYBACK_SPEED_FPS)

    pygame.quit()