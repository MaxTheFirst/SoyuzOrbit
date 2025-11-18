# run_simulation.py

import time

from md_simulation.backend import np, to_cpu
from md_simulation.constants import k_B, m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step
from md_simulation.plotting import plot_results


def main():
    print("--- 🚀 Запуск симуляции ---")

    pos, vel = initialize_particles(
        p.N, p.T_initial, m_Ar, p.piston_pos_initial, p.L
    )

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

    # Больше не накапливаем импульс за много шагов
    work_external_total = 0.0
    # Мгновенная внутренняя сила от газа (обновляется каждый шаг)
    force_internal = 0.0

    start_time = time.time()
    initial_len = p.piston_pos_initial

    for step in range(p.num_steps):
        current_len = piston_pos
        density_factor = initial_len / current_len

        # Ограничиваем, чтобы вероятность не ушла в > 1 (при сжатии) или в < 0
        dynamic_prob = p.collision_prob * density_factor
        if dynamic_prob > 1.0: dynamic_prob = 1.0

        # 1. Шаг симуляции частиц
        pos, vel, momentum_transfer = simulation_step(
            pos, vel, piston_pos, piston_vel, p.L, p.dt, dynamic_prob
        )

        # 2. Движение поршня КАЖДЫЙ шаг по текущему импульсу
        #    F_internal = Δp / Δt
        force_internal = momentum_transfer / p.dt
        force_external = p.P_external * piston_area
        force_net = force_internal - force_external

        piston_accel = force_net / p.piston_mass
        piston_vel += piston_accel * p.dt
        piston_pos += piston_vel * p.dt

        # 3. Сбор статистики раз в stats_every шагов
        if step % p.stats_every == 0 and step > 0:
            V = piston_pos * piston_area
            P_internal = force_internal / piston_area

            # --- ИСПРАВЛЕНИЕ: Считаем температуру относительно ЦЕНТРА МАСС газа ---
            # Находим среднюю скорость потока (ветра) по каждой оси
            mean_vx = np.mean(vel[:, 0])
            mean_vy = np.mean(vel[:, 1])
            mean_vz = np.mean(vel[:, 2])

            # Вычитаем поток, чтобы найти чисто тепловую (хаотическую) скорость
            v_thermal_x = vel[:, 0] - mean_vx
            v_thermal_y = vel[:, 1] - mean_vy
            v_thermal_z = vel[:, 2] - mean_vz

            # Считаем энергию хаоса (истинная температура)
            E_kin_x = 0.5 * m_Ar * np.sum(v_thermal_x ** 2)
            E_kin_y = 0.5 * m_Ar * np.sum(v_thermal_y ** 2)
            E_kin_z = 0.5 * m_Ar * np.sum(v_thermal_z ** 2)

            # ---

            T_x = (2.0 * E_kin_x) / (p.N * k_B)
            T_y = (2.0 * E_kin_y) / (p.N * k_B)
            T_z = (2.0 * E_kin_z) / (p.N * k_B)

            # Для полной энергии (E_total) мы по-прежнему используем ПОЛНУЮ скорость (vel),
            # так как энергия ветра - это тоже энергия газа!
            E_kin_total_real = 0.5 * m_Ar * np.sum(vel ** 2)

            T_total = (T_x + T_y + T_z) / 3.0

            if T_x > 1e-6:
                ratio_1D = (P_internal * V) / (p.N * k_B * T_x)
            else:
                ratio_1D = 0.0

            # ВАЖНО: В балансе энергии (U) участвует ВСЯ энергия (включая ветер)
            U_gas = E_kin_total_real
            K_piston = 0.5 * p.piston_mass * (piston_vel ** 2)
            E_total = U_gas + K_piston

            # dV за последний шаг статистики (примерно)
            # здесь можно хранить прошлый V, но для плавной эволюции
            # достаточно использовать приращение за текущий шаг
            delta_V = piston_vel * p.dt * piston_area
            work_external_total += -p.P_external * delta_V

            history['V'].append(V)
            history['P'].append(P_internal)
            history['T_total'].append(T_total)
            history['T_x'].append(T_x)
            history['T_y'].append(T_y)
            history['T_z'].append(T_z)
            history['ideal_gas_ratio_1D'].append(ratio_1D)
            history['energy_gas_U'].append(U_gas)
            history['energy_piston_K'].append(K_piston)
            history['energy_total'].append(E_total)
            history['work_external'].append(work_external_total)

            if p.head_and_tail and p.stats_every * 11 < step < p.num_steps - (p.stats_every * 10):
                continue
            elif p.head_and_tail and step == p.stats_every * 11:
                print("-------------------------------------------------------")
            else:
                print(
                    f"Шаг {step:>5} | V: {to_cpu(V):.2e} | P: {to_cpu(P_internal):.2e} | "
                    f"Tx: {to_cpu(T_x):.1f} Ty: {to_cpu(T_y):.1f} Tz: {to_cpu(T_z):.1f} | "
                    f"T_tot: {to_cpu(T_total):.1f} K | ", f"Prob: {dynamic_prob:.4f}"
                )

    end_time = time.time()
    print(f"--- ✅ Симуляция завершена за {end_time - start_time:.2f} сек. ---")

    history['final_pos'] = pos
    history['final_vel'] = vel

    plot_results(history)


if __name__ == "__main__":
    main()
