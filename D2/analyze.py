# D2/analyze_2d.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import config  # Читаем config из корня


def plot_energy_conservation_2d() -> None:
    """
    Читает данные об энергии и строит график для проверки закона сохранения.
    (Эта функция идентична 1D-версии, т.к. формат файла тот же)
    """
    try:
        # Загружаем данные из файла энергии
        energy_df = pd.read_csv(config.CSV_ENERGY_DATA_FILENAME)
    except FileNotFoundError:
        print(f"Файл {config.CSV_ENERGY_DATA_FILENAME} не найден. Запустите симуляцию.")
        return

    print("\nPlotting 2D energy conservation graph...")

    plt.figure(figsize=(12, 7))

    plt.plot(energy_df['time'], energy_df['kinetic_energy'], label='Кинетическая (KE)', color='orange')
    plt.plot(energy_df['time'], energy_df['potential_energy'], label='Потенциальная (PE)', color='blue')
    plt.plot(energy_df['time'], energy_df['total_energy'], label='Полная (Total)', color='red', linewidth=2.5)

    plt.title('Сохранение энергии в 2D-системе', fontsize=16)
    plt.xlabel('Время (с)')
    plt.ylabel('Энергия (Дж)')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Находим начальную полную энергию для сравнения
    if not energy_df.empty:
        initial_total_energy = energy_df['total_energy'].iloc[0]
        if initial_total_energy > 0:
            plt.ylim(0, initial_total_energy * 1.5)  # Ограничим ось Y

    plt.show()


def plot_wave_snapshot_2d(df: pd.DataFrame, time_snapshot: float) -> None:
    """
    Строит "снимок" 2D-волны в один заданный момент времени.
    Мы будем использовать heatmap для визуализации смещения.
    """
    print(f"\nPlotting 2D wave snapshot at t = {time_snapshot} s...")

    # 1. Выбираем ближайшие по времени данные
    available_times = df['time'].unique()
    if len(available_times) == 0:
        print("Error: No data in DataFrame.")
        return

    closest_time = available_times[np.abs(available_times - time_snapshot).argmin()]
    snapshot_df = df[df['time'] == closest_time].copy()

    if snapshot_df.empty:
        print(f"Error: No data found near time {time_snapshot}s.")
        return

    # 2. Рассчитываем величину смещения (displacement magnitude)
    # displacement = sqrt( (x - x_eq)^2 + (y - y_eq)^2 )
    # Мы не храним x_eq, y_eq в CSV, поэтому будем использовать
    # величину скорости (v = sqrt(vx^2 + vy^2)) как индикатор волны.

    # Альтернатива: Построим "теплокарту" кинетической энергии
    try:
        heatmap_data = snapshot_df.pivot(
            index='block_y',
            columns='block_x',
            values='kinetic_energy'
        )
    except Exception as e:
        print(f"Error creating pivot table: {e}")
        print("Убедитесь, что CSV-файл содержит 'block_y', 'block_x', и 'kinetic_energy'")
        return

    # 3. Строим график
    plt.figure(figsize=(10, 8))
    plt.imshow(heatmap_data, cmap='viridis', origin='lower',
               interpolation='bilinear')

    plt.title(f'Снимок 2D-волны (Кинетическая энергия) при t={closest_time:.2f}c', fontsize=16)
    plt.xlabel('X-индекс блока')
    plt.ylabel('Y-индекс блока')
    plt.colorbar(label='Кинетическая энергия (Дж)')
    plt.show()