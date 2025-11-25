# md_simulation/simulation.py

from md_simulation.backend import np
from md_simulation.constants import k_B, m_Ar


def initialize_particles(N, T, m_Ar, piston_pos_initial, L):
    """Создает начальные массивы позиций и скоростей."""
    pos = np.random.rand(N, 3) * np.array([piston_pos_initial, L, L])
    v_std = np.sqrt(k_B * T / m_Ar)
    vel = np.random.normal(scale=v_std, size=(N, 3))
    vel -= np.mean(vel, axis=0)
    print(f"Инициализировано {N} частиц.")

    # Расчет средней скорости для информации
    v_sq = np.sum(vel ** 2, axis=1)
    mean_v = np.mean(np.sqrt(v_sq))
    if hasattr(mean_v, 'item'):
        mean_v = mean_v.item()
    print(f"Средняя начальная скорость: {mean_v:.2f} м/с")

    return pos, vel


def simulation_step(pos, vel, piston_pos, piston_vel, L, dt, collision_prob=0.0, masses=None):
    """
    Универсальный шаг симуляции.
    Работает и для чистого газа (masses=None), и для смесей.
    """

    # 1. Движение
    pos_new = pos + vel * dt

    # 2. Отражения от стенок
    hit_x0 = pos_new[:, 0] < 0
    vel[hit_x0, 0] = -vel[hit_x0, 0]
    pos_new[hit_x0, 0] = -pos_new[hit_x0, 0]

    hit_y0 = pos_new[:, 1] < 0;
    hit_yL = pos_new[:, 1] > L
    vel[hit_y0 | hit_yL, 1] = -vel[hit_y0 | hit_yL, 1]
    pos_new[hit_y0, 1] = -pos_new[hit_y0, 1]
    pos_new[hit_yL, 1] = 2 * L - pos_new[hit_yL, 1]

    hit_z0 = pos_new[:, 2] < 0;
    hit_zL = pos_new[:, 2] > L
    vel[hit_z0 | hit_zL, 2] = -vel[hit_z0 | hit_zL, 2]
    pos_new[hit_z0, 2] = -pos_new[hit_z0, 2]
    pos_new[hit_zL, 2] = 2 * L - pos_new[hit_zL, 2]

    # 3. Столкновение с поршнем
    hit_piston = pos_new[:, 0] > piston_pos

    # Если masses не передан, считаем, что бьет Аргон (m_Ar)
    # Если передан - берем массу конкретной частицы
    if masses is None:
        mass_of_hitters = m_Ar
    else:
        mass_of_hitters = masses[hit_piston]
        if len(mass_of_hitters.shape) == 2:  # Убираем лишние измерения если есть
            mass_of_hitters = mass_of_hitters.flatten()

    vel_x_before_hit = vel[hit_piston, 0].copy()

    # Импульс dp = 2 * m * (v - v_piston)
    # Проверка на пустоту (если никто не ударил)
    if len(vel_x_before_hit) > 0:
        momentum_transfer = np.sum(2 * mass_of_hitters * (vel_x_before_hit - piston_vel))
    else:
        momentum_transfer = 0.0

    vel[hit_piston, 0] = -vel_x_before_hit + 2 * piston_vel
    pos_new[hit_piston, 0] = 2 * piston_pos - pos_new[hit_piston, 0]

    # --- 4. ПАРНЫЕ СТОЛКНОВЕНИЯ (ТЕРМАЛИЗАЦИЯ) ---
    if collision_prob > 0:
        N = len(vel)
        n_collisions = int(N * collision_prob) // 2 * 2

        if n_collisions > 0:
            indices = np.arange(N)
            np.random.shuffle(indices)

            idx1 = indices[:n_collisions:2]
            idx2 = indices[1:n_collisions:2]

            v1 = vel[idx1]
            v2 = vel[idx2]

            # --- ВЕТКА А: СМЕСЬ ГАЗОВ (Разные массы) ---
            if masses is not None:
                m1 = masses[idx1][:, None]
                m2 = masses[idx2][:, None]
                M_pair = m1 + m2

                # Скорость центра масс (взвешенная)
                v_cm = (m1 * v1 + m2 * v2) / M_pair

                # Относительная скорость
                v_rel = v1 - v2
                v_rel_mag = np.linalg.norm(v_rel, axis=1, keepdims=True)

                # Случайный поворот
                random_dirs = np.random.normal(size=v_rel.shape)
                random_dirs /= np.linalg.norm(random_dirs, axis=1, keepdims=True)
                v_rel_new = random_dirs * v_rel_mag

                # Обновление
                vel[idx1] = v_cm + (m2 / M_pair) * v_rel_new
                vel[idx2] = v_cm - (m1 / M_pair) * v_rel_new

            # --- ВЕТКА Б: ОБЫЧНЫЙ ГАЗ (Одинаковые массы) ---
            else:
                # Упрощенная и быстрая формула для равных масс
                v_cm = 0.5 * (v1 + v2)
                v_rel = v1 - v2
                v_rel_mag = np.linalg.norm(v_rel, axis=1, keepdims=True)

                random_dirs = np.random.normal(size=v_rel.shape)
                random_dirs /= np.linalg.norm(random_dirs, axis=1, keepdims=True)
                v_rel_new = random_dirs * v_rel_mag

                vel[idx1] = v_cm + 0.5 * v_rel_new
                vel[idx2] = v_cm - 0.5 * v_rel_new

    return pos_new, vel, momentum_transfer