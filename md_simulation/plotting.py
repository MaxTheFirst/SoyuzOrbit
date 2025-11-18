# md_simulation/plotting.py
import matplotlib.pyplot as plt
from md_simulation.backend import to_cpu
import numpy as cpu_np
from md_simulation.constants import k_B, m_Ar
from md_simulation.config import T_initial, L, GAMMA


def plot_results(history):
    """
    Строит 6 графиков. P-V диаграмма теперь сглажена и с теорией.
    """

    # --- ИСПРАВЛЕНИЕ: Явная конвертация в numpy массив ---
    # to_cpu возвращает list, нам нужен numpy array для математики (V ** GAMMA)
    V_cpu = cpu_np.array(to_cpu(history.get('V')))
    P_cpu = cpu_np.array(to_cpu(history.get('P')))
    T_x_cpu = cpu_np.array(to_cpu(history.get('T_x')))
    T_y_cpu = cpu_np.array(to_cpu(history.get('T_y')))
    T_z_cpu = cpu_np.array(to_cpu(history.get('T_z')))
    ratio_1D_cpu = cpu_np.array(to_cpu(history.get('ideal_gas_ratio_1D')))

    stats_every = history.get('stats_every', 1)

    U_gas_cpu = cpu_np.array(to_cpu(history.get('energy_gas_U')))
    K_piston_cpu = cpu_np.array(to_cpu(history.get('energy_piston_K')))
    E_total_cpu = cpu_np.array(to_cpu(history.get('energy_total')))
    W_ext_cpu = cpu_np.array(to_cpu(history.get('work_external')))

    final_pos_cpu = to_cpu(history.get('final_pos'))
    final_vel_cpu = to_cpu(history.get('final_vel'))
    # -----------------------------------------------------

    print("Построение графиков...")

    plt.figure(figsize=(14, 20))
    time_steps = cpu_np.arange(len(T_x_cpu)) * stats_every

    # --- 1. P-V Диаграмма (КРАСИВАЯ) ---
    plt.subplot(3, 2, 1)

    # А. Сырой шум (прозрачный)
    plt.plot(V_cpu, P_cpu, 'b-', alpha=0.15, label='Мгновенные удары')

    # Б. Сглаживание (Скользящее среднее)
    window = max(5, len(P_cpu) // 20)
    if len(P_cpu) > window:
        P_smooth = cpu_np.convolve(P_cpu, cpu_np.ones(window) / window, mode='valid')
        V_smooth = V_cpu[window // 2: -window // 2 + 1]
        if len(V_smooth) != len(P_smooth):
            V_smooth = V_cpu[:len(P_smooth)]
        plt.plot(V_smooth, P_smooth, 'b-', linewidth=2, label='Среднее давление')

        # В. Теоретическая Адиабата (P * V^gamma = const)
        # Берем точку старта из сглаженных данных
        if len(P_smooth) > 0:
            P0 = P_smooth[0]
            V0 = V_smooth[0]
            const_adiabat = P0 * (V0 ** GAMMA)
            P_theory = const_adiabat / (V_cpu ** GAMMA)
            plt.plot(V_cpu, P_theory, 'r--', linewidth=2, label='Теория (Адиабата)')

    plt.xlabel("Объем (V, м³)")
    plt.ylabel("Давление (P, Па)")
    plt.title("P-V Диаграмма")
    plt.legend()
    plt.grid(True)

    # --- 2. Температура T(t) ---
    plt.subplot(3, 2, 2)
    plt.plot(time_steps, T_x_cpu, 'r-', label='T_x')
    plt.plot(time_steps, T_y_cpu, 'g-', label='T_y')
    plt.plot(time_steps, T_z_cpu, 'b-', label='T_z')
    plt.title("Температура системы")
    plt.xlabel("Время (шаги)")
    plt.ylabel("T, K")
    plt.legend()
    plt.grid(True)

    # --- 3. Гистограмма скоростей ---
    plt.subplot(3, 2, 3)
    if final_vel_cpu is not None:
        mean_vx = cpu_np.mean(final_vel_cpu[:, 0])
        mean_vy = cpu_np.mean(final_vel_cpu[:, 1])
        mean_vz = cpu_np.mean(final_vel_cpu[:, 2])

        vx_thermal = final_vel_cpu[:, 0] - mean_vx
        vy_thermal = final_vel_cpu[:, 1] - mean_vy
        vz_thermal = final_vel_cpu[:, 2] - mean_vz

        T_x_final = (m_Ar * cpu_np.var(vx_thermal)) / k_B
        T_y_final = (m_Ar * cpu_np.var(vy_thermal)) / k_B
        T_z_final = (m_Ar * cpu_np.var(vz_thermal)) / k_B

        plt.hist(vx_thermal, bins='auto', density=True, alpha=0.6, color='tab:blue',
                 label=f'v_x (T={T_x_final:.1f}K)')
        plt.hist(vy_thermal, bins='auto', density=True, alpha=0.6, color='tab:orange',
                 label=f'v_y (T={T_y_final:.1f}K)')
        plt.hist(vy_thermal, bins='auto', density=True, alpha=0.6, color='tab:green',
                 label=f'v_y (T={T_z_final:.1f}K)')

        v_std_init = cpu_np.sqrt(k_B * T_initial / m_Ar)
        v_range = cpu_np.linspace(-4 * v_std_init, 4 * v_std_init, 200)
        pdf_init = (m_Ar / (2 * cpu_np.pi * k_B * T_initial)) ** 0.5 * cpu_np.exp(
            -m_Ar * v_range ** 2 / (2 * k_B * T_initial))
        plt.plot(v_range, pdf_init, 'k--', label='Старт 300K')

        plt.text(0.05, 0.95, f"Ветер: {mean_vx:.1f} м/с", transform=plt.gca().transAxes,
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.title("Распределение скоростей")
    plt.legend()
    plt.grid(True)

    # --- 4. Профиль плотности ---
    plt.subplot(3, 2, 4)
    if final_pos_cpu is not None and len(V_cpu) > 0:
        final_piston_pos = V_cpu[-1] / (L * L)
        plt.hist(final_pos_cpu[:, 0], bins=100, range=(0, final_piston_pos), label='Газ')
        plt.axvline(final_piston_pos, color='r', linestyle='--', label='Поршень')
    plt.title("Профиль плотности")
    plt.grid(True)

    # --- 5. Баланс Энергии ---
    plt.subplot(3, 2, 5)
    plt.plot(time_steps, U_gas_cpu, 'b-', label='U (Газ)')
    plt.plot(time_steps, K_piston_cpu, 'r-', label='K (Поршень)')
    plt.plot(time_steps, E_total_cpu, 'g-', label='Total', linewidth=2)

    if len(E_total_cpu) > 0 and W_ext_cpu is not None:
        # W_ext_cpu может быть списком, превращаем в массив для сложения
        E_theory = W_ext_cpu + E_total_cpu[0]
        plt.plot(time_steps, E_theory, 'k--', label='Теория')
    plt.title("Баланс Энергии")
    plt.legend()
    plt.grid(True)

    # --- 6. Проверка закона ---
    plt.subplot(3, 2, 6)
    if len(ratio_1D_cpu) > window:
        ratio_smooth = cpu_np.convolve(ratio_1D_cpu, cpu_np.ones(window) / window, mode='valid')
        time_smooth = time_steps[window // 2: -window // 2 + 1]
        if len(time_smooth) != len(ratio_smooth): time_smooth = time_steps[:len(ratio_smooth)]
        plt.plot(time_steps, ratio_1D_cpu, 'g-', alpha=0.2)
        plt.plot(time_smooth, ratio_smooth, 'g-', linewidth=2, label='PV / NkT')
    else:
        plt.plot(time_steps, ratio_1D_cpu, 'g-')

    plt.title("Проверка PV = NkT")
    plt.ylim(0, 2)
    plt.grid(True)

    plt.tight_layout()
    plt.show()