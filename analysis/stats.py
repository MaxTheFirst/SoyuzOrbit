import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
from simulation.particles import ParticleStatus, ParticleSystem
import copy

from simulation.solver import LaplaceSolver


def _get_stats_seed(cfg) -> int:
    return int(getattr(cfg.beam, "stats_random_seed", 12345))


def _set_component_voltage(grid, sweep_type, cfg, voltage_val):
    target_comp_name = "Anode" if sweep_type == "anode" else "Grid"

    def _get_voltage(name_substr: str, default: float) -> float:
        for comp in grid.components:
            if name_substr in comp.name:
                return float(getattr(comp, "voltage", default))
        return float(default)

    # grid_voltage_bias и iv_grid_min/max задаются как смещение относительно катода.
    cathode_v = _get_voltage("Cathode", -cfg.user.max_voltage / 2.0)
    voltage_abs = cathode_v + voltage_val if sweep_type == "grid" else voltage_val

    for comp in grid.components:
        if target_comp_name in comp.name:
            comp.voltage = voltage_abs
            comp.apply_to_grid(
                grid.potential,
                grid.fixed_mask,
                grid.structure_map,
                2 if "Anode" in comp.name else 4,  # ID: 2=Anode, 4=Grid
                grid.cfg.resolution,
            )

    return voltage_abs


def _solve_operating_point(voltage_val, sweep_type, cfg, grid_template, x_spawn, y_range):
    """
    Возвращает (rate_percent, grid_after_solve, target_current).
    """
    grid = copy.deepcopy(grid_template)
    _set_component_voltage(grid, sweep_type, cfg, voltage_val)

    solver = LaplaceSolver()
    target_current = cfg.beam.iv_beam_current_a if cfg.beam.iv_beam_current_a > 0 else cfg.beam.beam_current_a

    base_seed = _get_stats_seed(cfg)
    np.random.seed(base_seed)

    # 1. Начальное поле без заряда.
    grid.clear_charge()
    solver.solve(grid, max_iter=cfg.solver.max_iterations, tolerance=cfg.solver.tolerance)

    # 2. Самосогласование поле-частицы.
    ps = ParticleSystem(cfg)
    for iter_idx in range(3):
        grid.calculate_field()
        old_rho = grid.rho.copy()
        grid.clear_charge()

        np.random.seed(base_seed + iter_idx + 1)
        ps = ParticleSystem(cfg)
        ps.spawn_particles_manual(x_spawn, y_range)

        for _ in range(cfg.sim.total_steps):
            ps.update(grid, total_current_a=target_current)
            if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps.particles):
                break

        grid.rho = 0.5 * grid.rho + 0.5 * old_rho
        solver.solve(grid, max_iter=cfg.solver.max_iterations, tolerance=cfg.solver.tolerance)

    grid.calculate_field()
    hits = sum(1 for p in ps.particles if p.status == ParticleStatus.HIT_ANODE)
    rate = (hits / len(ps.particles)) * 100 if ps.particles else 0.0
    return rate, grid, target_current


# Глобальная функция-воркер для параллельных вычислений
# Она должна быть вне класса, чтобы корректно работать в мультипроцессинге
def _voltage_worker(voltage_val, sweep_type, cfg, grid_template, x_spawn, y_range):
    rate, _, _ = _solve_operating_point(voltage_val, sweep_type, cfg, grid_template, x_spawn, y_range)
    return rate


class StatisticsAnalyzer:
    def __init__(self, grid, config):
        self.grid = grid
        self.cfg = config

    def calculate_full_stats(self, x_spawn, y_range):
        """
        Основной метод расчета статистики с использованием мультипроцессинга
        """
        sweep_type = self.cfg.user.iv_sweep_type
        num_points = max(3, int(self.cfg.user.max_stat_simulation_steps))

        if sweep_type == "grid":
            # Сканируем напряжение сетки (проходная характеристика)
            voltages = np.linspace(self.cfg.user.iv_grid_min, self.cfg.user.iv_grid_max, num_points)
            if voltages[0] > voltages[-1]:
                voltages = voltages[::-1]
            print(
                f"--- Запуск расчета Проходной Характеристики (bias Grid относительно Cathode): "
                f"{voltages[0]:.1f}V ... {voltages[-1]:.1f}V ---"
            )
            working_voltage = float(self.cfg.user.grid_voltage_bias)
        else:
            # Старый режим: сканируем анод (выходная характеристика)
            max_v = self.cfg.user.max_voltage
            voltages = np.linspace(0, max_v, num_points)
            print(f"--- Запуск расчета Выходной Характеристики (Anode Sweep): {voltages[0]:.1f}V ... {voltages[-1]:.1f}V ---")
            working_voltage = float(self.cfg.user.max_voltage)

        # 2. Запуск пула процессов
        transmission_rates = []

        try:
            with ProcessPoolExecutor() as executor:
                futures = [
                    executor.submit(_voltage_worker, v, sweep_type, self.cfg, self.grid, x_spawn, y_range)
                    for v in voltages
                ]

                for i, future in enumerate(futures):
                    rate = future.result()
                    transmission_rates.append(rate)
                    if i % 5 == 0:
                        print(f"Прогресс: {i}/{len(voltages)}...")
        except Exception as exc:
            # В некоторых средах (ограниченные песочницы/IDE-runner) multiprocessing
            # может быть недоступен из-за ограничений на семафоры. Делаем fallback.
            print(f"ВНИМАНИЕ: multiprocessing недоступен ({exc}). Перехожу на последовательный расчет.")
            for i, v in enumerate(voltages):
                rate = _voltage_worker(v, sweep_type, self.cfg, self.grid, x_spawn, y_range)
                transmission_rates.append(rate)
                if i % 5 == 0:
                    print(f"Прогресс: {i}/{len(voltages)}...")

        # 3. Финальный прогон (для гистограмм и траекторий)
        # Всегда делаем на "рабочей точке" из конфига
        print("--- Финальный прогон для анализа спектра ---")
        _, working_grid, target_current = _solve_operating_point(
            working_voltage, sweep_type, self.cfg, self.grid, x_spawn, y_range
        )

        ps_final = ParticleSystem(self.cfg)
        np.random.seed(_get_stats_seed(self.cfg) + 1000)
        ps_final.spawn_particles_manual(x_spawn, y_range)

        step = 0
        while step < self.cfg.sim.total_steps * 5:
            ps_final.update(working_grid, total_current_a=target_current)
            if step % 50 == 0:
                if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps_final.particles):
                    break
            step += 1

        energies = [p.kinetic_energy_ev for p in ps_final.particles if p.status == ParticleStatus.HIT_ANODE]

        return {
            "iv_curve": (voltages, transmission_rates),
            "energy_hist": energies,
            "final_ps": ps_final,
            "working_grid": working_grid,
            "sweep_type": sweep_type,
            "working_voltage": working_voltage,
        }

    def plot_dashboard(self, stats_data):
        """Визуализация результатов"""
        voltages, currents = stats_data["iv_curve"]
        energies = stats_data["energy_hist"]
        final_ps = stats_data["final_ps"]
        sweep_type = stats_data.get("sweep_type", "anode")
        if "working_voltage" in stats_data:
            working_voltage = float(stats_data["working_voltage"])
        else:
            working_voltage = (
                float(self.cfg.user.grid_voltage_bias)
                if sweep_type == "grid"
                else float(self.cfg.user.max_voltage)
            )

        fig = plt.figure(figsize=(14, 10))
        gs = fig.add_gridspec(2, 2)

        # График 1: ВАХ
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(voltages, currents, 'o-', color='orange', markersize=3, linewidth=1.5)
        
        if sweep_type == "grid":
            ax1.set_title(f"Проходная характеристика (U_anode={self.cfg.user.max_voltage}В)")
            ax1.set_xlabel("Напряжение Сетки (В, отн. катода)")
        else:
            ax1.set_title("Выходная характеристика (U_grid=const)")
            ax1.set_xlabel("Напряжение Анода (В)")
            
        ax1.set_ylabel("Прозрачность (%)")
        ax1.grid(True, which='both', alpha=0.3)
        ax1.set_ylim(-5, 105)
        ax1.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

        # График 2: Энергетический спектр
        ax2 = fig.add_subplot(gs[0, 1])
        if len(energies) > 0:
            ax2.hist(energies, bins=20, color='cyan', edgecolor='black', alpha=0.7)
            if sweep_type == "grid":
                ax2.set_title(f"Спектр энергий (Ugrid_bias={working_voltage:.1f}В)")
            else:
                ax2.set_title(f"Спектр энергий (Uanode={working_voltage:.1f}В)")
        else:
            ax2.text(0.5, 0.5, "Нет данных (0% прохождения)", ha='center')
        ax2.set_xlabel("Энергия (эВ)")
        ax2.set_ylabel("Кол-во частиц")
        ax2.grid(True, alpha=0.2)

        # График 3: Фокусировка
        ax3 = fig.add_subplot(gs[1, :])
        hits = [p for p in final_ps.particles if p.status == ParticleStatus.HIT_ANODE]

        if hits:
            end_y = [p.r[1] for p in hits]
            start_y = [p.trajectory[0][1] for p in hits]
            e_vals = [p.kinetic_energy_ev for p in hits]

            sc = ax3.scatter(start_y, end_y, c=e_vals, cmap='viridis', s=20, alpha=0.8)
            
            # ИСПРАВЛЕНИЕ: "Идеал" для фокусировки - это горизонтальная линия (центр анода)
            # А не диагональ y=x.
            anode_center_y = self.grid.height_mm / 2.0
            ax3.axhline(y=anode_center_y, color='r', linestyle='--', alpha=0.5, label="Центр Анода (Идеал)")
            
            plt.colorbar(sc, ax=ax3, label="Энергия (эВ)")
            ax3.legend()

        ax3.set_title("Анализ смещения (Y_start vs Y_end)")
        ax3.set_xlabel("Y вылета (мм)")
        ax3.set_ylabel("Y прилета (мм)")
        ax3.grid(True, alpha=0.2)

        plt.tight_layout()
        plt.show()
