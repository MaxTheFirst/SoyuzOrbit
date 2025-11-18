from md_simulation.backend import np
from md_simulation.constants import k_B, m_Ar


def initialize_particles(N, T, m_Ar, piston_pos_initial, L):
    """Создает начальные массивы позиций и скоростей."""
    pos = np.random.rand(N, 3) * np.array([piston_pos_initial, L, L])
    v_std = np.sqrt(k_B * T / m_Ar)
    vel = np.random.normal(scale=v_std, size=(N, 3))
    vel -= np.mean(vel, axis=0)
    print(f"Инициализировано {N} частиц.")
    # Используем to_cpu для безопасного вывода, если backend поддерживает
    if hasattr(np, 'mean'):
        v_sq = np.sum(vel ** 2, axis=1)
        mean_v = np.mean(np.sqrt(v_sq))
        # Если это cupy массив, конвертируем (хотя здесь numpy)
        if hasattr(mean_v, 'item'):
            mean_v = mean_v.item()
        print(f"Средняя начальная скорость: {mean_v:.2f} м/с")
    return pos, vel


def simulation_step(pos, vel, piston_pos, piston_vel, L, dt, collision_prob=0.0):
    """
    Выполняет один шаг симуляции.
    Использует парные столкновения для сохранения импульса потока.
    """

    # 1. Движение
    pos_new = pos + vel * dt

    # 2. Столкновения со стенками
    hit_x0 = pos_new[:, 0] < 0
    vel[hit_x0, 0] = -vel[hit_x0, 0]
    pos_new[hit_x0, 0] = -pos_new[hit_x0, 0]

    hit_y0 = pos_new[:, 1] < 0
    hit_yL = pos_new[:, 1] > L
    vel[hit_y0 | hit_yL, 1] = -vel[hit_y0 | hit_yL, 1]
    pos_new[hit_y0, 1] = -pos_new[hit_y0, 1]
    pos_new[hit_yL, 1] = 2 * L - pos_new[hit_yL, 1]

    hit_z0 = pos_new[:, 2] < 0
    hit_zL = pos_new[:, 2] > L
    vel[hit_z0 | hit_zL, 2] = -vel[hit_z0 | hit_zL, 2]
    pos_new[hit_z0, 2] = -pos_new[hit_z0, 2]
    pos_new[hit_zL, 2] = 2 * L - pos_new[hit_zL, 2]

    # 3. Столкновение с поршнем
    hit_piston = pos_new[:, 0] > piston_pos
    vel_x_before_hit = vel[hit_piston, 0].copy()

    momentum_transfer = np.sum(2 * m_Ar * (vel_x_before_hit - piston_vel))

    vel[hit_piston, 0] = -vel_x_before_hit + 2 * piston_vel
    pos_new[hit_piston, 0] = 2 * piston_pos - pos_new[hit_piston, 0]

    # --- 4. ИСПРАВЛЕНИЕ: Парные столкновения (Сохранение Импульса) ---
    if collision_prob > 0:
        N = len(vel)
        # Выбираем кандидатов. collision_prob теперь - вероятность для ПАРЫ.
        # Для простоты берем фиксированное число пар каждый шаг для стабильности
        # Или используем маску.

        # Генерируем случайную перестановку индексов
        indices = np.arange(N)
        np.random.shuffle(indices)

        # Берем первые K частиц, где K зависит от вероятности
        # collision_prob = 0.1 значит 10% частиц вступают в реакцию
        n_collisions = int(N * collision_prob) // 2 * 2  # Должно быть четным

        if n_collisions > 0:
            idx1 = indices[:n_collisions:2]  # Первые половинки пар
            idx2 = indices[1:n_collisions:2]  # Вторые половинки пар

            v1 = vel[idx1]
            v2 = vel[idx2]

            # Скорость центра масс (сохраняется)
            v_cm = 0.5 * (v1 + v2)

            # Относительная скорость
            v_rel = v1 - v2
            v_rel_mag = np.linalg.norm(v_rel, axis=1, keepdims=True)

            # Генерируем случайные направления для относительной скорости
            random_dirs = np.random.normal(size=v_rel.shape)
            norms = np.linalg.norm(random_dirs, axis=1, keepdims=True)
            # Защита от деления на ноль
            norms = np.maximum(norms, 1e-10)
            random_dirs /= norms

            # Новая относительная скорость (той же величины, но случайного направления)
            v_rel_new = random_dirs * v_rel_mag

            # Новые скорости частиц
            vel[idx1] = v_cm + 0.5 * v_rel_new
            vel[idx2] = v_cm - 0.5 * v_rel_new

    # -------------------------------------------------------------------

    return pos_new, vel, momentum_transfer