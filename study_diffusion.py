import matplotlib.pyplot as plt
from md_simulation.backend import np, to_cpu
from md_simulation.constants import m_Ar
from md_simulation import config as p
from md_simulation.simulation import initialize_particles, simulation_step


def run_experiment(prob_collision, label):
    """
    Запускает симуляцию с заданной вероятностью столкновений
    и возвращает график смешивания.
    """
    print(f"--- Запуск эксперимента: Collision Prob = {prob_collision} ---")

    # 1. Инициализация
    fixed_L = p.L
    # Важно: фиксируем поршень
    piston_pos = np.array(fixed_L)
    piston_vel = np.array(0.0)

    pos, vel = initialize_particles(p.N, p.T_initial, m_Ar, fixed_L, p.L)

    # Определяем, кто "Левый" (Red), а кто "Правый" (Blue) в момент t=0
    # Создаем маску (True, если частица изначально слева)
    initial_x = pos[:, 0]
    center_x = fixed_L / 2.0
    is_originally_left = (initial_x < center_x)

    # Количество частиц, за которыми следим
    total_left_particles = np.sum(is_originally_left)  # Должно быть ~N/2

    # Списки для графика
    time_points = []
    fraction_still_left = []  # Какая доля "Левых" частиц всё еще слева?

    # 2. Цикл симуляции
    # Увеличим число шагов, чтобы увидеть процесс полностью
    steps = 4000

    for step in range(steps):
        # Двигаем частицы
        # Важно: передаем prob_collision для этого эксперимента
        pos, vel, _ = simulation_step(
            pos, vel, piston_pos, piston_vel, p.L, p.dt, collision_prob=prob_collision
        )

        # Собираем данные каждые 50 шагов
        if step % 50 == 0:
            # Берем текущие позиции "Изначально Левых" частиц
            current_x_of_left_group = pos[is_originally_left, 0]

            # Сколько из них СЕЙЧАС находятся слева?
            count_still_left = np.sum(current_x_of_left_group < center_x)

            # Доля (от 1.0 в начале до ~0.5 в конце)
            fraction = count_still_left / total_left_particles

            # Конвертируем в CPU для записи
            if hasattr(fraction, 'item'): fraction = fraction.item()

            time_points.append(step * p.dt)
            fraction_still_left.append(fraction)

    return time_points, fraction_still_left


def main():
    plt.figure(figsize=(10, 6))

    # Запустим 3 эксперимента с разной "густотой" среды

    # 1. Почти вакуум (частицы летают свободно, мгновенное перемешивание)
    t1, y1 = run_experiment(0.0, "Prob=0.0 (Вакуум)")
    plt.plot(t1, y1, label='Свободный полет (P=0.0)', linestyle='--')

    # 2. Немного столкновений (быстрая диффузия)
    t2, y2 = run_experiment(0.1, "Prob=0.1 (Разреженный газ)")
    plt.plot(t2, y2, label='Разреженный (P=0.1)')

    # 3. Плотная среда (медленная диффузия, как в жидкости)
    # Нужно искусственно увеличить probability для наглядности эффекта "густоты"
    # (в реальном газе prob зависит от плотности, но мы задаем вручную)
    t3, y3 = run_experiment(0.8, "Prob=0.8 (Плотный газ)")
    plt.plot(t3, y3, label='Плотный (P=0.8)', linewidth=2)

    # Теоретический предел
    plt.axhline(0.5, color='black', linestyle=':', label='Равновесие (0.5)')

    plt.title("Скорость диффузии (Смешивание газов)")
    plt.xlabel("Время (с)")
    plt.ylabel("Доля частиц, оставшихся в своей половине")
    plt.legend()
    plt.grid(True)

    print("Построение графика...")
    plt.show()


if __name__ == "__main__":
    main()