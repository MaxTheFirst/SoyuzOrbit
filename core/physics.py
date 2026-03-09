from __future__ import annotations

import math
from dataclasses import dataclass

EPSILON_0 = 8.8541878128e-12
MU_0 = 1.25663706212e-6
ELEMENTARY_CHARGE = 1.602176634e-19
BOLTZMANN = 1.380649e-23
ROOM_TEMPERATURE_C = 25.0
GMIN = 1.0e-9


@dataclass(frozen=True)
class MaterialProperties:
    name: str
    resistivity_ohm_m: float
    temperature_coefficient: float
    density_kg_m3: float
    specific_heat_j_kgk: float


MATERIALS: dict[str, MaterialProperties] = {
    "copper": MaterialProperties("Copper", 1.68e-8, 0.00393, 8960.0, 385.0),
    "aluminum": MaterialProperties("Aluminum", 2.82e-8, 0.00429, 2700.0, 897.0),
    "nichrome": MaterialProperties("Nichrome", 1.10e-6, 0.0004, 8400.0, 450.0),
    "tungsten": MaterialProperties("Tungsten", 5.60e-8, 0.0045, 19300.0, 134.0),
}


CHEMISTRY_CURVES: dict[str, dict[str, float]] = {
    "alkaline": {"soc_floor": 0.78, "soc_gain": 0.22, "cold_gain": 0.018},
    "liion": {"soc_floor": 0.90, "soc_gain": 0.10, "cold_gain": 0.011},
    "leadacid": {"soc_floor": 0.84, "soc_gain": 0.16, "cold_gain": 0.014},
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_exp(value: float, limit: float = 60.0) -> float:
    return math.exp(clamp(value, -limit, limit))


def celsius_to_kelvin(temp_c: float) -> float:
    return temp_c + 273.15


def thermal_voltage(temp_c: float) -> float:
    return BOLTZMANN * celsius_to_kelvin(temp_c) / ELEMENTARY_CHARGE


def smooth_limit(value: float, limit: float) -> float:
    if limit <= 0.0:
        return value
    return limit * math.tanh(value / limit)


def thermal_step(
    temp_c: float,
    power_w: float,
    dt_s: float,
    heat_capacity_j_per_k: float,
    thermal_resistance_k_per_w: float,
    ambient_c: float = ROOM_TEMPERATURE_C,
) -> float:
    heat_capacity = max(heat_capacity_j_per_k, 1.0e-9)
    if math.isinf(thermal_resistance_k_per_w):
        cooling_w = 0.0
    else:
        cooling_w = (temp_c - ambient_c) / max(thermal_resistance_k_per_w, 1.0e-9)
    delta = (power_w - cooling_w) * dt_s / heat_capacity
    return temp_c + delta


def saturation_curve(current_a: float, sat_current_a: float, floor: float = 0.2) -> float:
    if sat_current_a <= 0.0:
        return floor
    ratio = abs(current_a) / sat_current_a
    return floor + (1.0 - floor) / (1.0 + ratio * ratio)


def junction_capacitance(
    voltage_v: float,
    zero_bias_capacitance_f: float,
    built_in_potential_v: float = 0.7,
    grading_coefficient: float = 0.45,
) -> float:
    if zero_bias_capacitance_f <= 0.0:
        return 0.0
    if voltage_v < built_in_potential_v:
        scale = 1.0 - voltage_v / max(built_in_potential_v, 1.0e-6)
        return zero_bias_capacitance_f / max(scale ** grading_coefficient, 1.0e-6)
    return zero_bias_capacitance_f / (1.0 + (voltage_v - built_in_potential_v) * 0.3)


def wire_resistance(
    length_m: float,
    area_mm2: float,
    material: MaterialProperties,
    temp_c: float,
    reference_temp_c: float = ROOM_TEMPERATURE_C,
) -> float:
    area_m2 = max(area_mm2, 1.0e-6) * 1.0e-6
    base = material.resistivity_ohm_m * max(length_m, 1.0e-6) / area_m2
    return max(base * (1.0 + material.temperature_coefficient * (temp_c - reference_temp_c)), 1.0e-9)
