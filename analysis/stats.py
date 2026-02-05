import numpy as np
import matplotlib.pyplot as plt

from simulation.particles import ParticleStatus, ParticleSystem
import copy


class StatisticsAnalyzer:
    def __init__(self, grid, config):
        self.grid = grid
        self.cfg = config

    def run_iv_curve(self, voltage_steps=20):
        """
        Строит ВАХ (Вольт-Амперную характеристику).
        Использует уже рассчитанное поле grid, просто масштабирует его.
        """
        max_v = self.cfg.user.max_voltage
        voltages = np.linspace(0, max_v, voltage_steps)
        currents = []  # В % от эмиссии (Transmission rate)

        # Запоминаем параметры пучка, чтобы спавнить одинаково
        # В main мы рассчитывали координаты динамически, нам нужно их передать сюда
        # Для простоты предположим, что ps уже настроен, мы будем создавать копии

        print(f"Расчет ВАХ ({voltage_steps} точек)...")

        # Нам нужно знать точку старта. Возьмем её из layout конфига примерно
        # Или лучше передадим "эталонную" систему частиц

        for u in voltages:
            # Коэффициент масштаба поля
            # Если расчет был для max_voltage, то scale = u / max_voltage
            scale = u / max_v if max_v != 0 else 0

            # Создаем новую систему частиц для каждого теста
            ps = ParticleSystem(self.cfg)

            # ВАЖНО: Нам нужно знать, откуда спавнить.
            # Давай используем те же параметры, что и в конфиге,
            # но нужно пересчитать координаты мм в "абсолютные"
            # Для упрощения сейчас возьмем фиксированные из конфига (BeamConfig)
            # При условии, что BeamConfig хранит корректные абсолютные значения (мы это правили)
            # ЕСЛИ НЕТ: нужно прокинуть координаты спавна в run_iv_curve

            # ХАК: Пока спавним "на глаз" по конфигу, если он не обновлялся в main, будет ошибка.
            # Правильнее передать функцию спавна.
            pass

        return voltages, currents

    def calculate_full_stats(self, spawn_func):
        """
        Считает статистику, динамически ожидая завершения полета частиц.
        """
        # 1. Данные для ВАХ
        voltages = np.linspace(0, self.cfg.user.max_voltage, self.cfg.beam.particles_count)
        transmission_rates = []

        print(f"--- Запуск расчета ВАХ ({len(voltages)} точек) ---")

        for i, u in enumerate(voltages):
            if u == 0:
                transmission_rates.append(0.0)
                continue

            scale = u / self.cfg.user.max_voltage
            ps = ParticleSystem(self.cfg)
            spawn_func(ps)

            # --- УМНЫЙ ЦИКЛ СИМУЛЯЦИИ ---
            # При низком напряжении частицы летят медленно.
            # Даем им запас времени (например, 20-кратный от номинала),
            # но прерываемся, как только все долетели.
            max_steps_safety = self.cfg.sim.total_steps * 20

            step = 0
            while step < max_steps_safety:
                ps.update(self.grid, voltage_scale=scale)

                # Проверка: есть ли еще живые (летящие) частицы?
                # Оптимизация: проверяем не каждый шаг, а раз в 50 шагов
                if step % 50 == 0:
                    active_count = sum(1 for p in ps.particles if p.status == ParticleStatus.IN_FLIGHT)
                    if active_count == 0:
                        break  # Все долетели или врезались
                step += 1

            # Считаем результаты
            hits = sum(1 for p in ps.particles if p.status == ParticleStatus.HIT_ANODE)
            total = len(ps.particles)
            rate = (hits / total) * 100 if total > 0 else 0
            transmission_rates.append(rate)

            # Диагностика для первых точек (где обычно нули)
            if i < 3 or hits == 0:
                in_flight = sum(1 for p in ps.particles if p.status == ParticleStatus.IN_FLIGHT)
                wall = sum(1 for p in ps.particles if p.status == ParticleStatus.HIT_WALL)
                print(f"U={u:.1f}V: Anode={hits}, Wall={wall}, Flight={in_flight} (Steps taken: {step})")

        # 2. Данные по энергиям (на максимальном напряжении)
        print("--- Расчет спектра энергий ---")
        ps_final = ParticleSystem(self.cfg)
        spawn_func(ps_final)

        # Тоже используем умный цикл для финального прогона
        step = 0
        while step < self.cfg.sim.total_steps * 5:
            ps_final.update(self.grid, voltage_scale=1.0)
            if step % 50 == 0:
                if not any(p.status == ParticleStatus.IN_FLIGHT for p in ps_final.particles):
                    break
            step += 1

        energies = [p.kinetic_energy_ev for p in ps_final.particles if p.status == ParticleStatus.HIT_ANODE]

        print(f"Финальный прогон: долетело {len(energies)} из {len(ps_final.particles)}")
        if len(energies) == 0:
            # Выведем статус всех частиц для отладки
            status_counts = {}
            for p in ps_final.particles:
                s = p.status.name
                status_counts[s] = status_counts.get(s, 0) + 1
            print(f"ПОЧЕМУ ПУСТО? Статусы частиц: {status_counts}")

        # 3. Фазовый портрет (опционально, можно оставить пустым пока)

        return {
            "iv_curve": (voltages, transmission_rates),
            "energy_hist": energies,
            "final_ps": ps_final
        }

    def plot_dashboard(self, stats_data):
        """Рисует красивое окно с графиками"""
        voltages, currents = stats_data["iv_curve"]
        energies = stats_data["energy_hist"]

        fig = plt.figure(figsize=(14, 8))
        gs = fig.add_gridspec(2, 2)

        # График 1: ВАХ
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(voltages, currents, 'o-', color='orange', linewidth=2)
        ax1.set_title("ВАХ (Пропускание тока)")
        ax1.set_xlabel("Напряжение Анода (В)")
        ax1.set_ylabel("Токопрохождение (%)")
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(-5, 105)

        # График 2: Энергетический спектр
        ax2 = fig.add_subplot(gs[0, 1])
        if len(energies) > 0:
            ax2.hist(energies, bins=10, color='cyan', edgecolor='black', alpha=0.7)
        ax2.set_title("Спектр энергий на Аноде")
        ax2.set_xlabel("Энергия (эВ)")
        ax2.set_ylabel("Кол-во частиц")
        ax2.grid(True, alpha=0.3)

        # График 3: Разброс пучка (Y-координаты попадания)
        ax3 = fig.add_subplot(gs[1, :])
        final_ps = stats_data["final_ps"]

        # Собираем точки
        end_points_y = [p.r[1] for p in final_ps.particles if p.status == ParticleStatus.HIT_ANODE]
        start_points_y = [p.trajectory[0][1] for p in final_ps.particles if p.status == ParticleStatus.HIT_ANODE]

        if len(end_points_y) > 0:
            # Рисуем точки попаданий
            sc = ax3.scatter(start_points_y, end_points_y, c=energies, cmap='plasma', label="Попадания")

            # Рисуем идеальную прямую (reference)
            min_y, max_y = min(start_points_y), max(start_points_y)
            ax3.plot([min_y, max_y], [min_y, max_y], 'k--', alpha=0.5, label="Идеальная прямая")

            # ВАЖНО: Вызов legend теперь ВНУТРИ if
            ax3.legend()

            # Можно добавить colorbar для энергий, раз уж мы используем цвета
            plt.colorbar(sc, ax=ax3, label="Энергия (эВ)")
        else:
            # Если никто не долетел, пишем об этом
            ax3.text(0.5, 0.5, "Нет попаданий в Анод", ha='center', va='center', transform=ax3.transAxes)

        ax3.set_title("Фокусировка (Start Y vs End Y)")
        ax3.set_xlabel("Точка вылета Y (мм)")
        ax3.set_ylabel("Точка прилета Y (мм)")
        ax3.grid(True)

        plt.tight_layout()
        plt.show()