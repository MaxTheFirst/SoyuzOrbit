class SimulationComponent:
    def __init__(self, name: str):
        self.name = name

    def apply_to_grid(self, grid_potential, grid_mask, grid_struct, obj_id, resolution):
        pass


class RectangleElectrode(SimulationComponent):
    def __init__(self, name: str, voltage: float, x_range_mm: tuple, y_range_mm: tuple):
        super().__init__(name)
        self.voltage = voltage
        self.x_mm = x_range_mm
        self.y_mm = y_range_mm

    def apply_to_grid(self, grid_potential, grid_mask, grid_struct, obj_id, resolution):
        # Автоматический пересчет мм -> индексы ВНУТРИ компонента
        x_start = int(self.x_mm[0] / resolution)
        x_end = int(self.x_mm[1] / resolution)
        y_start = int(self.y_mm[0] / resolution)
        y_end = int(self.y_mm[1] / resolution)

        # Защита от выхода за границы массива
        ny, nx = grid_potential.shape
        x_start = max(0, min(x_start, nx))
        x_end = max(0, min(x_end, nx))
        y_start = max(0, min(y_start, ny))
        y_end = max(0, min(y_end, ny))

        grid_potential[y_start:y_end, x_start:x_end] = self.voltage
        grid_mask[y_start:y_end, x_start:x_end] = True
        if obj_id > 0:
            grid_struct[y_start:y_end, x_start:x_end] = obj_id


class SplitGrid(SimulationComponent):
    def __init__(self, name: str, voltage: float, x_pos_mm: float, width_mm: float, gap_mm: float,
                 world_height_mm: float):
        super().__init__(name)
        self.voltage = voltage
        self.x_pos = x_pos_mm
        self.width = width_mm
        self.gap = gap_mm
        self.h_world = world_height_mm

    def apply_to_grid(self, grid_potential, grid_mask, grid_struct, obj_id, resolution):
        # 1. Вычисляем координаты X
        x_start_idx = int((self.x_pos - self.width / 2) / resolution)
        x_end_idx = int((self.x_pos + self.width / 2) / resolution)

        # 2. Вычисляем координаты щели по Y
        center_y = self.h_world / 2
        gap_half = self.gap / 2

        y_gap_top_idx = int((center_y + gap_half) / resolution)
        y_gap_bot_idx = int((center_y - gap_half) / resolution)

        ny, nx = grid_potential.shape

        # Ограничиваем X
        x_start_idx = max(0, min(x_start_idx, nx))
        x_end_idx = max(0, min(x_end_idx, nx))

        # Вспомогательная функция для рисования куска
        def draw_block(y_start, y_end):
            y_start = max(0, min(y_start, ny))
            y_end = max(0, min(y_end, ny))
            if y_start < y_end and x_start_idx < x_end_idx:
                grid_potential[y_start:y_end, x_start_idx:x_end_idx] = self.voltage
                grid_mask[y_start:y_end, x_start_idx:x_end_idx] = True
                if obj_id > 0:
                    grid_struct[y_start:y_end, x_start_idx:x_end_idx] = obj_id

        # 3. Рисуем ВЕРХНЮЮ часть (от верха щели до потолка мира)
        draw_block(y_gap_top_idx, ny)

        # 4. Рисуем НИЖНЮЮ часть (от пола мира до низа щели)
        draw_block(0, y_gap_bot_idx)
