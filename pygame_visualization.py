# pygame_visualization.py

import pygame
import sys
import numpy as np

from simulation import (
    RADIUS_EARTH, RADIUS_MOON, LEO_RADIUS,
    DISTANCE_EARTH_MOON, calculate_moon_position
)

# --- Настройки ---
INITIAL_WIDTH = 1200
INITIAL_HEIGHT = 800
WINDOW_TITLE = "Интерактивная симуляция полета на Луну"
# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE = (100, 149, 237)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
LEO_BLUE = (173, 216, 230)
g0 = 9.80665


def animate_trajectory(simulation_result, *, mass_series=None, mdry=None,
                       show_moon_orbit=True, moon_orbit_alt=100e3,
                       show_metrics=True, rocket_px=2,
                       isp_for_thrust=None):  # ← ДОБАВИЛИ
    pygame.init()

    def draw_dashed_circle(surface, center_xy, radius_px, color, dashes=96):
        import math
        pts = []
        for i in range(dashes + 1):
            ang = 2 * math.pi * i / dashes
            x = center_xy[0] + radius_px * math.cos(ang)
            y = center_xy[1] + radius_px * math.sin(ang)
            pts.append((int(x), int(y)))
        for i in range(dashes):
            if i % 2 == 0:
                pygame.draw.line(surface, color, pts[i], pts[i + 1], 1)

    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # --- Данные траектории ---
    timestamps = np.asarray(simulation_result.t)
    coords = np.array(simulation_result.y[:2].T)  # (N, 2)
    # скорости (из решения, если есть; иначе численно)
    if simulation_result.y.shape[0] >= 4:
        vx = np.asarray(simulation_result.y[2])
        vy = np.asarray(simulation_result.y[3])
    else:
        vx = np.gradient(coords[:, 0], timestamps, edge_order=2)
        vy = np.gradient(coords[:, 1], timestamps, edge_order=2)
    speed = np.hypot(vx, vy)
    ax = np.gradient(vx, timestamps, edge_order=2)
    ay = np.gradient(vy, timestamps, edge_order=2)
    accel = np.hypot(ax, ay)

    # массы (если передали отдельно — используем их)
    if mass_series is not None:
        masses = np.asarray(mass_series)
    elif simulation_result.y.shape[0] >= 5:
        masses = np.asarray(simulation_result.y[4])
    else:
        masses = None

    if masses is not None and isp_for_thrust is not None:
        mdot = -np.gradient(masses, timestamps, edge_order=2)  # кг/с (положит. при расходе)
        ve = float(isp_for_thrust) * g0
        a_thrust = np.clip(mdot, 0, None) * ve / np.maximum(masses, 1e-6)  # м/с², только расход
    else:
        a_thrust = None

    # --- Камера ---
    def reset_view():
        nonlocal scale, offset_x, offset_y
        w, h = screen.get_size()
        scale = w / (DISTANCE_EARTH_MOON * 2.2)
        offset_x = w / 2
        offset_y = h / 2

    scale = 1.0
    offset_x = offset_y = 0.0
    reset_view()
    panning = False
    pan_start = (0, 0)
    paused = False
    frame_idx = 0
    animation_speed = max(1, len(timestamps) // 500)

    def to_screen(p):
        return (int(offset_x + p[0] * scale), int(offset_y - p[1] * scale))

    # --- Главный цикл ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                reset_view()
            elif event.type == pygame.MOUSEWHEEL:
                factor = 1.1 if event.y > 0 else 1 / 1.1
                mx, my = pygame.mouse.get_pos()
                wx = (mx - offset_x) / scale
                wy = (my - offset_y) / -scale
                scale *= factor
                offset_x = mx - wx * scale
                offset_y = my + wy * scale
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                panning = True
                pan_start = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                panning = False
            elif event.type == pygame.MOUSEMOTION and panning:
                dx = event.pos[0] - pan_start[0]
                dy = event.pos[1] - pan_start[1]
                offset_x += dx
                offset_y += dy
                pan_start = event.pos
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    reset_view()
                elif event.key == pygame.K_SPACE:
                    paused = not paused

        if not paused:
            frame_idx = min(frame_idx + animation_speed, len(timestamps) - 1)
        i = int(frame_idx)
        t_now = timestamps[i]

        screen.fill(BLACK)

        # Орбита Луны вокруг Земли (большая пунктирная)
        pts = [to_screen(np.array([DISTANCE_EARTH_MOON * np.cos(a),
                                   DISTANCE_EARTH_MOON * np.sin(a)]))
               for a in np.linspace(0, 2 * np.pi, 200)]
        pygame.draw.lines(screen, (40, 40, 40), True, pts, 1)

        # Орбита НОО (тонкая)
        if LEO_RADIUS * scale > 1:
            leo_pts = [to_screen(np.array([LEO_RADIUS * np.cos(a),
                                           LEO_RADIUS * np.sin(a)]))
                       for a in np.linspace(0, 2 * np.pi, 100)]
            pygame.draw.lines(screen, LEO_BLUE, True, leo_pts, 1)

        # Земля
        pygame.draw.circle(screen, BLUE, to_screen((0, 0)), max(1, int(RADIUS_EARTH * scale)))

        # Траектория (кусок до текущего кадра)
        if i > 0:
            trk = [to_screen(p) for p in coords[:i+1]]
            pygame.draw.lines(screen, GREEN, False, trk, 2)

        # Луна и её парковочная орбита
        moon_xy = np.array(calculate_moon_position(t_now))
        moon_px = to_screen(moon_xy)
        pygame.draw.circle(screen, GRAY, moon_px, max(1, int(RADIUS_MOON * scale)))
        if show_moon_orbit:
            r_orb = int((RADIUS_MOON + moon_orbit_alt) * scale)
            if r_orb > 2:
                draw_dashed_circle(screen, moon_px, r_orb, (160, 160, 160), dashes=96)

        # Ракета — маленькая фиксированная точка
        pygame.draw.circle(screen, RED, to_screen(coords[i]), max(1, int(rocket_px)))

        # Оверлей: время, скорость, ускорение, масса
        info = [f"Время: {t_now / 86400:.2f} дней"]
        if show_metrics:
            info.append(f"Скорость: {speed[i] / 1000:.2f} км/с")
            info.append(f"Грав. ускорение: {accel[i]:.3f} м/с²")
            if a_thrust is not None:
                info.append(f"Тяговое ускорение: {a_thrust[i]:.3f} м/с²")



        if masses is not None:
            m_now = float(masses[i])
            if mdry is not None:
                fuel = max(m_now - float(mdry), 0.0)
                info.append(f"Масса: {m_now:,.0f} кг  (топливо: {fuel:,.0f} кг)")
            else:
                info.append(f"Масса: {m_now:,.0f} кг")
        info += ["УПРАВЛЕНИЕ:", "  Колесо мыши — масштаб",
                 "  ЛКМ — перетаскивание", "  Пробел — пауза"]
        if paused:
            info.append("[ПАУЗА]")

        for k, line in enumerate(info):
            screen.blit(font.render(line, True, WHITE), (10, 10 + 20 * k))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()