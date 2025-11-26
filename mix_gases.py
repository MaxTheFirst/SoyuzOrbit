# mix_gases.py

import matplotlib.pyplot as plt
from md_simulation.backend import np, to_cpu
from md_simulation.constants import k_B, m_Ar, m_He
from md_simulation import config as p
from md_simulation.simulation import simulation_step


def initialize_mixture(N, T, m1, m2, L):
    """
    Создает смесь двух газов.
    Первая половина (0..N/2) - Тяжелый газ (m1).
    Вторая половина (N/2..N) - Легкий газ (m2).
    """
    pos = np.random.rand(N, 3) * L  # Равномерно по всему ящику

    # Массив масс: половина m1, половина m2
    masses = np.zeros(N)
    half = N // 2
    masses[:half] = m1
    masses[half:] = m2

    # Генерация скоростей с учетом массы! v ~ sqrt(kT / m)
    vel = np.zeros((N, 3))

    # Для тяжелых (Аргон)
    v_std1 = np.sqrt(k_B * T / m1)
    vel[:half] = np.random.normal(scale=v_std1, size=(half, 3))

    # Для легких (Гелий)
    v_std2 = np.sqrt(k_B * T / m2)
    vel[half:] = np.random.normal(scale=v_std2, size=(N - half, 3))

    # Убираем дрейф центра масс всей системы
    vel -= np.mean(vel, axis=0)

    return pos, vel, masses


def main():
    print("--- 🧪 Изучение Смеси Газов (Ar + He) с Теоретическими кривыми ---")

    # 1. Инициализация
    piston_pos = np.array(p.L)
    piston_vel = np.array(0.0)

    # Создаем смесь Аргона (m_Ar) и Гелия (m_He)
    pos, vel, masses = initialize_mixture(p.N, p.T_initial, m_Ar, m_He, p.L)

    pos_start = pos.copy()
    half = p.N // 2

    # Списки для хранения данных MSD
    time_points = []
    msd_Ar = []
    msd_He = []

    # 2. Симуляция
    steps = 2000
    print(f"Запуск симуляции на {steps} шагов...")

    for step in range(steps):
        # ВАЖНО: Передаем masses, чтобы симуляция знала, что частицы разные!
        pos, vel, _ = simulation_step(
            pos, vel, piston_pos, piston_vel, p.L, p.dt,
            collision_prob=0.8,
            masses=masses
        )

        # Сбор данных каждые 10 шагов
        if step % 10 == 0:
            # Считаем MSD отдельно для групп
            disp = pos - pos_start
            sq_dist = np.sum(disp ** 2, axis=1)

            # Аргон (первая половина)
            msd1 = np.mean(sq_dist[:half])
            # Гелий (вторая половина)
            msd2 = np.mean(sq_dist[half:])

            # Конвертируем в обычные числа (если используем GPU)
            if hasattr(msd1, 'item'): msd1 = msd1.item()
            if hasattr(msd2, 'item'): msd2 = msd2.item()

            time_points.append(step * p.dt)
            msd_Ar.append(msd1)
            msd_He.append(msd2)

    # Сохраняем финальные модули скоростей для гистограммы
    speeds = np.sqrt(np.sum(vel ** 2, axis=1))
    final_speeds_Ar = to_cpu(speeds[:half])
    final_speeds_He = to_cpu(speeds[half:])

    # 3. Построение Графиков
    plt.figure(figsize=(14, 6))

    # --- График А: Закон Грэма (MSD) ---
    plt.subplot(1, 2, 1)
    plt.plot(time_points, msd_He, 'r-', label='Гелий (Легкий)', linewidth=2)
    plt.plot(time_points, msd_Ar, 'b-', label='Аргон (Тяжелый)', linewidth=2)

    # Считаем отношение диффузии в конце
    if msd_Ar[-1] > 1e-20:
        ratio = msd_He[-1] / msd_Ar[-1]
    else:
        ratio = 0.0

    plt.title(f"Закон Грэма: Диффузия\nHe быстрее Ar в {ratio:.1f} раз")
    plt.xlabel("Время (с)")
    plt.ylabel(r"MSD $\langle r^2 \rangle$ ($м^2$)")
    plt.legend()
    plt.grid(True)

    # --- График Б: Распределение Максвелла + ТЕОРИЯ ---
    plt.subplot(1, 2, 2)

    # 1. Эксперимент (Гистограммы)
    # density=True важно, чтобы площадь была равна 1 (как у теории)
    plt.hist(final_speeds_Ar, bins=50, alpha=0.6, color='blue', density=True, label='Аргон (Exp)')
    plt.hist(final_speeds_He, bins=50, alpha=0.6, color='red', density=True, label='Гелий (Exp)')

    # 2. Теория (Кривые Максвелла)
    def maxwell_pdf(v, T, m):
        """Теоретическая плотность вероятности для скорости v"""
        # Формула распределения Максвелла по модулю скорости
        pref = (m / (2 * np.pi * k_B * T)) ** 1.5 * 4 * np.pi
        return pref * v ** 2 * np.exp(-m * v ** 2 / (2 * k_B * T))

    # Создаем массив скоростей для плавной линии
    v_max = max(np.max(final_speeds_He), 3000)
    v_range = np.linspace(0, v_max, 1000)

    # Считаем теорию
    pdf_Ar = maxwell_pdf(v_range, p.T_initial, m_Ar)
    pdf_He = maxwell_pdf(v_range, p.T_initial, m_He)

    # Рисуем пунктирные линии
    plt.plot(v_range, pdf_Ar, 'b--', linewidth=2, label='Аргон (Теория)')
    plt.plot(v_range, pdf_He, 'r--', linewidth=2, label='Гелий (Теория)')

    plt.title("Распределение Скоростей (T = const)")
    plt.xlabel("Скорость (м/с)")
    plt.ylabel("Вероятность")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()