import numpy as np


class SimulationGrid:
    def __init__(self, config):
        self.cfg = config.grid

        # 1. Потенциал (phi)
        self.potential = np.zeros((self.cfg.ny, self.cfg.nx))

        # 2. Маска (True там, где стоят электроды)
        self.fixed_mask = np.zeros((self.cfg.ny, self.cfg.nx), dtype=bool)

        # 3. Карта типов (0=Пусто, 1=Катод, 2=Анод, 3=Стена, 4=Сетка)
        self.structure_map = np.zeros((self.cfg.ny, self.cfg.nx), dtype=int)

        # 4. Электрическое поле (Ex, Ey) - в В/мм
        self.ex = np.zeros_like(self.potential)
        self.ey = np.zeros_like(self.potential)

        self._components_data = []

        self.rho = np.zeros((self.cfg.ny, self.cfg.nx))

        self.eps0 = self.cfg.eps0

    @property
    def components(self):
        """Возвращает только список компонентов, как раньше"""
        return [c for c, _ in self._components_data]

    def add_component(self, component):
        obj_id = 0
        if "Cathode" in component.name:
            obj_id = 1
        elif "Anode" in component.name:
            obj_id = 2
        elif "Wall" in component.name:
            obj_id = 3
        elif "Grid" in component.name:
            obj_id = 4

        self._components_data.append((component, obj_id))

        component.apply_to_grid(
            self.potential,
            self.fixed_mask,
            self.structure_map,
            obj_id,
            self.cfg.resolution
        )

    def calculate_field(self):
        """Расчет вектора E = -grad(phi)"""
        # np.gradient возвращает (d/dy, d/dx)
        # Делим на шаг сетки (resolution), чтобы получить В/мм
        grad_y, grad_x = np.gradient(self.potential, self.cfg.resolution)

        self.ex = -grad_x
        self.ey = -grad_y

    def reset(self):
        """Очистка поля"""
        self.potential[~self.fixed_mask] = 0
        for comp in self.components:
            comp.apply_to_grid(self.potential, self.fixed_mask, self.structure_map, self._get_obj_id(comp), self.cfg.resolution)

    def _get_obj_id(self, component):
        if "Cathode" in component.name:
            return 1
        elif "Anode" in component.name:
            return 2
        elif "Wall" in component.name:
            return 3
        elif "Grid" in component.name:
            return 4
        return 0

    def clear_charge(self):
        """Обнуляет накопленный заряд в пространстве"""
        self.rho.fill(0.0)
