# D2/visualisation_2d.py
import pygame
import pandas as pd
import numpy as np
import config  # Импортируем config из корневой папки
from D2.system_builder import build_system_2d  # Нам это нужно для получения equilibrium_positions
import sys

# --- НАСТРОЙКИ ВИЗУАЛИЗАЦИИ ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
BACKGROUND_COLOR = (10, 10, 10)  # Темный фон
PLAYBACK_SPEED_FPS = 60  # Скорость воспроизведения

# Глобальные переменные для размеров, чтобы не передавать их везде
NUM_Y = config.NUM_BLOCKS_Y
NUM_X = config.NUM_BLOCKS_X
CELL_WIDTH = SCREEN_WIDTH / NUM_X
CELL_HEIGHT = SCREEN_HEIGHT / NUM_Y


def get_color_heatmap(value_0_1: float) -> tuple:
    """
    Преобразует значение от 0.0 до 1.0 в цвет (Синий -> Зеленый -> Красный).
    """
    if value_0_1 < 0.0: value_0_1 = 0.0
    if value_0_1 > 1.0: value_0_1 = 1.0

    # Синий (0,0,255) -> Зеленый (0,255,0) -> Красный (255,0,0)
    if value_0_1 < 0.5:
        # От Синего к Зеленому
        g = int(255 * (value_0_1 * 2))
        b = int(255 * (1 - value_0_1 * 2))
        return tuple([0, g, b])
    else:
        # От Зеленого к Красному
        r = int(255 * ((value_0_1 - 0.5) * 2))
        g = int(255 * (1 - (value_0_1 - 0.5) * 2))
        return tuple([r, g, 0])


def preprocess_data_2d(filename: str) -> tuple:
    """
    Загружает CSV, обрабатывает его в "кадры" и находит макс. смещение.
    """
    print("Loading 2D simulation data...")
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден. Сначала запустите main.py.")
        sys.exit()

    if df.empty:
        print("Ошибка: CSV-файл пуст.")
        sys.exit()

    print("Re-building equilibrium grid to calculate displacements...")
    # Нам нужно знать равновесные позиции, чтобы рассчитать смещение
    try:
        (_, _, _,
         equilibrium_positions) = build_system_2d()  # (Y, X, 2)
    except Exception as e:
        print(f"Ошибка при вызове build_system_2d: {e}")
        print("Убедитесь, что config.py настроен правильно.")
        sys.exit()

    print("Processing data into animation frames...")
    timestamps = df['time'].unique()
    frames_data = []  # Будет хранить список 2D-массивов (Y, X)
    max_displacement = 0.0

    # Группируем по времени для быстрой обработки
    grouped = df.groupby('time')

    for time in timestamps:
        frame_df = grouped.get_group(time)

        # Воссоздаем (Y, X) сетки для pos_x и pos_y
        pos_x_grid = frame_df.pivot(index='block_y', columns='block_x', values='pos_x').values
        pos_y_grid = frame_df.pivot(index='block_y', columns='block_x', values='pos_y').values

        # Собираем их в (Y, X, 2) массив
        current_positions = np.stack((pos_x_grid, pos_y_grid), axis=-1)

        # Рассчитываем вектор смещения
        displacement_vectors = current_positions - equilibrium_positions

        # Рассчитываем величину смещения (Y, X)
        displacement_magnitudes = np.linalg.norm(displacement_vectors, axis=2)

        frames_data.append(displacement_magnitudes)

        # Находим максимальное смещение во всей симуляции для
        # нормализации цвета (чтобы 1.0 = красный = макс. смещение)
        current_max = displacement_magnitudes.max()
        if current_max > max_displacement:
            max_displacement = current_max

    if max_displacement == 0:
        print("Warning: Max displacement is 0. Setting to 1.0 to avoid division by zero.")
        max_displacement = 1.0

    print(f"Data ready. Found {len(frames_data)} frames. Max displacement: {max_displacement:.4f} m")
    return timestamps, frames_data, max_displacement


def run_animation_2d(timestamps: list, frames_data: list, max_displacement: float):
    """
    Основной цикл Pygame для отрисовки 2D-анимации (вид сверху).
    """
    pygame.init()
    pygame.font.init()

    font = pygame.font.Font(None, 32)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)
    pygame.display.set_caption("2D Продольные волны (Вид сверху) | 'Q' - выход")
    clock = pygame.time.Clock()

    frames_iterator = iter(zip(timestamps, frames_data))
    running = True
    animation_finished = False

    try:
        current_time, current_frame = next(frames_iterator)
    except StopIteration:
        print("Ошибка: Нет кадров для анимации.")
        return

    while running:
        if not animation_finished:
            try:
                current_time, current_frame = next(frames_iterator)
            except StopIteration:
                animation_finished = True
                print("Animation finished. View is now static. Press 'Q' or close window to exit.")

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                running = False

        # --- Отрисовка ---
        screen.fill(BACKGROUND_COLOR)

        # Рисуем сетку
        for y in range(NUM_Y):
            for x in range(NUM_X):
                # 1. Получаем смещение и нормализуем его
                magnitude = current_frame[y, x]
                normalized_mag = magnitude / max_displacement

                # 2. Получаем цвет
                color = get_color_heatmap(normalized_mag)

                # 3. Рисуем прямоугольник
                rect = pygame.Rect(x * CELL_WIDTH, y * CELL_HEIGHT,
                                   CELL_WIDTH, CELL_HEIGHT)
                pygame.draw.rect(screen, color, rect)

        # Выводим время
        time_surface = font.render(f"Time: {current_time:.2f} s", True, (255, 255, 255))
        screen.blit(time_surface, (20, 20))

        pygame.display.flip()
        clock.tick(PLAYBACK_SPEED_FPS)

    pygame.quit()