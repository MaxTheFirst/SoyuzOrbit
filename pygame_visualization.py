# pygame_visualization.py

import pygame
import sys
import numpy as np

from simulation import (
    RADIUS_EARTH, RADIUS_MOON, LEO_RADIUS,
    DISTANCE_EARTH_MOON, calculate_moon_position
)

# --- Настройки ---
INITIAL_WIDTH = 1200
INITIAL_HEIGHT = 800
WINDOW_TITLE = "Интерактивная симуляция полета на Луну"
# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LEO_BLUE = (173, 216, 230)


def animate_trajectory(simulation_result):
    pygame.init()

    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # --- Управление камерой ---
    # Начальный масштаб, чтобы видеть всю орбиту Луны
    initial_scale = screen.get_width() / (DISTANCE_EARTH_MOON * 2.2)

    # Динамические параметры камеры
    scale = initial_scale
    offset_x = screen.get_width() / 2
    offset_y = screen.get_height() / 2

    panning = False
    pan_start_pos = (0, 0)
    fullscreen = False

    # --- Подготовка данных траектории ---
    rocket_coords = np.array(simulation_result.y[:2].T)
    timestamps = simulation_result.t

    def reset_view():
        """Сбрасывает масштаб и положение камеры к начальным."""
        nonlocal scale, offset_x, offset_y
        w, h = screen.get_size()
        scale = w / (DISTANCE_EARTH_MOON * 2.2)
        offset_x = w / 2
        offset_y = h / 2

    # --- Основной цикл ---
    running = True
    frame_index = 0
    animation_speed = max(1, len(timestamps) // 500)
    paused = False

    while running:
        # --- Обработка событий (управление) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Изменение размера окна
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                reset_view()

            # Управление мышью
            elif event.type == pygame.MOUSEWHEEL:
                zoom_factor = 1.1 if event.y > 0 else 1 / 1.1
                mouse_x, mouse_y = pygame.mouse.get_pos()

                # Координаты мира под курсором до зума
                world_x_before = (mouse_x - offset_x) / scale
                world_y_before = (offset_y - mouse_y) / scale

                scale *= zoom_factor

                # Новые смещения, чтобы точка под курсором осталась на месте
                offset_x = mouse_x - world_x_before * scale
                offset_y = mouse_y + world_y_before * scale

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Левая кнопка мыши
                    panning = True
                    pan_start_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    dx, dy = event.pos[0] - pan_start_pos[0], event.pos[1] - pan_start_pos[1]
                    offset_x += dx
                    offset_y += dy
                    pan_start_pos = event.pos

            # Управление с клавиатуры
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:  # Полный экран
                    fullscreen = not fullscreen
                    if fullscreen:
                        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
                    reset_view()
                elif event.key == pygame.K_r:  # Сброс вида
                    reset_view()
                elif event.key == pygame.K_SPACE:  # Пауза
                    paused = not paused

        # --- Обновление анимации ---
        if not paused:
            frame_index += animation_speed
            if frame_index >= len(timestamps):
                frame_index = len(timestamps) - 1

        current_frame = int(frame_index)
        screen.fill(BLACK)

        # --- Отрисовка ---
        def to_screen_coords(pos_vec):
            screen_x = int(offset_x + pos_vec[0] * scale)
            screen_y = int(offset_y - pos_vec[1] * scale)
            return screen_x, screen_y

        # Орбита Луны
        moon_orbit_points = [
            to_screen_coords(np.array([DISTANCE_EARTH_MOON * np.cos(a), DISTANCE_EARTH_MOON * np.sin(a)])) for a in
            np.linspace(0, 2 * np.pi, 200)]
        pygame.draw.lines(screen, (40, 40, 40), True, moon_orbit_points, 1)

        # Орбита НОО
        # Рисуем, только если она больше 1 пикселя в радиусе
        if LEO_RADIUS * scale > 1:
            leo_points = [to_screen_coords(np.array([LEO_RADIUS * np.cos(a), LEO_RADIUS * np.sin(a)])) for a in
                          np.linspace(0, 2 * np.pi, 100)]
            pygame.draw.lines(screen, LEO_BLUE, True, leo_points, 1)

        # Земля
        earth_pos_screen = to_screen_coords(np.array([0, 0]))
        earth_radius_screen = max(1, int(RADIUS_EARTH * scale))
        pygame.draw.circle(screen, BLUE, earth_pos_screen, earth_radius_screen)

        # Траектория (рисуется вся, без хаков)
        if len(rocket_coords) > 1:
            screen_points = [to_screen_coords(p) for p in rocket_coords[:current_frame + 1]]
            if len(screen_points) > 1:
                pygame.draw.lines(screen, GREEN, False, screen_points, 2)

        # Луна
        current_time = timestamps[current_frame]
        moon_pos_world = calculate_moon_position(current_time)
        moon_pos_screen = to_screen_coords(np.array(moon_pos_world))
        moon_radius_screen = max(1, int(RADIUS_MOON * scale))
        pygame.draw.circle(screen, GRAY, moon_pos_screen, moon_radius_screen)

        # Ракета
        rocket_pos_screen = to_screen_coords(rocket_coords[current_frame])
        pygame.draw.circle(screen, RED, rocket_pos_screen, max(2, int(earth_radius_screen * 0.1)))

        # --- Интерфейс ---
        info_text = [
            f"Время: {(timestamps[current_frame] / (3600 * 24)):.2f} дней",
            "УПРАВЛЕНИЕ:",
            "  Колесо мыши - Масштаб",
            "  ЛКМ + Движение - Перемещение",
            "  Пробел - Пауза"
        ]
        if paused: info_text.append(" [ПАУЗА]")

        for i, line in enumerate(info_text):
            text_surface = font.render(line, True, WHITE)
            screen.blit(text_surface, (10, 10 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()