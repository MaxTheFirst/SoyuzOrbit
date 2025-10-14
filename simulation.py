import csv
from typing import List
from block import Block
import config


class DataLogger:
    """
    Управляет записью данных симуляции в CSV файл.
    """

    def __init__(self, filename: str):
        self.file_handle = open(filename, 'w', newline='')
        self.writer = csv.writer(self.file_handle)
        # Записываем заголовки
        self.writer.writerow(['time', 'block_index', 'position', 'velocity', 'acceleration'])

    def log(self, time: float, block_index: int, block: Block):
        """Записывает одну строку данных."""
        self.writer.writerow([
            f"{time:.4f}",
            block_index,
            f"{block.position:.6f}",
            f"{block.velocity:.6f}",
            f"{block.acceleration:.6f}"
        ])

    def close(self):
        """Закрывает файл."""
        self.file_handle.close()


class ChainSimulation:
    """
    Управляет симуляцией цепочки блоков и пружин.
    """

    def __init__(self):
        self.blocks = self._create_blocks()
        self.logger = DataLogger(config.CSV_FILENAME)
        self.time = 0.0

    @staticmethod
    def _create_blocks() -> List[Block]:
        """Создает список блоков в их равновесных позициях."""

        # Замечание: начало координат - первый блок
        return [
            Block(mass=config.MASS, initial_position=index * config.BLOCK_SPACING)
            for index in range(1, config.NUM_BLOCKS + 1)
        ]

    def _calculate_forces(self) -> List[float]:
        """Рассчитывает силы, действующие на каждый блок."""
        forces = [0.0] * config.NUM_BLOCKS
        k = config.SPRING_CONSTANT
        spacing = config.BLOCK_SPACING

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

            force_left = k * (pos_left - pos_current + spacing)
            force_right = k * (pos_right - pos_current - spacing)
            forces[i] = force_left + force_right

        # Сила для первого блока (учитывая левую стенку)
        pos_left = 0.0
        pos_current = self.blocks[0].position # equivalents to zero
        pos_right = self.blocks[1].position
        force_from_left_wall = k * (pos_left - pos_current + spacing)  # Пружина между стеной (в 0) и блоком
        force_from_right = k * (pos_right - pos_current - spacing)
        forces[0] = force_from_left_wall + force_from_right

        # Сила для последнего блока (учитывая правую стенку)
        pos_left = self.blocks[config.NUM_BLOCKS - 2].position
        pos_current = self.blocks[config.NUM_BLOCKS - 1].position
        pos_right = (config.NUM_BLOCKS + 1) * spacing

        force_from_left = k * (pos_left - pos_current + spacing)
        force_from_left_wall = k * (pos_right - pos_current - spacing)
        forces[config.NUM_BLOCKS - 1] = force_from_left + force_from_left_wall

        return forces

    def run(self):
        """Запускает главный цикл симуляции."""
        print("Starting simulation...")

        # Задаем начальное условие: смещаем первый блок
        self.blocks[config.BLOCK_TO_DISPLACE].position += config.INITIAL_DISPLACEMENT

        log_interval = 1.0 / config.SAMPLES_PER_SECOND
        next_log_time = 0.0

        while self.time <= config.SIMULATION_DURATION:
            # Расчет сил
            forces = self._calculate_forces()

            # Обновление состояния каждого блока
            for i, block in enumerate(self.blocks):
                block.update(forces[i], config.TIME_STEP)

            # Запись данных в CSV по расписанию
            if self.time >= next_log_time:
                for i, block in enumerate(self.blocks):
                    self.logger.log(self.time, i, block)
                next_log_time += log_interval
                print(f"Time: {self.time:.2f}s / {config.SIMULATION_DURATION:.2f}s", end='\r')

            self.time += config.TIME_STEP

        self.logger.close()
        print("\nSimulation finished. Data saved to", config.CSV_FILENAME)
