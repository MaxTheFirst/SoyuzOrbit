import numpy as np
from enum import Enum


# Добавляем перечисление для статусов
class ParticleStatus(Enum):
    IN_FLIGHT = 0
    HIT_ANODE = 1
    HIT_CATHODE = 2
    HIT_WALL = 3
    OUT_OF_BOUNDS = 4
    HIT_GRID = 5


class Particle:
    def __init__(self, x, y, q, m):
        self.r = np.array([x, y], dtype=float)
        self.v = np.array([0.0, 0.0], dtype=float)
        self.q = q
        self.m = m
        self.status = ParticleStatus.IN_FLIGHT  # Вместо alive
        self.trajectory = [self.r.copy()]
        # Добавим кинетическую энергию (в эВ) для графиков
        self.kinetic_energy_ev = 0.0


class ParticleSystem:
    def __init__(self, config):
        self.particles = []
        self.cfg = config

    def old_spawn_particles_manual(self, x_pos, y_range):
        ys = np.linspace(y_range[0], y_range[1], self.cfg.beam.particles_count)
        for y in ys:
            p = Particle(x_pos, y, self.cfg.physics.e_charge, self.cfg.physics.m_electron)
            self.particles.append(p)

    def spawn_particles_manual(self, x_pos, y_range):
        e = abs(self.cfg.physics.e_charge)
        m = self.cfg.physics.m_electron
        v_th = np.sqrt(2 * e * self.cfg.beam.thermal_energy_ev / m)

        ys = np.linspace(y_range[0], y_range[1], self.cfg.beam.particles_count)
        for y in ys:
            p = Particle(x_pos, y, self.cfg.physics.e_charge, self.cfg.physics.m_electron)

            angle = np.random.uniform(-np.pi / 3, np.pi / 3)
            p.v[0] = v_th * np.cos(angle)  # Скорость по X
            p.v[1] = v_th * np.sin(angle)  # Скорость по Y

            self.particles.append(p)

    def update(self, grid, voltage_scale=1.0, total_current_a=None):
        """
        grid: объект SimulationGrid
        voltage_scale: множитель потенциала
        total_current_a: Полный ток пучка в Амперах (на 1 метр глубины в 2D).
        Если None, берется cfg.beam.beam_current_a.
        """
        dt = self.cfg.sim.dt
        res = self.cfg.grid.resolution
        scale_si = 1.0 / self.cfg.physics.meters_per_unit
        if total_current_a is None:
            total_current_a = self.cfg.beam.beam_current_a

        # 1. Считаем, сколько заряда 'вносит' одна макрочастица за один шаг dt
        # dQ = (I_total * dt) / N_particles.
        # macro_charge_scale повышает эффективный заряд "макрочастицы"
        # и напрямую усиливает space-charge эффект без изменения q/m электрона.
        if len(self.particles) == 0: return
        macro_charge_scale = max(0.0, self.cfg.beam.macro_charge_scale)
        effective_current_a = total_current_a * macro_charge_scale
        charge_step = (effective_current_a * dt) / len(self.particles)

        # Объем ячейки (в 2D считаем глубину 1 метр)
        h_m = res * self.cfg.physics.meters_per_unit
        cell_volume = h_m * h_m * 1.0

        for p in self.particles:
            if p.status != ParticleStatus.IN_FLIGHT: continue

            ix_old = int(p.r[0] / res)
            iy_old = int(p.r[1] / res)

            # 1. Проверка границ
            if ix_old < 0 or ix_old >= self.cfg.grid.nx or iy_old < 0 or iy_old >= self.cfg.grid.ny:
                p.status = ParticleStatus.OUT_OF_BOUNDS
                continue

            # 2. Физика с учетом voltage_scale
            phi_old = grid.potential[iy_old, ix_old] * voltage_scale

            # Электроны несут минус, поэтому вычитаем плотность
            grid.rho[iy_old, ix_old] -= charge_step / cell_volume

            # E_new = E_calculated * (U_current / U_calculated)
            Ex_si = grid.ex[iy_old, ix_old] * scale_si * voltage_scale
            Ey_si = grid.ey[iy_old, ix_old] * scale_si * voltage_scale

            ax = (p.q / p.m) * Ex_si
            ay = (p.q / p.m) * Ey_si

            p.v[0] += ax * dt
            p.v[1] += ay * dt

            p.r[0] += (p.v[0] * dt) * scale_si
            p.r[1] += (p.v[1] * dt) * scale_si

            if not np.isfinite(p.r[0]) or not np.isfinite(p.r[1]):
                p.status = ParticleStatus.OUT_OF_BOUNDS
                continue

            if p.v[0] < -0.1:  # Небольшой порог
                p.status = ParticleStatus.HIT_CATHODE
                continue

            ix_new = int(p.r[0] / self.cfg.grid.resolution)
            iy_new = int(p.r[1] / self.cfg.grid.resolution)

            # 1. Вылет за границы
            if ix_new < 0 or ix_new >= self.cfg.grid.nx - 1 or iy_new < 0 or iy_new >= self.cfg.grid.ny - 1:
                p.status = ParticleStatus.OUT_OF_BOUNDS
                continue

            obj_id = grid.structure_map[iy_new, ix_new]
            if obj_id > 0:
                if obj_id == 2:  # Anode ID
                    p.status = ParticleStatus.HIT_ANODE
                    phi_anode = grid.potential[iy_new, ix_new] * voltage_scale
                    # Считаем, сколько вольт мы "перепрыгнули" за последний шаг
                    # delta_phi положительная, если летим к плюсу
                    delta_phi = phi_anode - phi_old
                    # Дополнительная работа поля: A = q * delta_phi
                    # Но так как q отрицательный, а мы летим на плюс, энергия растет.
                    # E_kin_added = |q * delta_phi|
                    correction_joules = abs(p.q * delta_phi)
                    # Текущая кинетическая энергия (mv^2/2)
                    v_sq = p.v[0] ** 2 + p.v[1] ** 2
                    current_e_joules = 0.5 * p.m * v_sq

                    # Итоговая энергия = То что насчитали + То что пропустили
                    total_joules = current_e_joules + correction_joules
                    # Переводим в эВ
                    p.kinetic_energy_ev = total_joules / abs(p.q)
                elif obj_id == 1:  # Cathode ID
                    p.status = ParticleStatus.HIT_CATHODE
                elif obj_id == 4:  # Grid ID
                    p.status = ParticleStatus.HIT_GRID
                else:
                    p.status = ParticleStatus.HIT_WALL
                continue

            # Считаем энергию: E = (mv^2)/2 / q_e (перевод в электрон-вольты)
            v_sq = p.v[0] ** 2 + p.v[1] ** 2
            p.kinetic_energy_ev = (0.5 * p.m * v_sq) / abs(p.q)

            p.trajectory.append(p.r.copy())
