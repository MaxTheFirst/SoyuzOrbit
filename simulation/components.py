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

class CurvedCathode(SimulationComponent):
    """
    Катод в форме дуги окружности для фокусировки пучка.
    Вогнутая поверхность (центр кривизны справа).
    """
    def __init__(self, name: str, voltage: float, x_center_mm: float, y_center_mm: float, 
                 radius_mm: float, height_mm: float, thickness_mm: float = 1.0):
        super().__init__(name)
        self.voltage = voltage
        self.xc = x_center_mm
        self.yc = y_center_mm
        self.R = radius_mm
        self.h = height_mm
        self.thickness = thickness_mm

    def apply_to_grid(self, grid_potential, grid_mask, grid_struct, obj_id, resolution):
        ny, nx = grid_potential.shape
        
        # Центр кривизны находится справа от катода на расстоянии R
        # То есть сама поверхность катода это левая часть окружности
        # Координаты центра окружности (фокуса):
        circle_x0 = self.xc + self.R 
        circle_y0 = self.yc

        # Проходим по bounding box для оптимизации
        # Катод находится в районе xc.
        x_min_idx = int((self.xc - self.thickness) / resolution)
        x_max_idx = int((self.xc + self.R) / resolution) # С запасом
        y_min_idx = int((self.yc - self.h/2 - self.thickness) / resolution)
        y_max_idx = int((self.yc + self.h/2 + self.thickness) / resolution)

        x_min_idx = max(0, x_min_idx)
        x_max_idx = min(nx, x_max_idx)
        y_min_idx = max(0, y_min_idx)
        y_max_idx = min(ny, y_max_idx)

        for iy in range(y_min_idx, y_max_idx):
            y_mm = iy * resolution
            
            # Проверяем, попадает ли Y в высоту катода
            if abs(y_mm - self.yc) > self.h / 2:
                continue

            for ix in range(x_min_idx, x_max_idx):
                x_mm = ix * resolution
                
                # Уравнение окружности: (x - x0)^2 + (y - y0)^2 = R^2
                dist_sq = (x_mm - circle_x0)**2 + (y_mm - circle_y0)**2
                dist = np.sqrt(dist_sq)

                # Катод имеет толщину. Мы рисуем его между R и R + thickness
                # Но так как он вогнутый влево, то поверхность это R, а "мясо" слева от R.
                # Значит условие: R <= dist <= R + thickness ? Нет.
                # Центр справа. Поверхность катода это точки на расстоянии R.
                # Точки левее имеют расстояние > R.
                
                if self.R <= dist <= self.R + self.thickness:
                    grid_potential[iy, ix] = self.voltage
                    grid_mask[iy, ix] = True
                    if obj_id > 0:
                        grid_struct[iy, ix] = obj_id


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
