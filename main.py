# main.py
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import numpy as np
from scipy.integrate import solve_ivp

# Импортируем функции с новыми, понятными именами
from simulation import (
    optimize_trajectory, generate_flight_summary_table,
    calculate_trajectory_derivatives, RADIUS_EARTH, MAX_SIMULATION_TIME
)
from visualization import visualize_trajectory
from pygame_visualization import animate_trajectory

if __name__ == "__main__":
    # 1. Находим лучшие параметры для запуска
    optimal_velocity, optimal_angle = optimize_trajectory()

    # 2. Пересчитываем финальную траекторию с высокой точностью для визуализации
    print("\nПересчет финальной траектории с высокой точностью...")
    initial_state = [0, RADIUS_EARTH + 1, optimal_velocity * np.cos(optimal_angle),
                     optimal_velocity * np.sin(optimal_angle)]

    # Импортируем события для финального расчета
    from simulation import event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes

    final_trajectory_solution = solve_ivp(
        calculate_trajectory_derivatives,
        (0, MAX_SIMULATION_TIME),
        initial_state,
        t_eval=np.linspace(0, MAX_SIMULATION_TIME, 5000),
        method='LSODA',
        rtol=1e-12,
        atol=1e-14,
        events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
    )

    # 3. Показываем статический график
    visualize_trajectory(final_trajectory_solution)

    # 4. Выводим таблицу с данными
    summary_table = generate_flight_summary_table(optimal_velocity, optimal_angle, num_points=15)
    print("\nКлючевые точки полета:")
    print(summary_table.round(2))

    # 5. Запускаем анимацию
    print("\nЗапуск анимации...")
    animate_trajectory(final_trajectory_solution)