class Block:
    """
    Представляет один блок (массу) в цепочке.
    """

    def __init__(self, mass: float, initial_position: float):
        self.mass = mass
        self.position = initial_position
        self.velocity = 0.0
        self.acceleration = 0.0

    def update(self, force: float, time_step: float):
        """
        Обновляет состояние блока (положение, скорость, ускорение)
        с использованием алгоритма Верле (Velocity Verlet).
        """
        # Обновляем положение на основе текущей скорости и ускорения
        self.position += self.velocity * time_step + 0.5 * self.acceleration * (time_step ** 2)

        # Рассчитываем новое ускорение на основе новой силы
        new_acceleration = force / self.mass

        # Обновляем скорость, используя среднее от старого и нового ускорения
        self.velocity += 0.5 * (self.acceleration + new_acceleration) * time_step

        # Сохраняем новое ускорение
        self.acceleration = new_acceleration