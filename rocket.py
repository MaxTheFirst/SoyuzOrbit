import math
import config
import pygame


class Rocket:
    def __init__(self, iss):
        self.iss = iss
        # Начальная позиция на поверхности Земли (снизу)
        self.pos = [0.0, -(config.R_EARTH * config.SCALE)]
        # Начальная скорость с учётом вращения Земли
        self.vel = [config.VEL_X, 0.0]

        # Текущая ступень
        self.stage_index = 0
        # Общая масса ракеты
        self.mass = sum(s["dry"] + s["fuel"] for s in config.stages)

        # Двигатель активен
        self.active = True

        # Скорость истечения
        g0 = 9.81
        self.ve = config.ISP * g0 / 1000.0

        # Состояние стыковки
        self.docked = False
        # Флаг выхода на орбиту
        self.on_orbit = False

    def update(self, dt):
        if self.docked:
            return

        # Расстояние от центра Земли в км
        r = math.sqrt(self.pos[0] ** 2 + self.pos[1] ** 2) / config.SCALE

        # Позиция МКС
        iss_x, iss_y = self.iss.get_position()
        iss_pos = [(iss_x - config.CENTER_X) / config.SCALE,
                   (iss_y - config.CENTER_Y) / config.SCALE]

        # Вектор к МКС
        dx = iss_pos[0] - self.pos[0] / config.SCALE
        dy = iss_pos[1] - self.pos[1] / config.SCALE
        distance_to_iss = math.sqrt(dx ** 2 + dy ** 2)

        # Стыковка
        if distance_to_iss < config.DOCKING_ERROR:  # 10 км допустимо
            r_iss = math.sqrt(iss_pos[0] ** 2 + iss_pos[1] ** 2)
            v_orb = math.sqrt(config.G * config.M_EARTH / r_iss)
            tx = -iss_pos[1] / r_iss
            ty = iss_pos[0] / r_iss
            self.vel[0] = v_orb * tx
            self.vel[1] = v_orb * ty
            self.docked = True
            self.active = False
            return

        # Радиальный и тангенциальный векторы
        rx, ry = self.pos
        mag_r = math.sqrt(rx ** 2 + ry ** 2)
        nx = rx / mag_r
        ny = ry / mag_r
        tx = -ny
        ty = nx

        # Работа двигателя
        thrust_acc = 0
        if self.active and self.stage_index < len(config.stages):
            stage = config.stages[self.stage_index]
            if stage["fuel"] > 0:
                fuel_burn = stage["mdot"] * dt * config.XTIME
                if fuel_burn > stage["fuel"]:
                    fuel_burn = stage["fuel"]
                stage["fuel"] -= fuel_burn
                self.mass -= fuel_burn
                thrust_acc = self.ve * (fuel_burn / dt) / self.mass
            else:
                self.mass -= stage["dry"]
                self.stage_index += 1
                if self.stage_index >= len(config.stages):
                    self.active = False

        # Гравитация
        grav_acc = config.G * config.M_EARTH / (r ** 2)

        # Определяем направление тяги
        if not self.on_orbit:
            # Пока не на орбите: двигаться вверх, радиально наружу
            thrust_dir_x, thrust_dir_y = nx, ny
        else:
            # На орбите: небольшая корректировка для догонки МКС
            # вектор от ракеты к МКС по касательной
            v_rel_x = dx - (self.vel[0] / config.SCALE)
            v_rel_y = dy - (self.vel[1] / config.SCALE)
            norm = math.sqrt(v_rel_x ** 2 + v_rel_y ** 2)
            if norm != 0:
                thrust_dir_x = v_rel_x / norm
                thrust_dir_y = v_rel_y / norm
            else:
                thrust_dir_x, thrust_dir_y = 0, 0

        # Суммарное ускорение
        ax = thrust_acc * thrust_dir_x - grav_acc * nx
        ay = thrust_acc * thrust_dir_y - grav_acc * ny

        # Обновление скорости и позиции
        self.vel[0] += ax * dt * config.XTIME
        self.vel[1] += ay * dt * config.XTIME
        self.pos[0] += self.vel[0] * dt * config.XTIME * config.SCALE
        self.pos[1] += self.vel[1] * dt * config.XTIME * config.SCALE

        # Достижение орбитальной высоты
        if r >= (config.R_EARTH + config.ALTITUDE) and not self.on_orbit:
            v_orb = math.sqrt(config.G * config.M_EARTH / r)
            self.vel[0] = v_orb * tx
            self.vel[1] = v_orb * ty
            self.active = False
            self.on_orbit = True

    def draw(self, surface):
        x = config.WIDTH // 2 + int(self.pos[0])
        y = config.HEIGHT // 2 + int(self.pos[1])
        pygame.draw.circle(surface, (255, 0, 0), (x, y), 5)

    def draw_info(self, surface):
        font = pygame.font.Font(None, 24)  # Создаем шрифт (размер 24)
        
        # Расчёт скорости и высоты
        speed = math.sqrt(self.vel[0] ** 2 + self.vel[1] ** 2) * config.SCALE
        r = math.sqrt(self.pos[0] ** 2 + self.pos[1] ** 2)
        altitude = r - config.R_EARTH * config.SCALE
        
        # Создаем строки для отображения
        info_lines = [
            f"Speed: {speed:.2f} m/s",
            f"Stage: {self.stage_index + 1}/{len(config.stages)}",
            f"Altitude: {altitude / config.SCALE:.2f} km"
        ]
        
        # Выводим строки в правом верхнем углу
        for i, line in enumerate(info_lines):
            text_surf = font.render(line, True, (255, 255, 255))
            surface.blit(text_surf, (config.WIDTH - 200, 10 + i * 20))