import numpy as np
import matplotlib.pyplot as plt
from pandas import DataFrame

import config


# import config


def plot_block_data(df: DataFrame, block_index: int, column_name: str, title: str,
                    ylabel: str) -> None:
    """
    Фильтрует данные для одного блока и строит график.
    """
    # Выбираем данные для указанного блока
    block_df = df[df['block_index'] == block_index]

    if block_df.empty:
        print(f"No data found for block {block_index}")
        return

    # Рассчитываем смещение от равновесного положения
    data = block_df[column_name].values

    # Строим график
    plt.figure(figsize=(12, 6))
    plt.plot(block_df['time'], data)
    plt.title(title)
    plt.xlabel('Время (с)')
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.show()


def plot_block_shift(df: DataFrame, block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график смещения.
    """
    plot_block_data(df=df, block_index=block_index, column_name="position",
                    title=f"Смещение блока №{block_index} от положения равновесия",
                    ylabel="Смещение (м)")


def plot_block_velocity(df: DataFrame, block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график скорости.
    """
    plot_block_data(df=df, block_index=block_index, column_name="velocity",
                    title=f"Скорость блока №{block_index}", ylabel="Скорость (м/с)")


def plot_block_acceleration(df: DataFrame, block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график ускорения.
    """
    plot_block_data(df=df, block_index=block_index, column_name="acceleration",
                    title=f"Ускорение блока №{block_index}", ylabel="Ускорение (м/с²)")


def plot_all_data_about_block(df: DataFrame, block_index: int) -> None:
    """
    Фильтрует данные для одного блока и возвращает их в виде графиков
    """
    plot_block_shift(df=df, block_index=block_index)
    plot_block_velocity(df=df, block_index=block_index)
    plot_block_acceleration(df=df, block_index=block_index)


def plot_energy_conservation(df: DataFrame) -> None:
    """
    Читает данные об энергии и строит график для проверки закона сохранения.
    """
    print("\nPlotting energy conservation graph...")

    plt.figure(figsize=(12, 7))

    # Строим графики для каждого вида энергии
    plt.plot(df['time'], df['kinetic_energy'], label='Кинетическая энергия (KE)', color='lime')
    plt.plot(df['time'], df['potential_energy'], label='Потенциальная энергия (PE)', color='blue')
    plt.plot(df['time'], df['total_energy'], label='Полная энергия (Total)', color='red')

    # Настройка графика для наглядности
    plt.title('Сохранение энергии в системе', fontsize=16)
    plt.xlabel('Время (с)')
    plt.ylabel('Энергия (Дж)')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Находим начальную полную энергию для сравнения
    initial_total_energy = df['total_energy'].iloc[0]
    plt.ylim(0, initial_total_energy * 1.5)  # Ограничим ось Y для лучшей читаемости

    plt.show()


def plot_wave_snapshot(df: DataFrame, spacings: list[float], time_snapshot: float) -> None:
    """
    Строит график "снимка" всей волны в один заданный момент времени.
    """
    print(f"\nPlotting wave snapshot at t = {time_snapshot} s...")

    # 1. Рассчитываем равновесные позиции всех блоков
    # У нас N блоков, но spacings имеет N+1 элементов.
    # Равновесная позиция i-го блока = sum(spacings[0...i])
    equilibrium_positions = np.cumsum(spacings[:-1])

    # 2. Выбираем ближайшие по времени данные
    # (прямое сравнение float может быть неточным, ищем ближайшее)
    available_times = df['time'].unique()
    closest_time = available_times[np.abs(available_times - time_snapshot).argmin()]

    snapshot_df = df[df['time'] == closest_time].copy()

    if snapshot_df.empty:
        print(f"Error: No data found near time {time_snapshot}s.")
        return

    # 3. Сортируем по блокам, чтобы линия была правильной
    snapshot_df = snapshot_df.sort_values(by='block_index')

    # 4. Получаем данные для графика
    positions_at_t = snapshot_df['position'].values

    # Убедимся, что число позиций совпадает с числом равновесных позиций
    if len(positions_at_t) != len(equilibrium_positions):
        print(f"Warning: Data mismatch. Found {len(positions_at_t)} blocks in snapshot.")
        # Обрезаем на всякий случай
        eq_len = min(len(positions_at_t), len(equilibrium_positions))
        positions_at_t = positions_at_t[:eq_len]
        equilibrium_positions = equilibrium_positions[:eq_len]

    amplitude = positions_at_t - equilibrium_positions

    # 5. Строим график
    plt.figure(figsize=(12, 7))
    plt.plot(np.arange(config.NUM_BLOCKS), amplitude, label=f"Снимок волны при t={closest_time:.2f}c")

    plt.title('Пространственный "снимок" волны', fontsize=16)
    plt.xlabel('Номер блока')
    plt.ylabel('Смещение (м)')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.show()
