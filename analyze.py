import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import config

# Загружаем данные из CSV
try:
    df = pd.read_csv('simulation_data.csv',
                     dtype={"time": np.float64, "block_index": np.int64, "position": np.float64, "velocity": np.float64,
                            "acceleration": np.float64})
except FileNotFoundError:
    print("Error: simulation_data.csv not found. Please run main.py first.")
    exit()


def plot_block_data(block_index: int, column_name: str, title: str, ylabel: str) -> None:
    """
    Фильтрует данные для одного блока и строит график.
    """
    # Выбираем данные для указанного блока
    block_df = df[df['block_index'] == block_index]

    if block_df.empty:
        print(f"No data found for block {block_index}")
        return

    # Рассчитываем смещение от равновесного положения
    equilibrium_pos = (block_index + 1) * config.BLOCK_SPACING  # Используем BLOCK_SPACING из config
    data = block_df[column_name].values
    # displacement = positions - equilibrium_pos

    # Строим график
    plt.figure(figsize=(12, 6))
    plt.plot(block_df['time'], data)
    plt.title(title)
    plt.xlabel('Время (с)')
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.show()


def plot_block_shift(block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график смещения.
    """
    plot_block_data(block_index, "position", f"Смещение блока №{block_index} от положения равновесия", "Смещение (м)")


def plot_block_velocity(block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график скорости.
    """
    plot_block_data(block_index, "velocity", f"Скорость блока №{block_index}", "Скорость (м/с)")


def plot_block_acceleration(block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график ускорения.
    """
    plot_block_data(block_index, "acceleration", f"Ускорение блока №{block_index}", "Ускорение (м/с^2)")

def get_all_data_about_block(block_index: int) -> None:
    """
    Фильтрует данные для одного блока и возвращает их в виде графиков
    """
    plot_block_shift(block_index=block_index)
    plot_block_velocity(block_index=block_index)
    plot_block_acceleration(block_index=block_index)

if __name__ == "__main__":
    get_all_data_about_block(block_index=1)
    get_all_data_about_block(block_index=99)