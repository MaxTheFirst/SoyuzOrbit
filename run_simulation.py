#!/usr/bin/env python
# run_simulation.py
import time

from md_simulation.backend import np, to_cpu
from md_simulation.constants import k_B, m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step
from md_simulation.plotting import plot_results


def main():
    print("--- 🚀 Запуск симуляции ---")

    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, p.piston_pos_initial, p.L)

    piston_pos = np.array(p.piston_pos_initial)
    piston_vel = np.array(0.0)
    piston_area = p.L * p.L

    history = {
        'V': [], 'P': [], 'T_total': [], 'stats_every': p.stats_every,
        'T_x': [], 'T_y': [], 'T_z': [],
        'ideal_gas_ratio_1D': [],
        'energy_gas_U': [], 'energy_piston_K': [],
        'energy_total': [], 'work_external': []
    }

    momentum_accumulator = np.array(0.0)
    work_external_total = 0.0

    start_time = time.time()
    for step in range(p.num_steps):

        # Движение поршня и сбор статистики (раз в 100 шагов)
        if step % p.stats_every == 0 and step > 0:

            # 1. Считаем СРЕДНЮЮ силу
            time_elapsed = p.dt * p.stats_every
            force_internal_avg = momentum_accumulator / time_elapsed
            force_external = p.P_external * piston_area
            force_net_avg = force_internal_avg - force_external

            # 2. Двигаем поршень (стабильный метод)
            piston_accel = force_net_avg / p.piston_mass
            piston_pos_old = piston_pos

            piston_vel += piston_accel * time_elapsed
            piston_pos += piston_vel * time_elapsed

            # 3. Сбор статистики
            V = piston_pos * piston_area
            P_internal = force_internal_avg / piston_area

            E_kin_x = 0.5 * m_Ar * np.sum(vel[:, 0] ** 2)
            E_kin_y = 0.5 * m_Ar * np.sum(vel[:, 1] ** 2)
            E_kin_z = 0.5 * m_Ar * np.sum(vel[:, 2] ** 2)

            T_x = (2.0 * E_kin_x) / (p.N * k_B)
            T_y = (2.0 * E_kin_y) / (p.N * k_B)
            T_z = (2.0 * E_kin_z) / (p.N * k_B)

            E_kin_total = E_kin_x + E_kin_y + E_kin_z
            T_total = (T_x + T_y + T_z) / 3.0

            if T_x > 1e-6:
                ratio_1D = (P_internal * V) / (p.N * k_B * T_x)
            else:
                ratio_1D = 0.0

            U_gas = E_kin_total
            K_piston = 0.5 * p.piston_mass * (piston_vel ** 2)
            E_total = U_gas + K_piston

            delta_V = V - (piston_pos_old * piston_area)
            work_external_total += -p.P_external * delta_V

            # Сохраняем
            history['V'].append(V);
            history['P'].append(P_internal)
            history['T_total'].append(T_total);
            history['T_x'].append(T_x)
            history['T_y'].append(T_y);
            history['T_z'].append(T_z)
            history['ideal_gas_ratio_1D'].append(ratio_1D)
            history['energy_gas_U'].append(U_gas)
            history['energy_piston_K'].append(K_piston)
            history['energy_total'].append(E_total)
            history['work_external'].append(work_external_total)

            momentum_accumulator = np.array(0.0)  # Сброс

            print(
                f"Шаг {step:>5} | V: {to_cpu(V):.2e} м³ | P_вн: {to_cpu(P_internal):.2e} Па | T_x: {to_cpu(T_x):.1f} K | (PV/NkT_x): {to_cpu(ratio_1D):.2f}")

        # Симуляция частиц (каждый шаг dt)
        pos, vel, momentum_transfer = simulation_step(
            pos, vel, piston_pos, piston_vel, p.L, p.dt
        )
        momentum_accumulator += momentum_transfer

    end_time = time.time()
    print(f"--- ✅ Симуляция завершена за {end_time - start_time:.2f} сек. ---")

    # --- <--- НОВОЕ: Сохраняем финальный "снимок" ---
    history['final_pos'] = pos
    history['final_vel'] = vel
    # ---

    # 4. Визуализация
    plot_results(history)


if __name__ == "__main__":
    main()