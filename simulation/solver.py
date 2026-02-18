import numpy as np


class LaplaceSolver:
    def __init__(self, method='gauss_seidel'):
        self.method = method

    def solve(self, grid, max_iter, tolerance):
        h_m = grid.cfg.resolution / 1000.0
        max_v = grid.cfg.user.max_voltage

        for k in range(max_iter):
            old_phi = grid.potential.copy()

            # Используем omega = 1.0 (чистый Гаусс-Зейдель) для максимальной стабильности
            # пока не найдем причину ошибки.
            self._step_gauss_seidel(grid.potential, grid.rho, grid.fixed_mask, h_m, grid.eps0, max_v)

            error = np.max(np.abs(grid.potential - old_phi))

            # Раз в 500 итераций пишем прогресс
            # if k % 500 == 0 and k > 0:
            #     print(f"  > Решатель: шаг {k}, текущая ошибка: {error:.2e}")

            if error < tolerance:
                print(f"  > Сходимость достигнута на шаге {k}")
                return True

        print(f"  > ВНИМАНИЕ: Превышен лимит! Ошибка остановилась на: {error:.2e}")
        return False

    @staticmethod
    @staticmethod
    def _step_gauss_seidel(phi, rho, mask, h_meters, eps0, max_v):
        """
        Стабильный метод SOR с ограничением значений
        """
        # Уменьшаем омегу для стабильности. 1.1-1.3 - безопасно.
        # 1.7 было слишком много для этой плотности заряда.
        omega = 1.

        top = phi[0:-2, 1:-1]
        bottom = phi[2:, 1:-1]
        left = phi[1:-1, 0:-2]
        right = phi[1:-1, 2:]

        source_term = (rho[1:-1, 1:-1] * (h_meters ** 2)) / eps0

        target_values = 0.25 * (top + bottom + left + right + source_term)

        current_values = phi[1:-1, 1:-1]
        new_values = current_values + omega * (target_values - current_values)

        # ПРЕДОХРАНИТЕЛЬ: Ограничиваем значения диапазоном [-max_v, max_v]
        # Это не даст решению уйти в бесконечность (overflow)
        new_values = np.clip(new_values, -abs(max_v), abs(max_v))

        internal_mask = mask[1:-1, 1:-1]
        phi[1:-1, 1:-1][~internal_mask] = new_values[~internal_mask]