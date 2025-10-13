# main.py (исправлённый)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
from config import *   # предполагается, что константы в config.py

class Spring:
    def __init__(self, k, L0):
        self.k = float(k)
        self.L0 = float(L0)

class ChainSystem:
    """
    Исправленный ChainSystem.
    Нахождение равновесия решает трёхдиагональную систему, выведенную из балансa сил.
    """
    def __init__(self, n_blocks=N_BLOCKS, random_seed=RANDOM_SEED):
        if random_seed is not None:
            np.random.seed(random_seed)
        self.N = int(n_blocks)
        # параметры
        self.masses = np.random.uniform(*MASS_RANGE, size=self.N)
        ks = np.random.uniform(*STIFFNESS_RANGE, size=self.N + 1)
        L0s = np.random.uniform(*LENGTH_RANGE, size=self.N + 1)
        self.springs = [Spring(k=ks[i], L0=L0s[i]) for i in range(self.N+1)]
        self.k_arr = np.array([s.k for s in self.springs])
        self.L0_arr = np.array([s.L0 for s in self.springs])
        # стены
        self.x_left = LEFT_WALL_X
        self.x_right = RIGHT_WALL_X
        # состояние
        self.x = np.zeros(self.N, dtype=float)
        self.v = np.zeros(self.N, dtype=float)
        self.damping = DAMPING if np.isscalar(DAMPING) else np.array(DAMPING)
        # equilibrium
        self.eq_positions = self.compute_equilibrium_positions()
        # инициализация в равновесии
        self.x[:] = self.eq_positions
        self.v[:] = 0.0

    def compute_equilibrium_positions(self):
        """Решаем (k_{i-1}+k_i) x_i - k_{i-1} x_{i-1} - k_i x_{i+1} = k_{i-1} L_{i-1} - k_i L_i
        с учётом известных x_0 = x_left и x_{N+1} = x_right.
        """
        N = self.N
        k = self.k_arr
        L0 = self.L0_arr

        # Матрица трёхдиагональная: diag a_i = k_{i-1} + k_i
        a = np.zeros(N, dtype=float)      # main diagonal
        lower = np.zeros(N-1, dtype=float)  # subdiag (-k_{i-1})
        upper = np.zeros(N-1, dtype=float)  # superdiag (-k_i)

        for i in range(N):
            a[i] = k[i] + k[i+1]
            if i < N-1:
                upper[i] = -k[i+1]
                lower[i] = -k[i+1]  # note: symmetric positions in our Thomas representation later

        # правая часть
        b = np.zeros(N, dtype=float)
        for i in range(1, N+1):  # i from 1..N in math notation
            idx = i-1
            term = k[i-1] * L0[i-1] - k[i] * L0[i]
            b[idx] = term
            if i == 1:
                # включает вклад левой стены: move -(-k_{0} x_0) -> + k0 * x_left
                b[idx] += k[0] * self.x_left
            if i == N:
                # включает вклад правой стены: move -(-k_N x_{N+1}) -> + kN * x_right
                b[idx] += k[N] * self.x_right

        # Решаем трёхдиагонную систему "A x = b", где A_ii = a[i], A_i,i+1 = -k[i+1], A_i,i-1 = -k[i]
        # Используем Thomas (но нужно явно подать subdiag = -k[1..N-1], superdiag = -k[2..N])
        # For clarity build sub, main, super as in standard algorithm:
        sub = np.zeros(N-1, dtype=float)   # a_{i,i-1}
        main = a.copy()
        sup = np.zeros(N-1, dtype=float)   # a_{i,i+1}
        for i in range(N-1):
            sub[i] = -k[i+1]   # coefficient at x_{i}
            sup[i] = -k[i+1]   # coefficient at x_{i+2} (symmetric)
        # Thomas algorithm
        # forward
        c_prime = np.zeros(N-1, dtype=float)
        d_prime = np.zeros(N, dtype=float)
        c_prime[0] = sup[0] / main[0]
        d_prime[0] = b[0] / main[0]
        for i in range(1, N-1):
            denom = main[i] - sub[i-1] * c_prime[i-1]
            c_prime[i] = sup[i] / denom
            d_prime[i] = (b[i] - sub[i-1] * d_prime[i-1]) / denom
        # last d_prime
        if N >= 2:
            denom = main[N-1] - sub[N-2] * c_prime[N-2]
            d_prime[N-1] = (b[N-1] - sub[N-2] * d_prime[N-2]) / denom
        else:
            # single equation
            d_prime[0] = b[0] / main[0]

        # back substitution
        x = np.zeros(N, dtype=float)
        x[-1] = d_prime[-1]
        for i in range(N-2, -1, -1):
            x[i] = d_prime[i] - c_prime[i] * x[i+1]
        return x

    def compute_forces(self, x):
        """Силы от пружин на блоки (без демпфинга)."""
        N = self.N
        nodes = np.empty(N + 2, dtype=float)
        nodes[0] = self.x_left
        nodes[1:-1] = x
        nodes[-1] = self.x_right
        lengths = nodes[1:] - nodes[:-1]            # current lengths of springs 0..N
        ext = lengths - self.L0_arr
        f_spring = self.k_arr * ext                 # positive => spring pulls right on left node
        # Force on block i = -f from left spring + f from right spring
        F = -f_spring[:-1] + f_spring[1:]
        return F

    def settle(self, dt=1e-4, max_steps=200000, vel_tol=1e-6, acc_tol=1e-6):
        """Доводим систему до равновесия (демпфирование включено)."""
        # временно увеличим демпфинг, чтобы быстрее сходилось
        saved_damping = self.damping
        if np.isscalar(saved_damping):
            saved_damping = float(saved_damping)
            self.damping = max(saved_damping, np.mean(self.k_arr) * 1e-4)
        else:
            self.damping = np.maximum(self.damping, np.mean(self.k_arr) * 1e-4)

        x = self.x.copy()
        v = self.v.copy()
        m = self.masses
        a = (self.compute_forces(x) - self.damping * v) / m

        for step in range(max_steps):
            # velocity-Verlet step
            x_half = x + v * dt + 0.5 * a * dt * dt
            f = self.compute_forces(x_half) - self.damping * v
            a_new = f / m
            v = v + 0.5 * (a + a_new) * dt
            x = x_half
            a = a_new
            if np.max(np.abs(v)) < vel_tol and np.max(np.abs(a)) < acc_tol:
                break

        # restore damping
        self.damping = saved_damping
        self.x = x
        self.v = v
        # зафиксируем новое положение равновесия
        self.eq_positions = self.x.copy()
        return step, np.max(np.abs(v)), np.max(np.abs(a))

    def simulate(self, t_total=SIM_TIME, dt=DT,
             displaced_block=DISPLACED_BLOCK_INDEX,
             displacement=INITIAL_DISPLACEMENT):
        """Основная симуляция:
        1. Находим равновесие.
        2. Сдвигаем один блок.
        3. Отпускаем систему (v=0, без внешних сил).
        """
        # 1. точное равновесие (аналитическое)
        self.eq_positions = self.compute_equilibrium_positions()
        self.x = self.eq_positions.copy()
        self.v[:] = 0.0

        # 2. возмущаем
        self.x[displaced_block] += displacement

        # 3. считаем
        N = self.N
        m = self.masses
        damping = self.damping
        steps = int(np.ceil(t_total / dt))
        times = np.linspace(0.0, steps * dt, steps + 1)
        xs = np.zeros((steps + 1, N))
        vs = np.zeros((steps + 1, N))
        accs = np.zeros((steps + 1, N))

        # начальные значения
        a = (self.compute_forces(self.x) - damping * self.v) / m
        xs[0] = self.x.copy()
        vs[0] = self.v.copy()
        accs[0] = a.copy()

        for i in range(1, steps + 1):
            x_half = self.x + self.v * dt + 0.5 * a * dt * dt
            f = self.compute_forces(x_half) - damping * self.v
            a_new = f / m
            self.v += 0.5 * (a + a_new) * dt
            self.x = x_half
            a = a_new
            xs[i] = self.x.copy()
            vs[i] = self.v.copy()
            accs[i] = a.copy()

        return times, xs, vs, accs

    def save_positions_relative_eq(self, filename, times, xs):
        df = pd.DataFrame(xs - self.eq_positions[np.newaxis, :],
                          columns=[f"block_{i+1}" for i in range(self.N)])
        df.insert(0, "time", times)
        df.to_csv(filename, index=False)
        print(f"CSV saved: {filename}")
        return df

# ---------------- Демонстрация ----------------
if __name__ == "__main__":
    system = ChainSystem()
    times, xs, vs, accs = system.simulate(t_total=SIM_TIME, dt=DT, displaced_block=DISPLACED_BLOCK_INDEX,
                                          displacement=INITIAL_DISPLACEMENT)

    # графики: координата, скорость, ускорение для целевого блока
    idx = max(1, min(system.N, TARGET_BLOCK)) - 1
    plt.figure(figsize=(10, 8))

    plt.subplot(3, 1, 1)
    plt.plot(times, xs[:, idx] - system.eq_positions[idx])
    plt.title(f"Координата блока {idx+1} (относительно eq)")
    plt.ylabel("x - x_eq (m)")

    plt.subplot(3, 1, 2)
    plt.plot(times, vs[:, idx])
    plt.ylabel("Скорость (m/s)")

    plt.subplot(3, 1, 3)
    plt.plot(times, accs[:, idx])
    plt.ylabel("Ускорение (m/s^2)")
    plt.xlabel("Время (s)")

    plt.tight_layout()
    plt.show()

    # Сохранение CSV
    df = system.save_positions_relative_eq("positions_relative_eq.csv", times, xs)
