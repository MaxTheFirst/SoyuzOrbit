from math import floor, sqrt, pi, log10


def __round_to_1(x):
    return pow(10, int(floor(log10(abs(x)))))  # Выбирает ближайшую снизу степень десятки


SIMULATION_MODE = '1D'

# --- 1D ПАРАМЕТРЫ ---
NUM_BLOCKS = 100  # Количество блоков (для 1D)

# Выберите режим генерации: 'uniform' (все одинаковые) или 'random' (случайные)
GENERATION_MODE = 'uniform'

DEFAULT_MASS = 1.0  # Масса одного блока (кг)
DEFAULT_SPRING_CONSTANT = 2.0  # Жесткость пружин (Н/м)
DEFAULT_BLOCK_SPACING = 1.0  # Равновесное расстояние между блоками (м)

# Параметры симуляции
SIMULATION_DURATION = 60.0  # Длительность симуляции (секунды)
SAMPLES_PER_SECOND = 60  # Количество записей данных в секунду
# Пересчитываем TIME_STEP, так как он зависит от k и m
TIME_STEP = __round_to_1(sqrt(
    DEFAULT_MASS / DEFAULT_SPRING_CONSTANT) * 2 * pi / 1000)  # Шаг по времени для расчетов (должен быть маленьким для стабильности)
DECIMAL_PLACES = 9

# Начальные условия
BLOCK_TO_DISPLACE = 0  # Индекс блока для начального смещения (первый блок)
INITIAL_DISPLACEMENT = 0.5  # Начальное смещение от положения равновесия (м)

# --- Флаг и параметры для затухания (трения) ---
ENABLE_DAMPING = False  # Поставьте False, чтобы отключить трение
if ENABLE_DAMPING:
    # Это примерное время в секундах, за которое амплитуда волны упадёт в ~2.7 раза.
    DECAY_TIME_SECONDS = 10.0

    # Коэффициент затухания рассчитывается автоматически из времени
    DAMPING_COEFFICIENT = (2 * DEFAULT_MASS) / DECAY_TIME_SECONDS

ENABLE_DRIVING_FORCE = False  # Поставьте True, чтобы включить внешнюю силу
if ENABLE_DRIVING_FORCE:
    DRIVEN_BLOCK_INDEX = 0  # Индекс блока, который мы будем "раскачивать"
    DRIVING_AMPLITUDE = 1.0  # Сила (в Ньютонах), с которой мы раскачиваем
    DRIVING_FREQUENCY_HERTZ = 0.01  # Частота (в Герцах) внешней силы

VISUALIZATION_SCALE = 1.0

# Выходной файл
CSV_SIMULATION_FILENAME = 'simulation_data.csv'
CSV_ENERGY_DATA_FILENAME = 'energy_data.csv'

# --- 2D ПАРАМЕТРЫ ---
NUM_BLOCKS_X = 10  # Количество блоков по горизонтали (для 2D)
NUM_BLOCKS_Y = 10  # Количество блоков по вертикали (для 2D)
BLOCK_TO_DISPLACE_2D = (0, 0)  # (Y, X) индекс блока для смещения
INITIAL_DISPLACEMENT_2D = (-0.5, -0.5) # (x_disp, y_disp) Сместить на 1.5 по x, 0.0 по y
