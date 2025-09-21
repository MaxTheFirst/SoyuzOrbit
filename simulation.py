# simulation.py
import numpy
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

# Физические константы
G = 6.67430e-11  # Гравитационная постоянная, м^3 кг^-1 с^-2
M_earth = 5.972e24  # Масса Земли, кг
M_moon = 7.348e22  # Масса Луны, кг
R_earth = 6.371e6  # Радиус Земли, м
R_moon = 1.737e6  # Радиус Луны, м
R_earth_moon = 3.844e8  # Расстояние между Землёй и Луной, м

# Параметры симуляции
t_max = 300000  # Максимальное время моделирования, секунды
t_eval = np.linspace(0, t_max, 30000)  # Шаги времени для интеграции


# Сила гравитации со стороны Земли
def force_earth(x, y):
    r = np.sqrt(x ** 2 + y ** 2)
    a_x = -G * M_earth * x / r ** 3
    a_y = -G * M_earth * y / r ** 3
    return a_x, a_y


# Сила гравитации со стороны Луны
def force_moon(x, y):
    r = np.sqrt((x - R_earth_moon) ** 2 + y ** 2)
    a_x = -G * M_moon * (x - R_earth_moon) / r ** 3
    a_y = -G * M_moon * y / r ** 3
    return a_x, a_y


# Уравнения движения с остановкой при достижении поверхности Луны
def equations_with_stop_at_surface(t, y):
    x, y_position, vx, vy = y

    distance_to_surface = np.sqrt((x - R_earth_moon) ** 2 + y_position ** 2) - R_moon

    if distance_to_surface <= 0:  # Если пересекаем поверхность Луны
        return [0, 0, 0, 0]  # Останавливаем движение

    ax_earth, ay_earth = force_earth(x, y_position)
    ax_moon, ay_moon = force_moon(x, y_position)

    return [vx, vy, ax_earth + ax_moon, ay_earth + ay_moon]


# Функция стоимости для оптимизации параметров
def cost_function(params):
    v0, theta0 = params
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

    if not solution.success:
        return np.inf

    x, y = solution.y[0], solution.y[1]
    distances_to_moon = np.sqrt((x - R_earth_moon) ** 2 + y ** 2)
    closest_distance = np.min(distances_to_moon) - R_moon
    closest_index = np.argmin(distances_to_moon)

    vx_closest, vy_closest = solution.y[2][closest_index], solution.y[3][closest_index]

    if closest_distance <= 0:
        velocity_penalty = (vx_closest ** 2 + vy_closest ** 2) * 500
        return velocity_penalty

    distance_penalty = closest_distance ** 2
    velocity_penalty = (vx_closest ** 2 + vy_closest ** 2) * 500

    return distance_penalty + velocity_penalty


# Функция для оптимизации начальных параметров
def optimize_trajectory():
    print("Начало грубой оптимизации...")
    initial_guess = numpy.array([1.12e4, np.pi / 4])
    coarse_bounds = [(8000, 25000), (0, np.pi)]
    result_coarse = minimize(
        cost_function,
        x0=initial_guess,
        bounds=coarse_bounds,
        method='Powell'
    )
    v0_coarse, theta0_coarse = result_coarse.x
    print(f"Грубая оптимизация завершена: v0 = {v0_coarse:.2f}, theta = {theta0_coarse:.4f}")

    print("Начало точной оптимизации...")
    fine_bounds = [
        (v0_coarse - 1000, v0_coarse + 1000),
        (theta0_coarse - 0.2, theta0_coarse + 0.2)
    ]
    result_fine = minimize(
        cost_function,
        x0=numpy.array([v0_coarse, theta0_coarse]),
        bounds=fine_bounds,
        method='Powell'
    )
    v0_fine, theta0_fine = result_fine.x
    print(f"Точная оптимизация завершена: v0 = {v0_fine:.2f}, theta = {theta0_fine:.4f}")

    return v0_fine, theta0_fine


# Функция для вычисления таблицы скоростей
def calculate_speed_table(v0, theta0, num_points=100):
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

    if not solution.success:
        raise ValueError("Интеграция не удалась!")

    x, y = solution.y[0], solution.y[1]
    vx, vy = solution.y[2], solution.y[3]
    times = solution.t

    total_points = len(times)
    selected_indices = np.linspace(0, total_points - 1, num_points, dtype=int)

    selected_times = times[selected_indices].astype(int)
    speeds = np.sqrt(vx[selected_indices] ** 2 + vy[selected_indices] ** 2)
    distances_from_earth = (np.sqrt(x[selected_indices] ** 2 + y[selected_indices] ** 2) - R_earth) / 1000
    distances_to_moon = (np.sqrt((x[selected_indices] - R_earth_moon) ** 2 + y[selected_indices] ** 2) - R_moon) / 1000

    speed_table = pd.DataFrame({
        "Время (с)": selected_times,
        "Скорость (м/с)": speeds,
        "Расстояние от Земли (км)": distances_from_earth,
        "Расстояние до Луны (км)": distances_to_moon
    })

    return speed_table