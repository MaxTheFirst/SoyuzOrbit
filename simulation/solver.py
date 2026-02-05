import numpy as np


class LaplaceSolver:
    def __init__(self, method='gauss_seidel'):
        self.method = method

    def solve(self, grid, max_iter, tolerance):
        """
        grid: объект SimulationGrid
        """
        print(f"Запуск решателя {self.method}...")

        for k in range(max_iter):
            # Сохраняем старую копию для проверки сходимости
            old_potential = grid.potential.copy()

            # --- ЯДРО ВЫЧИСЛЕНИЙ ---
            if self.method == 'gauss_seidel':
                self._step_gauss_seidel(grid.potential, grid.fixed_mask)
            elif self.method == 'jacobi':
                pass

            # Проверка сходимости
            diff = np.max(np.abs(grid.potential - old_potential))
            if diff < tolerance:
                print(f"Сошлось за {k} итераций. Точность: {diff}")
                return True

        print("Превышен лимит итераций!")
        return False

    @staticmethod
    def _step_gauss_seidel(phi, mask):
        """
        Один шаг итерации.
        Используем векторизацию NumPy для ускорения (вместо медленных циклов Python).
        Это аналог 'Креста', но сразу для всей матрицы.
        """
        # Сдвигаем массив в 4 стороны
        # phi[1:-1, 1:-1] - это внутренняя часть сетки (без границ)

        # Соседи
        top = phi[0:-2, 1:-1]
        bottom = phi[2:, 1:-1]
        left = phi[1:-1, 0:-2]
        right = phi[1:-1, 2:]

        # Вычисляем среднее
        new_values = 0.25 * (top + bottom + left + right)

        # Обновляем ТОЛЬКО те ячейки, которые НЕ являются электродами (mask == False)
        # Нам нужно вырезать соответствующий кусок маски для внутренней части
        internal_mask = mask[1:-1, 1:-1]

        # Применяем изменения
        # (Это немного упрощенный Jacobi-подобный подход в numpy,
        # для настоящего Гаусса-Зейделя "на лету" нужны циклы или Numba,
        # но для начала этого хватит)
        phi[1:-1, 1:-1][~internal_mask] = new_values[~internal_mask]