from analysis.stats import StatisticsAnalyzer
from config import AppConfig, UserParams
from simulation.grid import SimulationGrid
from simulation.components import RectangleElectrode
from simulation.solver import LaplaceSolver
from simulation.particles import ParticleSystem
from ui.visualizer import Visualizer


def get_rect_coords(center_x_ratio, width_ratio, height_ratio, grid_w, grid_h):
    """Вспомогательная функция: превращает % конфига в мм координат"""
    center_x = grid_w * center_x_ratio
    width = grid_w * width_ratio
    height = grid_h * height_ratio

    x_start = center_x - width / 2
    x_end = center_x + width / 2

    center_y = grid_h / 2  # Центрируем по вертикали
    y_start = center_y - height / 2
    y_end = center_y + height / 2

    return (x_start, x_end), (y_start, y_end)


from simulation.components import RectangleElectrode, SplitGrid


def setup_scenario_dynamic(grid, cfg):
    w = cfg.grid.width_mm
    h = cfg.grid.height_mm
    layout = cfg.layout

    # Расчет напряжений
    # Катод = -1000, Анод = +1000
    half_voltage = cfg.user.max_voltage / 2.0
    cathode_v = -half_voltage
    anode_v = +half_voltage

    # Напряжение сетки: оно должно быть НИЖЕ катода, чтобы тормозить электроны.
    # U_grid = U_cathode + Bias
    # Пример: -1000 + (-150) = -1150 В
    grid_v = cathode_v + cfg.user.grid_voltage_bias

    # 1. Катод
    c_x, c_y = get_rect_coords(layout.cathode_pos_x, layout.cathode_width, layout.cathode_height, w, h)
    grid.add_component(RectangleElectrode("Cathode", cathode_v, c_x, c_y))

    # 2. СЕТКА
    # Переводим относительные координаты в мм
    # g_x_pos = w * layout.grid_pos_x
    # g_width = w * layout.grid_width
    # g_gap = h * layout.grid_gap_ratio
    #
    # grid_component = SplitGrid("Grid", grid_v, g_x_pos, g_width, g_gap, h)
    # grid.add_component(grid_component)

    # 3. Анод
    a_x, a_y = get_rect_coords(layout.anode_pos_x, layout.anode_width, layout.anode_height, w, h)
    grid.add_component(RectangleElectrode("Anode", anode_v, a_x, a_y))

    # Диагностика
    # print(f"Сетка установлена: X={g_x_pos:.1f}мм, Щель={g_gap:.1f}мм, U={grid_v:.1f}В")

    return c_x[1], c_y


def main():
    cfg = AppConfig(
        user=UserParams(
            width_mm=40.0,  # Увеличили мир в 2 раза
            max_voltage=2000.0,  # Подняли напряжение (скорость вырастет)
            resolution_quality=150,  # Сделали сетку плотнее
            time_accuracy=0.15  # Повысили точность времени
        )
    )

    # Инициализация
    grid = SimulationGrid(cfg)

    # Динамическая настройка сцены
    cathode_right_edge, cathode_y_range = setup_scenario_dynamic(grid, cfg)

    # Решение
    solver = LaplaceSolver(method=cfg.solver.method)
    solver.solve(grid, cfg.solver.max_iterations, cfg.solver.tolerance)
    grid.calculate_field()

    # Частицы
    ps = ParticleSystem(cfg)

    def spawn_closure():
        """ЛОГИКА СПАВНА НА ОСНОВЕ ГЕОМЕТРИИ"""
        # Спавним частицы сразу за правым краем катода + отступ из конфига
        spawn_x = cathode_right_edge + cfg.beam.spawn_offset_mm

        # Вычисляем высоту пучка (чуть уже, чем сам катод)
        c_height = cathode_y_range[1] - cathode_y_range[0]
        beam_height = c_height * cfg.beam.spread_ratio
        center_y = cfg.grid.height_mm / 2
        spawn_y = (center_y - beam_height / 2, center_y + beam_height / 2)

        # Передаем рассчитанные координаты в спавнер
        # Нам нужно модифицировать метод spawn_particles, чтобы он принимал аргументы,
        # ИЛИ (лучше) обновить конфиг "на лету" перед созданием, но мы передадим явно.
        return spawn_x, spawn_y

    analyzer = StatisticsAnalyzer(grid, cfg)
    print("Сбор статистики...")
    stats = analyzer.calculate_full_stats(*spawn_closure())
    analyzer.plot_dashboard(stats)

    # Симуляция
    ps.spawn_particles_manual(*spawn_closure())
    for _ in range(cfg.sim.total_steps):
        ps.update(grid)

    viz = Visualizer(grid, ps)
    viz.plot_field_and_trajectories()


if __name__ == "__main__":
    main()