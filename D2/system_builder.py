# D2/system_builder_2d.py
import numpy as np
import config  # Мы читаем config из корневой папки


def print_generated_data(masses: np.ndarray, num_x: int, num_y: int, spring_constants_x: np.ndarray,
                         spring_constants_y: np.ndarray, equilibrium_positions: np.ndarray) -> None:
    # Выводим сгенерированные значения для информации
    print(f"Grid Size (Y, X): ({num_y}, {num_x})")
    print(f"Masses shape: {masses.shape}")
    print(f"Equilibrium Positions shape: {equilibrium_positions.shape}")
    print(f"Springs X shape: {spring_constants_x.shape}")
    print(f"Springs Y shape: {spring_constants_y.shape}")
    print("\n--- Generated Masses ---")
    print(masses)
    print("\n--- Generated Spring Constants ---")
    print(spring_constants_x)
    print(spring_constants_y)
    print("\n--- Generated Spacings ---")
    print(equilibrium_positions)
    print("-" * 30 + "\n")


def generate_uniform_properties_2d(num_x: int, num_y: int):
    """
    Создает 2D-массивы со свойствами (все одинаковые).
    """
    print("Generating UNIFORM 2D system properties...")

    # 1. Массы блоков (сетка Y, X)
    masses = np.full((num_y, num_x), config.DEFAULT_MASS)

    # 2. Горизонтальные пружины (вдоль оси X)
    # У нас N_Y рядов, в каждом N_X+1 пружина (включая крепления к стенам)
    spring_constants_x = np.full((num_y, num_x + 1), config.DEFAULT_SPRING_CONSTANT)

    # 3. Вертикальные пружины (вдоль оси Y)
    # У нас N_X столбцов, в каждом N_Y+1 пружина (включая крепления к стенам)
    spring_constants_y = np.full((num_y + 1, num_x), config.DEFAULT_SPRING_CONSTANT)

    # 4. Скелет равновесных положений (САМОЕ ВАЖНОЕ)
    # Это массив (Y, X, 2), где [i, j, 0] = x_0, а [i, j, 1] = y_0

    # Создаем 1D-оси
    x_eq = (np.arange(num_x) + 1.0) * config.DEFAULT_BLOCK_SPACING
    y_eq = (np.arange(num_y) + 1.0) * config.DEFAULT_BLOCK_SPACING

    # Создаем 2D-сетки координат
    xx, yy = np.meshgrid(x_eq, y_eq)

    # Собираем их в один (Y, X, 2) массив
    equilibrium_positions = np.stack((xx, yy), axis=-1)

    print_generated_data(masses, num_x, num_y, spring_constants_x, spring_constants_y, equilibrium_positions)

    return masses, spring_constants_x, spring_constants_y, equilibrium_positions


def generate_random_properties_2d(num_x: int, num_y: int):
    """
    Создает 2D-массивы со случайными свойствами.
    """
    print("Generating RANDOM 2D system properties...")

    # 1. Массы
    masses = np.random.uniform(config.DEFAULT_MASS * 0.8, config.DEFAULT_MASS * 1.2,
                               size=(num_y, num_x))

    # 2. Горизонтальные пружины
    spring_constants_x = np.random.uniform(config.DEFAULT_SPRING_CONSTANT * 0.8, config.DEFAULT_SPRING_CONSTANT * 1.2,
                                           size=(num_y, num_x + 1))

    # 3. Вертикальные пружины
    spring_constants_y = np.random.uniform(config.DEFAULT_SPRING_CONSTANT * 0.8, config.DEFAULT_SPRING_CONSTANT * 1.2,
                                           size=(num_y + 1, num_x))

    # 4. Скелет равновесных положений (САМОЕ ВАЖНОЕ)
    # Это массив (Y, X, 2), где [i, j, 0] = x_0, а [i, j, 1] = y_0

    # Создаем 1D-оси
    x_eq = (np.arange(num_x) + 1.0) * config.DEFAULT_BLOCK_SPACING
    y_eq = (np.arange(num_y) + 1.0) * config.DEFAULT_BLOCK_SPACING

    # Создаем 2D-сетки координат
    xx, yy = np.meshgrid(x_eq, y_eq)

    # Собираем их в один (Y, X, 2) массив
    equilibrium_positions = np.stack((xx, yy), axis=-1)

    print_generated_data(masses, num_x, num_y, spring_constants_x, spring_constants_y, equilibrium_positions)

    return masses, spring_constants_x, spring_constants_y, equilibrium_positions


def build_system_2d():
    """
    Главная функция-конструктор для 2D-системы.
    """
    num_x = config.NUM_BLOCKS_X
    num_y = config.NUM_BLOCKS_Y

    if config.GENERATION_MODE == 'uniform':
        return generate_uniform_properties_2d(num_x, num_y)
    elif config.GENERATION_MODE == 'random':
        return generate_random_properties_2d(num_x, num_y)
    else:
        raise ValueError(f"Unknown GENERATION_MODE: {config.GENERATION_MODE}")
