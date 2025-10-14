# system_builder.py
import random
import config


def print_generated_data(masses: list[float], spring_constants: list[float], spacings: list[float]):
    # Выводим сгенерированные значения для информации
    print("\n--- Generated Masses ---")
    print([f"{m:.2f}" for m in masses])
    print("\n--- Generated Spring Constants ---")
    print([f"{k:.2f}" for k in spring_constants])
    print("\n--- Generated Spacings ---")
    print([f"{s:.2f}" for s in spacings])
    print("-" * 30 + "\n")


def generate_uniform_properties(num_blocks: int):
    """
    Создает списки со свойствами, как в предыдущей реализации (все одинаковые).
    """
    print("Generating UNIFORM system properties...")
    # Задаем "стандартные" значения здесь
    masses = [config.DEFAULT_MASS] * num_blocks
    # Нужно N+1 пружин и расстояний (включая те, что крепятся к стенам)
    spring_constants = [config.DEFAULT_SPRING_CONSTANT] * (num_blocks + 1)
    spacings = [config.DEFAULT_BLOCK_SPACING] * (num_blocks + 1)

    # Выводим сгенерированные значения для информации
    print_generated_data(masses, spring_constants, spacings)

    return masses, spring_constants, spacings


def generate_random_properties(num_blocks: int):
    """
    Создает списки со случайными свойствами в заданных диапазонах.
    """
    print("Generating RANDOM system properties...")
    masses = [random.uniform(config.DEFAULT_MASS * 0.8, config.DEFAULT_MASS * 1.2) for _ in range(num_blocks)]
    spring_constants = [random.uniform(config.DEFAULT_SPRING_CONSTANT * 0.8, config.DEFAULT_SPRING_CONSTANT * 1.2) for _
                        in range(num_blocks + 1)]
    spacings = [random.uniform(config.DEFAULT_BLOCK_SPACING * 0.8, config.DEFAULT_BLOCK_SPACING * 1.2) for _ in
                range(num_blocks + 1)]

    # Выводим сгенерированные значения для информации
    print_generated_data(masses, spring_constants, spacings)

    return masses, spring_constants, spacings


def build_system():
    """
    Главная функция-конструктор, которая вызывает нужный генератор.
    """
    if config.GENERATION_MODE == 'uniform':
        return generate_uniform_properties(config.NUM_BLOCKS)
    elif config.GENERATION_MODE == 'random':
        return generate_random_properties(config.NUM_BLOCKS)
    else:
        raise ValueError(f"Unknown GENERATION_MODE: {config.GENERATION_MODE}")
