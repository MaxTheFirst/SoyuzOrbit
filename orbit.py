import config
import pygame
import math


NUM_POINTS = 200


class Orbit:
    def __init__(self):
        self.radius_px = int((config.R_EARTH + config.ALTITUDE) * config.SCALE)

    def draw(self, surface):
        points = []
        for i in range(NUM_POINTS):
            a = 2 * math.pi * i / NUM_POINTS
            x = config.CENTER_X + self.radius_px * math.cos(a)
            y = config.CENTER_Y + self.radius_px * math.sin(a)
            points.append((x, y))
        # пунктир
        for i in range(0, len(points), 4):
            if i + 2 < len(points):
                pygame.draw.line(surface, (200, 200, 200), points[i], points[i+2], 1)