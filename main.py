# main.py
import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import numpy as np
from scipy.integrate import solve_ivp

# Импортируем обновленные функции и новые константы
from simulation import (
    optimize_trajectory, generate_flight_summary_table,
    calculate_trajectory_derivatives, MAX_SIMULATION_TIME,
    LEO_RADIUS, LEO_VELOCITY, RTOL, ATOL
)
from visualization import visualize_trajectory
from pygame_visualization import animate_trajectory

if __name__ == "__main__":
    # 1. Находим лучшие параметры для старта с НОО
    optimal_angle, optimal_dv = optimize_trajectory()

    # 2. Пересчитываем финальную траекторию с высокой точностью
    print("\nПересчет финальной траектории с высокой точностью...")

    # Расчет начального состояния ПОСЛЕ импульса TLI (Trans-Lunar Injection)
    pos_x0 = LEO_RADIUS * np.cos(optimal_angle)
    pos_y0 = LEO_RADIUS * np.sin(optimal_angle)
    vel_x0 = -LEO_VELOCITY * np.sin(optimal_angle)
    vel_y0 = LEO_VELOCITY * np.cos(optimal_angle)

    vel_magnitude_before_burn = np.sqrt(vel_x0 ** 2 + vel_y0 ** 2)
    impulse_dir_x = vel_x0 / vel_magnitude_before_burn
    impulse_dir_y = vel_y0 / vel_magnitude_before_burn

    initial_state = [
        pos_x0,
        pos_y0,
        vel_x0 + optimal_dv * impulse_dir_x,
        vel_y0 + optimal_dv * impulse_dir_y
    ]

    from simulation import event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes

    final_trajectory_solution = solve_ivp(
        calculate_trajectory_derivatives,
        (0, MAX_SIMULATION_TIME),
        initial_state,
        t_eval=np.linspace(0, MAX_SIMULATION_TIME, 5000),
        method='LSODA',
        rtol=RTOL,
        atol=ATOL,
        events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
    )

    # 3. Показываем статический график (файл не менялся)
    visualize_trajectory(final_trajectory_solution)

    # 4. Выводим таблицу с данными
    summary_table = generate_flight_summary_table(optimal_angle, optimal_dv, num_points=15)
    print("\nКлючевые точки полета:")
    print(summary_table.round(2))

    # 5. Запускаем анимацию (файл не менялся)
    print("\nЗапуск анимации...")
    animate_trajectory(final_trajectory_solution)