from dataclasses import dataclass
import numpy as np

g_start = 9.80665 # м / с^2
G = 6.67430e-11 # м^3 / (кг * c^2)
little_eps = 1e-12 # м

@dataclass(slots=True)
class Planets:
    mu_: float = 3.986004418e14 # в м^3 / c^2  = M * G (Вроде это вычисляется более точно, чем просто M и G)
    r_: float = 6371e3 # в м
    w_: float = 7.292115e-5 # рад / с = 2 * pi / T (T - период вращения Земли вокруг своей оси)

    def set_mu(self, mu: float) -> None:
        self.mu_: float = mu

    def set_r(self, r: float) -> None:
        self.r_: float = r

    def set_w(self, w: float) -> None:
        self.w_: float = w

    def set_mass(self, mass: float) -> None:
        self.mu_: float = mass * G

    def get_mu(self) -> float:
        return self.mu_

    def get_r(self) -> float:
        return self.r_

    def get_w(self) -> float:
        return self.w_

    def gravity_accel(self, r: np.ndarray) -> np.ndarray: # Позиция точки относительно центра планеты
        r_norm = np.linalg.norm(r)
        return -self.mu * r / (r_norm**3 + little_eps)

    @property
    def mass(self) -> float:
        return self.mu_ / G

    def height(self, r: float) -> float:
        return r - self.r_

@dataclass(slots=True)
class Atmosphere:
    density_default_ : float = 1.225 # кг / м^3
    height_of_fall_ : float = 8500 # м

    def set_density_default(self, density_default: float) -> None:
        self.density_default_: float = density_default

    def set_height_of_fall(self, height_of_fall: float) -> None:
        self.height_of_fall_: float = height_of_fall

    def get_density_default(self) -> float:
        return self.density_default_

    def get_height_of_fall(self) -> float:
        return self.height_of_fall_

    def density(self, h : float) -> float: # плотность на высоте h
        return self.density_default_ * np.exp(-max(h, 0.0) / self.height_of_fall_)

