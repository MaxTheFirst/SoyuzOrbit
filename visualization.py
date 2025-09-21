# visualization.py

import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import numpy as np

# Импортируем переменные и функции из модуля симуляции
from simulation import (
    equations_with_stop_at_surface, R_earth, R_moon,
    R_earth_moon, t_max, t_eval
)


# Функция для построения траектории
def visualize_trajectory(v0, theta0):
    initial_state = [0, R_earth, v0 * np.cos(theta0), v0 * np.sin(theta0)]

    solution = solve_ivp(
        equations_with_stop_at_surface,
        (0, t_max),
        initial_state,
        t_eval=t_eval,
        method='DOP853',
        rtol=1e-12,
        atol=1e-14
    )

    x, y = solution.y[0], solution.y[1]

    plt.figure(figsize=(12, 6))
    plt.plot(x / 1e6, y / 1e6, label="Траектория", color="green")

    earth_circle = plt.Circle((0, 0), R_earth / 1e6, color="blue", label="Земля", alpha=0.7)
    plt.gca().add_artist(earth_circle)

    moon_circle = plt.Circle((R_earth_moon / 1e6, 0), R_moon / 1e6, color="gray", label="Луна", alpha=0.7)
    plt.gca().add_artist(moon_circle)

    plt.xlabel("х (тыс. км)")
    plt.ylabel("у (тыс. км)")
    plt.title("Оптимизированная траектория до поверхности Луны")
    plt.legend()
    plt.grid(True)
    plt.axis("scaled")

    buffer = 0.1 * 1e8 / 1e6
    y_min = min(y.min() / 1e6, -R_earth / 1e6) - 2 * buffer
    y_max = max(y.max() / 1e6, R_moon / 1e6) + buffer
    plt.gca().set_ylim([y_min, y_max])

    filename = 'trajectory.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"График сохранён в файл: {filename}")
    plt.show()