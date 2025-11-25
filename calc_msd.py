import matplotlib.pyplot as plt
from md_simulation.backend import np, to_cpu
from md_simulation.constants import m_Ar, k_B
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step


def run_msd_experiment(prob_collision, label):
    """
    Считает Mean Squared Displacement (MSD) = <r^2(t)>
    """
    print(f"--- Запуск MSD: Collision Prob = {prob_collision} ---")

    # 1. Инициализация
    # Фиксируем поршень (объем постоянен)
    piston_pos = np.array(p.L)
    piston_vel = np.array(0.0)

    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, p.L, p.L)

    # Запоминаем НАЧАЛЬНЫЕ позиции
    # ВАЖНО: В замкнутом ящике MSD выйдет на плато, когда частицы разлетятся по углам.
    # Чтобы увидеть чистую диффузию, мы смотрим на начальный этап.
    pos_start = pos.copy()

    time_points = []
    msd_values = []

    # 2. Цикл
    # Берем меньше шагов, но смотрим подробнее
    steps = 2000

    for step in range(steps):
        # Шаг физики
        pos, vel, _ = simulation_step(
            pos, vel, piston_pos, piston_vel, p.L, p.dt, collision_prob=prob_collision
        )

        # Сбор данных каждые 10 шагов
        if step % 10 == 0:
            # Вектор смещения (dx, dy, dz)
            displacement = pos - pos_start

            # Квадрат расстояния r^2 = dx^2 + dy^2 + dz^2
            sq_dist = np.sum(displacement ** 2, axis=1)

            # Среднее по всем частицам <r^2>
            mean_sq_dist = np.mean(sq_dist)

            # Конвертация для графика
            if hasattr(mean_sq_dist, 'item'): mean_sq_dist = mean_sq_dist.item()

            time_points.append(step * p.dt)
            msd_values.append(mean_sq_dist)

    return time_points, msd_values


def main():
    plt.figure(figsize=(10, 6))

    # 1. Баллистический режим (без столкновений)
    # Частицы летят прямо: r ~ t, значит r^2 ~ t^2 (парабола)
    t1, y1 = run_msd_experiment(0.0, "Вакуум (P=0.0)")
    plt.plot(t1, y1, label='Вакуум (P=0.0)', linestyle='--')

    # 2. Диффузионный режим (частые столкновения)
    # Частицы блуждают: r^2 ~ t (линейный рост)
    t2, y2 = run_msd_experiment(0.8, "Плотный газ (P=0.8)")
    plt.plot(t2, y2, label='Плотный газ (P=0.8)', linewidth=2)

    plt.title("Среднеквадратичное смещение (MSD)")
    plt.xlabel("Время (с)")
    plt.ylabel("MSD <r^2> (м^2)")
    plt.legend()
    plt.grid(True)

    # Теоретическое пояснение на графике
    plt.text(t1[len(t1) // 4], y1[len(y1) // 4], r"$\sim t^2$ (Баллистика)", color='blue')
    plt.text(t2[len(t2) // 2], y2[len(y2) // 2], r"$\sim t$ (Диффузия)", color='green')

    print("Построение графика...")
    plt.show()


if __name__ == "__main__":
    main()
