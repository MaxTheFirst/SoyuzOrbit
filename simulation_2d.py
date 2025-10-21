# simulation_2d.py
import numpy as np
import pandas as pd
from block_2d import Block2D
import config

class ChainSimulation2D:
    """
    Управляет симуляцией 2D сетки блоков и пружин.
    """
    
    def __init__(self, masses: np.ndarray, spring_constants: np.ndarray, 
                 spacings_x: np.ndarray, spacings_y: np.ndarray):
        self.masses = masses
        self.spring_constants = spring_constants
        self.spacings_x = spacings_x
        self.spacings_y = spacings_y
        
        # Проверяем размеры
        self._validate_dimensions()
        
        self.blocks = self._create_blocks()
        self.time = 0.0
        
        # Предварительно вычисляем равновесные позиции
        self.equilibrium_positions = self._compute_equilibrium_positions()
        
    def _validate_dimensions(self):
        """Проверяет соответствие размеров массивов."""
        print("Validating system dimensions...")
        print(f"Expected blocks: {config.NUM_BLOCKS_X}×{config.NUM_BLOCKS_Y}")
        print(f"Masses shape: {self.masses.shape}")
        print(f"Spring constants shape: {self.spring_constants.shape}")
        print(f"Spacings X shape: {self.spacings_x.shape}")
        print(f"Spacings Y shape: {self.spacings_y.shape}")
        
        print("All dimensions are correct!")
        
    def _compute_equilibrium_positions(self):
        """Вычисляет равновесные позиции всех блоков."""
        equilibrium = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y, 2))
        
        for i in range(config.NUM_BLOCKS_X):
            for j in range(config.NUM_BLOCKS_Y):
                # Равновесная позиция блока (i,j)
                pos_x = np.sum(self.spacings_x[:i+1, j])
                pos_y = np.sum(self.spacings_y[i, :j+1])
                equilibrium[i, j] = [pos_x, pos_y]
        
        return equilibrium
        
    def _create_blocks(self) -> np.ndarray:
        """Создает 2D сетку блоков в равновесных позициях."""
        print(f"Creating {config.NUM_BLOCKS_X}×{config.NUM_BLOCKS_Y} blocks...")
        blocks = np.empty((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y), dtype=object)
        
        # Создаем равновесные позиции
        for i in range(config.NUM_BLOCKS_X):
            for j in range(config.NUM_BLOCKS_Y):
                # Равновесная позиция блока (i,j)
                pos_x = np.sum(self.spacings_x[:i+1, j])
                pos_y = np.sum(self.spacings_y[i, :j+1])
                initial_position = np.array([pos_x, pos_y], dtype=np.float64)
                blocks[i, j] = Block2D(self.masses[i, j], initial_position)
        
        print("Blocks created successfully!")
        return blocks
    
    def _get_positions_array(self) -> np.ndarray:
        """Возвращает массив всех позиций блоков."""
        positions = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y, 2))
        for i in range(config.NUM_BLOCKS_X):
            for j in range(config.NUM_BLOCKS_Y):
                positions[i, j] = self.blocks[i, j].position
        return positions
    
    def _get_velocities_array(self) -> np.ndarray:
        """Возвращает массив всех скоростей блоков."""
        velocities = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y, 2))
        for i in range(config.NUM_BLOCKS_X):
            for j in range(config.NUM_BLOCKS_Y):
                velocities[i, j] = self.blocks[i, j].velocity
        return velocities
    
    def _calculate_forces(self) -> np.ndarray:
        """Рассчитывает силы для всех блоков с правильной физикой."""
        forces = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y, 2))
        positions = self._get_positions_array()
        
        # Вычисляем смещения от равновесия
        displacements = positions - self.equilibrium_positions
        
        # Силы от горизонтальных пружин (X-направление)
        for i in range(config.NUM_BLOCKS_X):
            for j in range(config.NUM_BLOCKS_Y):
                force_x = 0.0
                force_y = 0.0
                
                # Горизонтальные соседи (пружины по X)
                if i > 0:  # Левый сосед
                    k_left = self.spring_constants[i, j, 0]
                    dx = displacements[i, j, 0] - displacements[i-1, j, 0]
                    force_x += k_left * dx
                
                if i < config.NUM_BLOCKS_X - 1:  # Правый сосед
                    k_right = self.spring_constants[i+1, j, 0]
                    dx = displacements[i, j, 0] - displacements[i+1, j, 0]
                    force_x += k_right * dx
                
                # Вертикальные соседи (пружины по Y)
                if j > 0:  # Верхний сосед
                    k_top = self.spring_constants[i, j, 1]
                    dy = displacements[i, j, 1] - displacements[i, j-1, 1]
                    force_y += k_top * dy
                
                if j < config.NUM_BLOCKS_Y - 1:  # Нижний сосед
                    k_bottom = self.spring_constants[i, j+1, 1]
                    dy = displacements[i, j, 1] - displacements[i, j+1, 1]
                    force_y += k_bottom * dy
                
                # Граничные условия - пружины к стенам
                if i == 0:  # Левая стена
                    k_wall = self.spring_constants[0, j, 0]
                    dx = displacements[0, j, 0]  # Смещение от стены (стена на 0)
                    force_x += k_wall * dx
                
                if i == config.NUM_BLOCKS_X - 1:  # Правая стена
                    k_wall = self.spring_constants[config.NUM_BLOCKS_X, j, 0]
                    dx = displacements[i, j, 0]  # Смещение от стены
                    force_x += k_wall * dx
                
                if j == 0:  # Верхняя стена
                    k_wall = self.spring_constants[i, 0, 1]
                    dy = displacements[i, 0, 1]  # Смещение от стены
                    force_y += k_wall * dy
                
                if j == config.NUM_BLOCKS_Y - 1:  # Нижняя стена
                    k_wall = self.spring_constants[i, config.NUM_BLOCKS_Y, 1]
                    dy = displacements[i, j, 1]  # Смещение от стены
                    force_y += k_wall * dy
                
                forces[i, j, 0] = -force_x  # Отрицательный знак - сила возвращает к равновесию
                forces[i, j, 1] = -force_y
        
        # Добавляем затухание (сила трения, пропорциональная скорости)
        if config.ENABLE_DAMPING:
            velocities = self._get_velocities_array()
            forces -= config.DAMPING_COEFFICIENT * velocities
        
        return forces
    
    def run(self):
        """Запускает главный цикл симуляции."""
        print("Starting 2D simulation...")
        print(f"System size: {config.NUM_BLOCKS_X}×{config.NUM_BLOCKS_Y}")
        print(f"Duration: {config.SIMULATION_DURATION}s")
        print(f"Time step: {config.TIME_STEP}s")
        
        # Проверяем индексы смещаемого блока
        if (config.BLOCK_TO_DISPLACE_X >= config.NUM_BLOCKS_X or 
            config.BLOCK_TO_DISPLACE_Y >= config.NUM_BLOCKS_Y):
            raise ValueError(f"Block to displace ({config.BLOCK_TO_DISPLACE_X}, {config.BLOCK_TO_DISPLACE_Y}) "
                           f"is out of bounds for system size {config.NUM_BLOCKS_X}×{config.NUM_BLOCKS_Y}")
        
        # Начальное смещение (от равновесной позиции)
        displace_i = config.BLOCK_TO_DISPLACE_X
        displace_j = config.BLOCK_TO_DISPLACE_Y
        
        # Получаем равновесную позицию и добавляем смещение
        eq_pos = self.equilibrium_positions[displace_i, displace_j]
        self.blocks[displace_i, displace_j].position = eq_pos + np.array([
            config.INITIAL_DISPLACEMENT_X, 
            config.INITIAL_DISPLACEMENT_Y
        ])
        
        print(f"Displaced block at ({displace_i}, {displace_j}) from {eq_pos} to {self.blocks[displace_i, displace_j].position}")
        
        # Подготовка данных для записи
        log_interval = 1.0 / config.SAMPLES_PER_SECOND
        next_log_time = 0.0
        
        # Создаем файл для записи
        with open(config.CSV_FILENAME, 'w') as f:
            # Записываем заголовок
            f.write('time,block_x,block_y,position_x,position_y,velocity_x,velocity_y,acceleration_x,acceleration_y\n')
            
            step_count = 0
            last_progress = 0
            
            while self.time <= config.SIMULATION_DURATION:
                # Расчет сил
                forces = self._calculate_forces()
                
                # Обновление всех блоков
                for i in range(config.NUM_BLOCKS_X):
                    for j in range(config.NUM_BLOCKS_Y):
                        self.blocks[i, j].update(forces[i, j], config.TIME_STEP)
                
                # Запись данных
                if self.time >= next_log_time:
                    self._log_data(f)
                    next_log_time += log_interval
                    
                    # Обновляем прогресс каждые 10%
                    progress = int(self.time / config.SIMULATION_DURATION * 100)
                    if progress >= last_progress + 10:
                        print(f"Progress: {progress}%")
                        last_progress = progress
                
                self.time += config.TIME_STEP
                step_count += 1
                
                # Проверка на численную нестабильность
                if step_count % 1000 == 0:
                    max_velocity = np.max(np.abs(self._get_velocities_array()))
                    if max_velocity > 1e6:  # Если скорости стали слишком большими
                        print(f"Numerical instability detected! Max velocity: {max_velocity}")
                        print("Stopping simulation...")
                        break
        
        print(f"\nSimulation finished! Data saved to {config.CSV_FILENAME}")
        print(f"Total steps: {step_count}")
        print(f"Final time: {self.time:.2f}s")
    
    def _log_data(self, file_handle):
        """Записывает данные всех блоков в файл."""
        for i in range(config.NUM_BLOCKS_X):
            for j in range(config.NUM_BLOCKS_Y):
                block = self.blocks[i, j]
                file_handle.write(
                    f"{self.time:.4f},"
                    f"{i},{j},"
                    f"{block.position[0]:.6f},{block.position[1]:.6f},"
                    f"{block.velocity[0]:.6f},{block.velocity[1]:.6f},"
                    f"{block.acceleration[0]:.6f},{block.acceleration[1]:.6f}\n"
                )