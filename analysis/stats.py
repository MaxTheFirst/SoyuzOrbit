import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
from simulation.particles import ParticleStatus, ParticleSystem
import copy

from simulation.solver import LaplaceSolver


# Глобальная функция-воркер для параллельных вычислений
# Она должна быть вне класса, чтобы корректно работать в мультипроцессинге
def _voltage_worker(anode_voltage, cfg, grid_template, x_spawn, y_range):
    """
    Считает одну точку ВАХ по заданному абсолютному напряжению анода.
    """
    grid = copy.deepcopy(grid_template)

    # Устанавливаем напряжение анода
    for comp in grid.components:
        if "Anode" in comp.name:
            comp.voltage = anode_voltage
            comp.apply_to_grid(grid.potential, grid.fixed_mask, grid.structure_map, 2, grid.cfg.resolution)

    solver = LaplaceSolver()
    target_current = cfg.beam.iv_beam_current_a if cfg.beam.iv_beam_current_a > 0 else cfg.beam.beam_current_a

    # 1. Сначала решаем Лапласа (без заряда) как начальное приближение.
    # Это в разы ускорит последующую сходимость Пуассона.
    grid.clear_charge()
    solver.solve(grid, max_iter=cfg.solver.max_iterations, tolerance=cfg.solver.tolerance)

    # 2. Цикл самосогласования (Пуассон)
    for _ in range(3):  # 3 итераций "поле-частицы" достаточно для точки ВАХ
        grid.calculate_field()

        old_rho = grid.rho.copy()
        grid.clear_charge()

        ps = ParticleSystem(cfg)
        ps.spawn_particles_manual(x_spawn, y_range)

        for _ in range(cfg.sim.total_steps):
            ps.update(grid, total_current_a=target_current)
            if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps.particles):
                break

        grid.rho = 0.5 * grid.rho + 0.5 * old_rho

        # Используем лимиты из конфига! (Обычно 5000+)
        solver.solve(grid, max_iter=cfg.solver.max_iterations, tolerance=cfg.solver.tolerance)

    hits = sum(1 for p in ps.particles if p.status == ParticleStatus.HIT_ANODE)
    return (hits / len(ps.particles)) * 100 if ps.particles else 0


class StatisticsAnalyzer:
    def __init__(self, grid, config):
        self.grid = grid
        self.cfg = config

    def calculate_full_stats(self, x_spawn, y_range):
        """
        Основной метод расчета статистики с использованием мультипроцессинга
        """
        max_v = self.cfg.user.max_voltage
        num_points = max(3, int(self.cfg.user.max_stat_simulation_steps))
        
        # Генерация диапазона напряжений, включая отрицательную часть
        # iv_negative_fraction определяет, насколько глубоко уходим в минус
        neg_limit = -max_v * self.cfg.user.iv_negative_fraction
        
        # Создаем линейный диапазон от отрицательного до положительного максимума
        anode_voltages = np.linspace(neg_limit, max_v, num_points)
        
        print(
            f"--- Запуск ПАРАЛЛЕЛЬНОГО расчета ВАХ ({len(anode_voltages)} точек), "
            f"Uанода от {anode_voltages[0]:.1f} до {anode_voltages[-1]:.1f} В ---"
        )

        # 2. Запуск пула процессов
        transmission_rates = []

        # Используем ProcessPoolExecutor для задействования всех ядер CPU
        with ProcessPoolExecutor() as executor:
            # Подготавливаем список задач
            futures = [
                executor.submit(_voltage_worker, u_anode, self.cfg, self.grid, x_spawn, y_range)
                for u_anode in anode_voltages
            ]

            # Собираем результаты по мере завершения
            for i, future in enumerate(futures):
                rate = future.result()
                transmission_rates.append(rate)

                # Небольшой прогресс-бар в консоль
                if i % 10 == 0:
                    print(f"Прогресс ВАХ: {i}/{len(anode_voltages)} точек рассчитано...")

        # 3. Финальный прогон на максимальном напряжении (для гистограмм и траекторий)
        # Делаем его в основном потоке, так как нам нужны объекты частиц целиком
        print("--- Финальный прогон для анализа спектра ---")
        ps_final = ParticleSystem(self.cfg)
        ps_final.spawn_particles_manual(x_spawn, y_range)

        step = 0
        while step < self.cfg.sim.total_steps * 5:
            ps_final.update(self.grid, voltage_scale=1.0)
            if step % 50 == 0:
                if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps_final.particles):
                    break
            step += 1

        energies = [p.kinetic_energy_ev for p in ps_final.particles if p.status == ParticleStatus.HIT_ANODE]

        return {
            "iv_curve": (anode_voltages, transmission_rates),
            "energy_hist": energies,
            "final_ps": ps_final
        }

    def plot_dashboard(self, stats_data):
        """Визуализация результатов"""
        anode_voltages, currents = stats_data["iv_curve"]
        energies = stats_data["energy_hist"]
        final_ps = stats_data["final_ps"]

        fig = plt.figure(figsize=(14, 10))
        gs = fig.add_gridspec(2, 2)

        # График 1: ВАХ
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(anode_voltages, currents, 'o-', color='orange', markersize=3, linewidth=1.5)
        ax1.set_title("ВАХ (Токопрохождение)")
        ax1.set_xlabel("Напряжение Анода (В)")
        ax1.set_ylabel("Прозрачность (%)")
        ax1.grid(True, which='both', alpha=0.3)
        ax1.set_ylim(-5, 105)
        
        # Добавляем вертикальную линию на 0 вольт
        ax1.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        # Добавляем горизонтальную линию на 0%
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

        # График 2: Энергетический спектр
        ax2 = fig.add_subplot(gs[0, 1])
        if len(energies) > 0:
            ax2.hist(energies, bins=20, color='cyan', edgecolor='black', alpha=0.7)
            ax2.set_title(f"Спектр энергий (U_max={self.cfg.user.max_voltage}В)")
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
            ax3.plot([min(start_y), max(start_y)], [min(start_y), max(start_y)], 'r--', alpha=0.5, label="Идеал")
            plt.colorbar(sc, ax=ax3, label="Энергия (эВ)")
            ax3.legend()

        ax3.set_title("Анализ смещения (Y_start vs Y_end)")
        ax3.set_xlabel("Y вылета (мм)")
        ax3.set_ylabel("Y прилета (мм)")
        ax3.grid(True, alpha=0.2)

        plt.tight_layout()
        plt.show()
