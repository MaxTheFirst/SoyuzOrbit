# calculate_wave_speed.py
import pandas as pd
import numpy as np
import sys

from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks

import config

# Порог срабатывания: волна считается "прибывшей", когда смещение блока
# впервые превысит этот процент от начального смещения.
# Это помогает отфильтровать числовой шум.
ARRIVAL_THRESHOLD_PERCENT = 1.0


def calculate_arrival_times(df: pd.DataFrame, equilibrium_positions: np.ndarray) -> list:
    """
    Анализирует данные и находит время первого прибытия волны для каждого блока.
    """
    arrival_times = []
    threshold = config.INITIAL_DISPLACEMENT * (ARRIVAL_THRESHOLD_PERCENT / 100.0)

    print(f"\nCalculating arrival times with a threshold of {threshold:.4f} m...")

    for i in range(config.NUM_BLOCKS):
        block_df = df[df['block_index'] == i]
        if block_df.empty:
            print(f"Warning: No data found for block {i}. Stopping analysis.")
            return []

        # Вычисляем смещение для текущего блока
        displacement = block_df['position'] - equilibrium_positions[i]

        # Находим все моменты времени, когда смещение превысило порог
        triggered_events = block_df[np.abs(displacement) > threshold]

        if triggered_events.empty:
            print(f"Warning: Wave did not reach block {i} with sufficient amplitude. Analysis might be incomplete.")
            break  # Прерываем, если волна затухла и не дошла до конца

        # Записываем самое первое время
        arrival_time = triggered_events['time'].iloc[0]
        arrival_times.append(arrival_time)

    print(f"Successfully found arrival times for {len(arrival_times)} blocks.")
    return arrival_times


def calculate_average_speed(df: pd.DataFrame, spacings: list[float]) -> float:
    """
    Основная функция для запуска анализа скорости волны.
    """
    print("--- Wave Speed Analysis Upon Reaching ---")

    # 1. Расчет равновесных положений
    # np.cumsum создает массив [spacing0, spacing0+spacing1, ...]
    equilibrium_positions = np.cumsum(spacings[:config.NUM_BLOCKS])

    # 3. Вычисление времен прибытия волны
    arrival_times = calculate_arrival_times(df, equilibrium_positions)

    if len(arrival_times) < 2:
        print("Error: Not enough data to calculate speed (need at least 2 blocks).")
        sys.exit()

    if arrival_times != sorted(arrival_times):
        print("Error: Counterintuitive data")
        sys.exit()

    # 4. Расчет локальных скоростей
    local_speeds = []

    # Устанавливаем диапазон для анализа, чтобы игнорировать "шум" в начале и конце
    START_BLOCK = 20
    END_BLOCK = 80

    print(f"\nAnalyzing speeds between block {START_BLOCK} and {END_BLOCK} for better accuracy...")

    # Убедимся, что у нас достаточно данных для анализа в этом диапазоне
    if len(arrival_times) <= START_BLOCK:
        print("Error: Wave did not reach the analysis start block.")
        sys.exit()

    # Обрезаем диапазон анализа до END_BLOCK, если волна не дошла дальше
    analysis_range_end = min(len(arrival_times) - 1, END_BLOCK)

    for i in range(START_BLOCK, analysis_range_end):
        delta_t = arrival_times[i + 1] - arrival_times[i]
        delta_x = spacings[i + 1]

        if delta_t > 0:
            local_speed = delta_x / delta_t
            local_speeds.append(local_speed)

    # 5. Анализ и вывод результатов
    if not local_speeds:
        print("Could not calculate any local speeds.")
        sys.exit()

    avg_speed = np.mean(local_speeds)
    min_speed = np.min(local_speeds)
    max_speed = np.max(local_speeds)

    print("\n--- Analysis Results ---")
    print(f"Average Wave Speed: {avg_speed:.4f} m/s")
    print(f"Minimum Speed Found: {min_speed:.4f} m/s")
    print(f"Maximum Speed Found: {max_speed:.4f} m/s")

    return float(avg_speed)


def find_dominant_frequency(time_series_df: pd.DataFrame, equilibrium_pos: float) -> float:
    """
    Использует FFT для поиска доминирующей частоты в колебаниях одного блока.
    """
    # 1. Получаем сигнал (смещение) и временные отсчеты
    displacements = time_series_df['position'].values - equilibrium_pos
    times = time_series_df['time'].values

    if len(times) < 2:
        print("Error (FFT): Not enough time data to find frequency.")
        return 0.0

    # 2. Определяем параметры для FFT
    N = len(displacements)
    dt = times[1] - times[0]  # Шаг времени (по данным логгера)

    if dt == 0:
        print("Error (FFT): Time step is zero.")
        return 0.0

    # 3. Выполняем FFT
    yf: np.ndarray = fft(displacements)
    xf: np.ndarray = fftfreq(N, dt)  # Получаем реальные частоты в Герцах

    # 4. Ищем пик (максимальную амплитуду)
    # Нам нужны только положительные частоты, и мы пропускаем 0-ю (постоянная составляющая)
    positive_freq_mask = (xf > 0)

    if not np.any(positive_freq_mask):
        print("Error (FFT): No positive frequencies found.")
        return 0.0

    peak_index = np.argmax(np.abs(yf[positive_freq_mask]))
    dominant_frequency = xf[positive_freq_mask][peak_index]

    return float(dominant_frequency)


def find_wavelength(snapshot_df: pd.DataFrame, equilibrium_positions: np.ndarray) -> float:
    """
    Использует find_peaks для поиска средней длины волны на "снимке" системы.
    """
    # 1. Получаем сигнал (смещение) в пространстве
    displacements = snapshot_df['position'].values - equilibrium_positions

    # 2. Находим все пики (гребни волны)
    # Устанавливаем минимальную высоту пика, чтобы отсеять шум
    min_height = np.max(displacements) * 0.1
    peaks_indices, _ = find_peaks(displacements, height=min_height, distance=5)

    if len(peaks_indices) < 2:
        print("Error (Peaks): Not enough peaks found to measure wavelength.")
        return 0.0

    # 3. Получаем реальные *позиции* этих пиков
    peak_positions = equilibrium_positions[peaks_indices]

    # 4. Рассчитываем расстояния между пиками (это и есть длины волн)
    wavelengths = np.diff(peak_positions)

    # 5. Усредняем
    avg_wavelength = np.mean(wavelengths)
    return float(avg_wavelength)


def calculate_wave_speed_by_form(df: pd.DataFrame, spacings: list[float]) -> float:
    """
    Основная функция для запуска анализа скорости волны (Метод 2: v = f * lambda).
    """

    # --- 1. Находим частоту (f) ---
    print("Wave Speed by Waveform")
    equilibrium_positions = np.cumsum(spacings[:config.NUM_BLOCKS])

    # Берем данные по блоку из середины цепи для "чистого" сигнала
    middle_block_index = config.NUM_BLOCKS // 2
    time_series_df = df[df['block_index'] == middle_block_index].copy()

    # Игнорируем "переходный процесс" в начале симуляции
    start_time = config.SIMULATION_DURATION * 0.25
    time_series_df = time_series_df[time_series_df['time'] > start_time]

    if time_series_df.empty:
        print("Error: No time-series data found for middle block.")
        return 0.0

    f = find_dominant_frequency(time_series_df, float(equilibrium_positions[middle_block_index]))
    if f == 0.0: return 0.0

    print(f"Dominant Frequency (f): {f:.4f} Hz (Period T = {1 / f:.4f} s)")

    # --- 2. Находим длину волны (λ) ---


    # Берем "снимок" ближе к концу симуляции, чтобы волна установилась
    snapshot_time = config.SIMULATION_DURATION * 0.75
    available_times = df['time'].unique()
    closest_time = available_times[np.abs(available_times - snapshot_time).argmin()]

    snapshot_df = df[df['time'] == closest_time].copy().sort_values(by='block_index')

    if snapshot_df.empty or len(snapshot_df) != len(equilibrium_positions):
        print(f"Error: Snapshot data at t={closest_time}s is incomplete.")
        return 0.0

    lambda_val = find_wavelength(snapshot_df, equilibrium_positions)
    if lambda_val == 0.0: return 0.0

    print(f"Average Wavelength (\u03BB): {lambda_val:.4f} m")

    # --- 3. Рассчитываем скорость ---
    speed = f * lambda_val
    print("\n--- Form-Based Result ---")
    print(f"Calculated Speed (v = f * \u03BB): {speed:.4f} m/s")

    return speed


def difference_between_theoretical_and_simulated_speed(simulated_speed: float, masses: list[float],
                                                       spring_constants: list[float], spacings: list[float]):
    """
    Вычисляет процентное отклонение между теоретической и смоделированной скоростью.
    (Эта функция остается без изменений)
    """
    if config.GENERATION_MODE == 'uniform':
        # Получаем стандартные значения
        mass = config.DEFAULT_MASS
        k = config.DEFAULT_SPRING_CONSTANT
        a = config.DEFAULT_BLOCK_SPACING

        theoretical_speed = a * np.sqrt(k / mass)
        print("--------------------------")
        print(f"Theoretical Speed (for uniform case): {theoretical_speed:.4f} m/s")
        print(f"Difference from average: {abs(simulated_speed - theoretical_speed):.4f} m/s")
    elif config.GENERATION_MODE == 'random':
        # Для случайной системы используем средние значения
        mass = float(np.mean([m for m in masses]))
        k = float(np.mean([k for k in spring_constants]))
        a = float(np.mean([s for s in spacings]))

        theoretical_speed = a * np.sqrt(k / mass)
        print("--------------------------")
        print(f"Theoretical Speed (using average properties): {theoretical_speed:.4f} m/s")
        print(f"Difference from average: {abs(simulated_speed - theoretical_speed):.4f} m/s")
