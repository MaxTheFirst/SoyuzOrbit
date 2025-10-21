# config.py
import numpy as np

# Размеры системы (уменьшено для стабильности)
NUM_BLOCKS_X = 8   # Маленькая система для стабильности
NUM_BLOCKS_Y = 8
TOTAL_BLOCKS = NUM_BLOCKS_X * NUM_BLOCKS_Y

# Режим генерации
GENERATION_MODE = 'uniform'

# Стандартные значения (уменьшены для стабильности)
DEFAULT_MASS = 1.0
DEFAULT_SPRING_CONSTANT = 1.0  # Уменьшена жесткость
DEFAULT_BLOCK_SPACING_X = 1.0
DEFAULT_BLOCK_SPACING_Y = 1.0

# Параметры симуляции (уменьшены для стабильности)
SIMULATION_DURATION = 5.0
SAMPLES_PER_SECOND = 20
TIME_STEP = 0.01  # Увеличен шаг для стабильности
DECIMAL_PLACES = 6

# Начальные условия (уменьшены для стабильности)
BLOCK_TO_DISPLACE_X = 4
BLOCK_TO_DISPLACE_Y = 4
INITIAL_DISPLACEMENT_X = 0.2  # Маленькое смещение
INITIAL_DISPLACEMENT_Y = 0.1

# Затухание (усилено для стабильности)
ENABLE_DAMPING = True
DECAY_TIME_SECONDS = 1.0
DAMPING_COEFFICIENT = (5 * DEFAULT_MASS) / DECAY_TIME_SECONDS  # Усиленное затухание

# Визуализация
VISUALIZATION_SCALE = 1.0
CSV_FILENAME = 'simulation_data_2d.csv'