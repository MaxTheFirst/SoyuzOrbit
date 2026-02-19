import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
from simulation.particles import ParticleStatus, ParticleSystem
import copy

from simulation.solver import LaplaceSolver


# Глобальная функция-воркер для параллельных вычислений
# Она должна быть вне класса, чтобы корректно работать в мультипроцессинге
def _voltage_worker(u, max_v, cfg, grid_template, x_spawn, y_range):
    """Исправленный воркер: берет лимиты из конфига и не 'падает'"""
    grid = copy.deepcopy(grid_template)

    # Устанавливаем напряжение анода
    for comp in grid.components:
        if "Anode" in comp.name:
            comp.voltage = u
            comp.apply_to_grid(grid.potential, grid.fixed_mask, grid.structure_map, 2, grid.cfg.resolution)

    solver = LaplaceSolver()
    target_current = 0.5

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
            # ВАЖНО: При расчете ВАХ мы меняем напряжение анода (u), но не меняем max_voltage в конфиге.
            # Поэтому voltage_scale = u / max_v, чтобы частицы чувствовали изменение поля.
            # Но постойте, мы уже изменили граничные условия в grid.potential!
            # Значит voltage_scale должен быть 1.0, так как поле уже пересчитано под новое U.
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
        # 1. Формируем массив напряжений с плотностью у нуля (без хардкода)
        # Степень 6 гарантирует "микроскопический" просмотр начала ВАХ
        max_v = self.cfg.user.max_voltage
        num_points = self.cfg.user.max_stat_simulation_steps

        # Линейная шкала лучше для обзорной ВАХ
        voltages = np.linspace(0, max_v, num_points)
        
        print(f"--- Запуск ПАРАЛЛЕЛЬНОГО расчета ВАХ ({len(voltages)} точек) ---")

        # 2. Запуск пула процессов
        transmission_rates = []

        # Используем ProcessPoolExecutor для задействования всех ядер CPU
        # ВАЖНО: Передаем копию конфига, чтобы не было гонок
        with ProcessPoolExecutor() as executor:
            # Подготавливаем список задач
            futures = []
            for u in voltages:
                futures.append(executor.submit(_voltage_worker, u, max_v, self.cfg, self.grid, x_spawn, y_range))

            # Собираем результаты по мере завершения
            # ВАЖНО: Нужно собирать в том же порядке, что и voltages!
            # as_completed не гарантирует порядок, поэтому просто итерируемся по futures
            for i, future in enumerate(futures):
                try:
                    rate = future.result()
                    transmission_rates.append(rate)
                except Exception as e:
                    print(f"Ошибка в воркере {i}: {e}")
                    transmission_rates.append(0.0)

                # Небольшой прогресс-бар в консоль
                if i % 5 == 0:
                    print(f"Прогресс ВАХ: {i}/{len(voltages)} точек рассчитано...")

        # 3. Финальный прогон на максимальном напряжении (для гистограмм и траекторий)
        # Делаем его в основном потоке, так как нам нужны объекты частиц целиком
        print("--- Финальный прогон для анализа спектра ---")
        ps_final = ParticleSystem(self.cfg)
        ps_final.spawn_particles_manual(x_spawn, y_range)

        step = 0
        # Увеличиваем лимит шагов, чтобы точно долетели
        max_steps = self.cfg.sim.total_steps * 2 
        
        while step < max_steps:
            ps_final.update(self.grid, voltage_scale=1.0)
            if step % 50 == 0:
                if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps_final.particles):
                    break
            step += 1

        energies = [p.kinetic_energy_ev for p in ps_final.particles if p.status == ParticleStatus.HIT_ANODE]

        return {
            "iv_curve": (voltages, transmission_rates),
            "energy_hist": energies,
            "final_ps": ps_final
        }

    def plot_dashboard(self, stats_data):
        """Визуализация результатов"""
        voltages, currents = stats_data["iv_curve"]
        energies = stats_data["energy_hist"]
        final_ps = stats_data["final_ps"]

        fig = plt.figure(figsize=(14, 10))
        gs = fig.add_gridspec(2, 2)

        # График 1: ВАХ
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(voltages, currents, 'o-', color='orange', markersize=3, linewidth=1.5)
        ax1.set_title("ВАХ (Токопрохождение)")
        ax1.set_xlabel("Напряжение Анода (В)")
        ax1.set_ylabel("Прозрачность (%)")
        ax1.grid(True, which='both', alpha=0.3)
        ax1.set_ylim(-5, 105)

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
            # Рисуем линию идеального прохождения (y_in = y_out)
            if len(start_y) > 0 and len(end_y) > 0:
                min_val = min(min(start_y), min(end_y))
                max_val = max(max(start_y), max(end_y))
                ax3.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5, label="Идеал (1:1)")
            plt.colorbar(sc, ax=ax3, label="Энергия (эВ)")
            ax3.legend()
        else:
            ax3.text(0.5, 0.5, "Нет попаданий в анод", ha='center')

        ax3.set_title("Анализ смещения (Y_start vs Y_end)")
        ax3.set_xlabel("Y вылета (мм)")
        ax3.set_ylabel("Y прилета (мм)")
        ax3.grid(True, alpha=0.2)

        plt.tight_layout()
        plt.show()