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
    
    # ВАЖНО: Уменьшил смещение сетки, чтобы электроны могли пролететь.
    # При -50В и узкой щели была полная отсечка (ток = 0).
    grid_voltage_bias: float = -10.0  
    
    # Среда
    gas_pressure_pa: float = 1e-3  # Давление остаточного газа (Па).

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
    
    sigma_gas: float = 2e-19 
    kb: float = 1.38e-23
    temperature_k: float = 300.0


@dataclass
class GridConfig:
    eps0 = 8.854e-12

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
    cathode_radius_mm: float = 20.0 # Увеличил радиус для более мягкой фокусировки

    anode_pos_x: float = 0.9
    anode_width: float = 0.05
    anode_height: float = 0.8

    grid_pos_x: float = 0.25  
    grid_width: float = 0.02 # Сделал сетку тоньше
    grid_gap_ratio: float = 0.50  # Увеличил щель до 50%, чтобы ток точно пошел


@dataclass
class SolverConfig:
    user: UserParams
    grid: GridConfig
    method: str = "gauss_seidel"

    @property
    def max_iterations(self):
        base = 8000
        scale = 1.0
        if self.user.solver_precision == "High": scale = 2.0
        if self.user.solver_precision == "Low": scale = 0.5
        cells_factor = (self.grid.nx * self.grid.ny) / 2000
        return int(base * scale * max(1.0, cells_factor))

    @property
    def tolerance(self):
        if self.user.solver_precision == "High": return 1e-5
        if self.user.solver_precision == "Low": return 1e-3
        return 1e-4


@dataclass
class SimulationConfig:
    user: UserParams
    grid: GridConfig
    physics: PhysicsConfig

    @property
    def dt(self):
        q = abs(self.physics.e_charge)
        m = self.physics.m_electron
        u = self.user.max_voltage
        v_max = math.sqrt(2 * q * u / m)
        if v_max == 0: v_max = 1.0
        h_meters = self.grid.resolution * self.physics.meters_per_unit
        dt_val = (self.user.time_accuracy * h_meters) / v_max
        return dt_val

    @property
    def total_steps(self):
        w_meters = self.grid.width_mm * self.physics.meters_per_unit
        v_avg = math.sqrt(2 * abs(self.physics.e_charge) * self.user.max_voltage / self.physics.m_electron) * 0.5
        if v_avg == 0: return 100
        time_flight = w_meters / v_avg
        steps = int((time_flight / self.dt) * 1.5)
        return steps


@dataclass
class BeamConfig:
    spawn_offset_mm: float = 0.05 # Чуть дальше от катода, чтобы не залипали
    particles_count: int = 500
    spread_ratio: float = 0.8
    thermal_energy_ev: float = 0.2
    beam_current_a: float = 2.0 # Ток эмиссии (Ампер)

@dataclass
class AppConfig:
    user: UserParams = field(default_factory=UserParams)
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    beam: BeamConfig = field(default_factory=BeamConfig)

    grid: GridConfig = field(init=False)
    solver: SolverConfig = field(init=False)
    sim: SimulationConfig = field(init=False)

    def __post_init__(self):
        self.grid = GridConfig(user=self.user)
        self.solver = SolverConfig(user=self.user, grid=self.grid)
        self.sim = SimulationConfig(user=self.user, grid=self.grid, physics=self.physics)
