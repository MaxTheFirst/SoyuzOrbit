# D2/simulation_2d.py
import numpy as np
import csv
import config


# --- Логгеры (остаются без изменений) ---
class DataLogger:
    def __init__(self, filename: str):
        self.file_handle = open(filename, 'w', newline='')
        self.writer = csv.writer(self.file_handle)
        self.writer.writerow([
            'time', 'block_y', 'block_x', 'pos_x', 'pos_y',
            'vel_x', 'vel_y', 'acc_x', 'acc_y', 'kinetic_energy'
        ])
        print(f"DataLogger_2D: Запись в {filename}...")

    def log_snapshot_2d(self, time: float, num_y: int, num_x: int,
                        pos: np.ndarray, vel: np.ndarray, acc: np.ndarray, ke: np.ndarray):
        rows = []
        time_str = f"{time:.4f}"
        for y in range(num_y):
            for x in range(num_x):
                rows.append([
                    time_str, y, x,
                    f"{pos[y, x, 0]:.6f}", f"{pos[y, x, 1]:.6f}",
                    f"{vel[y, x, 0]:.6f}", f"{vel[y, x, 1]:.6f}",
                    f"{acc[y, x, 0]:.6f}", f"{acc[y, x, 1]:.6f}",
                    f"{ke[y, x]:.6f}"
                ])
        self.writer.writerows(rows)

    def close(self):
        self.file_handle.close()


class EnergyLogger:
    def __init__(self, filename: str):
        self.file_handle = open(filename, 'w', newline='')
        self.writer = csv.writer(self.file_handle)
        self.writer.writerow(['time', 'kinetic_energy', 'potential_energy', 'total_energy'])
        print(f"EnergyLogger_2D: Запись в {filename}...")

    def log(self, time: float, ke: float, pe: float, total_e: float):
        self.writer.writerow([f"{time:.4f}", f"{ke:.6f}", f"{pe:.6f}", f"{total_e:.6f}"])

    def close(self): self.file_handle.close()


# --- Конец логгеров ---


class GridSimulation:
    """
    Управляет симуляцией 2D-сетки блоков и пружин
    для ПРОДОЛЬНЫХ волн (КОРРЕКТНАЯ ВЕРСИЯ).
    """

    def __init__(self, masses: np.ndarray, spring_constants_x: np.ndarray,
                 spring_constants_y: np.ndarray, equilibrium_positions: np.ndarray):

        # --- 1. Размеры ---
        self.num_y, self.num_x = masses.shape
        self.spacing = config.DEFAULT_BLOCK_SPACING

        # --- 2. Статические свойства ---
        self.equilibrium_positions = equilibrium_positions  # (Y, X, 2)
        self.masses_2d = masses  # (Y, X)
        self.masses_3d = masses.reshape(self.num_y, self.num_x, 1)  # (Y, X, 1)
        self.spring_constants_x = spring_constants_x  # (Y, X+1)
        self.spring_constants_y = spring_constants_y  # (Y+1, X)

        # --- 3. Динамические массивы состояния ---
        self.positions = self.equilibrium_positions.copy()  # (Y, X, 2)
        self.velocities = np.zeros_like(self.positions)  # (Y, X, 2)
        self.accelerations = np.zeros_like(self.positions)  # (Y, X, 2)

        # --- 4. Логгеры и время ---
        self.time = 0.0
        self.data_logger = DataLogger(config.CSV_SIMULATION_FILENAME)
        self.energy_logger = EnergyLogger(config.CSV_ENERGY_DATA_FILENAME)

        # --- 5. Энергия ---
        self.kinetic_energies = np.zeros_like(self.masses_2d)
        self.total_kinetic_energy = 0.0
        # Массивы для хранения PE *каждой* пружины
        self.pe_springs_x = np.zeros_like(self.spring_constants_x)  # (Y, X+1)
        self.pe_springs_y = np.zeros_like(self.spring_constants_y)  # (Y+1, X)
        self.total_potential_energy = 0.0
        self.total_energy = 0.0

        print("2D GridSimulation (Longitudinal) initialized.")

        # D2/simulation_2d.py

    def _calculate_forces_and_pe(self, current_time: float) -> np.ndarray:
        """
        Рассчитывает 2D-вектор силы И потенциальную энергию.
        Это "настоящая" 2D-векторная физика. (ИСПРАВЛЕННАЯ ВЕРСИЯ)
        """

        total_forces = np.zeros_like(self.positions)  # (Y, X, 2)
        total_pe = 0.0
        epsilon = 1e-9  # Для избежания деления на ноль

        # --- A. Горизонтальные пружины (Y, X+1) ---

        # 1. Создаем (Y, X+2, 2) массив положений, включая "стены"
        pos_with_walls_x = np.zeros((self.num_y, self.num_x + 2, 2))
        pos_with_walls_x[:, 1:-1, :] = self.positions  # Вставляем подвижные блоки
        # Левая стена (неподвижна, в равновесии)
        pos_with_walls_x[:, 0, 1] = self.equilibrium_positions[:, 0, 1]  # y-коорд.
        # Правая стена (неподвижна, в равновесии)
        pos_with_walls_x[:, -1, 0] = (self.num_x + 1.0) * self.spacing
        pos_with_walls_x[:, -1, 1] = self.equilibrium_positions[:, -1, 1]  # y-коорд.

        # 2. Векторы пружин (Y, X+1, 2) [V_j = P_{j+1} - P_j]
        vectors_x = pos_with_walls_x[:, 1:, :] - pos_with_walls_x[:, :-1, :]

        # 3. Длины пружин (Y, X+1)
        lengths_x = np.linalg.norm(vectors_x, axis=2)

        # 4. Деформация (L - L0)
        deformations_x = lengths_x - self.spacing

        # 5. Потенциальная энергия (0.5 * k * dL^2)
        self.pe_springs_x = 0.5 * self.spring_constants_x * (deformations_x ** 2)
        total_pe += np.sum(self.pe_springs_x)

        # 6. Величина силы (k * dL)
        force_magnitudes_x = self.spring_constants_x * deformations_x

        # 7. Векторы силы (F_mag * V / L)
        force_vectors_x = force_magnitudes_x[..., np.newaxis] * (vectors_x / (lengths_x[..., np.newaxis] + epsilon))

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # 8. Применяем силы к блокам
        # force_vectors_x[j] = сила пружины j (между j-1 и j)
        # Она тянет блок j-1 ВПРАВО (+)
        # Она тянет блок j ВЛЕВО (-)
        # total_forces[j] = F_vec[j+1] (от правой пружины) - F_vec[j] (от левой пружины)

        total_forces += force_vectors_x[:, 1:, :]  # Силы от пружин справа (j+1)
        total_forces -= force_vectors_x[:, :-1, :]  # Силы от пружин слева (j)
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

        # --- B. Вертикальные пружины (Y+1, X) ---

        # 1. Создаем (Y+2, X, 2) массив положений, включая "стены"
        pos_with_walls_y = np.zeros((self.num_y + 2, self.num_x, 2))
        pos_with_walls_y[1:-1, :, :] = self.positions  # Вставляем подвижные блоки
        # Верхняя стена
        pos_with_walls_y[0, :, 0] = self.equilibrium_positions[0, :, 0]  # x-коорд.
        # Нижняя стена
        pos_with_walls_y[-1, :, 0] = self.equilibrium_positions[-1, :, 0]  # x-коорд.
        pos_with_walls_y[-1, :, 1] = (self.num_y + 1.0) * self.spacing

        # 2. Векторы пружин (Y+1, X, 2)
        vectors_y = pos_with_walls_y[1:, :, :] - pos_with_walls_y[:-1, :, :]

        # 3. Длины пружин (Y+1, X)
        lengths_y = np.linalg.norm(vectors_y, axis=2)

        # 4. Деформация (L - L0)
        deformations_y = lengths_y - self.spacing

        # 5. Потенциальная энергия
        self.pe_springs_y = 0.5 * self.spring_constants_y * (deformations_y ** 2)
        total_pe += np.sum(self.pe_springs_y)

        # 6. Величина силы (k * dL)
        force_magnitudes_y = self.spring_constants_y * deformations_y

        # 7. Векторы силы
        force_vectors_y = force_magnitudes_y[..., np.newaxis] * (vectors_y / (lengths_y[..., np.newaxis] + epsilon))

        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # 8. Применяем силы к блокам
        # force_vectors_y[i] = сила пружины i (между i-1 и i)
        # Она тянет блок i-1 ВНИЗ (+)
        # Она тянет блок i ВВЕРХ (-)
        # total_forces[i] = F_vec[i+1] (от нижней пружины) - F_vec[i] (от верхней пружины)

        total_forces += force_vectors_y[1:, :, :]  # Силы от пружин снизу (i+1)
        total_forces -= force_vectors_y[:-1, :, :]  # Силы от пружин сверху (i)
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

        self.total_potential_energy = total_pe

        # --- C. Внешние силы ---
        if config.ENABLE_DAMPING:
            total_forces -= config.DAMPING_COEFFICIENT * self.velocities

        return total_forces

    def _update_state(self, time_step: float, current_time: float):
        """
        Обновляет состояние всех блоков (алгоритм Верле, 2D-векторизованно).
        """
        # 1. Обновляем положения
        self.positions += self.velocities * time_step + 0.5 * self.accelerations * (time_step ** 2)

        # 2. Рассчитываем НОВЫЕ силы И НОВУЮ PE
        new_forces = self._calculate_forces_and_pe(current_time + time_step)

        # 3. Рассчитываем новые ускорения
        new_accelerations = new_forces / self.masses_3d

        # 4. Обновляем скорости
        self.velocities += 0.5 * (self.accelerations + new_accelerations) * time_step

        # 5. Сохраняем новое ускорение
        self.accelerations = new_accelerations

    def _update_energies(self):
        """
        Обновляет ТОЛЬКО кинетическую энергию.
        (Потенциальная теперь считается вместе с силами)
        """
        # v^2 = vx^2 + vy^2
        v_sq = np.sum(self.velocities ** 2, axis=2)  # (Y, X, 2) -> (Y, X)
        self.kinetic_energies = 0.5 * self.masses_2d * v_sq
        self.total_kinetic_energy = np.sum(self.kinetic_energies)

        # Обновляем полную энергию
        self.total_energy = self.total_kinetic_energy + self.total_potential_energy

    def run(self):
        """Запускает главный цикл симуляции."""
        print("Starting 2D simulation (Corrected Vector Physics)...")

        if not config.ENABLE_DRIVING_FORCE:
            y_idx, x_idx = config.BLOCK_TO_DISPLACE_2D
            disp_x, disp_y = config.INITIAL_DISPLACEMENT_2D
            self.positions[y_idx, x_idx, 0] += disp_x
            self.positions[y_idx, x_idx, 1] += disp_y
            print(f"Displaced block ({y_idx}, {x_idx}) by ({disp_x}, {disp_y})")

        log_interval = 1.0 / config.SAMPLES_PER_SECOND
        next_log_time = 0.0

        # --- Рассчитываем начальное состояние ---
        # 1. Рассчитываем начальные силы и PE
        initial_forces = self._calculate_forces_and_pe(self.time)
        # 2. Рассчитываем начальную KE (должна быть 0)
        self._update_energies()
        # 3. Рассчитываем начальное ускорение
        self.accelerations = initial_forces / self.masses_3d
        # ---

        while self.time <= config.SIMULATION_DURATION:
            self._update_state(config.TIME_STEP, self.time)
            # PE уже обновлена внутри _update_state, обновляем KE
            self._update_energies()

            if self.time >= next_log_time:
                self.data_logger.log_snapshot_2d(
                    self.time, self.num_y, self.num_x,
                    self.positions, self.velocities,
                    self.accelerations, self.kinetic_energies
                )
                self.energy_logger.log(
                    self.time,
                    self.total_kinetic_energy,
                    self.total_potential_energy,
                    self.total_energy
                )

                print(
                    f"Time: {self.time:.2f}s / {config.SIMULATION_DURATION:.2f}s | "
                    f"Total Energy: {self.total_energy:.6f} J",
                    end='\r'
                )
                next_log_time += log_interval

            self.time += config.TIME_STEP

        self.data_logger.close()
        self.energy_logger.close()
        print(
            f"\n2D Simulation finished. Data saved to {config.CSV_SIMULATION_FILENAME} and {config.CSV_ENERGY_DATA_FILENAME}.")
