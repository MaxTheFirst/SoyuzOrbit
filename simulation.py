# simulation.py

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import differential_evolution

# --- Физические константы ---
GRAVITATIONAL_CONSTANT = 6.67430e-11
MASS_EARTH = 5.972e24
MASS_MOON = 7.348e22
RADIUS_EARTH = 6.371e6
RADIUS_MOON = 1.737e6
DISTANCE_EARTH_MOON = 3.844e8

# --- Параметры симуляции ---
MAX_SIMULATION_TIME = 300000
TIME_EVALUATION_POINTS = np.linspace(0, MAX_SIMULATION_TIME, 30000)

# --- Параметры орбиты Луны ---
PERIOD_MOON_ORBIT = 27.32 * 24 * 3600  # в секундах
ANGULAR_VELOCITY_MOON = 2 * np.pi / PERIOD_MOON_ORBIT


def calculate_moon_position(time):
    """Рассчитывает X, Y координаты Луны в зависимости от времени."""
    angle = ANGULAR_VELOCITY_MOON * time
    moon_x = DISTANCE_EARTH_MOON * np.cos(angle)
    moon_y = DISTANCE_EARTH_MOON * np.sin(angle)
    return moon_x, moon_y


def calculate_moon_gravity_acceleration(rocket_pos_x, rocket_pos_y, moon_pos_x, moon_pos_y):
    """Рассчитывает вектор ускорения ракеты из-за гравитации Луны."""
    distance_vec_x = rocket_pos_x - moon_pos_x
    distance_vec_y = rocket_pos_y - moon_pos_y
    distance_to_moon = np.sqrt(distance_vec_x ** 2 + distance_vec_y ** 2)

    if distance_to_moon == 0: return 0, 0

    accel_x = -GRAVITATIONAL_CONSTANT * MASS_MOON * distance_vec_x / distance_to_moon ** 3
    accel_y = -GRAVITATIONAL_CONSTANT * MASS_MOON * distance_vec_y / distance_to_moon ** 3
    return accel_x, accel_y


def calculate_earth_gravity_acceleration(rocket_pos_x, rocket_pos_y):
    """Рассчитывает вектор ускорения ракеты из-за гравитации Земли."""
    distance_to_earth = np.sqrt(rocket_pos_x ** 2 + rocket_pos_y ** 2)

    if distance_to_earth == 0: return 0, 0

    accel_x = -GRAVITATIONAL_CONSTANT * MASS_EARTH * rocket_pos_x / distance_to_earth ** 3
    accel_y = -GRAVITATIONAL_CONSTANT * MASS_EARTH * rocket_pos_y / distance_to_earth ** 3
    return accel_x, accel_y


# --- Функции-события для остановки симуляции ---
def event_rocket_hits_earth(time, state_vector):
    distance_from_center = np.sqrt(state_vector[0] ** 2 + state_vector[1] ** 2)
    return distance_from_center - RADIUS_EARTH


event_rocket_hits_earth.terminal = True
event_rocket_hits_earth.direction = -1


def event_rocket_hits_moon(time, state_vector):
    moon_pos_x, moon_pos_y = calculate_moon_position(time)
    distance_from_center = np.sqrt((state_vector[0] - moon_pos_x) ** 2 + (state_vector[1] - moon_pos_y) ** 2)
    return distance_from_center - RADIUS_MOON


event_rocket_hits_moon.terminal = True
event_rocket_hits_moon.direction = -1


def event_rocket_escapes(time, state_vector):
    distance_from_earth = np.sqrt(state_vector[0] ** 2 + state_vector[1] ** 2)
    return (DISTANCE_EARTH_MOON * 1.5) - distance_from_earth


event_rocket_escapes.terminal = True
event_rocket_escapes.direction = -1


def calculate_trajectory_derivatives(time, state_vector):
    """Главная функция для решателя ODE. Рассчитывает производные состояния."""
    pos_x, pos_y, vel_x, vel_y = state_vector

    moon_pos_x, moon_pos_y = calculate_moon_position(time)

    accel_earth_x, accel_earth_y = calculate_earth_gravity_acceleration(pos_x, pos_y)
    accel_moon_x, accel_moon_y = calculate_moon_gravity_acceleration(pos_x, pos_y, moon_pos_x, moon_pos_y)

    total_accel_x = accel_earth_x + accel_moon_x
    total_accel_y = accel_earth_y + accel_moon_y

    return [vel_x, vel_y, total_accel_x, total_accel_y]


def calculate_optimization_cost(launch_parameters):
    """Функция стоимости для оптимизатора."""
    initial_velocity, launch_angle = launch_parameters
    initial_state_vector = [0, RADIUS_EARTH + 1, initial_velocity * np.cos(launch_angle),
                            initial_velocity * np.sin(launch_angle)]

    simulation_result = solve_ivp(
        calculate_trajectory_derivatives,
        (0, MAX_SIMULATION_TIME),
        initial_state_vector,
        t_eval=TIME_EVALUATION_POINTS,
        method='LSODA',
        rtol=1e-12,
        atol=1e-14,
        events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
    )

    if not simulation_result.success: return np.inf

    rocket_x_coords = simulation_result.y[0]
    rocket_y_coords = simulation_result.y[1]
    rocket_vx = simulation_result.y[2]
    rocket_vy = simulation_result.y[3]
    timestamps = simulation_result.t

    moon_x_coords, moon_y_coords = calculate_moon_position(timestamps)

    distances_to_moon_center = np.sqrt((rocket_x_coords - moon_x_coords) ** 2 + (rocket_y_coords - moon_y_coords) ** 2)
    closest_distance_to_surface = np.min(distances_to_moon_center) - RADIUS_MOON
    closest_approach_index = np.argmin(distances_to_moon_center)

    velocity_at_closest_x = rocket_vx[closest_approach_index]
    velocity_at_closest_y = rocket_vy[closest_approach_index]

    if closest_distance_to_surface <= 0:
        landing_velocity_sq = velocity_at_closest_x ** 2 + velocity_at_closest_y ** 2
        velocity_penalty = landing_velocity_sq * 500
        return velocity_penalty

    distance_penalty = closest_distance_to_surface ** 2
    velocity_penalty = (velocity_at_closest_x ** 2 + velocity_at_closest_y ** 2) * 500

    return distance_penalty + velocity_penalty


# simulation.py

# ... (все импорты и остальные функции остаются без изменений) ...
from scipy.optimize import minimize, differential_evolution


def optimize_trajectory():
    """Запускает двухэтапный процесс оптимизации для поиска лучшей траектории."""

    # --- Этап 1: Глобальный поиск с помощью differential_evolution ---
    print("Этап 1: Начало глобальной параллельной оптимизации...")
    launch_bounds = [(10800, 11200), (np.pi / 6, np.pi / 2.5)]

    # Запускаем глобальный поиск, но с меньшим количеством итераций,
    # так как нам не нужна идеальная точность, а лишь хорошая отправная точка.
    coarse_result = differential_evolution(
        calculate_optimization_cost,
        launch_bounds,
        workers=-1,
        maxiter=50,  # Ограничиваем количество итераций для скорости
        popsize=15,
        tol=0.1  # Снижаем требования к точности для этого этапа
    )

    v0_coarse, theta0_coarse = coarse_result.x
    print(f"Глобальный поиск завершен: v0 ≈ {v0_coarse:.2f} м/с, theta ≈ {np.degrees(theta0_coarse):.2f}°")

    # --- Этап 2: Локальная "полировка" результата с помощью Powell ---
    print("\nЭтап 2: Начало локальной уточняющей оптимизации...")

    fine_bounds = [
        (v0_coarse - 50, v0_coarse + 50),
        (theta0_coarse - np.radians(1), theta0_coarse + np.radians(1))
    ]

    # Запускаем Powell, который очень эффективен в поиске локального минимума.
    fine_result = minimize(
        calculate_optimization_cost,
        x0=[v0_coarse, theta0_coarse],  # Начинаем с лучшей точки, найденной ранее
        method='Powell',
        bounds=fine_bounds,
        options={'xtol': 1e-4, 'ftol': 1e-4}  # Устанавливаем высокую точность для финала
    )

    best_velocity, best_angle = fine_result.x
    min_cost = fine_result.fun

    print(f"\nОптимизация полностью завершена:")
    print(f"  - Начальная скорость: {best_velocity:.2f} м/с")
    print(f"  - Угол старта: {np.degrees(best_angle):.2f}°")
    print(f"  - Минимальный штраф: {min_cost:.2f}")

    return best_velocity, best_angle


def generate_flight_summary_table(initial_velocity, launch_angle, num_points=100):
    """Создает таблицу (DataFrame) с ключевыми параметрами полета."""
    initial_state_vector = [0, RADIUS_EARTH + 1, initial_velocity * np.cos(launch_angle),
                            initial_velocity * np.sin(launch_angle)]

    final_time_points = np.linspace(0, MAX_SIMULATION_TIME, 5000)

    simulation_result = solve_ivp(
        calculate_trajectory_derivatives,
        (0, MAX_SIMULATION_TIME),
        initial_state_vector,
        t_eval=final_time_points,
        method='LSODA',
        rtol=1e-12,
        atol=1e-14,
        events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
    )

    if not simulation_result.success and len(simulation_result.t_events[0]) == 0 and len(
            simulation_result.t_events[1]) == 0 and len(simulation_result.t_events[2]) == 0:
        raise ValueError("Интеграция не удалась и не было событий!")

    x_coords, y_coords, vx, vy = simulation_result.y
    timestamps = simulation_result.t

    total_points = len(timestamps)
    if total_points < num_points: num_points = total_points
    if total_points == 0: return pd.DataFrame()

    selected_indices = np.linspace(0, total_points - 1, num_points, dtype=int)

    selected_times = timestamps[selected_indices]

    moon_x_at_times, moon_y_at_times = calculate_moon_position(selected_times)

    distances_to_moon_surface_km = (np.sqrt((x_coords[selected_indices] - moon_x_at_times) ** 2 +
                                            (y_coords[selected_indices] - moon_y_at_times) ** 2) - RADIUS_MOON) / 1000

    flight_speeds_ms = np.sqrt(vx[selected_indices] ** 2 + vy[selected_indices] ** 2)
    distances_from_earth_surface_km = (np.sqrt(
        x_coords[selected_indices] ** 2 + y_coords[selected_indices] ** 2) - RADIUS_EARTH) / 1000

    summary_table = pd.DataFrame({
        "Время полета (с)": selected_times.astype(int),
        "Скорость (м/с)": flight_speeds_ms,
        "Высота над Землей (км)": distances_from_earth_surface_km,
        "Высота над Луной (км)": distances_to_moon_surface_km
    })

    return summary_table