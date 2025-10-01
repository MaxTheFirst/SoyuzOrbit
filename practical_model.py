# practical_model.py
import numpy as np
from dataclasses import dataclass
from types import SimpleNamespace
from scipy.integrate import solve_ivp

from simulation import (
    GRAVITATIONAL_CONSTANT as G,
    MASS_EARTH as ME,
    MASS_MOON as MM,
    RADIUS_EARTH, RADIUS_MOON,
    LEO_RADIUS, LEO_VELOCITY,
    DISTANCE_EARTH_MOON as RM,
    ANGULAR_VELOCITY_MOON as OM,
    calculate_moon_position,
    calculate_trajectory_derivatives as rhs_grav,  # та же RHS, что у опорной
)

g0 = 9.80665
MU_M = G * MM

# ---------------- гравитация ----------------
def _a_earth(x, y):
    r2 = x*x + y*y
    if r2 == 0.0:
        return 0.0, 0.0
    inv = 1.0 / (r2 * np.sqrt(r2))
    f = -G * ME * inv
    return f * x, f * y

def _a_moon(x, y, t):
    mx, my = calculate_moon_position(t)
    dx, dy = x - mx, y - my
    r2 = dx*dx + dy*dy
    if r2 == 0.0:
        return 0.0, 0.0
    inv = 1.0 / (r2 * np.sqrt(r2))
    f = -MU_M * inv
    return f * dx, f * dy

def _moon_vel(t):
    ang = OM * t
    return (-RM * OM * np.sin(ang), RM * OM * np.cos(ang))

# ---------------- параметры ----------------
@dataclass
class Guidance:
    use_moon_gravity: bool = True

@dataclass
class Propulsion:
    Isp: float = 320.0
    Tmax: float = 6e5
    m0: float = 50000.0
    mdry: float = 10000.0
    reserve_kg: float = 1000.0

# ---------------- посадка (с расходом топлива) ----------------
def _landing_rhs_fuel(t, s, prop: Propulsion, v_target: float):
    # s = [x, y, vx, vy, m]
    x, y, vx, vy, m = s
    axE, ayE = _a_earth(x, y)
    axM, ayM = _a_moon(x, y, t)
    ax_g, ay_g = axE + axM, ayE + ayM

    vmx, vmy = _moon_vel(t)
    vrx, vry = vx - vmx, vy - vmy
    vrel = np.hypot(vrx, vry)

    mx, my = calculate_moon_position(t)
    h = np.hypot(x - mx, y - my) - RADIUS_MOON

    a_max = prop.Tmax / max(m, 1.0)
    need_burn = (h > 0.0) and (vrel*vrel >= 2.0 * a_max * max(h, 1.0) + v_target*v_target)

    if need_burn and m > (prop.mdry + prop.reserve_kg):
        ux, uy = (-vrx / (vrel + 1e-12), -vry / (vrel + 1e-12))
        a_tx, a_ty = a_max * ux, a_max * uy
        mdot = -prop.Tmax / (prop.Isp * g0)
        # не уходим ниже сухой+резерв
        if m + mdot < prop.mdry + prop.reserve_kg:
            mdot = (prop.mdry + prop.reserve_kg - m)  # «догораем» ровно до порога за этот шаг
    else:
        a_tx = a_ty = 0.0
        mdot = 0.0

    return [vx, vy, ax_g + a_tx, ay_g + a_ty, mdot]

def _event_touchdown(t, s):
    x, y = s[0], s[1]
    mx, my = calculate_moon_position(t)
    return np.hypot(x - mx, y - my) - RADIUS_MOON
_event_touchdown.terminal = True
_event_touchdown.direction = -1

def _event_reach_start_alt(alt_target):
    def f(t, s):
        x, y = s[0], s[1]
        mx, my = calculate_moon_position(t)
        return np.hypot(x - mx, y - my) - (RADIUS_MOON + alt_target)
    f.terminal = True
    f.direction = -1
    return f

# ---------------- импульсы ----------------
def _rocket_eq_mass_after_dv(m_before, dv, Isp, mdry_min):
    ve = Isp * g0
    dv = max(0.0, float(dv))
    m_after = m_before * np.exp(-dv / ve)
    if m_after < mdry_min:
        dv_possible = ve * np.log(m_before / mdry_min)
        m_after = mdry_min
        return m_after, dv_possible, True
    return m_after, dv, False

def _circularize_impulse(x, y, vx, vy, t, r_circ):
    """Импульс, который делает орбиту вокруг Луны круговой радиуса r_circ."""
    mx, my = calculate_moon_position(t)
    vmx, vmy = _moon_vel(t)
    dx, dy = x - mx, y - my
    r = np.hypot(dx, dy)
    erx, ery = dx / r, dy / r
    etx, ety = -ery, erx  # тангенс (левый поворот)

    vx_rel, vy_rel = vx - vmx, vy - vmy
    vr = vx_rel * erx + vy_rel * ery
    vt = vx_rel * etx + vy_rel * ety

    v_circ = np.sqrt(MU_M / r_circ)

    dv_r = -vr
    dv_t = (v_circ - vt)
    dvx = dv_r * erx + dv_t * etx
    dvy = dv_r * ery + dv_t * ety
    dv_mag = np.hypot(dvx, dvy)

    return dv_mag, vx + dvx, vy + dvy

def _deorbit_impulse_for_rp(r_a, r_p):
    """Δv ретроград в апоцентре, чтобы получить эллипс с перицентром r_p."""
    v_circ = np.sqrt(MU_M / r_a)
    v_apo  = np.sqrt(MU_M * (2.0 / r_a - 1.0 / ((r_a + r_p) / 2.0)))
    return max(0.0, v_circ - v_apo)

# ---------------- главная функция ----------------
def simulate_with_fuel(reference_solution,
                       prop: Propulsion = Propulsion(),
                       guide: Guidance = Guidance(),
                       dv_init: float | None = None,
                       # взлёт и НОО
                       add_ascent_to_leo: bool = True,
                       ascent_time_s: float = 600.0,
                       leo_angle: float | None = None,
                       drop_mass_at_leo_kg: float = 20000.0,
                       # Луна: LPO и посадка
                       do_loi: bool = True,
                       lpo_alt_m: float = 100e3,
                       coast_on_lpo_s: float = 120.0,
                       do_deorbit: bool = True,
                       landing_start_alt: float = 15e3,
                       v_touchdown: float = 1.0,
                       consume_fuel: bool = True):

    # опорная (гравитационная) траектория
    t_ref = reference_solution.t.copy()
    x_ref = reference_solution.y[0].copy()
    y_ref = reference_solution.y[1].copy()
    vx_ref = reference_solution.y[2].copy()
    vy_ref = reference_solution.y[3].copy()

    # аккумуляторы выходной траектории
    t_all, x_all, y_all, vx_all, vy_all, m_all = [], [], [], [], [], []
    thrust_accel = []

    m = prop.m0
    m_min = prop.mdry + prop.reserve_kg

    # -------- 0) взлёт до НОО (анимационный) --------
    time_offset = 0.0
    if add_ascent_to_leo and leo_angle is not None and ascent_time_s > 0.0:
        n = 200
        t_asc = np.linspace(0.0, ascent_time_s, n)
        u = t_asc / ascent_time_s
        s = 3*u*u - 2*u*u*u  # smoothstep
        r = RADIUS_EARTH + (LEO_RADIUS - RADIUS_EARTH) * s
        c, sng = np.cos(leo_angle), np.sin(leo_angle)

        x_asc = r * c
        y_asc = r * sng
        vx_leo, vy_leo = -LEO_VELOCITY * sng, LEO_VELOCITY * c
        vx_asc, vy_asc = vx_leo * s, vy_leo * s

        t_all += list(t_asc)
        x_all += list(x_asc);  y_all += list(y_asc)
        vx_all += list(vx_asc); vy_all += list(vy_asc)
        m_all  += [m] * n
        thrust_accel += [0.0] * n

        # сброс массы на НОО
        m = max(m_min, m - drop_mass_at_leo_kg)

        time_offset = t_all[-1]  # дальнейшие времена = t_ref + этот сдвиг

    # -------- 1) долёт до окружности LPO --------
    r_lpo = RADIUS_MOON + lpo_alt_m
    mx_ref, my_ref = calculate_moon_position(t_ref)
    r_to_moon = np.hypot(x_ref - mx_ref, y_ref - my_ref)

    idx_loi = None
    for i in range(len(t_ref) - 1):
        if r_to_moon[i] > r_lpo and r_to_moon[i+1] <= r_lpo:
            idx_loi = i + 1
            break
    if idx_loi is None:
        idx_loi = int(np.argmin(r_to_moon))

    t_pre  = t_ref[:idx_loi+1]
    x_pre  = x_ref[:idx_loi+1]
    y_pre  = y_ref[:idx_loi+1]
    vx_pre = vx_ref[:idx_loi+1]
    vy_pre = vy_ref[:idx_loi+1]

    t_all  += list(t_pre + time_offset)
    x_all  += list(x_pre);  y_all  += list(y_pre)
    vx_all += list(vx_pre); vy_all += list(vy_pre)
    m_all  += [m] * len(t_pre)
    thrust_accel += [0.0] * len(t_pre)

    # текущее состояние/время
    t0  = t_all[-1]
    x0  = x_all[-1];  y0  = y_all[-1]
    vx0 = vx_all[-1]; vy0 = vy_all[-1]

    # -------- 2) LOI: перевод на круговую LPO --------
    loi_info = dict(dv_loi_req=0.0, dv_loi_used=0.0, loi_fuel_limited=False)
    if do_loi:
        dv_loi, vx1, vy1 = _circularize_impulse(x0, y0, vx0, vy0, t0, r_lpo)
        if consume_fuel:
            m_after, dv_used, limited = _rocket_eq_mass_after_dv(m, dv_loi, prop.Isp, m_min)
            m = m_after
        else:
            dv_used, limited = dv_loi, False

        # фиксируем «мгновенный» импульс
        t_all.append(t0)
        x_all.append(x0);  y_all.append(y0)
        vx_all.append(vx1); vy_all.append(vy1)
        m_all.append(m);   thrust_accel.append(0.0)

        # короткий круиз по LPO (честной гравитацией)
        sol_lpo = solve_ivp(
            rhs_grav, (t0, t0 + max(10.0, coast_on_lpo_s)),
            [x0, y0, vx1, vy1],
            method="LSODA", rtol=1e-9, atol=1e-12, max_step=5.0
        )
        t_all  += list(sol_lpo.t[1:])
        x_all  += list(sol_lpo.y[0, 1:]); y_all  += list(sol_lpo.y[1, 1:])
        vx_all += list(sol_lpo.y[2, 1:]); vy_all += list(sol_lpo.y[3, 1:])
        m_all  += [m] * (sol_lpo.t.size - 1)
        thrust_accel += [0.0] * (sol_lpo.t.size - 1)

        # состояние для следующей фазы
        t0  = t_all[-1]
        x0  = x_all[-1];  y0  = y_all[-1]
        vx0 = vx_all[-1]; vy0 = vy_all[-1]

        loi_info = dict(dv_loi_req=float(dv_loi), dv_loi_used=float(dv_used), loi_fuel_limited=bool(limited))

    # -------- 3) деорбит с LPO --------
    deo_info = dict(dv_deorbit_req=0.0, dv_deorbit_used=0.0, deorbit_fuel_limited=False)
    if do_deorbit:
        r_a = r_lpo
        r_p = RADIUS_MOON + landing_start_alt
        dv_deo = _deorbit_impulse_for_rp(r_a, r_p)

        # ретроград по тангенсу локальной орбиты вокруг Луны
        mx, my = calculate_moon_position(t0)
        dx, dy = x0 - mx, y0 - my
        r = np.hypot(dx, dy)
        etx, ety = -dy / r, dx / r  # единичный тангенс
        vx1, vy1 = vx0 - dv_deo * etx, vy0 - dv_deo * ety

        if consume_fuel:
            m_after, dv_used, limited_deo = _rocket_eq_mass_after_dv(m, dv_deo, prop.Isp, m_min)
            m = m_after
        else:
            dv_used, limited_deo = dv_deo, False

        # «мгновенный» импульс
        t_all.append(t0)
        x_all.append(x0);  y_all.append(y0)
        vx_all.append(vx1); vy_all.append(vy1)
        m_all.append(m);   thrust_accel.append(0.0)

        # свободный полёт до высоты посадочного старта
        a = 0.5 * (r_a + r_p)
        T_ell = 2.0 * np.pi * np.sqrt(a ** 3 / MU_M)
        t_to_peri  = 0.5 * T_ell
        t_horizon  = max(900.0, min(6 * 3600.0, 1.2 * t_to_peri))

        sol_drop = solve_ivp(
            rhs_grav, (t0, t0 + t_horizon),
            [x0, y0, vx1, vy1],
            events=[_event_reach_start_alt(landing_start_alt)],
            method="LSODA", rtol=1e-9, atol=1e-12, max_step=3.0
        )
        t_all  += list(sol_drop.t[1:])
        x_all  += list(sol_drop.y[0, 1:]); y_all  += list(sol_drop.y[1, 1:])
        vx_all += list(sol_drop.y[2, 1:]); vy_all += list(sol_drop.y[3, 1:])
        m_all  += [m] * (sol_drop.t.size - 1)
        thrust_accel += [0.0] * (sol_drop.t.size - 1)

        # состояние для посадки
        t0  = t_all[-1]
        x0  = x_all[-1];  y0  = y_all[-1]
        vx0 = vx_all[-1]; vy0 = vy_all[-1]

        deo_info = dict(dv_deorbit_req=float(dv_deo), dv_deorbit_used=float(dv_used), deorbit_fuel_limited=bool(limited_deo))

    # -------- 4) мягкая посадка --------
    s0 = [x0, y0, vx0, vy0, m]
    sol_land = solve_ivp(
        lambda tt, ss: _landing_rhs_fuel(tt, ss, prop, v_touchdown),
        (t0, t0 + 20000.0), s0,
        method="LSODA", rtol=1e-9, atol=1e-12,
        events=[_event_touchdown], max_step=1.0
    )

    # профиль тягового ускорения для HUD: 0 или Tmax/m
    thrust_a = []
    for ti, xi, yi, vxi, vyi, mi in zip(sol_land.t, *sol_land.y):
        vmx, vmy = _moon_vel(ti)
        vrel = np.hypot(vxi - vmx, vyi - vmy)
        mx, my = calculate_moon_position(ti)
        h = np.hypot(xi - mx, yi - my) - RADIUS_MOON
        a_max = prop.Tmax / max(mi, 1.0)
        need = (h > 0.0) and (vrel*vrel >= 2.0*a_max*max(h, 1.0) + v_touchdown*v_touchdown) and (mi > m_min)
        thrust_a.append(a_max if need else 0.0)

    t_all  += list(sol_land.t[1:])
    x_all  += list(sol_land.y[0, 1:]); y_all  += list(sol_land.y[1, 1:])
    vx_all += list(sol_land.y[2, 1:]); vy_all += list(sol_land.y[3, 1:])
    m_all  += list(sol_land.y[4, 1:])
    thrust_accel += list(thrust_a[1:])

    # собрать решение-объект
    Y = np.vstack([np.array(x_all), np.array(y_all),
                   np.array(vx_all), np.array(vy_all), np.array(m_all)])
    sol = SimpleNamespace(t=np.array(t_all), y=Y, success=True,
                          thrust_accel=np.array(thrust_accel))

    summary = {
        "start_mass_kg": prop.m0,
        "mass_after_LEO_kg": float(max(prop.mdry + prop.reserve_kg, prop.m0 - drop_mass_at_leo_kg)),
        "final_mass_kg": float(m_all[-1]),
        "fuel_used_total_kg": float(prop.m0 - m_all[-1]),
        "dv_TLI_m_s": float(dv_init or 0.0),
        **loi_info,
        **deo_info,
        "landing_target_touchdown_m_s": float(v_touchdown),
        "lpo_alt_m": float(lpo_alt_m),
    }
    return sol, summary