#!/usr/bin/env python
import pygame
import time

# Импорты
from md_simulation.backend import np, to_cpu
from md_simulation.constants import k_B, m_Ar, m_He
from md_simulation import config as p
from md_simulation.simulation import simulation_step

# --- Настройки Визуализации ---
SCREEN_WIDTH = 1000  # Чуть шире для текста
SCREEN_HEIGHT = 600
SIM_WIDTH = 800  # Ширина зоны симуляции
N_VISUALIZED = 1500  # Сколько частиц рисовать

# Цвета
COLOR_BG = (15, 15, 20)
COLOR_UI_BG = (30, 30, 40)
COLOR_AR = (80, 100, 255)  # Аргон (Синий, Тяжелый)
COLOR_HE = (255, 80, 80)  # Гелий (Красный, Легкий)
COLOR_TEXT = (220, 220, 220)
COLOR_LINE = (100, 100, 100)


def initialize_mixture(N, T, m1, m2, L):
    """Создаем смесь: Слева (0..N/2) - Тяжелый, Справа - Легкий"""
    pos = np.random.rand(N, 3) * np.array([L, L, L])

    # Расставляем: Аргон (0..N/2) слева, Гелий (N/2..N) справа
    half = N // 2
    pos[:half, 0] *= 0.5  # Сжимаем Аргон в левую половину (0 - L/2)
    pos[half:, 0] = L / 2 + pos[half:, 0] * 0.5  # Сдвигаем Гелий в правую (L/2 - L)

    # Массы
    masses = np.zeros(N)
    masses[:half] = m1
    masses[half:] = m2

    # Скорости (V ~ 1/sqrt(m))
    vel = np.zeros((N, 3))
    v_std1 = np.sqrt(k_B * T / m1)
    vel[:half] = np.random.normal(scale=v_std1, size=(half, 3))

    v_std2 = np.sqrt(k_B * T / m2)
    vel[half:] = np.random.normal(scale=v_std2, size=(N - half, 3))

    vel -= np.mean(vel, axis=0)
    return pos, vel, masses


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Визуализация: Смесь Газов (Ar + He)")
    clock = pygame.time.Clock()

    # --- ИСПРАВЛЕНИЕ ШРИФТОВ (Arial вместо Consolas) ---
    # Arial есть почти везде и поддерживает кириллицу
    try:
        font = pygame.font.SysFont("Arial", 16)
        font_large = pygame.font.SysFont("Arial", 20, bold=True)
    except:
        # Резервный вариант, если что-то пойдет не так
        font = pygame.font.SysFont(None, 24)
        font_large = pygame.font.SysFont(None, 32)

    # 1. Инициализация Физики
    fixed_L = p.L
    piston_pos = np.array(fixed_L)
    piston_vel = np.array(0.0)

    print("Инициализация смеси...")
    pos, vel, masses = initialize_mixture(p.N, p.T_initial, m_Ar, m_He, fixed_L)

    # --- Подготовка индексов для отрисовки ---
    viz_indices = np.linspace(0, p.N - 1, N_VISUALIZED, dtype=int)

    # Определяем цвета для этих визуализируемых частиц ЗАРАНЕЕ
    viz_colors = []
    half_idx = p.N // 2
    for idx in viz_indices:
        if idx < half_idx:
            viz_colors.append(COLOR_AR)
        else:
            viz_colors.append(COLOR_HE)

    # Масштабирование
    scale_factor = SIM_WIDTH / (fixed_L * 1.05)

    # Переменные для статистики
    sim_time = 0.0
    step_count = 0
    he_crossed_percent = 0.0  # Сколько гелия ушло налево

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. Физика (20 шагов за кадр для скорости)
        steps_per_frame = 20
        for _ in range(steps_per_frame):
            # ВАЖНО: передаем masses!
            pos, vel, _ = simulation_step(
                pos, vel, piston_pos, piston_vel, p.L, p.dt,
                collision_prob=0.8,  # Ставим высокую плотность для наглядности диффузии
                masses=masses
            )
            sim_time += p.dt
            step_count += 1

        # 3. Расчет статистики (раз в кадр)
        # Считаем, сколько Гелия (индексы >= half_idx) находится СЛЕВА (x < L/2)
        he_pos_x = pos[half_idx::100, 0]
        count_he_left = np.sum(he_pos_x < fixed_L / 2)
        total_he_sample = len(he_pos_x)
        he_crossed_percent = (count_he_left / total_he_sample) * 100.0

        # 4. Отрисовка
        screen.fill(COLOR_BG)

        # --- Зона симуляции ---
        # Рисуем ящик
        box_w = int(fixed_L * scale_factor)
        box_h = int(p.L * scale_factor)
        pygame.draw.rect(screen, COLOR_LINE, (0, 0, box_w, box_h), 2)

        # Рисуем центр (пунктир)
        mid_x = int(fixed_L / 2 * scale_factor)
        for y in range(0, box_h, 20):
            pygame.draw.line(screen, (50, 50, 50), (mid_x, y), (mid_x, y + 10), 1)

        # Рисуем частицы
        pos_draw = to_cpu(pos[viz_indices])

        for i in range(len(pos_draw)):
            x = int(pos_draw[i, 0] * scale_factor)
            y = int(pos_draw[i, 1] * scale_factor)

            if 0 <= x < SIM_WIDTH and 0 <= y < SCREEN_HEIGHT:
                pygame.draw.circle(screen, viz_colors[i], (x, y), 2)

        # --- Зона UI (Параметры) ---
        ui_rect = pygame.Rect(SIM_WIDTH, 0, SCREEN_WIDTH - SIM_WIDTH, SCREEN_HEIGHT)
        pygame.draw.rect(screen, COLOR_UI_BG, ui_rect)
        pygame.draw.line(screen, COLOR_LINE, (SIM_WIDTH, 0), (SIM_WIDTH, SCREEN_HEIGHT), 2)

        x_text = SIM_WIDTH + 15
        y_text = 20

        def draw_stat(title, value, color=COLOR_TEXT):
            nonlocal y_text
            img_title = font.render(title, True, (150, 150, 150))
            screen.blit(img_title, (x_text, y_text))
            y_text += 20
            img_val = font_large.render(value, True, color)
            screen.blit(img_val, (x_text, y_text))
            y_text += 35

        draw_stat("Время (с)", f"{sim_time:.2e}")
        draw_stat("Шагов", f"{step_count}")

        y_text += 10
        draw_stat("Гелий слева (Mix)", f"{he_crossed_percent:.1f}%", COLOR_HE)

        y_text += 10
        draw_stat("Аргон (Синий)", "m = 40", COLOR_AR)
        draw_stat("Гелий (Красный)", "m = 4", COLOR_HE)

        # Пояснение
        info = font.render("Пунктир = граница старта", True, (100, 100, 100))
        screen.blit(info, (x_text, SCREEN_HEIGHT - 30))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()