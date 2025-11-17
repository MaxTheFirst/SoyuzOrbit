# md_simulation/plotting.py
import matplotlib.pyplot as plt
from md_simulation.backend import to_cpu
import numpy as cpu_np
from md_simulation.constants import k_B, m_Ar
from md_simulation.config import T_initial, L


def plot_results(history):
    """
    Строит 6 графиков для полного анализа физики симуляции.
    """

    # --- Извлекаем данные ---
    # Эти списки уже состоят из Python-чисел (CPU), т.к. to_cpu() вызывается для каждого
    V_cpu = [to_cpu(v) for v in history.get('V', [])]
    P_cpu = [to_cpu(p) for p in history.get('P', [])]
    T_x_cpu = [to_cpu(t) for t in history.get('T_x', [])]
    T_y_cpu = [to_cpu(t) for t in history.get('T_y', [])]
    T_z_cpu = [to_cpu(t) for t in history.get('T_z', [])]

    # --- ИСПРАВЛЕНИЕ 1: Используем cpu_np.array ---
    ratio_1D_cpu = cpu_np.array([to_cpu(r) for r in history.get('ideal_gas_ratio_1D', [])])

    stats_every = history.get('stats_every', 1)

    # --- ИСПРАВЛЕНИЕ 2: Используем cpu_np.array ---
    U_gas_cpu = cpu_np.array([to_cpu(u) for u in history.get('energy_gas_U', [])])
    K_piston_cpu = cpu_np.array([to_cpu(k) for k in history.get('energy_piston_K', [])])
    E_total_cpu = cpu_np.array([to_cpu(e) for e in history.get('energy_total', [])])
    W_ext_cpu = cpu_np.array([to_cpu(w) for w in history.get('work_external', [])])

    # to_cpu() корректно возвращает numpy-массив
    final_pos_cpu = to_cpu(history.get('final_pos'))
    final_vel_cpu = to_cpu(history.get('final_vel'))

    print("Построение 6-и графиков анализа...")

    plt.figure(figsize=(14, 20))

    # --- ИСПРАВЛЕНИЕ 3: Используем cpu_np.arange ---
    time_steps = cpu_np.arange(len(T_x_cpu)) * stats_every

    # --- 1. P-V Диаграмма ---
    plt.subplot(3, 2, 1)
    plt.plot(V_cpu, P_cpu, 'b-', alpha=0.7)
    plt.xlabel("Объем (V, м³)")
    plt.ylabel("Давление (P, Па)")
    plt.title("P-V Диаграмма ")
    plt.grid(True)

    # --- 2. Температура T(t) (по осям) ---
    plt.subplot(3, 2, 2)
    # Здесь все переменные уже numpy или списки (на CPU)
    plt.plot(time_steps, T_x_cpu, 'r-', label='T_x (Охлаждается)')
    plt.plot(time_steps, T_y_cpu, 'g-', label='T_y (Горячая)')
    plt.plot(time_steps, T_z_cpu, 'b-', label='T_z (Горячая)')
    plt.title("Температура системы (по осям) ")
    plt.xlabel(f"Время (x{stats_every} шагов)")
    plt.ylabel("Температура (T, K)")
    plt.legend()
    plt.grid(True)

    # --- 3. Гистограмма скоростей ---
    plt.subplot(3, 2, 3)
    if final_vel_cpu is not None:
        # final_vel_cpu уже numpy-массив
        v_std_init = cpu_np.sqrt(k_B * T_initial / m_Ar)
        v_range = cpu_np.linspace(-3 * v_std_init, 3 * v_std_init, 200)
        pdf_init = (m_Ar / (2 * cpu_np.pi * k_B * T_initial)) ** 0.5 * cpu_np.exp(
            -m_Ar * v_range ** 2 / (2 * k_B * T_initial))

        plt.hist(final_vel_cpu[:, 0], bins='auto', density=True, alpha=0.7, label='v_x (Охладилась)')
        plt.hist(final_vel_cpu[:, 1], bins='auto', density=True, alpha=0.7, label='v_y (Осталась горячей)')
        plt.plot(v_range, pdf_init, 'k--', label=f'Теория (T={T_initial}K)')

    plt.title("Распределение скоростей (Финальный 'снимок')")
    plt.xlabel("Скорость (м/с)")
    plt.ylabel("Плотность вероятности")
    plt.legend()
    plt.grid(True)

    # --- 4. Профиль плотности ---
    plt.subplot(3, 2, 4)
    if final_pos_cpu is not None and len(V_cpu) > 0:
        final_piston_pos = V_cpu[-1] / (L * L)

        # final_pos_cpu уже numpy-массив
        plt.hist(final_pos_cpu[:, 0], bins=100, range=(0, final_piston_pos), label='Плотность газа')
        plt.axvline(final_piston_pos, color='r', linestyle='--', label='Положение поршня')

    plt.title("Профиль плотности по оси X (Финальный 'снимок')")
    plt.xlabel("Позиция X (м)")
    plt.ylabel("Кол-во частиц")
    plt.legend()
    plt.grid(True)

    # --- 5. Баланс Энергии ---
    plt.subplot(3, 2, 5)
    # Все эти массивы теперь cpu_np
    plt.plot(time_steps, U_gas_cpu, 'b-', label='U (Энергия газа)')
    plt.plot(time_steps, K_piston_cpu, 'r-', label='K (Энергия поршня)')
    plt.plot(time_steps, E_total_cpu, 'g-', label='E_total (U+K)', linewidth=2)

    if len(E_total_cpu) > 0:
        E_theory = W_ext_cpu + E_total_cpu[0]
        plt.plot(time_steps, E_theory, 'k--', label='E_initial + W_ext (Теория)', linewidth=2)

    plt.title("Баланс Энергии (ΔE_total = W_ext)")
    plt.xlabel(f"Время (x{stats_every} шагов)")
    plt.ylabel("Энергия (Дж)")
    plt.legend()
    plt.grid(True)

    # --- 6. Провал Закона Идеального Газа ---
    plt.subplot(3, 2, 6)
    # ratio_1D_cpu теперь cpu_np
    plt.plot(time_steps, ratio_1D_cpu, 'g-', label='(PV)/(NkT_x)')
    plt.title("Провал Закона Идеального Газа (PV != NkT_x)")
    plt.xlabel(f"Время (x{stats_every} шагов)")
    plt.ylabel("Отношение")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()