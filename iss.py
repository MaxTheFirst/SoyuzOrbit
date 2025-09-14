import config
import pygame
import math

from orbit import Orbit


class ISS:
    def __init__(self, orbit: Orbit):
        self.orbit_radius_px = orbit.radius_px
        # угловая скорость (рад/с)
        self.omega = config.V_ORBIT / orbit.radius_px
        self.omega_sim = self.omega * config.XTIME
        self.angle = 0.0
        self.size = 8

    def update(self, dt):
        self.angle += self.omega_sim * dt

    def get_position(self):
        x = config.CENTER_X + self.orbit_radius_px * math.cos(self.angle)
        y = config.CENTER_Y + self.orbit_radius_px * math.sin(self.angle)
        return x, y

    def draw(self, surface):
        x, y = self.get_position()
        pygame.draw.line(surface, (255, 255, 255), (x-self.size, y-self.size), (x+self.size, y+self.size), 2)
        pygame.draw.line(surface, (255, 255, 255), (x-self.size, y+self.size), (x+self.size, y-self.size), 2)