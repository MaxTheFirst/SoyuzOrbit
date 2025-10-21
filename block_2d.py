# block_2d.py
import numpy as np

class Block2D:
    """
    Представляет один блок в 2D сетке с упрощенной физикой.
    """
    
    def __init__(self, mass: float, initial_position: np.ndarray):
        self.mass = mass
        self.position = initial_position.astype(np.float64).copy()
        self.velocity = np.zeros(2, dtype=np.float64)
        self.acceleration = np.zeros(2, dtype=np.float64)
    
    def update(self, force: np.ndarray, time_step: float):
        """
        Простое обновление через метод Эйлера для стабильности.
        """
        # Новое ускорение
        new_acceleration = force / self.mass
        
        # Обновление скорости (половинный шаг)
        self.velocity += 0.5 * (self.acceleration + new_acceleration) * time_step
        
        # Обновление положения
        self.position += self.velocity * time_step
        
        # Сохраняем ускорение
        self.acceleration = new_acceleration