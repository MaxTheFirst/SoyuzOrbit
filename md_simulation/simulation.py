from md_simulation.backend import np
from md_simulation.constants import k_B, m_Ar


def initialize_particles(N, T, m_Ar, piston_pos_initial, L):
    """Создает начальные массивы позиций и скоростей."""

    # 1. Позиции (x, y, z)
    pos = np.random.rand(N, 3) * np.array([piston_pos_initial, L, L])

    # 2. Скорости (vx, vy, vz) по Максвеллу-Больцману
    v_std = np.sqrt(k_B * T / m_Ar)
    vel = np.random.normal(scale=v_std, size=(N, 3))

    # Центрируем скорости (чтобы ящик не улетал)
    vel -= np.mean(vel, axis=0)

    print(f"Инициализировано {N} частиц.")
    print(f"Средняя начальная скорость: {np.mean(np.sqrt(np.sum(vel ** 2, axis=1))):.2f} м/с")

    return pos, vel


def simulation_step(pos, vel, piston_pos, piston_vel, L, dt):
    """
    Выполняет один шаг симуляции для всех N частиц.
    """

    # 1. Движение
    pos_new = pos + vel * dt

    # 2. Столкновения с неподвижными стенками
    # Ось X (задняя стенка)
    hit_x0 = pos_new[:, 0] < 0
    vel[hit_x0, 0] = -vel[hit_x0, 0]
    pos_new[hit_x0, 0] = -pos_new[hit_x0, 0]

    # Ось Y
    hit_y0 = pos_new[:, 1] < 0
    hit_yL = pos_new[:, 1] > L
    vel[hit_y0 | hit_yL, 1] = -vel[hit_y0 | hit_yL, 1]
    pos_new[hit_y0, 1] = -pos_new[hit_y0, 1]
    pos_new[hit_yL, 1] = 2 * L - pos_new[hit_yL, 1]

    # Ось Z
    hit_z0 = pos_new[:, 2] < 0
    hit_zL = pos_new[:, 2] > L
    vel[hit_z0 | hit_zL, 2] = -vel[hit_z0 | hit_zL, 2]
    pos_new[hit_z0, 2] = -pos_new[hit_z0, 2]
    pos_new[hit_zL, 2] = 2 * L - pos_new[hit_zL, 2]

    # 3. Столкновения с подвижным поршнем
    hit_piston = pos_new[:, 0] > piston_pos

    vel_x_before_hit = vel[hit_piston, 0].copy()

    # Считаем суммарный импульс, переданный поршню F = dp/dt
    # p_piston = 2*m*(v_old - piston_vel)
    momentum_transfer = np.sum(2 * m_Ar * (vel_x_before_hit - piston_vel))

    # Обновляем скорости частиц
    vel[hit_piston, 0] = -vel_x_before_hit + 2 * piston_vel

    # Корректируем позиции
    pos_new[hit_piston, 0] = 2 * piston_pos - pos_new[hit_piston, 0]

    return pos_new, vel, momentum_transfer