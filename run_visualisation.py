#!/usr/bin/env python
import pygame
import time

# Импорт бэкенда (должен быть первым)
from md_simulation.backend import np, to_cpu

# Импорт физики и настроек
from md_simulation.constants import k_B, m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step

# (plotting.py нам не нужен, мы рисуем сами)

# --- Настройки визуализации ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
SIM_WIDTH = 800  # Область для симуляции (оставляем 200px для UI)
UI_WIDTH = 200

# Количество частиц для отрисовки (из N)
N_VISUALIZED = 10000
# Сколько шагов физики делать между кадрами (ускоряем время)
STEPS_PER_FRAME = 20

# Цвета
COLOR_BG = (10, 10, 20)
COLOR_WALL = (100, 100, 100)
COLOR_PISTON = (200, 200, 200)
COLOR_PARTICLE = (0, 150, 255)
COLOR_TEXT = (255, 255, 255)


def scale_x(x_sim):
    """Конвертирует X-координату симуляции в X-координату экрана."""
    # Мы масштабируем симуляцию (от 0 до p.L) на ширину экрана
    # (p.L*2, т.к. поршень может уехать до L*2)
    return int(x_sim / (p.L * 2) * SIM_WIDTH)


def scale_y(y_sim):
    """Конвертирует Y-координату симуляции в Y-координату экрана."""
    return int(y_sim / p.L * SCREEN_HEIGHT)


def main():
    # --- 1. Инициализация Pygame ---
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Молекулярная Динамика")
    clock = pygame.time.Clock()
    font_s = pygame.font.SysFont("Consolas", 18)
    font_l = pygame.font.SysFont("Consolas", 24, bold=True)

    # --- 2. Инициализация Физики ---
    # (Берем N из parameters.py, хоть и рисуем N_VISUALIZED)
    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, p.piston_pos_initial, p.L)

    piston_pos = np.array(p.piston_pos_initial)
    piston_vel = np.array(0.0)
    piston_area = p.L * p.L  # 3D площадь, хоть и рисуем 2D

    # Аккумуляторы для статистики
    momentum_accumulator = 0.0
    stats_step_counter = 0

    # Переменные для UI
    last_T = p.T_initial
    last_P = 0.0
    last_V = piston_pos * piston_area

    running = True

    # --- 3. Главный цикл (Pygame) ---
    while running:
        # --- 3.1. Обработка событий ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- 3.2. Обновление Физики (несколько шагов) ---
        for _ in range(STEPS_PER_FRAME):
            pos, vel, momentum_transfer = simulation_step(
                pos, vel, piston_pos, piston_vel, p.L, p.dt, p.collision_prob
            )

            momentum_accumulator += momentum_transfer
            stats_step_counter += 1

            force_internal = momentum_transfer / p.dt
            force_external = p.P_external * piston_area
            force_net = force_internal - force_external

            piston_accel = force_net / p.piston_mass
            piston_vel += piston_accel * p.dt
            piston_pos += piston_vel * p.dt

            # (Важно: не даем поршню улететь или сломаться)
            if piston_pos < 1e-10:  # Не даем уйти в 0
                piston_pos = np.array(1e-10)
                piston_vel = np.array(0.0)

        # --- 3.3. Сбор статистики (раз в ~16мс) ---
        time_elapsed = p.dt * stats_step_counter
        force_internal_avg = momentum_accumulator / time_elapsed
        last_P = force_internal_avg / piston_area

        E_kin_total = 0.5 * m_Ar * np.sum(vel ** 2)
        last_T = (2 / 3) * E_kin_total / (p.N * k_B)

        last_V = piston_pos * piston_area

        # Сброс аккумуляторов
        momentum_accumulator = 0.0
        stats_step_counter = 0

        # --- 3.4. Отрисовка ---
        screen.fill(COLOR_BG)

        # --- A. Рисуем Область Симуляции ---
        sim_surface = screen.subsurface(pygame.Rect(0, 0, SIM_WIDTH, SCREEN_HEIGHT))

        # Рисуем стенки (Y-ось)
        pygame.draw.line(sim_surface, COLOR_WALL, (0, 0), (SIM_WIDTH, 0), 2)
        pygame.draw.line(sim_surface, COLOR_WALL, (0, SCREEN_HEIGHT - 1), (SIM_WIDTH, SCREEN_HEIGHT - 1), 2)
        # Рисуем заднюю стенку (X=0)
        pygame.draw.line(sim_surface, COLOR_WALL, (0, 0), (0, SCREEN_HEIGHT), 2)

        # Рисуем поршень
        piston_x_pixel = scale_x(to_cpu(piston_pos))
        pygame.draw.line(sim_surface, COLOR_PISTON, (piston_x_pixel, 0), (piston_x_pixel, SCREEN_HEIGHT), 5)

        # Рисуем N_VISUALIZED частиц
        # (Конвертируем с GPU в CPU только те, что будем рисовать)
        pos_to_draw = to_cpu(pos[:N_VISUALIZED])

        for i in range(N_VISUALIZED):
            # Берем (x, y) - 2D проекция
            x_px = scale_x(pos_to_draw[i, 0])
            y_px = scale_y(pos_to_draw[i, 1])

            # (Простая проверка, чтобы не рисовать за экраном)
            if x_px < SIM_WIDTH:
                pygame.draw.circle(sim_surface, COLOR_PARTICLE, (x_px, y_px), 2)

        # --- B. Рисуем UI (Панель статистики) ---
        ui_surface = screen.subsurface(pygame.Rect(SIM_WIDTH, 0, UI_WIDTH, SCREEN_HEIGHT))
        ui_surface.fill((30, 30, 40))  # Фон для UI

        y_offset = 20

        def draw_text(text, value, unit, font=font_s):
            nonlocal y_offset
            text_surf = font.render(text, True, (150, 150, 150))
            screen.blit(text_surf, (SIM_WIDTH + 15, y_offset))
            y_offset += 25

            if isinstance(value, float):
                val_str = f"{value:.2e}" if value < 1e-3 or value > 1e6 else f"{value:.2f}"
            else:
                val_str = str(value)

            val_surf = font_l.render(f"{val_str} {unit}", True, COLOR_TEXT)
            screen.blit(val_surf, (SIM_WIDTH + 15, y_offset))
            y_offset += 40

        draw_text("Температура ", to_cpu(last_T), "K")
        draw_text("Давление ", to_cpu(last_P), "Па")
        draw_text("Объем ", to_cpu(last_V), "м³")
        draw_text("Шаг (dt)", p.dt, "с")
        draw_text("N (всего)", p.N, "")
        draw_text("N (рисуем)", N_VISUALIZED, "")

        # --- 3.5. Обновление экрана ---
        pygame.display.flip()
        clock.tick(60)  # Ограничиваем до 60 FPS

    pygame.quit()


if __name__ == "__main__":
    main()
