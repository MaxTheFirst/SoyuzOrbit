from dataclasses import dataclass, field
import math


# --- 1. ПАРАМЕТРЫ, КОТОРЫЕ ЗАДАЕТ ПОЛЬЗОВАТЕЛЬ (ИЛИ UI) ---
@dataclass
class UserParams:
    """То, что можно вывести в UI"""
    # Геометрия
    width_mm: float = 20.0  # Ширина мира
    aspect_ratio: float = 0.6  # Отношение Высота / Ширина (0.6 = 12мм при ширине 20)

    # Физика
    max_voltage: float = 2000.0  # Опорное напряжение (для расчета скорости)
    grid_voltage_bias: float = -150.0  # Напряжение на сетке (отрицательное относительно катода!)
    # Настройки качества (ползунки)
    resolution_quality: int = 100  # Кол-во ячеек по ширине (Grid density)
    time_accuracy: float = 0.2  # Коэф. Куранта (меньше = точнее и медленнее). 0.1-0.5 ок.
    solver_precision: str = "High"  # Low, Medium, High
    max_stat_simulation_steps: int = 20


# --- 2. АВТОМАТИЧЕСКИЕ КОНФИГИ (ВЫЧИСЛЯЕМЫЕ) ---

@dataclass
class PhysicsConfig:
    e_charge: float = -1.602e-19
    m_electron: float = 9.109e-31
    meters_per_unit: float = 1e-3


@dataclass
class GridConfig:
    user: UserParams

    @property
    def width_mm(self):
        return self.user.width_mm

    @property
    def height_mm(self):
        return self.user.width_mm * self.user.aspect_ratio

    @property
    def resolution(self):
        # Шаг сетки (h) = Ширина / Кол-во ячеек
        return self.user.width_mm / self.user.resolution_quality

    @property
    def nx(self): return int(self.user.resolution_quality)

    @property
    def ny(self): return int(self.nx * self.user.aspect_ratio)


@dataclass
class LayoutConfig:
    """Геометрия в процентах (0.0 - 1.0)"""
    cathode_pos_x: float = 0.1
    cathode_width: float = 0.02
    cathode_height: float = 0.5

    anode_pos_x: float = 0.9
    anode_width: float = 0.05
    anode_height: float = 0.8

    grid_pos_x: float = 0.20  # Сетка стоит близко к катоду
    grid_width: float = 0.10
    grid_gap_ratio: float = 0.80  # Размер щели (80% от высоты экрана)


@dataclass
class SolverConfig:
    user: UserParams
    grid: GridConfig
    method: str = "gauss_seidel"

    @property
    def max_iterations(self):
        # Эвристика: кол-во итераций ~ N^2 для простых методов, но линейно растет с размером
        # База 1000, плюс добавка от количества ячеек
        base = 1000
        scale = 1.0
        if self.user.solver_precision == "High": scale = 2.0
        if self.user.solver_precision == "Low": scale = 0.5

        # Чем больше ячеек, тем труднее сходиться
        cells_factor = (self.grid.nx * self.grid.ny) / 2000
        return int(base * scale * max(1.0, cells_factor))

    @property
    def tolerance(self):
        if self.user.solver_precision == "High": return 1e-4
        if self.user.solver_precision == "Low": return 1e-2
        return 1e-3


@dataclass
class SimulationConfig:
    user: UserParams
    grid: GridConfig
    physics: PhysicsConfig

    @property
    def dt(self):
        """
        Автоматический расчет шага времени (CFL Condition).
        Электрон не должен пролетать больше, чем time_accuracy * размер_ячейки.
        """
        # 1. Максимальная возможная скорость (v = sqrt(2qU/m))
        # Используем модуль заряда и напряжения
        q = abs(self.physics.e_charge)
        m = self.physics.m_electron
        u = self.user.max_voltage

        # v_max в м/с
        v_max = math.sqrt(2 * q * u / m)
        if v_max == 0: v_max = 1.0  # Защита от деления на 0

        # 2. Размер ячейки в метрах
        h_meters = self.grid.resolution * self.physics.meters_per_unit

        # 3. dt = (CFL * h) / v
        dt_val = (self.user.time_accuracy * h_meters) / v_max
        return dt_val

    @property
    def total_steps(self):
        """
        Считаем, сколько шагов нужно, чтобы пролететь экран насквозь.
        """
        # Ширина в метрах
        w_meters = self.grid.width_mm * self.physics.meters_per_unit

        # Примерная средняя скорость (половина от макс, грубая оценка)
        v_avg = math.sqrt(2 * abs(self.physics.e_charge) * self.user.max_voltage / self.physics.m_electron) * 0.5
        if v_avg == 0: return 100

        # Время полета
        time_flight = w_meters / v_avg

        # Количество шагов + запас 50%
        steps = int((time_flight / self.dt) * 1.5)
        return steps


@dataclass
class BeamConfig:
    spawn_offset_mm: float = 0.01
    particles_count: int = 500
    spread_ratio: float = 0.8
    thermal_energy_ev: float = 10.0

@dataclass
class AppConfig:
    # Создаем параметры пользователя
    # В реальном приложении значения сюда будут прилетать из UI
    user: UserParams = field(default_factory=UserParams)

    # Физика статична
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    beam: BeamConfig = field(default_factory=BeamConfig)

    # Остальные конфиги создаем в __post_init__, так как они зависят от user
    grid: GridConfig = field(init=False)
    solver: SolverConfig = field(init=False)
    sim: SimulationConfig = field(init=False)

    def __post_init__(self):
        # Связываем зависимости
        self.grid = GridConfig(user=self.user)
        self.solver = SolverConfig(user=self.user, grid=self.grid)
        self.sim = SimulationConfig(user=self.user, grid=self.grid, physics=self.physics)
