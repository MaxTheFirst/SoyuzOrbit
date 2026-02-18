import numpy as np
from config import AppConfig, UserParams
from simulation.grid import SimulationGrid
from simulation.components import RectangleElectrode, SplitGrid
from simulation.solver import LaplaceSolver
from simulation.particles import ParticleSystem, ParticleStatus
from analysis.stats import StatisticsAnalyzer
from ui.visualizer import Visualizer


def get_rect_coords(center_x_ratio, width_ratio, height_ratio, grid_w, grid_h):
    """Превращает % конфига в мм координат"""
    center_x = grid_w * center_x_ratio
    width = grid_w * width_ratio
    height = grid_h * height_ratio
    x_start = center_x - width / 2
    x_end = center_x + width / 2
    center_y = grid_h / 2
    y_start = center_y - height / 2
    y_end = center_y + height / 2
    return (x_start, x_end), (y_start, y_end)


def setup_scenario_dynamic(grid, cfg):
    """Настройка электродов: Катод, Сетка, Анод"""
    w = cfg.grid.width_mm
    h = cfg.grid.height_mm
    layout = cfg.layout

    half_voltage = cfg.user.max_voltage / 2.0
    cathode_v = -half_voltage
    anode_v = +half_voltage
    grid_v = cathode_v + cfg.user.grid_voltage_bias

    c_x, c_y = get_rect_coords(layout.cathode_pos_x, layout.cathode_width, layout.cathode_height, w, h)
    grid.add_component(RectangleElectrode("Cathode", cathode_v, c_x, c_y))

    # g_x_pos = w * layout.grid_pos_x
    # g_width = w * layout.grid_width
    # g_gap = h * layout.grid_gap_ratio
    # grid.add_component(SplitGrid("Grid", grid_v, g_x_pos, g_width, g_gap, h))

    a_x, a_y = get_rect_coords(layout.anode_pos_x, layout.anode_width, layout.anode_height, w, h)
    grid.add_component(RectangleElectrode("Anode", anode_v, a_x, a_y))

    return c_x[1], c_y


def main():
    cfg = AppConfig(
        user=UserParams(
            width_mm=40.0,
            max_voltage=2000.0,
            resolution_quality=150,
            time_accuracy=0.15
        )
    )

    grid = SimulationGrid(cfg)
    cathode_right_edge, cathode_y_range = setup_scenario_dynamic(grid, cfg)
    solver = LaplaceSolver(method=cfg.solver.method)

    def spawn_closure():
        """Логика координат спавна частиц"""
        spawn_x = cathode_right_edge + cfg.beam.spawn_offset_mm
        c_height = cathode_y_range[1] - cathode_y_range[0]
        beam_height = c_height * cfg.beam.spread_ratio
        center_y = cfg.grid.height_mm / 2
        spawn_y = (center_y - beam_height / 2, center_y + beam_height / 2)
        return spawn_x, spawn_y

    # --- ЦИКЛ САМОСОГЛАСОВАНИЯ (SPACE CHARGE) ---
    print("--- Запуск самосогласованного расчета ---")
    grid.clear_charge()  # Обнуляем rho перед стартом

    # Целевой ток пучка для расчета плотности заряда (Ампер)
    # Это главный параметр для закона 3/2
    target_current = 2.

    for i in range(5):  # 5 итераций обычно хватает для сходимости
        print(f"Итерация {i + 1}/5...")

        # 1. Решаем Пуассона (учитывает текущий grid.rho)
        solver.solve(grid, cfg.solver.max_iterations, cfg.solver.tolerance)
        grid.calculate_field()

        # 2. Сохраняем старый заряд для релаксации
        old_rho = grid.rho.copy()
        grid.clear_charge()

        # 3. Пускаем частицы для накопления НОВОГО заряда rho
        ps_iter = ParticleSystem(cfg)
        ps_iter.spawn_particles_manual(*spawn_closure())

        for _ in range(cfg.sim.total_steps):
            # Внутри update происходит депонирование rho
            ps_iter.update(grid, total_current_a=target_current)
            # print(f"DEBUG: Max rho = {np.max(np.abs(grid.rho)):.2e} C/m^3")
            # print(
            #     f"DEBUG: Source term scale = {np.max(np.abs(grid.rho)) * ((grid.cfg.resolution / 1000) ** 2) / grid.eps0:.2e}")
            if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps_iter.particles):
                break

        # 4. РЕЛАКСАЦИЯ: Смешиваем заряды, чтобы решение не осциллировало
        grid.rho = 0.1 * grid.rho + 0.9 * old_rho

    # --- ПОСТ-ОБРАБОТКА ---
    print("Сбор финальной статистики...")
    analyzer = StatisticsAnalyzer(grid, cfg)
    # Параллельный расчет ВАХ теперь будет учитывать "замороженное" облако заряда
    stats = analyzer.calculate_full_stats(*spawn_closure())
    analyzer.plot_dashboard(stats)

    # Финальная визуализация траекторий в установившемся поле
    ps_final = ParticleSystem(cfg)
    ps_final.spawn_particles_manual(*spawn_closure())
    for _ in range(cfg.sim.total_steps):
        ps_final.update(grid, total_current_a=target_current)

    viz = Visualizer(grid, ps_final)
    viz.plot_field_and_trajectories()


if __name__ == "__main__":
    main()