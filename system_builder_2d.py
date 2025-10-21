# system_builder_2d.py
import numpy as np
import config

def build_2d_system():
    """
    Строит 2D систему блоков и пружин.
    """
    if config.GENERATION_MODE == 'uniform':
        return generate_uniform_2d_properties()
    elif config.GENERATION_MODE == 'random':
        return generate_random_2d_properties()
    else:
        raise ValueError(f"Unknown GENERATION_MODE: {config.GENERATION_MODE}")

def generate_uniform_2d_properties():
    """
    Создает однородную 2D систему.
    """
    print("Generating UNIFORM 2D system properties...")
    
    # Массы (NUM_BLOCKS_X × NUM_BLOCKS_Y)
    masses = np.full((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y), config.DEFAULT_MASS)
    
    # Жесткости пружин (NUM_BLOCKS_X+1 × NUM_BLOCKS_Y+1 × 2)
    # Последняя размерность: 0 - горизонтальные, 1 - вертикальные
    spring_constants = np.full((config.NUM_BLOCKS_X + 1, config.NUM_BLOCKS_Y + 1, 2), 
                              config.DEFAULT_SPRING_CONSTANT)
    
    # Расстояния между блоками
    # spacings_x: между блоками по X (NUM_BLOCKS_X+1 × NUM_BLOCKS_Y)
    spacings_x = np.full((config.NUM_BLOCKS_X + 1, config.NUM_BLOCKS_Y), config.DEFAULT_BLOCK_SPACING_X)
    
    # spacings_y: между блоками по Y (NUM_BLOCKS_X × NUM_BLOCKS_Y+1)
    spacings_y = np.full((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y + 1), config.DEFAULT_BLOCK_SPACING_Y)
    
    print_system_info(masses, spring_constants, spacings_x, spacings_y)
    
    return masses, spring_constants, spacings_x, spacings_y

def generate_random_2d_properties():
    """
    Создает случайную 2D систему.
    """
    print("Generating RANDOM 2D system properties...")
    
    # Массы
    masses = np.random.uniform(
        config.DEFAULT_MASS * 0.8, 
        config.DEFAULT_MASS * 1.2, 
        (config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y)
    )
    
    # Жесткости пружин
    spring_constants = np.random.uniform(
        config.DEFAULT_SPRING_CONSTANT * 0.8,
        config.DEFAULT_SPRING_CONSTANT * 1.2,
        (config.NUM_BLOCKS_X + 1, config.NUM_BLOCKS_Y + 1, 2)
    )
    
    # Расстояния
    spacings_x = np.random.uniform(
        config.DEFAULT_BLOCK_SPACING_X * 0.8,
        config.DEFAULT_BLOCK_SPACING_X * 1.2,
        (config.NUM_BLOCKS_X + 1, config.NUM_BLOCKS_Y)
    )
    spacings_y = np.random.uniform(
        config.DEFAULT_BLOCK_SPACING_Y * 0.8,
        config.DEFAULT_BLOCK_SPACING_Y * 1.2,
        (config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y + 1)
    )
    
    print_system_info(masses, spring_constants, spacings_x, spacings_y)
    
    return masses, spring_constants, spacings_x, spacings_y

def print_system_info(masses, spring_constants, spacings_x, spacings_y):
    """Выводит информацию о системе."""
    print(f"Masses shape: {masses.shape}")
    print(f"Spring constants shape: {spring_constants.shape}")
    print(f"X-spacings shape: {spacings_x.shape}")
    print(f"Y-spacings shape: {spacings_y.shape}")
    print(f"Total blocks: {config.NUM_BLOCKS_X * config.NUM_BLOCKS_Y}")
    print("-" * 50)