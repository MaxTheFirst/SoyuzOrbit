# main.py

import numpy as np
from scipy.integrate import solve_ivp

# Импортируем необходимые функции из других модулей
from simulation import (
    optimize_trajectory, calculate_speed_table,
    equations_with_stop_at_surface, R_earth, t_max, t_eval
)
from visualization import visualize_trajectory
from pygame_visualization import animate_trajectory

if __name__ == "__main__":
    # 1. Оптимизация траектории
    print("--- Этап 1: Оптимизация траектории ---")
    v0_opt, theta0_opt = optimize_trajectory()
    print("-" * 40)

    # 2. Построение статического графика (Matplotlib)
    print("\n--- Этап 2: Построение статического графика (Matplotlib) ---")
    visualize_trajectory(v0_opt, theta0_opt)
    print("-" * 40)

    # 3. Расчёт и вывод таблицы скоростей
    print("\n--- Этап 3: Расчет ключевых точек полета ---")
    speed_table = calculate_speed_table(v0_opt, theta0_opt, num_points=10)
    print("Таблица ключевых точек полета:")
    print(speed_table)
    print("-" * 40)

    # 4. Запуск анимации Pygame
    print("\n--- Этап 4: Запуск динамической анимации (Pygame) ---")
    print("Сейчас откроется окно с анимацией. Нажмите ESC или закройте окно для выхода.")

    initial_state = [0, R_earth, v0_opt * np.cos(theta0_opt), v0_opt * np.sin(theta0_opt)]
    full_solution = solve_ivp(
        equations_with_stop_at_surface,
        (0, t_max),
        initial_state,
        t_eval=t_eval,
        method='DOP853',
        rtol=1e-12,
        atol=1e-14
    )

    animate_trajectory(full_solution)