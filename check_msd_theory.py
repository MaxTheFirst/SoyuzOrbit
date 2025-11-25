import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from md_simulation.backend import np
from md_simulation.constants import m_Ar, k_B
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step


def run_msd(prob_collision):
    """Считает MSD для одной симуляции"""
    # ... (код инициализации тот же, что раньше) ...
    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, p.L, p.L)
    pos_start = pos.copy()
    piston_pos = np.array(p.L);
    piston_vel = np.array(0.0)

    time_points = []
    msd_values = []

    # Берем первые 2000 шагов
    for step in range(2000):
        pos, vel, _ = simulation_step(pos, vel, piston_pos, piston_vel, p.L, p.dt, prob_collision)
        if step % 20 == 0:
            disp = pos - pos_start
            msd = np.mean(np.sum(disp ** 2, axis=1))
            if hasattr(msd, 'item'): msd = msd.item()
            time_points.append(step * p.dt)
            msd_values.append(msd)

    return np.array(time_points), np.array(msd_values)


def main():
    plt.figure(figsize=(12, 6))

    # --- 1. ЭКСПЕРИМЕНТ: Вакуум (P=0) ---
    t_vac, msd_vac = run_msd(0.0)
    plt.plot(t_vac, msd_vac, 'b.', label='Sim: Вакуум (P=0)', alpha=0.3)

    # --- 1. ТЕОРИЯ: Баллистика (Парабола) ---
    # v_rms^2 = 3 * k_B * T / m
    v_sq_theory = 3 * k_B * p.T_initial / m_Ar
    theory_ballistic = v_sq_theory * (t_vac ** 2)
    plt.plot(t_vac, theory_ballistic, 'k--', linewidth=2, label=r'Theory: $v^2 t^2$')

    # --- 2. ЭКСПЕРИМЕНТ: Плотный газ (P=0.8) ---
    t_gas, msd_gas = run_msd(0.8)
    plt.plot(t_gas, msd_gas, 'g-', linewidth=2, label='Sim: Газ (P=0.8)')

    # --- 2. ТЕОРИЯ: Диффузия (Линия Эйнштейна) ---
    # Мы берем "хвост" графика (вторую половину), где движение уже установилось
    # и строим линейную регрессию y = k * x + b
    def linear_func(x, k, b): return k * x + b

    # Фиттим данные
    popt, _ = curve_fit(linear_func, t_gas[50:], msd_gas[50:])
    slope_D = popt[0]  # Это и есть 6*D

    plt.plot(t_gas, linear_func(t_gas, *popt), 'r:', linewidth=2,
             label=f'Fit: Эйнштейн ($6D \\cdot t$)\n$D \\approx {slope_D / 6:.2e} m^2/s$')

    plt.title("Проверка теории Эйнштейна (MSD)")
    plt.xlabel("Время (с)")
    plt.ylabel("MSD $<r^2>$ (м²)")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    main()