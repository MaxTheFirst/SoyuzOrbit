import config
import pygame
import math

from orbit import Orbit

class ISS:
    def __init__(self, orbit: Orbit):
        self.orbit_radius_px = orbit.radius_px
        # радиус в км
        self.orbit_radius_km = self.orbit_radius_px / config.SCALE

        # гравитационный параметр (км^3/с^2)
        mu = config.G * config.M_EARTH  # убедись, что это км^3/с^2

        # угловая скорость круговой орбиты (рад/с)
        self.omega = math.sqrt(mu / (self.orbit_radius_km ** 3))

        self.angle = 0.0
        self.size = 8

    def update(self, dt):
        dt_eff = dt * config.XTIME
        self.angle = (self.angle + self.omega * dt_eff) % (2 * math.pi)

    def get_position(self):
        x = config.CENTER_X + self.orbit_radius_px * math.cos(self.angle)
        y = config.CENTER_Y + self.orbit_radius_px * math.sin(self.angle)
        return x, y

    def draw(self, surface):
        x, y = self.get_position()
        pygame.draw.line(surface, (255, 255, 255), (x-self.size, y-self.size), (x+self.size, y+self.size), 2)
        pygame.draw.line(surface, (255, 255, 255), (x-self.size, y+self.size), (x+self.size, y-self.size), 2)