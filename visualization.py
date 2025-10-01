# visualization.py

import matplotlib.pyplot as plt
import numpy as np

# Импортируем константы и функции с новыми именами
from simulation import (
    RADIUS_EARTH, RADIUS_MOON,
    DISTANCE_EARTH_MOON, calculate_moon_position
)


def visualize_trajectory(simulation_result):
    x_coords = simulation_result.y[0]
    y_coords = simulation_result.y[1]

    plt.figure(figsize=(12, 8))

    # Отображение орбиты Луны
    orbit_angles = np.linspace(0, 2 * np.pi, 200)
    orbit_x = DISTANCE_EARTH_MOON * np.cos(orbit_angles)
    orbit_y = DISTANCE_EARTH_MOON * np.sin(orbit_angles)
    plt.plot(orbit_x / 1e6, orbit_y / 1e6, color="gray", linestyle="--", label="Орбита Луны")

    # Траектория ракеты
    plt.plot(x_coords / 1e6, y_coords / 1e6, label="Траектория ракеты", color="green")

    # Земля
    earth_circle = plt.Circle((0, 0), RADIUS_EARTH / 1e6, color="blue", label="Земля", alpha=0.7)
    plt.gca().add_artist(earth_circle)

    # Луна в точке встречи
    flight_time = simulation_result.t[-1]
    moon_final_x, moon_final_y = calculate_moon_position(flight_time)
    moon_circle = plt.Circle(
        (moon_final_x / 1e6, moon_final_y / 1e6),
        RADIUS_MOON / 1e6, color="gray", label="Луна (точка встречи)", alpha=0.7
    )
    plt.gca().add_artist(moon_circle)

    # Настройки графика
    plt.xlabel("X координата (тыс. км)")
    plt.ylabel("Y координата (тыс. км)")
    plt.title("Оптимизированная траектория до движущейся Луны")
    plt.legend()
    plt.grid(True)
    plt.axis("scaled")

    filename = 'optimized_trajectory.png'
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"График сохранён в файл: {filename}")
    plt.show()