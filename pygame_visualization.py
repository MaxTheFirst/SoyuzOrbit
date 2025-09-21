# pygame_visualization.py

import pygame
import sys
import numpy as np

# Импортируем физические константы из модуля симуляции
from simulation import R_earth, R_moon, R_earth_moon

# Настройки окна
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
WINDOW_TITLE = "Анимация полета на Луну"

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
RED = (255, 0, 0)


def animate_trajectory(solution):
    """
    Основная функция для запуска анимации Pygame.
    Принимает на вход результат работы solve_ivp.
    """
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # Масштабирование
    scale = SCREEN_WIDTH / (R_earth_moon * 1.1)
    offset_x = 50
    offset_y = SCREEN_HEIGHT // 2

    def to_screen_coords(x, y):
        screen_x = int(offset_x + x * scale)
        screen_y = int(offset_y - y * scale)
        return screen_x, screen_y

    # Подготовка объектов
    earth_pos = to_screen_coords(0, 0)
    earth_radius = int(R_earth * scale) if int(R_earth * scale) > 0 else 1

    moon_pos = to_screen_coords(R_earth_moon, 0)
    moon_radius = int(R_moon * scale) if int(R_moon * scale) > 0 else 1

    traj_x = solution.y[0]
    traj_y = solution.y[1]
    times = solution.t

    screen_points = [to_screen_coords(x, y) for x, y in zip(traj_x, traj_y)]

    # Основной цикл анимации
    running = True
    frame_index = 0
    animation_speed = 50

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        screen.fill(BLACK)

        # Отрисовка
        pygame.draw.circle(screen, BLUE, earth_pos, earth_radius)
        pygame.draw.circle(screen, GRAY, moon_pos, moon_radius)

        if frame_index > 1:
            pygame.draw.lines(screen, GREEN, False, screen_points[:frame_index], 1)

        if frame_index < len(screen_points):
            rocket_pos = screen_points[frame_index]
            pygame.draw.circle(screen, RED, rocket_pos, 3)

            flight_time_days = times[frame_index] / (3600 * 24)
            time_text = font.render(f"Время полета: {flight_time_days:.2f} дней", True, WHITE)
            screen.blit(time_text, (10, 10))

        frame_index += animation_speed
        if frame_index >= len(screen_points):
            frame_index = len(screen_points) - 1

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()