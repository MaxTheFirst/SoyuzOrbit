# calculate_wave_speed.py
import pandas as pd
import numpy as np
from pandas.core.interchange.dataframe_protocol import DataFrame
from scipy.cluster.hierarchy import average

import config
import system_builder
import sys

from system_builder import build_system
from simulation import ChainSimulation

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


def CalculateAverageSpeed(df: DataFrame, spacings: list[float]) -> float:
    """
    Основная функция для запуска анализа скорости волны.
    """
    print("--- Wave Speed Analysis ---")

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


def DifferenceBetweenTheoreticalAndSimulatedSpeed(simulated_speed: float, masses: list[float],
                                                  spring_constants: list[float], spacings: list[float]):
    """
    Вычисляет процентное отклонение между теоретической и смоделированной скоростью.
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
