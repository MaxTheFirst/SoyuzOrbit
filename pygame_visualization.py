# pygame_visualization.py

import pygame
import sys
import numpy as np

from simulation import RADIUS_EARTH, RADIUS_MOON, DISTANCE_EARTH_MOON, calculate_moon_position

# --- Настройки ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
WINDOW_TITLE = "Анимация полета на Луну"
# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
RED = (255, 0, 0)


def animate_trajectory(simulation_result):
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    scale = SCREEN_WIDTH / (DISTANCE_EARTH_MOON * 2.2)
    offset_x = SCREEN_WIDTH // 2
    offset_y = SCREEN_HEIGHT // 2

    def to_screen_coords(x, y):
        screen_x = int(offset_x + x * scale)
        screen_y = int(offset_y - y * scale)
        return screen_x, screen_y

    earth_pos = to_screen_coords(0, 0)

    MIN_EARTH_RADIUS_PX = 20
    MIN_MOON_RADIUS_PX = 8

    earth_radius_screen = max(int(RADIUS_EARTH * scale), MIN_EARTH_RADIUS_PX)

    orbit_points = []
    for angle in np.linspace(0, 2 * np.pi, 200):
        orbit_x = DISTANCE_EARTH_MOON * np.cos(angle)
        orbit_y = DISTANCE_EARTH_MOON * np.sin(angle)
        orbit_points.append(to_screen_coords(orbit_x, orbit_y))

    rocket_x_coords = simulation_result.y[0]
    rocket_y_coords = simulation_result.y[1]
    timestamps = simulation_result.t

    screen_trajectory_points = [to_screen_coords(x, y) for x, y in zip(rocket_x_coords, rocket_y_coords)]

    ### ИЗМЕНЕНО: Находим кадр ВИЗУАЛЬНОГО СТАРТА ###
    visual_launch_frame = 0
    for i in range(len(screen_trajectory_points)):
        rocket_pos_screen = screen_trajectory_points[i]
        distance_from_earth_center_pixels = np.hypot(rocket_pos_screen[0] - earth_pos[0],
                                                     rocket_pos_screen[1] - earth_pos[1])
        # Как только ракета оказывается снаружи видимого круга Земли, это наш старт
        if distance_from_earth_center_pixels > earth_radius_screen:
            visual_launch_frame = i
            break

    # Находим кадр визуального столкновения с Луной (как и раньше)
    visual_impact_frame = -1
    for i in range(len(timestamps)):
        moon_x, moon_y = calculate_moon_position(timestamps[i])
        moon_pos_screen = to_screen_coords(moon_x, moon_y)
        moon_radius_screen = max(int(RADIUS_MOON * scale), MIN_MOON_RADIUS_PX)
        rocket_pos_screen = screen_trajectory_points[i]
        distance_pixels = np.hypot(rocket_pos_screen[0] - moon_pos_screen[0], rocket_pos_screen[1] - moon_pos_screen[1])
        if distance_pixels <= moon_radius_screen:
            visual_impact_frame = i
            break

    running = True
    # Начинаем анимацию с кадра визуального старта
    frame_index = visual_launch_frame
    animation_speed = max(1, len(timestamps) // 500)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        screen.fill(BLACK)

        current_frame = int(frame_index)

        # Замораживаем анимацию при визуальном контакте с Луной
        if visual_impact_frame != -1 and current_frame >= visual_impact_frame:
            current_frame = visual_impact_frame
        else:
            frame_index += animation_speed
            if frame_index >= len(timestamps):
                frame_index = len(timestamps) - 1
            current_frame = int(frame_index)

        # Отрисовка
        pygame.draw.lines(screen, (40, 40, 40), True, orbit_points, 1)
        pygame.draw.circle(screen, BLUE, earth_pos, earth_radius_screen)

        # Рисуем хвост, начиная от кадра визуального старта
        if current_frame > visual_launch_frame:
            pygame.draw.lines(screen, GREEN, False, screen_trajectory_points[visual_launch_frame:current_frame + 1], 1)

        current_time = timestamps[current_frame]
        moon_x, moon_y = calculate_moon_position(current_time)
        moon_pos = to_screen_coords(moon_x, moon_y)
        moon_radius = max(int(RADIUS_MOON * scale), MIN_MOON_RADIUS_PX)
        pygame.draw.circle(screen, GRAY, moon_pos, moon_radius)

        rocket_pos = screen_trajectory_points[current_frame]
        pygame.draw.circle(screen, RED, rocket_pos, 3)

        flight_time_days = timestamps[current_frame] / (3600 * 24)
        time_text = font.render(f"Время полета: {flight_time_days:.2f} дней", True, WHITE)
        screen.blit(time_text, (10, 10))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()