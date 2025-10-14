import numpy as np
import matplotlib.pyplot as plt
from pandas import DataFrame

import config


def plot_block_data(df: DataFrame, spacings: list[float], block_index: int, column_name: str, title: str,
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
    # equilibrium_positions = np.cumsum(spacings[:config.NUM_BLOCKS])  # Используем BLOCK_SPACING из config
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


def plot_block_shift(df: DataFrame, spacings: list[float], block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график смещения.
    """
    plot_block_data(df=df, spacings=spacings, block_index=block_index, column_name="position",
                    title=f"Смещение блока №{block_index} от положения равновесия",
                    ylabel="Смещение (м)")


def plot_block_velocity(df: DataFrame, spacings: list[float], block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график скорости.
    """
    plot_block_data(df=df, spacings=spacings, block_index=block_index, column_name="velocity",
                    title=f"Скорость блока №{block_index}", ylabel="Скорость (м/с)")


def plot_block_acceleration(df: DataFrame, spacings: list[float], block_index: int) -> None:
    """
    Фильтрует данные для одного блока и строит график ускорения.
    """
    plot_block_data(df=df, spacings=spacings, block_index=block_index, column_name="acceleration",
                    title=f"Ускорение блока №{block_index}", ylabel="Ускорение (м/с^2)")


def plot_all_data_about_block(df: DataFrame, spacings: list[float], block_index: int) -> None:
    """
    Фильтрует данные для одного блока и возвращает их в виде графиков
    """
    plot_block_shift(df=df, spacings=spacings, block_index=block_index)
    plot_block_velocity(df=df, spacings=spacings, block_index=block_index)
    plot_block_acceleration(df=df, spacings=spacings, block_index=block_index)
