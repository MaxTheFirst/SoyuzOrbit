# pygame_visualization.py
import pygame
import numpy as np

from simulation import (
    GRAVITATIONAL_CONSTANT as G,
    MASS_EARTH as ME, MASS_MOON as MM,
    RADIUS_EARTH, RADIUS_MOON, LEO_RADIUS,
    DISTANCE_EARTH_MOON, calculate_moon_position
)

INITIAL_WIDTH = 1200
INITIAL_HEIGHT = 800
WINDOW_TITLE = "Интерактивная симуляция полета на Луну"

# цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE  = (100, 149, 237)
GRAY  = (128, 128, 128)
GREEN = (0, 255, 0)
RED   = (255, 0, 0)
LEO_BLUE = (173, 216, 230)


def animate_trajectory(simulation_result, *, mass_series=None, mdry=None,
                       show_moon_orbit=True, moon_orbit_alt=100e3,
                       show_metrics=True, rocket_px=2,
                       thrust_accel_series=None):
    """
    Воспроизводит траекторию из solution-like объекта (solve_ivp-совместимый).
    Если передан thrust_accel_series (м/с^2) — выводит тяговое ускорение.
    mass_series — масса на кадры; mdry — сухая масса (для HUD).
    """
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # ---------- входные ряды ----------
    t = np.asarray(simulation_result.t, dtype=float)
    x = np.asarray(simulation_result.y[0], dtype=float)
    y = np.asarray(simulation_result.y[1], dtype=float)

    if simulation_result.y.shape[0] >= 4:
        vx = np.asarray(simulation_result.y[2], dtype=float)
        vy = np.asarray(simulation_result.y[3], dtype=float)
    else:
        vx = np.gradient(x, t, edge_order=2)
        vy = np.gradient(y, t, edge_order=2)

    speed = np.hypot(vx, vy)

    if mass_series is not None:
        m = np.asarray(mass_series, dtype=float)
    elif simulation_result.y.shape[0] >= 5:
        m = np.asarray(simulation_result.y[4], dtype=float)
    else:
        m = None

    a_thrust = np.asarray(thrust_accel_series, dtype=float) if thrust_accel_series is not None else None

    # ---------- предвычисление модуля гравитационного ускорения ----------
    # |a_g| = |a_E + a_M|, где a_E = -GM_E*r_E/|r_E|^3; a_M аналогично
    def grav_mag_at(i: int) -> float:
        xi, yi, ti = float(x[i]), float(y[i]), float(t[i])

        r2 = xi*xi + yi*yi
        r3 = r2 * np.sqrt(max(r2, 1e-30))
        axE = -G * ME * xi / (r3 + 1e-30)
        ayE = -G * ME * yi / (r3 + 1e-30)

        mx, my = calculate_moon_position(ti)
        dx, dy = xi - mx, yi - my
        rm2 = dx*dx + dy*dy
        rm3 = rm2 * np.sqrt(max(rm2, 1e-30))
        axM = -G * MM * dx / (rm3 + 1e-30)
        ayM = -G * MM * dy / (rm3 + 1e-30)

        return float(np.hypot(axE + axM, ayE + ayM))

    g_mag = np.array([grav_mag_at(i) for i in range(len(t))], dtype=float)

    # ---------- камера / преобразования ----------
    def reset_view():
        nonlocal scale, ox, oy
        w, h = screen.get_size()
        scale = w / (DISTANCE_EARTH_MOON * 2.2)
        ox, oy = w / 2, h / 2

    def to_screen(px: float, py: float) -> tuple[int, int]:
        return int(ox + px * scale), int(oy - py * scale)

    scale = 1.0
    ox = oy = 0.0
    reset_view()

    # ---------- вспомогательная геометрия ----------
    def dashed_circle(surface, center_xy, radius_px, color, dashes=96):
        # рисуем пунктирную окружность по пиксельному радиусу
        import math
        pts = []
        for i in range(dashes + 1):
            ang = 2 * math.pi * i / dashes
            pts.append((
                int(center_xy[0] + radius_px * math.cos(ang)),
                int(center_xy[1] + radius_px * math.sin(ang))
            ))
        for i in range(dashes):
            if i % 2 == 0:
                pygame.draw.line(surface, color, pts[i], pts[i + 1], 1)

    # ---------- состояние проигрывателя ----------
    paused = False
    k = 0  # индекс текущей точки
    # стартовая скорость — медленная
    step = max(1, len(t) // 2000)   # чем больше массив, тем крупнее шаг
    step_min, step_max = 1, max(1, len(t) // 40)

    panning = False
    pan_start = (0, 0)

    running = True
    while running:
        # ---- события ----
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(e.size, pygame.RESIZABLE)
                reset_view()

            elif e.type == pygame.MOUSEWHEEL:
                # приближение к курсору
                factor = 1.1 if e.y > 0 else 1 / 1.1
                mx, my = pygame.mouse.get_pos()
                wx = (mx - ox) / scale
                wy = (my - oy) / -scale
                scale *= factor
                ox = mx - wx * scale
                oy = my + wy * scale

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                panning = True
                pan_start = e.pos

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                panning = False

            elif e.type == pygame.MOUSEMOTION and panning:
                dx = e.pos[0] - pan_start[0]
                dy = e.pos[1] - pan_start[1]
                ox += dx
                oy += dy
                pan_start = e.pos

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_r:
                    reset_view()
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                # пошагово в паузе
                elif e.key in (pygame.K_RIGHT, pygame.K_PERIOD):
                    k = min(k + 1, len(t) - 1)
                elif e.key in (pygame.K_LEFT, pygame.K_COMMA):
                    k = max(k - 1, 0)
                # скорость
                elif e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_RIGHTBRACKET):
                    step = min(step * 2, step_max)
                elif e.key in (pygame.K_MINUS, pygame.K_LEFTBRACKET, pygame.K_UNDERSCORE):
                    step = max(step // 2, step_min)
                elif e.key == pygame.K_0:
                    step = step_min  # сброс скорости

        if not paused:
            k = min(k + step, len(t) - 1)

        i = int(k)
        ti = t[i]

        # ---- отрисовка ----
        screen.fill(BLACK)

        # орбита Луны (пунктир)
        pts = [to_screen(DISTANCE_EARTH_MOON*np.cos(a),
                         DISTANCE_EARTH_MOON*np.sin(a))
               for a in np.linspace(0, 2*np.pi, 200)]
        pygame.draw.lines(screen, (40, 40, 40), True, pts, 1)

        # НОО (тонкая)
        if LEO_RADIUS * scale > 1:
            leo_pts = [to_screen(LEO_RADIUS*np.cos(a), LEO_RADIUS*np.sin(a))
                       for a in np.linspace(0, 2*np.pi, 120)]
            pygame.draw.lines(screen, LEO_BLUE, True, leo_pts, 1)

        # Земля
        pygame.draw.circle(screen, BLUE, to_screen(0.0, 0.0), max(1, int(RADIUS_EARTH * scale)))

        # траектория (кусок до текущего кадра)
        if i > 0:
            tr = [to_screen(xj, yj) for xj, yj in zip(x[:i+1], y[:i+1])]
            pygame.draw.lines(screen, GREEN, False, tr, 2)

        # Луна и парковочная орбита
        mx, my = calculate_moon_position(ti)
        pygame.draw.circle(screen, GRAY, to_screen(mx, my), max(1, int(RADIUS_MOON * scale)))
        if show_moon_orbit:
            rpx = int((RADIUS_MOON + moon_orbit_alt) * scale)
            if rpx > 2:
                dashed_circle(screen, to_screen(mx, my), rpx, (160, 160, 160), 96)

        # ракета
        pygame.draw.circle(screen, RED, to_screen(x[i], y[i]), max(1, int(rocket_px)))

        # HUD
        info = [
            f"Время: {ti/86400:.2f} дней",
            f"Скорость: {speed[i]/1000:.2f} км/с",
            f"Грав. ускорение: {g_mag[i]:.3f} м/с²",
        ]
        if a_thrust is not None:
            info.append(f"Тяговое ускорение: {float(a_thrust[i]):.3f} м/с²")

        if m is not None:
            m_now = float(m[i])
            if mdry is not None:
                info.append(f"Масса: {m_now:,.0f} кг  (сухая: {float(mdry):,.0f} кг)")
            else:
                info.append(f"Масса: {m_now:,.0f} кг")

        info += [
            "УПРАВЛЕНИЕ:",
            "  Колесо мыши — масштаб (к курсору)",
            "  ЛКМ — перетаскивание",
            "  Пробел — пауза",
        ]

        for j, line in enumerate(info):
            screen.blit(font.render(line, True, WHITE), (10, 10 + 20 * j))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()