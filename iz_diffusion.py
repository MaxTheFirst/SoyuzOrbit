#!/usr/bin/env python
import pygame
import time

# Импорты
from md_simulation.backend import np, to_cpu
from md_simulation.constants import m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step

# --- Настройки ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
N_VISUALIZED = 1000  # Рисуем 1000 частиц для ясности

# Цвета
COLOR_BG = (15, 15, 20)
COLOR_LEFT = (255, 80, 80)  # Красные (были слева)
COLOR_RIGHT = (80, 150, 255)  # Синие (были справа)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Визуализация Диффузии")
    clock = pygame.time.Clock()

    # 1. Инициализация
    # Фиксируем поршень, чтобы объем был постоянным для чистоты эксперимента
    fixed_L = p.L
    piston_pos = np.array(fixed_L)
    piston_vel = np.array(0.0)

    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, fixed_L, p.L)

    # --- САМОЕ ВАЖНОЕ: Назначаем цвета по начальному положению ---
    # Мы делаем это один раз в начале. Массив цветов не меняется, меняются позиции частиц.
    pos_cpu_init = to_cpu(pos)
    particle_colors = []

    # Центр ящика по X
    center_x = fixed_L / 2.0

    for i in range(N_VISUALIZED):
        if pos_cpu_init[i, 0] < center_x:
            particle_colors.append(COLOR_LEFT)  # Те, кто начал слева
        else:
            particle_colors.append(COLOR_RIGHT)  # Те, кто начал справа
    # -------------------------------------------------------------

    scale_factor = SCREEN_WIDTH / (fixed_L * 1.1)  # Чуть с запасом

    running = True
    print(f"Эксперимент начат. Вероятность столкновений: {p.collision_prob}")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. Физика (делаем 10 шагов за кадр для плавности)
        for _ in range(10):
            # Передаем фиксированный piston_pos, он не двигается
            pos, vel, _ = simulation_step(
                pos, vel, piston_pos, piston_vel, p.L, p.dt, collision_prob=p.collision_prob
            )

        # 3. Отрисовка
        screen.fill(COLOR_BG)

        # Рисуем границы ящика
        box_w = int(fixed_L * scale_factor)
        box_h = int(p.L * scale_factor)
        pygame.draw.rect(screen, (100, 100, 100), (0, 0, box_w, box_h), 2)

        # Рисуем разделительную линию (центр), где была "перегородка"
        mid_x = int(center_x * scale_factor)
        pygame.draw.line(screen, (50, 50, 50), (mid_x, 0), (mid_x, box_h), 1)

        # Рисуем частицы
        pos_draw = to_cpu(pos[:N_VISUALIZED])

        for i in range(N_VISUALIZED):
            x = int(pos_draw[i, 0] * scale_factor)
            y = int(pos_draw[i, 1] * scale_factor)

            # Рисуем только если внутри экрана
            if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT:
                pygame.draw.circle(screen, particle_colors[i], (x, y), 3)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()