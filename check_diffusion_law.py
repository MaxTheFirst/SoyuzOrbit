import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from md_simulation.backend import np
from md_simulation.constants import m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step


def run_mixing(prob_collision):
    # ... (стандартная инициализация) ...
    piston_pos = np.array(p.L);
    piston_vel = np.array(0.0)
    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, p.L, p.L)

    # Считаем начальных левых
    center = p.L / 2
    is_left = (pos[:, 0] < center)
    total_tracked = np.sum(is_left)

    times = [];
    fractions = []

    for step in range(3000):  # Чуть длиннее
        pos, vel, _ = simulation_step(pos, vel, piston_pos, piston_vel, p.L, p.dt, prob_collision)
        if step % 50 == 0:
            current_left = np.sum(pos[is_left, 0] < center)
            frac = current_left / total_tracked
            if hasattr(frac, 'item'): frac = frac.item()
            times.append(step * p.dt);
            fractions.append(frac)

    return np.array(times), np.array(fractions)


def exponential_decay(t, tau):
    """Теоретический закон релаксации к 0.5"""
    return 0.5 + 0.5 * np.exp(-t / tau)


def main():
    plt.figure(figsize=(10, 6))

    # 1. Запускаем плотный газ
    print("Симуляция...")
    t_data, y_data = run_mixing(0.8)

    plt.plot(t_data, y_data, 'g-', alpha=0.6, linewidth=3, label='Симуляция (P=0.8)')

    # 2. Подбираем теоретическую кривую (curve_fit)
    # Мы просим компьютер: "Найди такое tau, чтобы формула идеально легла на график"
    popt, _ = curve_fit(exponential_decay, t_data, y_data, p0=[1e-10])
    tau_fitted = popt[0]

    y_theory = exponential_decay(t_data, tau_fitted)

    plt.plot(t_data, y_theory, 'k--', linewidth=1.5,
             label=f'Теория (Экспонента)\n$\\tau \\approx {tau_fitted:.2e} с$')

    plt.axhline(0.5, color='gray', linestyle=':', label='Равновесие')

    plt.title("Проверка Закона Фика (Релаксация)")
    plt.xlabel("Время (с)")
    plt.ylabel("Доля частиц в своей половине")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    main()