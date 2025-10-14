import numpy as np
import pandas as pd

import config
from calculate_wave_speed import CalculateAverageSpeed, DifferenceBetweenTheoreticalAndSimulatedSpeed
from system_builder import build_system
from analyze import plot_all_data_about_block
from simulation import ChainSimulation
from visualisation_demo import preprocess_data, run_animation

if __name__ == "__main__":
    masses, spring_constants, spacings = build_system()
    simulation = ChainSimulation(
        masses=masses,
        spring_constants=spring_constants,
        spacings=spacings
    )
    simulation.run()

    try:
        df = pd.read_csv('simulation_data.csv',
                         dtype={"time": np.float64, "block_index": np.int64, "position": np.float64,
                                "velocity": np.float64,
                                "acceleration": np.float64})
    except FileNotFoundError:
        print("Error: simulation_data.csv not found. Please run main.py first.")
        exit()

    average_speed = CalculateAverageSpeed(df=df, spacings=spacings)
    if config.GENERATION_MODE == 'uniform':
        DifferenceBetweenTheoreticalAndSimulatedSpeed(simulated_speed=average_speed)

    plot_all_data_about_block(df=df, spacings=spacings, block_index=99)

    positions_data, velocities_data, accelerations_data = preprocess_data(filename=config.CSV_FILENAME)
    run_animation(positions_df=positions_data, spacings=spacings, velocities_df=velocities_data, accelerations_df=accelerations_data)
