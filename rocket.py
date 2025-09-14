import math
import config
import pygame


import math
import config
import pygame


class Rocket:
    def __init__(self):
        # Начальная позиция (на поверхности Земли сверху)
        self.pos = [0.0, -(config.R_EARTH * config.SCALE)]
        # Начальная скорость с учётом вращения Земли
        self.vel = [config.VEL_X, 0.0]

        # Текущая ступень
        self.stage_index = 0
        # Общая масса ракеты (сухая + топливо всех ступеней)
        self.mass = sum(s["dry"] + s["fuel"] for s in config.stages)

        # Двигатель активен
        self.active = True

        # Скорость истечения (км/с)
        # ISP (с) * g0 (м/с²) / 1000 = км/с
        g0 = 9.81  # стандартное ускорение, м/с²
        self.ve = config.ISP * g0 / 1000.0

    def update(self, dt):
        # Радиус-вектор
        r = math.sqrt(self.pos[0]**2 + self.pos[1]**2) / config.SCALE

        # Если двигатели выключены → только гравитация
        if not self.active:
            grav_acc = config.G * config.M_EARTH / (r**2)
            nx = -self.pos[0] / (r * config.SCALE)
            ny = -self.pos[1] / (r * config.SCALE)

            self.vel[0] += grav_acc * nx * dt * config.XTIME
            self.vel[1] += grav_acc * ny * dt * config.XTIME
            self.pos[0] += self.vel[0] * dt * config.XTIME * config.SCALE
            self.pos[1] += self.vel[1] * dt * config.XTIME * config.SCALE
            return

        # Проверка достижения орбиты (и нужной скорости)
        if r >= (config.R_EARTH + config.ALTITUDE):
            v = math.sqrt(self.vel[0]**2 + self.vel[1]**2)
            v_orb = math.sqrt(config.G * config.M_EARTH / r)
            if v >= 0.95 * v_orb:
                self.active = False
                # выравниваем по круговой орбите
                rx, ry = self.pos
                mag_r = math.sqrt(rx**2 + ry**2)
                nx = rx / mag_r
                ny = ry / mag_r
                # тангенциальный вектор
                tx = -ny
                ty = nx
                self.vel[0] = v_orb * tx
                self.vel[1] = v_orb * ty
                return

        # Работа двигателя по уравнению Мещерского
        stage = config.stages[self.stage_index]
        if stage["fuel"] > 0:
            # Массовый расход (кг/с)
            mdot = 1000  
            # Сколько сожгли за шаг
            fuel_burn = mdot * dt * config.XTIME
            if fuel_burn > stage["fuel"]:
                fuel_burn = stage["fuel"]

            stage["fuel"] -= fuel_burn
            self.mass -= fuel_burn

            # Ускорение от тяги (км/с²)
            thrust_acc = self.ve * (fuel_burn / dt) / self.mass
        else:
            # Ступень отработала → сбрасываем сухую массу
            self.mass -= stage["dry"]
            self.stage_index += 1
            if self.stage_index >= len(config.stages):
                self.active = False
            return

        # Гравитация
        grav_acc = config.G * config.M_EARTH / (r**2)
        nx = -self.pos[0] / (r * config.SCALE)
        ny = -self.pos[1] / (r * config.SCALE)

        # Направление тяги (радиально наружу)
        tx = -nx
        ty = -ny

        # Суммарное ускорение
        ax = thrust_acc * tx + grav_acc * nx
        ay = thrust_acc * ty + grav_acc * ny

        # Обновление скорости и позиции
        self.vel[0] += ax * dt * config.XTIME
        self.vel[1] += ay * dt * config.XTIME
        self.pos[0] += self.vel[0] * dt * config.XTIME * config.SCALE
        self.pos[1] += self.vel[1] * dt * config.XTIME * config.SCALE

    def draw(self, surface):
        x = config.WIDTH // 2 + int(self.pos[0])
        y = config.HEIGHT // 2 + int(self.pos[1])
        pygame.draw.circle(surface, (255, 0, 0), (x, y), 5)
