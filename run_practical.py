import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

from pygame_visualization import animate_trajectory
from practical_model import simulate_with_fuel, Propulsion, Guidance
from simulation import (
    LEO_RADIUS, LEO_VELOCITY, MAX_SIMULATION_TIME, RTOL, ATOL,
    calculate_trajectory_derivatives,
    event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes,
    RADIUS_EARTH, RADIUS_MOON, DISTANCE_EARTH_MOON, calculate_moon_position
)

# 1) ОПОРНАЯ (теоретическая) траектория после TLI
deg = np.deg2rad(-128.02)
tli_dv = 3142.82  # м/с

pos_x0 = LEO_RADIUS * np.cos(deg)
pos_y0 = LEO_RADIUS * np.sin(deg)
vel_x0 = -LEO_VELOCITY * np.sin(deg)
vel_y0 =  LEO_VELOCITY * np.cos(deg)

v0 = np.hypot(vel_x0, vel_y0)
dirx, diry = vel_x0 / v0, vel_y0 / v0
state0 = [pos_x0, pos_y0, vel_x0 + tli_dv * dirx, vel_y0 + tli_dv * diry]

ref_sol = solve_ivp(
    calculate_trajectory_derivatives,
    (0, MAX_SIMULATION_TIME),
    state0,
    t_eval=np.linspace(0, MAX_SIMULATION_TIME, 5000),
    method="LSODA", rtol=RTOL, atol=ATOL,
    dense_output=False,
    events=[event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes]
)

# 2) Практическая модель: взлёт→НОО (сброс 20 т)→перелёт→LOI→LPO→деорбит→мягкая посадка
prop = Propulsion(Isp=320.0, Tmax=6e5, m0=50000.0, mdry=10000.0, reserve_kg=1000.0)
guide = Guidance(use_moon_gravity=True)

prac_sol, summary = simulate_with_fuel(
    ref_sol,
    prop=prop,
    guide=guide,
    dv_init=tli_dv,
    # Взлёт и НОО
    add_ascent_to_leo=True,
    ascent_time_s=600.0,
    leo_angle=deg,
    drop_mass_at_leo_kg=20000.0,
    # Параметры «лунного блока»
    do_loi=True,           # делаем захват на круговую орбиту Луны
    lpo_alt_m=100e3,       # высота LPO
    coast_on_lpo_s=1800.0, # немного покружим на орбите (видно в анимации)
    do_deorbit=True,       # деорбит с LPO
    landing_start_alt=15e3,
    v_touchdown=1.0,
    consume_fuel=True      # тратим топливо на LOI, деорбит и посадку
)

print("\n=== Практическая модель — итог ===")
for k, v in summary.items():
    if isinstance(v, (int, float)):
        print(f"{k:>28}: {v:,.3f}")
    else:
        print(f"{k:>28}: {v}")

# 3) Статическая картинка-наложение
plt.figure(figsize=(12, 8))
ang = np.linspace(0, 2*np.pi, 200)
plt.plot(DISTANCE_EARTH_MOON*np.cos(ang)/1e6,
         DISTANCE_EARTH_MOON*np.sin(ang)/1e6, "--", color="gray", label="Орбита Луны")

earth = plt.Circle((0,0), RADIUS_EARTH/1e6, color="blue", alpha=0.7, label="Земля")
plt.gca().add_artist(earth)
mx, my = calculate_moon_position(prac_sol.t[-1])
moon = plt.Circle((mx/1e6, my/1e6), RADIUS_MOON/1e6, color="gray", alpha=0.7, label="Луна")
plt.gca().add_artist(moon)

plt.plot(ref_sol.y[0]/1e6, ref_sol.y[1]/1e6, color="green", label="Теоретическая")
plt.plot(prac_sol.y[0]/1e6, prac_sol.y[1]/1e6, color="orange", alpha=0.9, label="Практическая")

plt.axis("scaled"); plt.grid(True)
plt.xlabel("X (тыс. км)"); plt.ylabel("Y (тыс. км)")
plt.title("Практическая: взлёт → НОО (-20т) → перелёт → LPO → деорбит → мягкая посадка")
plt.legend()
plt.tight_layout()
plt.savefig("practical_vs_theoretical.png", dpi=300, bbox_inches="tight")
print("График сохранён: practical_vs_theoretical.png")
plt.show()

# 4) Анимация
print("\nЗапуск анимации...")
animate_trajectory(
    prac_sol,
    mass_series=prac_sol.y[4],
    mdry=prop.mdry,
    rocket_px=3,
    show_metrics=True,
    show_moon_orbit=True,
    moon_orbit_alt=100e3,
    thrust_accel_series=getattr(prac_sol, "thrust_accel", None)
)