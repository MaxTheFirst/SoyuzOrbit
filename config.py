
# Случайность
RANDOM_SEED = 42   # None = случайно каждый раз

# Параметры системы
N_BLOCKS = 100
MASS_RANGE = (0.5, 1.5)       # кг
STIFFNESS_RANGE = (100, 300)  # Н/м
LENGTH_RANGE = (0.8, 1.2)     # м

# Положение стен
LEFT_WALL_X = 0.0
RIGHT_WALL_X = N_BLOCKS + 1.0  # грубо, просто чтобы хватало места

# Начальные условия
INITIAL_DISPLACEMENT = 0.5    # м
DISPLACED_BLOCK_INDEX = 0      # какой блок отодвигаем
DAMPING = 0.15                 # демпфирование
SETTLE_TIME = 5.0              # секунд, дать системе "успокоиться"

# Параметры симуляции
DT = 0.0005                    # шаг интегрирования (с)
SIM_TIME = 60.0                # время симуляции (с)
TARGET_BLOCK = 80              # для графиков

# Вывод
OUTPUT_CSV = "positions_relative_eq.csv"