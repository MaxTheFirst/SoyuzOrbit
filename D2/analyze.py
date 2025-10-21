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


def plot_block_data_2d(time_values: pd.Series, data_x: pd.Series, data_y: pd.Series,
                       label_x: str, label_y: str, title: str, ylabel: str) -> None:
    """
    Общая (внутренняя) функция для построения графика (X и Y компоненты)
    для одного блока.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(time_values, data_x, label=label_x)
    plt.plot(time_values, data_y, label=label_y)
    plt.title(title, fontsize=16)
    plt.xlabel('Время (с)')
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True, linestyle='--')
    plt.show()


def plot_block_displacement_2d(time_values: pd.Series, block_df: pd.DataFrame,
                               y_idx: int, x_idx: int) -> None:
    """Строит график смещения для одного блока."""
    plot_block_data_2d(
        time_values=time_values,
        data_x=block_df['disp_x'],
        data_y=block_df['disp_y'],
        label_x='Смещение X',
        label_y='Смещение Y',
        title=f'Смещение блока ({y_idx}, {x_idx}) от времени',
        ylabel='Смещение (м)'
    )


def plot_block_velocity_2d(time_values: pd.Series, block_df: pd.DataFrame,
                           y_idx: int, x_idx: int) -> None:
    """Строит график скорости для одного блока."""
    plot_block_data_2d(
        time_values=time_values,
        data_x=block_df['vel_x'],
        data_y=block_df['vel_y'],
        label_x='Скорость X',
        label_y='Скорость Y',
        title=f'Скорость блока ({y_idx}, {x_idx}) от времени',
        ylabel='Скорость (м/с)'
    )


def plot_block_acceleration_2d(time_values: pd.Series, block_df: pd.DataFrame,
                               y_idx: int, x_idx: int) -> None:
    """Строит график ускорения для одного блока."""
    plot_block_data_2d(
        time_values=time_values,
        data_x=block_df['acc_x'],
        data_y=block_df['acc_y'],
        label_x='Ускорение X',
        label_y='Ускорение Y',
        title=f'Ускорение блока ({y_idx}, {x_idx}) от времени',
        ylabel='Ускорение (м/с²)'
    )


def plot_all_data_about_block_2d(df: pd.DataFrame, y_idx: int, x_idx: int,
                                 equilibrium_positions: np.ndarray) -> None:
    """
    Главная функция: фильтрует данные и вызывает 3 функции-плоттера.
    """
    print(f"\nGenerating plots for block ({y_idx}, {x_idx})...")

    # 1. Фильтруем DataFrame для нужного блока
    block_df = df[(df['block_y'] == y_idx) & (df['block_x'] == x_idx)].copy()

    if block_df.empty:
        print(f"Error: No data found for block ({y_idx}, {x_idx}).")
        return

    # 2. Рассчитываем равновесные позиции для расчета смещения
    eq_x = equilibrium_positions[y_idx, x_idx, 0]
    eq_y = equilibrium_positions[y_idx, x_idx, 1]

    # 3. Рассчитываем смещение и добавляем как новые столбцы
    block_df['disp_x'] = block_df['pos_x'] - eq_x
    block_df['disp_y'] = block_df['pos_y'] - eq_y

    time_values = block_df['time']

    # 4. Вызываем отдельные плоттеры
    plot_block_displacement_2d(time_values, block_df, y_idx, x_idx)
    plot_block_velocity_2d(time_values, block_df, y_idx, x_idx)
    plot_block_acceleration_2d(time_values, block_df, y_idx, x_idx)