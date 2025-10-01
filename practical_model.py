# practical_model.py
import numpy as np
from dataclasses import dataclass
from scipy.integrate import solve_ivp

from simulation import (
    GRAVITATIONAL_CONSTANT, MASS_EARTH, RADIUS_MOON,
    calculate_moon_position, event_rocket_hits_moon, event_rocket_escapes
)

g0 = 9.80665

def earth_gravity(x, y):
    r = np.hypot(x, y)
    if r == 0.0:
        return 0.0, 0.0
    fac = -GRAVITATIONAL_CONSTANT * MASS_EARTH / (r**3)
    return fac * x, fac * y

@dataclass
class Guidance:
    # используем только флаг Луны; без ПИД (минимум законов)
    use_moon_gravity: bool = True

@dataclass
class Propulsion:
    Isp: float = 320.0         # [s]
    Tmax: float = 6e5          # [N] тяга на TLI
    m0: float = 30000.0        # [kg]
    mdry: float = 10000.0      # [kg]
    reserve_kg: float = 300.0  # [kg] запас, который НЕ сжигаем к прибытию    # [kg] сухая масса

def _moon_gravity(x, y, t):
    mx, my = calculate_moon_position(t)
    dx, dy = x - mx, y - my
    r = np.hypot(dx, dy)
    if r == 0.0:
        return 0.0, 0.0
    # GM_луны = 6.67430e-11 * 7.348e22
    fac = -6.67430e-11 * 7.348e22 / (r**3)
    return fac * dx, fac * dy

from types import SimpleNamespace

def simulate_with_fuel(reference_solution,
                       prop: Propulsion = Propulsion(),
                       guide: Guidance = Guidance(),
                       t_max: float | None = None,
                       dv_init: float | None = None,
                       start_from_preburn: bool = True,
                       t_li_dump_s: float = 120.0,   # быстрый «прожиг» в начале
                       reserve_kg: float = 300.0):   # резерв на финише сверх mdry
    """
    Траектория = теоретическая (x,y,vx,vy берём из reference_solution).
    Считаем только массу m(t): много вначале (имитация TLI), затем ровно до конца.
    Никакой тяги и интегрирования — значит совпадение с теорией идеальное.
    """
    # 0) забираем референс
    t_ref = reference_solution.t
    if t_max is not None:
        t_end = min(float(t_ref[-1]), float(t_max))
    else:
        t_end = float(t_ref[-1])
    idx_end = np.searchsorted(t_ref, t_end, side="right")
    t = t_ref[:idx_end]
    x_ref, y_ref, vx_ref, vy_ref = (reference_solution.y[0, :idx_end],
                                    reference_solution.y[1, :idx_end],
                                    reference_solution.y[2, :idx_end],
                                    reference_solution.y[3, :idx_end])

    # 1) массы
    ve = prop.Isp * g0
    dv = float(dv_init or 0.0)
    m_after_tli = max(prop.mdry, prop.m0 * np.exp(-dv / ve)) if dv > 0 else prop.m0
    m_final = max(prop.mdry, prop.mdry + reserve_kg)

    # фаза «dump» в начале
    t0 = float(t[0])
    t_dump_end = t0 + max(t_li_dump_s, 1.0)
    dump_amount = max(0.0, prop.m0 - m_after_tli)
    mdot_dump = dump_amount / (t_dump_end - t0) if dump_amount > 0 else 0.0

    # фаза «круиз»: растягиваем остаток линейно до конца
    cruise_time = max(1.0, t_end - t_dump_end)
    cruise_amount = max(0.0, m_after_tli - m_final)
    mdot_cruise = cruise_amount / cruise_time if cruise_amount > 0 else 0.0

    # 2) строим m(t)
    m = np.empty_like(t, dtype=float)
    for i, ti in enumerate(t):
        if ti <= t_dump_end:
            burned = mdot_dump * (ti - t0)
            m[i] = max(prop.m0 - burned, m_after_tli)
        else:
            burned_after = mdot_cruise * (ti - t_dump_end)
            m[i] = max(m_after_tli - burned_after, m_final)

    # 3) собираем «решение», совместимое с solve_ivp (t, y)
    y = np.vstack([x_ref, y_ref, vx_ref, vy_ref, m])
    sol = SimpleNamespace(t=t, y=y, success=True, t_events=reference_solution.t_events)

    summary = {
        "prop_used_kg": prop.m0 - float(m[-1]),
        "dv_used_m_s": dv,
        "end_mass_kg": float(m[-1]),
        "dump_phase_s": float(t_li_dump_s),
        "cruise_mdot_kg_s": float(mdot_cruise),
    }
    return sol, summary