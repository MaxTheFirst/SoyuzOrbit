import csv

import numpy as np

import config


class DataLogger:
    """
    Управляет записью данных симуляции для КАЖДОГО БЛОКА в CSV файл.
    """

    def __init__(self, filename: str):
        self.file_handle = open(filename, 'w', newline='')
        self.writer = csv.writer(self.file_handle)
        # Записываем заголовки
        self.writer.writerow(['time', 'block_index', 'position', 'velocity', 'acceleration', 'kinetic_energy'])

    def log(self, time: float, num_blocks: int, pos_arr: np.ndarray, vel_arr: np.ndarray, acc_arr: np.ndarray,
            ke_arr: np.ndarray):
        """Записывает одну строку данных."""
        rows = []
        for i in range(num_blocks):
            rows.append([
                f"{time:.4f}",
                i,
                f"{pos_arr[i]:.6f}",
                f"{vel_arr[i]:.6f}",
                f"{acc_arr[i]:.6f}",
                f"{ke_arr[i]:.6f}"
            ])
        self.writer.writerows(rows)

    def close(self):
        """Закрывает файл."""
        self.file_handle.close()


class EnergyLogger:
    """
    Управляет записью данных об ОБЩЕЙ ЭНЕРГИИ СИСТЕМЫ в CSV файл.
    """

    def __init__(self, filename: str):
        self.file_handle = open(filename, 'w', newline='')
        self.writer = csv.writer(self.file_handle)
        self.writer.writerow(['time', 'kinetic_energy', 'potential_energy', 'total_energy'])

    def log(self, time: float, kinetic_energy: float, potential_energy: float, total_energy: float):
        """Записывает одну строку данных об энергии."""
        self.writer.writerow([
            f"{time:.4f}",
            f"{kinetic_energy:.6f}",
            f"{potential_energy:.6f}",
            f"{total_energy:.6f}"
        ])

    def close(self):
        self.file_handle.close()


class ChainSimulation:
    """
    Управляет симуляцией цепочки блоков и пружин.
    """

    def __init__(self, masses: np.ndarray, spring_constants: np.ndarray, spacings: np.ndarray):
        """
        Инициализирует симуляцию с заданными физическими свойствами.
        """
        self.masses = masses
        self.positions = np.cumsum(spacings[:-1])  # Равновесные позиции
        self.velocities = np.zeros(config.NUM_BLOCKS)
        self.accelerations = np.zeros(config.NUM_BLOCKS)

        self.spring_constants = spring_constants
        self.spacings = spacings

        self.right_wall_pos = np.sum(spacings)

        self.kinetic_energies = np.zeros(config.NUM_BLOCKS)
        self.potential_energies = np.zeros(config.NUM_BLOCKS + 1)
        self.total_kinetic_energy = 0.0
        self.total_potential_energy = 0.0
        self.total_energy = 0.0

        self.data_logger = DataLogger(config.CSV_SIMULATION_FILENAME)
        self.energy_logger = EnergyLogger(config.CSV_ENERGY_DATA_FILENAME)

        self.time = 0.0

    def _update_energies(self):
        """Рассчитывает и обновляет общую энергию системы."""
        # --- 1. Кинетическая энергия ---
        self.kinetic_energies = 0.5 * self.masses * (self.velocities ** 2)
        self.total_kinetic_energy = np.sum(self.kinetic_energies)

        # --- 2. Потенциальная энергия ---

        # Создаем массив позиций ВСЕХ точек крепления пружин
        # [левая стена, блок 0, блок 1, ..., блок N-1, правая стена]
        all_points_pos = np.concatenate(([0.0], self.positions, [self.right_wall_pos]))

        # Рассчитываем текущие длины всех N+1 пружин (pos[i+1] - pos[i])
        current_lengths = np.diff(all_points_pos)

        # Рассчитываем деформацию
        deformations = current_lengths - self.spacings

        # Рассчитываем энергию
        self.potential_energies = 0.5 * self.spring_constants * (deformations ** 2)
        self.total_potential_energy = np.sum(self.potential_energies)

        # --- 3. Полная энергия ---
        self.total_energy = self.total_kinetic_energy + self.total_potential_energy

    def _calculate_forces(self) -> np.ndarray:
        """Рассчитывает силы, действующие на каждый блок."""

        # --- 1. Готовим "соседние" массивы ---

        # Позиции "левых" соседей для каждого блока
        # [левая стена (0.0), блок 0, блок 1, ..., блок N-2]
        pos_left = np.concatenate(([0.0], self.positions[:-1]))

        # Позиции "правых" соседей для каждого блока
        # [блок 1, блок 2, ..., блок N-1, правая стена]
        pos_right = np.concatenate((self.positions[1:], [self.right_wall_pos]))

        # --- 2. Рассчитываем силы от пружин ---

        # Силы от N левых пружин (k_0 ... k_N-1)
        k_left = self.spring_constants[:-1]
        spacing_left = self.spacings[:-1]
        force_left = k_left * (pos_left - self.positions + spacing_left)

        # Силы от N правых пружин (k_1 ... k_N)
        k_right = self.spring_constants[1:]
        spacing_right = self.spacings[1:]
        force_right = k_right * (pos_right - self.positions - spacing_right)

        # Суммарная сила
        forces = force_left + force_right

        # --- 3. Добавляем затухание (если включено) ---
        if config.ENABLE_DAMPING:
            forces -= config.DAMPING_COEFFICIENT * self.velocities

        return forces

    def _update_state(self, time_step: float):
        """Обновляет состояние всех блоков (алгоритм Верле, векторизованно)."""

        # Обновляем положения
        self.positions += self.velocities * time_step + 0.5 * self.accelerations * (time_step ** 2)

        # Рассчитываем новые силы на основе новых положений
        forces = self._calculate_forces()

        # Рассчитываем новые ускорения
        new_accelerations = forces / self.masses

        # Обновляем скорости
        self.velocities += 0.5 * (self.accelerations + new_accelerations) * time_step

        # Сохраняем новые ускорения
        self.accelerations = new_accelerations

    def run(self):
        """Запускает главный цикл симуляции."""
        print("Starting simulation (NumPy optimized)...")

        # Задаем начальное условие
        self.positions[config.BLOCK_TO_DISPLACE] += config.INITIAL_DISPLACEMENT

        log_interval = 1.0 / config.SAMPLES_PER_SECOND
        next_log_time = 0.0

        initial_forces = self._calculate_forces()
        self.accelerations = initial_forces / self.masses

        # Рассчитаем начальную энергию
        self._update_energies()

        while self.time <= config.SIMULATION_DURATION:
            self._update_state(config.TIME_STEP)
            self._update_energies()

            if self.time >= next_log_time:
                # Логируем снимок состояния
                self.data_logger.log(
                    self.time, config.NUM_BLOCKS,
                    self.positions, self.velocities,
                    self.accelerations, self.kinetic_energies
                )

                # Логируем данные об энергии
                self.energy_logger.log(
                    self.time,
                    self.total_kinetic_energy,
                    self.total_potential_energy,
                    self.total_energy
                )
                print(
                    f"Time: {self.time:.2f}s | "
                    f"Total Energy: {self.total_energy:.4f} J "
                    f"(KE: {self.total_kinetic_energy:.4f}, PE: {self.total_potential_energy:.4f})",
                    end='\r'
                )
                next_log_time += log_interval

            self.time += config.TIME_STEP

        self.data_logger.close()
        self.energy_logger.close()
        print("\nSimulation finished. Data saved to", config.CSV_SIMULATION_FILENAME, "and energy_data.csv")
