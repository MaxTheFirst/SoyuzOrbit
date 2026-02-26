import numpy as np


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


class EllipseElectrode(SimulationComponent):
    """
    Эллиптический электрод внутри заданного прямоугольного bounding box.
    Полезно для моделирования "скругленного" катода.
    """
    def __init__(self, name: str, voltage: float, x_range_mm: tuple, y_range_mm: tuple):
        super().__init__(name)
        self.voltage = voltage
        self.x_mm = x_range_mm
        self.y_mm = y_range_mm

    def apply_to_grid(self, grid_potential, grid_mask, grid_struct, obj_id, resolution):
        x_start = int(self.x_mm[0] / resolution)
        x_end = int(self.x_mm[1] / resolution)
        y_start = int(self.y_mm[0] / resolution)
        y_end = int(self.y_mm[1] / resolution)

        ny, nx = grid_potential.shape
        x_start = max(0, min(x_start, nx))
        x_end = max(0, min(x_end, nx))
        y_start = max(0, min(y_start, ny))
        y_end = max(0, min(y_end, ny))

        if x_start >= x_end or y_start >= y_end:
            return

        cx = 0.5 * (x_start + x_end - 1)
        cy = 0.5 * (y_start + y_end - 1)
        rx = max(0.5, 0.5 * (x_end - x_start))
        ry = max(0.5, 0.5 * (y_end - y_start))

        yy, xx = np.ogrid[y_start:y_end, x_start:x_end]
        ellipse_mask = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) <= 1.0

        region_phi = grid_potential[y_start:y_end, x_start:x_end]
        region_fix = grid_mask[y_start:y_end, x_start:x_end]
        region_phi[ellipse_mask] = self.voltage
        region_fix[ellipse_mask] = True

        if obj_id > 0:
            region_struct = grid_struct[y_start:y_end, x_start:x_end]
            region_struct[ellipse_mask] = obj_id


class ConcaveCathodeElectrode(SimulationComponent):
    """
    Вогнутый катод: базовый прямоугольник с "вырезом" на правой кромке.
    Вогнутость смотрит в сторону сетки/анода (вправо).
    """
    def __init__(
        self,
        name: str,
        voltage: float,
        x_range_mm: tuple,
        y_range_mm: tuple,
        concavity_ratio: float = 0.4,
    ):
        super().__init__(name)
        self.voltage = voltage
        self.x_mm = x_range_mm
        self.y_mm = y_range_mm
        self.concavity_ratio = float(concavity_ratio)

    def apply_to_grid(self, grid_potential, grid_mask, grid_struct, obj_id, resolution):
        x_start = int(self.x_mm[0] / resolution)
        x_end = int(self.x_mm[1] / resolution)
        y_start = int(self.y_mm[0] / resolution)
        y_end = int(self.y_mm[1] / resolution)

        ny, nx = grid_potential.shape
        x_start = max(0, min(x_start, nx))
        x_end = max(0, min(x_end, nx))
        y_start = max(0, min(y_start, ny))
        y_end = max(0, min(y_end, ny))

        if x_start >= x_end or y_start >= y_end:
            return

        width = x_end - x_start
        if width <= 1:
            grid_potential[y_start:y_end, x_start:x_end] = self.voltage
            grid_mask[y_start:y_end, x_start:x_end] = True
            if obj_id > 0:
                grid_struct[y_start:y_end, x_start:x_end] = obj_id
            return

        concavity_ratio = max(0.0, min(self.concavity_ratio, 0.95))
        depth_cells = concavity_ratio * max(1, (width - 1))

        yy, xx = np.ogrid[y_start:y_end, x_start:x_end]
        cy = 0.5 * (y_start + y_end - 1)
        ry = max(1.0, 0.5 * (y_end - y_start))
        t = (yy - cy) / ry

        # Параболическая вогнутость: максимум "выреза" в центре по Y.
        x_right = (x_end - 1) - depth_cells * (1.0 - np.clip(t * t, 0.0, 1.0))
        concave_mask = xx <= x_right

        region_phi = grid_potential[y_start:y_end, x_start:x_end]
        region_fix = grid_mask[y_start:y_end, x_start:x_end]
        region_phi[concave_mask] = self.voltage
        region_fix[concave_mask] = True

        if obj_id > 0:
            region_struct = grid_struct[y_start:y_end, x_start:x_end]
            region_struct[concave_mask] = obj_id


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
