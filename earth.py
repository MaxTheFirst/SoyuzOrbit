import config
import pygame
import math

class Earth:
    def __init__(self):
        self.radius_px = int(config.R_EARTH * config.SCALE)
        # скорость вращения Земли (рад/с)
        self.omega = 2 * math.pi / (24 * 3600)   # полный оборот за 24 ч
        self.omega_sim = self.omega * config.XTIME
        self.angle = 0.0

    def update(self, dt):
        self.angle += self.omega_sim * dt

    def draw(self, surface):
        pygame.draw.circle(surface, (0, 200, 0), (config.CENTER_X, config.CENTER_Y), self.radius_px)

    def draw_radius(self, surface):
        # Конец радиуса по текущему углу
        x = config.CENTER_X + self.radius_px * math.cos(self.angle)
        y = config.CENTER_Y + self.radius_px * math.sin(self.angle)
        pygame.draw.line(surface, (255, 100, 100), (config.CENTER_X, config.CENTER_Y), (x, y), 3)