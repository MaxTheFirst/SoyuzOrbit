import csv

import numpy as np

import config

from scipy.interpolate import interp1d


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

    def _calculate_forces(self, current_time: float, driving_func=None) -> np.ndarray:
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

        if config.ABSORBING_BOUNDARY_RIGHT:
            # Эта секция заменяет силу от "правой стены"
            # на "идеальное поглощение" (согласование импеданса).

            # 4.1. Рассчитываем волновое сопротивление (импеданс)
            # (Для однородной цепи)
            m = config.DEFAULT_MASS
            k = config.DEFAULT_SPRING_CONSTANT
            impedance = np.sqrt(k * m)

            # 4.2. Рассчитываем поглощающую силу для ПОСЛЕДНЕГО блока
            v_last = self.velocities[-1]
            absorbing_force = -impedance * v_last

            # 4.3. Нам нужно *заменить* силу от правой стены на эту силу.
            # Исходная сила на последнем блоке:
            # forces[-1] = force_left_last + force_right_wall

            # Находим силу, которую мы хотим удалить:
            k_N = self.spring_constants[-1]
            spacing_N = self.spacings[-1]
            force_right_wall = k_N * (self.right_wall_pos - self.positions[-1] - spacing_N)

            # Заменяем:
            forces[-1] = forces[-1] - force_right_wall + absorbing_force

        # --- 4. Добавляем внешнюю вынуждающую силу ---

        if driving_func is not None:
            # Используем интерполированную функцию, а не sin()
            driving_force = driving_func(current_time)
            forces[config.DRIVEN_BLOCK_INDEX] += driving_force
        elif config.ENABLE_DRIVING_FORCE:
            # Рассчитываем угловую частоту: omega = 2 * pi * f
            omega = 2.0 * np.pi * config.DRIVING_FREQUENCY_HERTZ
            # F(t) = A * sin(omega * t)
            driving_force = config.DRIVING_AMPLITUDE * np.sin(omega * current_time)

            # Прикладываем силу к выбранному блоку
            forces[config.DRIVEN_BLOCK_INDEX] += driving_force

        return forces

    def _update_state(self, time_step: float, current_time: float, driving_func=None):
        """Обновляет состояние всех блоков (алгоритм Верле, векторизованно)."""

        # Обновляем положения
        self.positions += self.velocities * time_step + 0.5 * self.accelerations * (time_step ** 2)

        # Рассчитываем новые силы на основе новых положений
        forces = self._calculate_forces(current_time + time_step, driving_func)

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
        if not config.ENABLE_DRIVING_FORCE:
            self.positions[config.BLOCK_TO_DISPLACE] += config.INITIAL_DISPLACEMENT

        log_interval = 1.0 / config.SAMPLES_PER_SECOND
        next_log_time = 0.0

        self._update_energies()
        initial_forces = self._calculate_forces(self.time)
        self.accelerations = initial_forces / self.masses

        # Рассчитаем начальную энергию
        self._update_energies()

        while self.time <= config.SIMULATION_DURATION:
            self._update_state(config.TIME_STEP, self.time)
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

        # D1/simulation_1d.py (ЗАМЕНИТЬ этот метод)

    def run_audio_simulation(self, time_array: np.ndarray, signal_array: np.ndarray,
                             output_sample_rate: int) -> np.ndarray:
        """
        Запускает симуляцию, используя аудиосигнал как внешнюю силу.
        Записывает СИЛУ на ПОСЛЕДНEM блоке (для совпадения F_in -> F_out).
        """
        print("Starting audio-driven simulation (Recording Force)...")

        # --- 1. СБРОС СИМУЛЯЦИИ ---
        print("Resetting simulation state...")
        self.time = 0.0
        self.positions = np.cumsum(self.spacings[:-1])
        self.velocities = np.zeros(config.NUM_BLOCKS)
        self.accelerations = np.zeros(config.NUM_BLOCKS)

        # --- 2. РАСЧЕТ ФИЗИКИ ---
        MIC_INDEX = config.NUM_BLOCKS - 1
        total_duration = config.SIMULATION_DURATION

        # --- 3. [ИЗМЕНЕНИЕ] Рассчитываем импеданс Z ---
        # Мы должны использовать те же параметры, что и в _calculate_forces
        m = config.DEFAULT_MASS
        k = config.DEFAULT_SPRING_CONSTANT
        impedance = np.sqrt(k * m)
        print(f"Calculated Impedance (Z): {impedance:.4f}")

        # --- 4. Подготовка (Интерполятор и Запись) ---
        driving_force_func = interp1d(time_array, signal_array * 1.0,  # Можно вернуть 1.0
                                      bounds_error=False, fill_value=0.0)

        output_recording = []
        log_interval = 1.0 / output_sample_rate
        time_step = min(config.TIME_STEP, config.round_to_1(log_interval))
        next_log_time = 0.0
        flag = False

        # --- 5. Начальное состояние ---
        initial_forces = self._calculate_forces(self.time, driving_force_func)
        self.accelerations = initial_forces / self.masses

        # --- 6. ГЛАВНЫЙ ЦИКЛ ---
        while self.time <= total_duration:
            self._update_state(time_step * 10, self.time, driving_force_func)

            # "Микрофон"
            if not flag and abs(self.velocities[MIC_INDEX]) > 1.0 / 100000.0:
                next_log_time = self.time
                total_duration = self.time + time_array[-1]
                flag = True

            if flag and self.time >= next_log_time:
                # --- ГЛАВНОЕ ИЗМЕНЕНИЕ ---
                # Раньше было: output_recording.append(self.velocities[MIC_INDEX])
                # Теперь:
                output_force = impedance * self.velocities[MIC_INDEX]
                output_recording.append(output_force)
                # ---

                next_log_time += log_interval

            self.time += time_step

        print("\nAudio simulation finished.")
        return np.array(output_recording)

    def run_audio_simulation_test(self, time_array: np.ndarray, signal_array: np.ndarray,
                                  output_sample_rate: int) -> np.ndarray:
        """
        Запускает симуляцию, используя АУДИОСИГНАЛ как внешнюю силу.
        """
        print("Starting audio-driven simulation...")

        # 1. Нам нужен "интерполятор", чтобы находить F(t) для любого time_step
        # Он будет линейно интерполировать наш входной аудиосигнал
        # Умножаем сигнал на 10.0 (сила в Ньютонах)
        driving_force_func = interp1d(time_array, signal_array * 10.0,
                                      bounds_error=False, fill_value=0.0)

        # 2. Подготовка к записи
        # Мы должны записывать на *каждом шаге* симуляции!
        # Но это слишком много данных. Мы будем записывать с частотой output_sample_rate

        output_recording = []
        log_interval = 1.0 / output_sample_rate
        next_log_time = 0.0
        time_step = min(config.TIME_STEP, config.round_to_1(log_interval / 2.0))

        # 3. Рассчитываем начальное состояние
        # (Начальное смещение 0, т.к. мы используем внешнюю силу)
        initial_forces = self._calculate_forces(self.time, driving_force_func)
        self.accelerations = initial_forces / self.masses

        total_duration = time_array[-1]

        while self.time <= total_duration:
            # Обновляем состояние
            self._update_state(config.TIME_STEP, self.time, driving_force_func)

            # (Энергию не считаем, т.к. внешняя сила постоянно вкачивает энергию)

            # "Микрофон": записываем скорость последнего блока
            if self.time >= next_log_time:
                output_recording.append(self.velocities[-1])  # Запись!
                next_log_time += log_interval

            print(f"Audio sim time: {self.time:.2f}s / {total_duration:.2f}s", end='\r')
            self.time += time_step

        print("\nAudio simulation finished.")
        return np.array(output_recording)
