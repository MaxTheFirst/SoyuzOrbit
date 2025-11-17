#!/usr/bin/env python
import pygame
import time

# Импорт бэкенда (должен быть первым)
from md_simulation.backend import np, to_cpu

# Импорт физики и настроек
from md_simulation.constants import k_B, m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step

# --- Настройки визуализации ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
SIM_WIDTH = 800  # Область для симуляции
UI_WIDTH = 200

N_VISUALIZED = 500
STEPS_PER_FRAME = 20

# Цвета
COLOR_BG = (10, 10, 20)
COLOR_WALL = (100, 100, 100)
COLOR_PISTON = (200, 200, 200)
COLOR_PARTICLE = (0, 150, 255)
COLOR_TEXT = (255, 255, 255)


def get_scale_factor(piston_pos_cpu):
    world_max_dim = max(piston_pos_cpu * 1.1, p.L)
    scale = min(SIM_WIDTH / world_max_dim, SCREEN_HEIGHT / world_max_dim)
    return scale


def scale(sim_coord, scale_factor):
    return int(sim_coord * scale_factor)


def main():
    # --- 1. Инициализация Pygame ---
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Молекулярная Динамика")
    clock = pygame.time.Clock()
    font_s = pygame.font.SysFont("Consolas", 18)
    font_l = pygame.font.SysFont("Consolas", 24, bold=True)

    # --- 2. Инициализация Физики ---
    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, p.piston_pos_initial, p.L)

    piston_pos = np.array(p.piston_pos_initial)
    piston_vel = np.array(0.0)
    piston_area = p.L * p.L

    momentum_accumulator = 0.0
    stats_step_counter = 0

    # --- Переменные для UI ---
    last_T = p.T_initial
    last_P = 0.0
    last_V = piston_pos * piston_area

    # --- НОВЫЕ переменные для UI ---
    work_external_total = 0.0
    U_gas = (3 / 2) * p.N * k_B * p.T_initial
    K_piston = 0.0
    E_total_initial = U_gas + K_piston  # Сохраняем E вначале
    E_total_current = E_total_initial
    ideal_gas_ratio = 1.0
    adiabat_const = 0.0

    running = True

    # --- 3. Главный цикл (Pygame) ---
    while running:
        # --- 3.1. Обработка событий ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- 3.2. Обновление Физики (несколько шагов) ---
        for _ in range(STEPS_PER_FRAME):
            # Аккумулируем работу W_ext = -P_ext * dV
            piston_pos_step_old = piston_pos

            pos, vel, momentum_transfer = simulation_step(
                pos, vel, piston_pos, piston_vel, p.L, p.dt
            )

            momentum_accumulator += momentum_transfer
            stats_step_counter += 1

            force_internal = momentum_transfer / p.dt
            force_external = p.P_external * piston_area
            force_net = force_internal - force_external

            piston_accel = force_net / p.piston_mass
            piston_vel += piston_accel * p.dt
            piston_pos += piston_vel * p.dt

            # --- НОВОЕ: Накопление работы ---
            delta_V_step = (piston_pos - piston_pos_step_old) * piston_area
            work_external_total += -p.P_external * delta_V_step

            if piston_pos < 1e-10:
                piston_pos = np.array(1e-10)
                piston_vel = np.array(0.0)

        # --- 3.3. Сбор статистики (раз в ~16мс) ---
        time_elapsed = p.dt * stats_step_counter
        last_P = (momentum_accumulator / time_elapsed) / piston_area
        E_kin_total = 0.5 * m_Ar * np.sum(vel ** 2)
        last_T = (2 / 3) * E_kin_total / (p.N * k_B)
        last_V = piston_pos * piston_area

        # --- НОВЫЕ расчеты для UI ---
        U_gas = E_kin_total
        K_piston = 0.5 * p.piston_mass * (piston_vel ** 2)
        E_total_current = U_gas + K_piston

        if last_T > 1e-6:
            ideal_gas_ratio = (last_P * last_V) / (p.N * k_B * last_T)

        adiabat_const = last_P * (last_V ** p.GAMMA)

        # Сброс аккумуляторов
        momentum_accumulator = 0.0
        stats_step_counter = 0

        # --- 3.4. Отрисовка ---
        screen.fill(COLOR_BG)

        # --- A. Рисуем Область Симуляции ---
        sim_surface = screen.subsurface(pygame.Rect(0, 0, SIM_WIDTH, SCREEN_HEIGHT))
        piston_pos_cpu = to_cpu(piston_pos)
        scale_factor = get_scale_factor(piston_pos_cpu)

        wall_y_px = scale(p.L, scale_factor)
        pygame.draw.line(sim_surface, COLOR_WALL, (0, 0), (SIM_WIDTH, 0), 2)
        pygame.draw.line(sim_surface, COLOR_WALL, (0, wall_y_px), (SIM_WIDTH, wall_y_px), 2)
        pygame.draw.line(sim_surface, COLOR_WALL, (0, 0), (0, SCREEN_HEIGHT), 2)

        piston_x_pixel = scale(piston_pos_cpu, scale_factor)
        pygame.draw.line(sim_surface, COLOR_PISTON, (piston_x_pixel, 0), (piston_x_pixel, wall_y_px), 5)

        pos_to_draw = to_cpu(pos[:N_VISUALIZED])
        for i in range(N_VISUALIZED):
            x_px = scale(pos_to_draw[i, 0], scale_factor)
            y_px = scale(pos_to_draw[i, 1], scale_factor)
            if x_px < SIM_WIDTH and y_px < SCREEN_HEIGHT:
                pygame.draw.circle(sim_surface, COLOR_PARTICLE, (x_px, y_px), 2)

        # --- B. Рисуем UI (Панель статистики) ---
        ui_surface = screen.subsurface(pygame.Rect(SIM_WIDTH, 0, UI_WIDTH, SCREEN_HEIGHT))
        ui_surface.fill((30, 30, 40))

        y_offset = 20

        def draw_text(text, value, unit, font=font_s):
            nonlocal y_offset
            text_surf = font.render(text, True, (150, 150, 150))
            screen.blit(text_surf, (SIM_WIDTH + 15, y_offset))
            y_offset += 20  # Уменьшаем, чтобы влезло

            if isinstance(value, (float, np.ndarray)):
                val_cpu = to_cpu(value)
                val_str = f"{val_cpu:.2e}" if (abs(val_cpu) < 1e-3 or abs(
                    val_cpu) > 1e6) and val_cpu != 0 else f"{val_cpu:.2f}"
            else:
                val_str = str(value)

            val_surf = font_l.render(f"{val_str} {unit}", True, COLOR_TEXT)
            screen.blit(val_surf, (SIM_WIDTH + 15, y_offset))
            y_offset += 30  # Уменьшаем

        # --- Блок 1: Основные ---
        draw_text("Температура ", last_T, "K")
        draw_text("Давление ", last_P, "Па")
        draw_text("Объем ", last_V, "м³")

        # --- Блок 2: Проверка Законов ---
        draw_text("(PV)/(NkT) [~1.0]", ideal_gas_ratio, "")
        draw_text("PV^gamma [const]", adiabat_const, "")

        # --- Блок 3: Проверка Энергии ---
        draw_text("E_total (U+K)", E_total_current, "Дж")
        draw_text("E_initial + W_ext", E_total_initial + work_external_total, "Дж")
        draw_text("U (Газ)", U_gas, "Дж")
        draw_text("K (Поршень)", K_piston, "Дж")

        # --- 3.5. Обновление экрана ---
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()