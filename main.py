import numpy as np
import pandas as pd

import config
from D1.calculate_wave_speed import calculate_average_speed, difference_between_theoretical_and_simulated_speed
from D1.system_builder import build_system
from D1.analyze import plot_all_data_about_block, plot_energy_conservation, plot_wave_snapshot
from D1.simulation import ChainSimulation
from D1.visualisation_demo import preprocess_data, run_animation

from D2.analyze import plot_energy_conservation_2d, plot_wave_snapshot_2d
from D2.system_builder import build_system_2d
from D2.simulation import GridSimulation
from D2.visualisation import preprocess_data_2d_realistic, run_animation_2d_realistic
from D2.visualisation_demo import preprocess_data_2d, run_animation_2d

def run_1d_simulation():
    masses, spring_constants, spacings = build_system()
    simulation = ChainSimulation(
        masses=masses,
        spring_constants=spring_constants,
        spacings=spacings
    )
    simulation.run()

    try:
        df_simulation = pd.read_csv('simulation_data.csv',
                                    dtype={"time": np.float64, "block_index": np.int64, "position": np.float64,
                                           "velocity": np.float64,
                                           "acceleration": np.float64,
                                           "kinetic_energy": np.float64}
                                    )
    except FileNotFoundError:
        print("Error: simulation_data.csv not found.")
        exit()

    try:
        energy_df = pd.read_csv('energy_data.csv',
                                dtype={"time": np.float64,
                                       "kinetic_energy": np.float64,
                                       "potential_energy": np.float64,
                                       "total_energy": np.float64}
                                )
    except FileNotFoundError:
        print("Error: energy_data.csv not found.")
        exit()

    if config.BLOCK_TO_DISPLACE == 0:
        print("Average Method")
        average_speed = calculate_average_speed(df=df_simulation, spacings=spacings)
        difference_between_theoretical_and_simulated_speed(
            simulated_speed=average_speed,
            masses=masses,
            spring_constants=spring_constants,
            spacings=spacings
        )

    # Не работает
    # print("Form Method")
    # form_speed = calculate_wave_speed_by_form(df=df_simulation, spacings=spacings)
    # difference_between_theoretical_and_simulated_speed(
    #     simulated_speed=form_speed,
    #     masses=masses,
    #     spring_constants=spring_constants,
    #     spacings=spacings
    # )

    plot_all_data_about_block(df=df_simulation, block_index=50)
    plot_wave_snapshot(df=df_simulation, spacings=spacings, time_snapshot=30.0)

    plot_energy_conservation(df=energy_df)

    positions_data, velocities_data, accelerations_data = preprocess_data(filename=config.CSV_SIMULATION_FILENAME)
    run_animation(positions_df=positions_data, spacings=spacings, velocities_df=velocities_data,
                  accelerations_df=accelerations_data)


def run_2d_simulation():
    # 1. Импортируем 2D модули
    # (Визуализацию и анализ импортируем позже)

    # 2. Строим 2D-систему
    (masses, spring_constants_x,
     spring_constants_y, equilibrium_positions) = build_system_2d()

    # 3. Создаем и запускаем симуляцию
    simulation_2d = GridSimulation(
        masses=masses,
        spring_constants_x=spring_constants_x,
        spring_constants_y=spring_constants_y,
        equilibrium_positions=equilibrium_positions
    )

    simulation_2d.run()

    # 4. Анализ
    print("Загрузка 2D-данных для анализа...")
    try:
        df = pd.read_csv(config.CSV_SIMULATION_FILENAME)
    except FileNotFoundError:
        print(f"Ошибка: {config.CSV_SIMULATION_FILENAME} не найден.")
        exit()

    # 5. Строим графики
    plot_energy_conservation_2d()
    plot_wave_snapshot_2d(df, time_snapshot=config.SIMULATION_DURATION * 0.5)

    # 6. Визуализация
    timestamps, frames_data, max_disp = preprocess_data_2d(config.CSV_SIMULATION_FILENAME)
    run_animation_2d(timestamps, frames_data, max_disp)

    # Визуализация 2: Реалистичная (может быть медленнее)
    print("Запуск Реалистичной анимации...")
    pos_x_df, pos_y_df, eq_pos = preprocess_data_2d_realistic(config.CSV_SIMULATION_FILENAME)
    run_animation_2d_realistic(pos_x_df, pos_y_df, eq_pos)

if __name__ == "__main__":
    if config.SIMULATION_MODE == "1D":
        run_1d_simulation()
    elif config.SIMULATION_MODE == "2D":
        run_2d_simulation()
    else:
        raise ValueError(f"Неизвестный SIMULATION_MODE: '{config.SIMULATION_MODE}' в config.py")
