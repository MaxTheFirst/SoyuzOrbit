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

# --- НОВЫЕ КОНСТАНТЫ: Параметры низкой околоземной орбиты (НОО) ---
LEO_ALTITUDE = 200e3  # Высота НОО - 200 км
LEO_RADIUS = RADIUS_EARTH + LEO_ALTITUDE
LEO_VELOCITY = np.sqrt(GRAVITATIONAL_CONSTANT * MASS_EARTH / LEO_RADIUS)

# --- Параметры симуляции ---
MAX_SIMULATION_TIME = 600000  # Увеличим максимальное время, полет стал дольше
TIME_EVALUATION_POINTS = np.linspace(0, MAX_SIMULATION_TIME, 5000)

# --- Параметры орбиты Луны ---
PERIOD_MOON_ORBIT = 27.32 * 24 * 3600
ANGULAR_VELOCITY_MOON = 2 * np.pi / PERIOD_MOON_ORBIT

RTOL=1e-10
ATOL=1e-12

# высота целевой низкой орбиты вокруг Луны
LUNAR_PARKING_ALT = 100e3  # 100 км

def event_reaches_lunar_parking_orbit(time, state_vector):
    # расстояние от корабля до центра Луны в момент time
    mx, my = calculate_moon_position(time)
    dx = state_vector[0] - mx
    dy = state_vector[1] - my
    r_sc_moon = np.hypot(dx, dy)
    # ноль -> когда касаемся окружности радиуса R_MOON + ALT
    return r_sc_moon - (RADIUS_MOON + LUNAR_PARKING_ALT)

# уменьшаем расстояние (подлетаем) -> корень с направлением -1
event_reaches_lunar_parking_orbit.terminal = True
event_reaches_lunar_parking_orbit.direction = -1

# --- НОВОЕ СОБЫТИЕ: достигли орбиты Луны (радиус орбиты от центра Земли) ---
def event_reaches_moon_orbit(time, state_vector):
    # расстояние корабля от Земли
    r = np.hypot(state_vector[0], state_vector[1])
    # ноль, когда пересекаем окружность радиуса DISTANCE_EARTH_MOON
    return r - DISTANCE_EARTH_MOON

# пересекаем «снизу-вверх» (улетаем от Земли)
event_reaches_moon_orbit.terminal = True
event_reaches_moon_orbit.direction = +1


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


def calculate_hohmann_cost(launch_params):
    """
    НОВАЯ ФУНКЦИЯ СТОИМОСТИ: Рассчитывает "штраф" для траектории Хоманна.
    Цель: минимизировать расстояние до Луны и относительную скорость (Δv для LOI).
    """
    start_angle_offset, tli_dv_magnitude = launch_params

    # 1. Начальные условия на НОО в момент подачи импульса
    pos_x0 = LEO_RADIUS * np.cos(start_angle_offset)
    pos_y0 = LEO_RADIUS * np.sin(start_angle_offset)
    vel_x0 = -LEO_VELOCITY * np.sin(start_angle_offset)
    vel_y0 = LEO_VELOCITY * np.cos(start_angle_offset)

    # 2. Применение импульса TLI (Trans-Lunar Injection)
    # Направление импульса совпадает с вектором скорости на НОО
    vel_magnitude_before_burn = np.sqrt(vel_x0 ** 2 + vel_y0 ** 2)
    impulse_dir_x = vel_x0 / vel_magnitude_before_burn
    impulse_dir_y = vel_y0 / vel_magnitude_before_burn

    vel_x_after_burn = vel_x0 + tli_dv_magnitude * impulse_dir_x
    vel_y_after_burn = vel_y0 + tli_dv_magnitude * impulse_dir_y

    initial_state = [pos_x0, pos_y0, vel_x_after_burn, vel_y_after_burn]

    # 3. Запуск симуляции
    sol = solve_ivp(
        calculate_trajectory_derivatives, (0, MAX_SIMULATION_TIME), initial_state,
        t_eval=TIME_EVALUATION_POINTS, method='LSODA',
        rtol=RTOL, atol=ATOL,
        events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
    )

    if not sol.success: return np.inf

    # 4. Расчет стоимости (штрафа)
    moon_x, moon_y = calculate_moon_position(sol.t)
    distances_to_moon = np.sqrt((sol.y[0] - moon_x) ** 2 + (sol.y[1] - moon_y) ** 2)

    # Если даже близко не подлетели - огромный штраф
    if np.min(distances_to_moon) > DISTANCE_EARTH_MOON * 0.4: return 1e12

    idx_closest = np.argmin(distances_to_moon)
    min_dist_to_surface = distances_to_moon[idx_closest] - RADIUS_MOON

    # Если врезались - большой штраф, но не бесконечный, чтобы дать оптимизатору информацию
    if min_dist_to_surface <= 0: return 1e8 + abs(min_dist_to_surface) * 100

    # Расчет относительной скорости в точке сближения (это и есть Δv для LOI)
    t_closest = sol.t[idx_closest]
    moon_angle = ANGULAR_VELOCITY_MOON * t_closest
    moon_vx = -ANGULAR_VELOCITY_MOON * DISTANCE_EARTH_MOON * np.sin(moon_angle)
    moon_vy = ANGULAR_VELOCITY_MOON * DISTANCE_EARTH_MOON * np.cos(moon_angle)

    relative_vx = sol.y[2, idx_closest] - moon_vx
    relative_vy = sol.y[3, idx_closest] - moon_vy
    relative_speed_at_closest = np.sqrt(relative_vx ** 2 + relative_vy ** 2)

    # Итоговый штраф: комбинация расстояния и скорости, которую надо погасить
    distance_penalty = min_dist_to_surface
    velocity_penalty = relative_speed_at_closest

    # Коэффициенты подобраны, чтобы сбалансировать важность сближения и экономии топлива
    cost = distance_penalty * 0.1 + velocity_penalty

    return cost


def optimize_trajectory():
    """ОБНОВЛЕННАЯ ФУНКЦИЯ ОПТИМИЗАЦИИ для траектории Хоманна."""
    print("Этап 1: Начало глобальной оптимизации траектории Хоманна...")

    # Границы поиска: [угол старта (радианы), величина импульса TLI (м/с)]
    # Теоретический импульс для Хоманна ~3120 м/с. Ищем вокруг этого значения.
    # Угол старта должен быть "за" Луной, чтобы догнать ее.
    # Луна движется из квадранта I в II, значит старт должен быть в IV или III.
    bounds = [(-2 * np.pi, 0), (3050, 3200)]

    result = differential_evolution(
        calculate_hohmann_cost,
        bounds,
        workers=-1,
        maxiter=150,  # Увеличим число итераций
        popsize=20,
        tol=1e-3,
        updating='deferred'
    )

    best_angle, best_dv = result.x
    min_cost = result.fun

    print(f"\nОптимизация полностью завершена:")
    print(f"  - Оптимальный угол старта на НОО: {np.degrees(best_angle):.2f}°")
    print(f"  - Оптимальный импульс TLI: {best_dv:.2f} м/с")
    print(f"  - Минимальный штраф (целевая функция): {min_cost:.2f}")

    return best_angle, best_dv


def generate_flight_summary_table(start_angle, tli_dv, num_points=15):
    """ОБНОВЛЕННАЯ ФУНКЦИЯ: Создает таблицу с ключевыми параметрами полета."""
    # Расчет начального состояния после импульса TLI (аналогично cost-функции)
    pos_x0 = LEO_RADIUS * np.cos(start_angle)
    pos_y0 = LEO_RADIUS * np.sin(start_angle)
    vel_x0 = -LEO_VELOCITY * np.sin(start_angle)
    vel_y0 = LEO_VELOCITY * np.cos(start_angle)
    vel_mag = np.sqrt(vel_x0 ** 2 + vel_y0 ** 2)
    dir_x, dir_y = vel_x0 / vel_mag, vel_y0 / vel_mag

    initial_state_vector = [
        pos_x0, pos_y0,
        vel_x0 + tli_dv * dir_x,
        vel_y0 + tli_dv * dir_y
    ]

    # Симуляция с высокой точностью для итоговой траектории
    simulation_result = solve_ivp(
        calculate_trajectory_derivatives, (0, MAX_SIMULATION_TIME), initial_state_vector,
        t_eval=np.linspace(0, MAX_SIMULATION_TIME, 5000),
        method='LSODA', rtol=RTOL, atol=ATOL,
        events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
    )

    if not simulation_result.success:
        print("Внимание: финальная интеграция не удалась.")
        if not simulation_result.t.size: return pd.DataFrame()

    x, y, vx, vy = simulation_result.y
    t = simulation_result.t
    total_points = len(t)
    indices = np.linspace(0, total_points - 1, num_points, dtype=int)

    moon_x, moon_y = calculate_moon_position(t[indices])

    dist_moon_surf_km = (np.sqrt((x[indices] - moon_x) ** 2 + (y[indices] - moon_y) ** 2) - RADIUS_MOON) / 1000
    flight_speeds_ms = np.sqrt(vx[indices] ** 2 + vy[indices] ** 2)
    dist_earth_surf_km = (np.sqrt(x[indices] ** 2 + y[indices] ** 2) - RADIUS_EARTH) / 1000

    return pd.DataFrame({
        "Время полета (дни)": t[indices] / (3600 * 24),
        "Скорость (км/с)": flight_speeds_ms / 1000,
        "Высота над Землей (тыс.км)": dist_earth_surf_km / 1000,
        "Высота над Луной (тыс.км)": dist_moon_surf_km / 1000
    })