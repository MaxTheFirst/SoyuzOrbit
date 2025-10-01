# run_practical.py
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

from pygame_visualization import animate_trajectory
from practical_model import simulate_with_fuel, Propulsion, Guidance
from simulation import (
    LEO_RADIUS, LEO_VELOCITY, MAX_SIMULATION_TIME, RTOL, ATOL,
    calculate_trajectory_derivatives,
    event_rocket_hits_earth, event_rocket_hits_moon, event_rocket_escapes,
    event_reaches_lunar_parking_orbit,  # <-- новое
    LUNAR_PARKING_ALT,
    RADIUS_EARTH, RADIUS_MOON, DISTANCE_EARTH_MOON, calculate_moon_position
)



# 1) строим ОПОРНУЮ (теоретическую) траекторию под твои числа
deg = np.deg2rad(-128.02)
tli_dv = 3142.82  # м/с

pos_x0 = LEO_RADIUS * np.cos(deg)
pos_y0 = LEO_RADIUS * np.sin(deg)
vel_x0 = -LEO_VELOCITY * np.sin(deg)
vel_y0 =  LEO_VELOCITY * np.cos(deg)

v0 = np.hypot(vel_x0, vel_y0)
dirx, diry = vel_x0 / v0, vel_y0 / v0

state0 = [pos_x0, pos_y0, vel_x0 + tli_dv * dirx, vel_y0 + tli_dv * diry]

ref_sol_raw = solve_ivp(
    calculate_trajectory_derivatives,
    (0, MAX_SIMULATION_TIME),
    state0,
    t_eval=np.linspace(0, MAX_SIMULATION_TIME, 5000),
    method="LSODA", rtol=RTOL, atol=ATOL,
    dense_output=True,  # <-- ВАЖНО: чтобы можно было взять состояние в момент события
    events=[event_rocket_hits_earth,
            event_reaches_lunar_parking_orbit,  # <-- касание орбиты Луны
            event_rocket_hits_moon,
            event_rocket_escapes]
)

# ВСТАВИМ ТОЧКУ СОБЫТИЯ (чтобы последняя точка была ровно на орбите)
from types import SimpleNamespace
if ref_sol_raw.t_events[1].size:                 # индекс 1 -> наш event в списке выше
    te = float(ref_sol_raw.t_events[1][0])       # время касания орбиты
    ye = ref_sol_raw.sol(te)                     # состояние в точке события
    mask = ref_sol_raw.t < te - 1e-12            # всё строго до события
    ref_sol = SimpleNamespace(
        t = np.append(ref_sol_raw.t[mask], te),
        y = np.hstack([ref_sol_raw.y[:, mask], ye.reshape(-1, 1)]),
        t_events = ref_sol_raw.t_events,
        success = ref_sol_raw.success
    )
else:
    ref_sol = ref_sol_raw

# 2) запускаем ПРАКТИЧЕСКУЮ модель (минимум физики: Земля + топливо)
prop = Propulsion(Isp=320.0, Tmax=6e5, m0=30000.0, mdry=10000.0)
guide = Guidance(use_moon_gravity=True)  # можно True, если захочешь

prac_sol, summary = simulate_with_fuel(
    ref_sol,
    prop=prop,
    guide=guide,
    dv_init=tli_dv,            # ← столько хотим отдать в TLI
    start_from_preburn=True    # ← начинаем с «добурновой» скорости
)

print("\n=== Практическая модель — итог ===")
for k, v in summary.items():
    if "kg" in k:
        print(f"{k:>24}: {v:,.2f}")
    elif "m_s" in k:
        print(f"{k:>24}: {v:,.2f}")
    else:
        print(f"{k:>24}: {v:,.3f}")

# >>> НОВОЕ: консольная «лента» массы по времени (10 равномерных точек)
print("\nМасса по времени:")
check_idx = np.linspace(0, prac_sol.t.size - 1, 10, dtype=int)
for idx in check_idx:
    t_days = prac_sol.t[idx] / 86400.0
    m_val = prac_sol.y[4, idx]
    print(f"  t = {t_days:6.2f} д  |  m = {m_val:,.1f} кг")

# 3) картинка наложения
plt.figure(figsize=(12, 8))

# орбита Луны
ang = np.linspace(0, 2*np.pi, 200)
plt.plot(DISTANCE_EARTH_MOON*np.cos(ang)/1e6,
         DISTANCE_EARTH_MOON*np.sin(ang)/1e6, "--", color="gray", label="Орбита Луны")

# Земля/Луна (в момент конца полёта)
earth = plt.Circle((0,0), RADIUS_EARTH/1e6, color="blue", alpha=0.7, label="Земля")
plt.gca().add_artist(earth)
mx, my = calculate_moon_position(ref_sol.t[-1])
moon = plt.Circle((mx/1e6, my/1e6), RADIUS_MOON/1e6, color="gray", alpha=0.7, label="Луна")
plt.gca().add_artist(moon)

# >>> НОВОЕ: орбита вокруг Луны (например, 100 км высоты)
LPO_ALT = 100e3  # высота низкой орбиты вокруг Луны
theta = np.linspace(0, 2*np.pi, 360)
lpo_r = RADIUS_MOON + LPO_ALT
lpo_x = mx + lpo_r * np.cos(theta)
lpo_y = my + lpo_r * np.sin(theta)
plt.plot(lpo_x/1e6, lpo_y/1e6, linestyle="--", color="gray", alpha=0.8,
         label=f"Орбита вокруг Луны ({int(LPO_ALT/1e3)} км)")

# траектории
plt.plot(ref_sol.y[0]/1e6, ref_sol.y[1]/1e6, color="green", label="Теоретическая")
plt.plot(prac_sol.y[0]/1e6, prac_sol.y[1]/1e6, color="orange", alpha=0.9, label="Практическая (с топливом)")

plt.axis("scaled"); plt.grid(True)
plt.xlabel("X (тыс. км)"); plt.ylabel("Y (тыс. км)")
plt.title("Следование практической модели за теоретической траекторией")
plt.legend()
plt.tight_layout()
plt.savefig("practical_vs_theoretical.png", dpi=300, bbox_inches="tight")
print("График сохранён: practical_vs_theoretical.png")
plt.show()

# >>> НОВОЕ: анимация с массой на экране
print("\nЗапуск анимации...")
animate_trajectory(
    prac_sol,
    mass_series=prac_sol.y[4],
    mdry=prop.mdry,
    rocket_px=3,
    show_metrics=True,
    show_moon_orbit=True,
    moon_orbit_alt=100e3,
    isp_for_thrust=prop.Isp,   # ← НОВОЕ: чтобы посчитать a_thrust
)