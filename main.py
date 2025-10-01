import math
import sys
import numpy as np
from dataclasses import dataclass
from typing import Callable
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve

# pygame
import pygame

@dataclass
class Data:
    mu : float = 4890.0e9
    Rm : float = 0.5*3476e3
    m : float = 1500.0
    F : Callable[[float], float] = lambda t: 0.0
    Fmax : float = 10e3
    Isp : float = 3500.0

p = Data()

def dqdt(t, q, p):
    r  = q[0:3]
    v  = q[3:6]
    mf = q[6]
    vnorm = np.linalg.norm(v)
    if vnorm == 0:
        ev = np.array([0.0,0.0,0.0])
    else:
        ev = v / vnorm
    mass = p.m - mf
    a = - p.mu * r / (np.linalg.norm(r)**3) - ev * p.F(t) / mass
    dm = abs(p.F(t)) / p.Isp
    return np.hstack([v, a, dm])

def event_hv(t, q, p, vk):
    r = np.linalg.norm(q[0:3])
    er = q[0:3] / r
    vr = np.dot(q[3:6], er)
    return vr - vk

def get_he_v_eq_0(h1, p, v2):
    R0  = p.Rm + h1
    V0  = math.sqrt(p.mu / R0)
    q0  = np.array([R0, 0.0, 0.0,   0.0, V0, 0.0,  0.0])
    ev = lambda t,q: event_hv(t,q,p,v2)
    ev.terminal = True
    ev.direction = 1
    sol = solve_ivp(lambda t,q: dqdt(t,q,p), [0,500], q0, method='RK45', events=[ev], rtol=1e-8)
    if sol.y.shape[1] == 0:
        return -1.0
    he = np.sqrt(np.sum(sol.y[0:3]**2, axis=0)) - p.Rm
    return he[-1]

# посадочные параметры
h2_target = 100.0
v2_target = -1.0
p.F = lambda t: p.Fmax

try:
    h1_guess = 10000.0
    h1 = float(fsolve(lambda x: get_he_v_eq_0(x[0], p, v2_target) - h2_target, [h1_guess])[0])
except Exception as e:
    h1 = 10000.0

R0  = p.Rm + h1
V0  = math.sqrt(p.mu / R0)
q0  = np.array([R0, 0.0, 0.0,   0.0, V0, 0.0,  0.0])
ev = lambda t,q: event_hv(t,q,p,v2_target)
ev.direction = 1
ev.terminal = True
sol = solve_ivp(lambda t,q: dqdt(t,q,p), [0,500], q0, method='RK45', events=[ev], rtol=1e-8)

r_vec = np.sqrt(np.sum(sol.y[0:3]**2, 0))
height = r_vec - p.Rm
h2 = height[-1]

b = abs(p.Fmax) / p.Isp
g = p.mu / p.Rm**2
m2 = p.m - sol.y[6][-1]
Ve = 0.0

f1 = lambda tp,ta: v2_target - g*(ta+tp) - p.Isp*np.log((m2 - b*ta)/m2) - Ve
f2 = lambda tp,ta: h2 + v2_target*(ta+tp) - g/2*(ta+tp)**2 - (p.Isp*((ta - m2/b)*(np.log(1 - b/m2*ta) - 1) - m2/b))
f = lambda x: (f1(x[0], x[1]), f2(x[0], x[1]))

try:
    t23e = fsolve(lambda x: f(x), [5.0, 2.0])
    tp = float(t23e[0])
    ta = float(t23e[1])
except Exception:
    tp = 9.7
    ta = 1.8

t0 = sol.t[-1]
q0 = sol.y[:, -1]
te = tp + ta
p.F = lambda t: (t > t0 + tp) * p.Fmax
sol2 = solve_ivp(lambda t,q: dqdt(t,q,p), [t0, t0+te], q0, method='BDF', rtol=1e-8)

t1 = sol.t
t2 = sol2.t
pos1 = sol.y[0:3, :].T
pos2 = sol2.y[0:3, :].T
vel1 = sol.y[3:6, :].T
vel2 = sol2.y[3:6, :].T

times = np.concatenate([t1, t2])
positions = np.vstack([pos1, pos2])
velocities = np.vstack([vel1, vel2])

r_all = np.linalg.norm(positions, axis=1)
heights = r_all - p.Rm
er_all = positions / r_all.reshape(-1,1)
vr_all = np.sum(er_all * velocities, axis=1)

# -----------------------------
# Визуализация в pygame
# -----------------------------

WIDTH, HEIGHT = 1000, 700
CENTER = np.array([WIDTH//2, HEIGHT//2])

moon_px = 200.0
scale = moon_px / p.Rm
orbit_radius = np.max(r_all) * scale
if orbit_radius > min(WIDTH, HEIGHT) * 0.45:
    scale = (min(WIDTH, HEIGHT) * 0.45) / np.max(r_all)
    moon_px = p.Rm * scale

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Посадка на Луну — моделирование')
clock = pygame.time.Clock()
font = pygame.font.SysFont('arial', 16)

orbit_display_radius = int((p.Rm + h1) * scale)

paused = False
running = True
idx = 0
n = len(times)

# коэффициент замедления (чем больше, тем медленнее)
time_scale = 0.02

fps = 60
frames_per_step = max(1, int(1 / time_scale))
frame_counter = 0

def draw_dashed_circle(surface, color, center, radius, dash_len=6, gap=6, width=1):
    circumference = 2 * math.pi * radius
    num_dashes = max(12, int(circumference / (dash_len + gap)))
    for i in range(num_dashes):
        theta1 = (i / num_dashes) * 2 * math.pi
        theta2 = ((i + 0.5) / num_dashes) * 2 * math.pi
        x1 = center[0] + radius * math.cos(theta1)
        y1 = center[1] + radius * math.sin(theta1)
        x2 = center[0] + radius * math.cos(theta2)
        y2 = center[1] + radius * math.sin(theta2)
        pygame.draw.line(surface, color, (x1,y1), (x2,y2), width)

def rocket_polygon(pos_px, vel_vec):
    l = 18
    w = 10
    points = np.array([[l,0], [-l/2, w/2], [-l/2, -w/2]])
    ang = math.atan2(vel_vec[1], vel_vec[0])
    c = math.cos(ang)
    s = math.sin(ang)
    R = np.array([[c, -s],[s, c]])
    pts = (points @ R.T) + pos_px
    return pts.tolist()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_ESCAPE:
                running = False

    if not paused:
        frame_counter += 1
        if frame_counter >= frames_per_step:
            frame_counter = 0
            idx = min(n-1, idx + 1)

    screen.fill((10,10,30))

    moon_radius_px = int(p.Rm * scale)
    pygame.draw.circle(screen, (230,230,230), CENTER, moon_radius_px)

    draw_dashed_circle(screen, (180,180,180), CENTER, orbit_display_radius, dash_len=8, gap=6, width=2)

    pos = positions[idx]
    vel = velocities[idx]
    x_px = CENTER[0] + pos[0] * scale
    y_px = CENTER[1] - pos[1] * scale
    vel_px = np.array([vel[0]*scale, -vel[1]*scale])

    tri = rocket_polygon(np.array([x_px,y_px]), vel_px)
    pygame.draw.polygon(screen, (220,50,50), tri)
    pygame.draw.polygon(screen, (0,0,0), tri, 1)

    h_now = heights[idx]
    vr_now = vr_all[idx]
    lines = [f't = {times[idx]:.1f} s', f'Высота = {h_now:.1f} m', f'Вертикальная скорость = {vr_now:.2f} m/s', f'h1 = {h1:.1f} m']
    for i, line in enumerate(lines):
        txt = font.render(line, True, (240,240,240))
        screen.blit(txt, (10, 10 + i*20))

    help_txt = font.render('Space — пауза/продолжить    Esc — выход', True, (200,200,200))
    screen.blit(help_txt, (10, HEIGHT-30))

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
sys.exit()
