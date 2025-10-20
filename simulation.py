import csv
from block import Block
from spring import Spring
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

    def log(self, time: float, block_index: int, block: Block):
        """Записывает одну строку данных."""
        self.writer.writerow([
            f"{time:.4f}",
            block_index,
            f"{block.position:.6f}",
            f"{block.velocity:.6f}",
            f"{block.acceleration:.6f}",
            f"{block.kinetic_energy:.6f}"
        ])

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

    def __init__(self, masses: list[float], spring_constants: list[float], spacings: list[float]):
        """
        Инициализирует симуляцию с заданными физическими свойствами.
        """
        self.masses = masses
        self.spring_constants = spring_constants
        self.spacings = spacings

        self.blocks = self._create_blocks()
        self.springs = self._create_springs()
        self.logger = DataLogger(config.CSV_SIMULATION_FILENAME)
        self.energy_logger = EnergyLogger(config.CSV_ENERGY_DATA_FILENAME)
        self.time = 0.0

    def _create_blocks(self) -> list[Block]:
        """Создает список блоков в их равновесных позициях."""

        blocks_list = []
        current_pos = 0.0
        for i in range(config.NUM_BLOCKS):
            # Равновесная позиция i-го блока - это сумма всех расстояний до него
            current_pos += self.spacings[i]
            block = Block(
                mass=self.masses[i],
                initial_position=current_pos
            )
            blocks_list.append(block)
        return blocks_list

    def _create_springs(self) -> list[Spring]:
        """Создает список пружин."""
        springs_list = []
        # У нас N блоков и N+1 пружина (включая те, что крепятся к стенам)
        for i in range(config.NUM_BLOCKS + 1):
            spring = Spring(
                spring_constant=self.spring_constants[i],
                equilibrium_length=self.spacings[i]
            )
            springs_list.append(spring)
        return springs_list

    def _update_energies(self):
        """Рассчитывает и обновляет общую энергию системы."""
        # 1. Кинетическая энергия (просто суммируем энергии всех блоков)
        self.total_kinetic_energy = sum(block.kinetic_energy for block in self.blocks)

        # 2. Потенциальная энергия (обновляем и суммируем энергии пружин)
        # Первая пружина (между левой стеной и первым блоком)
        pos_1 = 0.0
        pos_2 = self.blocks[0].position
        self.springs[0].update_energy(pos_1, pos_2)

        # Пружины между блоками
        for i in range(1, config.NUM_BLOCKS):
            pos1 = self.blocks[i - 1].position
            pos2 = self.blocks[i].position
            self.springs[i].update_energy(pos1, pos2)

        # Последняя пружина (между последним блоком и правой стеной)
        pos_1 = self.blocks[-1].position
        pos_2 = sum(self.spacings)
        self.springs[-1].update_energy(pos_1, pos_2)

        self.total_potential_energy = sum(s.potential_energy for s in self.springs)

        # 3. Полная энергия
        self.total_energy = self.total_kinetic_energy + self.total_potential_energy

    def _calculate_forces(self) -> list[float]:
        """Рассчитывает силы, действующие на каждый блок."""
        forces = [0.0] * config.NUM_BLOCKS

        # Рассчитываем силы для всех блоков, кроме крайних
        for i in range(1, config.NUM_BLOCKS - 1):
            pos_current = self.blocks[i].position
            pos_left = self.blocks[i - 1].position
            pos_right = self.blocks[i + 1].position

            # force_left = -k * (delta_pos_current - delta_pos_left) =
            # = k * (delta_pos_left - delta_pos_current) =
            # = k * (pos_left - init_pos_left - (pos_current - init_pos_current)) =
            # = k * (pos_left - init_pos_left - pos_current + init_pos_left + spacing)
            # = k * (pos_left - pos_current + spacing)

            force_left = self.spring_constants[i] * round(pos_left - pos_current + self.spacings[i],
                                                          config.DECIMAL_PLACES)
            force_right = self.spring_constants[i + 1] * round(pos_right - pos_current - self.spacings[i + 1],
                                                               config.DECIMAL_PLACES)
            forces[i] = force_left + force_right

        # Сила для первого блока (учитывая левую стенку)
        pos_left = 0.0
        pos_current = self.blocks[0].position  # equivalents to zero
        pos_right = self.blocks[1].position
        force_from_left_wall = self.spring_constants[0] * round(
            pos_left - pos_current + self.spacings[0], config.DECIMAL_PLACES)  # Пружина между стеной (в 0) и блоком
        force_from_right = self.spring_constants[1] * round(pos_right - pos_current - self.spacings[0],
                                                            config.DECIMAL_PLACES)
        forces[0] = force_from_left_wall + force_from_right

        # Сила для последнего блока (учитывая правую стенку)
        pos_left = self.blocks[config.NUM_BLOCKS - 2].position
        pos_current = self.blocks[config.NUM_BLOCKS - 1].position
        pos_right = sum(self.spacings)

        force_from_left = self.spring_constants[config.NUM_BLOCKS - 1] * round(
            pos_left - pos_current + self.spacings[config.NUM_BLOCKS - 1], config.DECIMAL_PLACES)
        force_from_left_wall = self.spring_constants[config.NUM_BLOCKS] * round(
            pos_right - pos_current - self.spacings[config.NUM_BLOCKS], config.DECIMAL_PLACES)
        forces[config.NUM_BLOCKS - 1] = force_from_left + force_from_left_wall

        # --- Теперь добавляем опциональные силы, если флаги включены ---

        if config.ENABLE_DAMPING:
            for i in range(config.NUM_BLOCKS):
                forces[i] += -config.DAMPING_COEFFICIENT * self.blocks[i].velocity

        return forces

    def run(self):
        """Запускает главный цикл симуляции."""
        print("Starting simulation...")

        # Задаем начальное условие: смещаем первый блок
        self.blocks[config.BLOCK_TO_DISPLACE].position += config.INITIAL_DISPLACEMENT

        log_interval = 1.0 / config.SAMPLES_PER_SECOND
        next_log_time = 0.0

        self._update_energies()

        while self.time <= config.SIMULATION_DURATION:
            # Расчет сил
            forces = self._calculate_forces()

            # Обновление состояния каждого блока
            for i, block in enumerate(self.blocks):
                block.update(forces[i], config.TIME_STEP)

            self.energy_logger.log(
                self.time,
                self.total_kinetic_energy,
                self.total_potential_energy,
                self.total_energy
            )

            self._update_energies()

            # Запись данных в CSV по расписанию
            if self.time >= next_log_time:
                for i, block in enumerate(self.blocks):
                    self.logger.log(self.time, i, block)
                next_log_time += log_interval
                print(f"Time: {self.time:.2f}s / {config.SIMULATION_DURATION:.2f}s", end='\r')

            self.time += config.TIME_STEP

        self.logger.close()
        self.energy_logger.close()
        print("\nSimulation finished. Data saved to", config.CSV_SIMULATION_FILENAME)
