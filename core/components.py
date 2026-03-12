from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np

from .component import Component, TwoTerminalComponent
from .physics import (
    CHEMISTRY_CURVES,
    ELEMENTARY_CHARGE,
    EPSILON_0,
    GMIN,
    MATERIALS,
    celsius_to_kelvin,
    clamp,
    junction_capacitance,
    safe_exp,
    saturation_curve,
    smooth_limit,
    thermal_voltage,
    wire_resistance,
)


def numerical_jacobian(
    current_fn: Callable[[np.ndarray], np.ndarray],
    voltages: np.ndarray,
    eps: float = 1.0e-6,
) -> np.ndarray:
    base = current_fn(voltages)
    jacobian = np.zeros((base.size, voltages.size), dtype=float)
    for index in range(voltages.size):
        shifted = voltages.copy()
        shifted[index] += eps
        jacobian[:, index] = (current_fn(shifted) - base) / eps
    return jacobian


class RealResistor(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        resistance_ohm: float,
        tolerance: float = 0.05,
        tolerance_bias: float = 0.0,
        temperature_coefficient: float = 0.0039,
        heat_capacity_j_per_k: float = 7.5,
        thermal_resistance_k_per_w: float = 30.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.nominal_resistance_ohm = resistance_ohm
        self.tolerance = tolerance
        self.tolerance_bias = clamp(tolerance_bias, -1.0, 1.0)
        self.temperature_coefficient = temperature_coefficient
        self.actual_resistance_ohm = resistance_ohm * (1.0 + tolerance * self.tolerance_bias)
        self.heat_capacity_j_per_k = heat_capacity_j_per_k
        self.thermal_resistance_k_per_w = thermal_resistance_k_per_w
        self.contact_thermal_resistance_k_per_w = 95.0
        self.calibrate_thermal_network(case_fraction=0.62, junction_fraction=0.24)

    def effective_resistance(self) -> float:
        factor = 1.0 + self.temperature_coefficient * (self.temperature_c - self.reference_temperature_c)
        return max(self.actual_resistance_ohm * factor, 1.0e-6)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        resistance = self.effective_resistance()
        conductance = 1.0 / resistance
        return conductance * voltage_v, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        resistance = self.effective_resistance()
        self.integrate_temperature(self.last_current_a * self.last_current_a * resistance, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "resistance_ohm": float(self.effective_resistance()),
                "tolerance": float(self.tolerance),
            }
        )
        return data


class Thermistor(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        resistance_at_25c_ohm: float = 10000.0,
        beta_k: float = 3950.0,
        series_resistance_ohm: float = 0.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.resistance_at_25c_ohm = max(resistance_at_25c_ohm, 1.0e-3)
        self.beta_k = max(beta_k, 10.0)
        self.series_resistance_ohm = max(series_resistance_ohm, 0.0)
        self.heat_capacity_j_per_k = 2.8
        self.thermal_resistance_k_per_w = 26.0
        self.contact_thermal_resistance_k_per_w = 110.0
        self.calibrate_thermal_network(case_fraction=0.54, junction_fraction=0.34)

    def effective_resistance(self) -> float:
        temp_k = celsius_to_kelvin(self.temperature_c)
        reference_k = celsius_to_kelvin(25.0)
        beta_term = self.beta_k * (1.0 / max(temp_k, 1.0) - 1.0 / reference_k)
        core_resistance = self.resistance_at_25c_ohm * math.exp(beta_term)
        return max(core_resistance + self.series_resistance_ohm, 1.0e-3)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        conductance = 1.0 / self.effective_resistance()
        return conductance * voltage_v, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.integrate_temperature(self.last_current_a * self.last_current_a * self.effective_resistance(), dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "resistance_ohm": float(self.effective_resistance()),
                "beta_k": float(self.beta_k),
            }
        )
        return data


class RealCapacitor(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        capacitance_f: float,
        esr_ohm: float = 0.12,
        esl_h: float = 2.0e-8,
        leak_resistance_ohm: float = 2.0e6,
        max_voltage_v: float = 16.0,
        heat_capacity_j_per_k: float = 6.0,
        thermal_resistance_k_per_w: float = 22.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.capacitance_f = capacitance_f
        self.esr_ohm = esr_ohm
        self.esl_h = esl_h
        self.leak_resistance_ohm = leak_resistance_ohm
        self.max_voltage_v = max_voltage_v
        self.capacitor_voltage_v = 0.0
        self.previous_branch_voltage_v = 0.0
        self.breakdown_active = False
        self.heat_capacity_j_per_k = heat_capacity_j_per_k
        self.thermal_resistance_k_per_w = thermal_resistance_k_per_w
        self.contact_thermal_resistance_k_per_w = 105.0
        self.calibrate_thermal_network(case_fraction=0.66, junction_fraction=0.22)

    def _companion(self, dt_s: float) -> tuple[float, float]:
        dt = max(dt_s, 1.0e-12)
        rate = self.capacitance_f / dt
        hf_factor = 1.0 / (1.0 + (self.esl_h / dt) * 5.0e3)
        conductance = rate / max(1.0 + rate * self.esr_ohm, 1.0e-9)
        conductance *= hf_factor
        history = -conductance * self.capacitor_voltage_v
        return conductance, history

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        g_cap, i_eq = self._companion(dt_s)
        g_leak = 0.0 if math.isinf(self.leak_resistance_ohm) else 1.0 / max(self.leak_resistance_ohm, 1.0)
        self.breakdown_active = abs(voltage_v) > self.max_voltage_v
        g_break = 1.0 / max(self.esr_ohm + 0.15, 0.15) if self.breakdown_active else 0.0
        total_conductance = g_cap + g_leak + g_break
        current = total_conductance * voltage_v + i_eq
        return current, total_conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        g_cap, i_eq = self._companion(dt_s)
        cap_current = g_cap * self.last_voltage_v + i_eq
        self.capacitor_voltage_v = self.last_voltage_v - cap_current * self.esr_ohm
        self.previous_branch_voltage_v = self.last_voltage_v
        leak_power = 0.0 if math.isinf(self.leak_resistance_ohm) else (self.last_voltage_v ** 2) / max(self.leak_resistance_ohm, 1.0)
        self.integrate_temperature(cap_current * cap_current * self.esr_ohm + leak_power, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "capacitance_f": float(self.capacitance_f),
                "capacitor_voltage_v": float(self.capacitor_voltage_v),
                "charge_c": float(self.capacitance_f * self.capacitor_voltage_v),
                "breakdown": float(self.breakdown_active),
            }
        )
        return data


class RealInductor(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        inductance_h: float,
        dc_resistance_ohm: float = 0.18,
        saturation_current_a: float = 2.0,
        relative_permeability: float = 25.0,
        interwinding_capacitance_f: float = 3.0e-11,
        heat_capacity_j_per_k: float = 12.0,
        thermal_resistance_k_per_w: float = 20.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.air_core_inductance_h = inductance_h
        self.relative_permeability = max(relative_permeability, 1.0)
        self.dc_resistance_ohm = dc_resistance_ohm
        self.saturation_current_a = saturation_current_a
        self.interwinding_capacitance_f = interwinding_capacitance_f
        self.magnetic_current_a = 0.0
        self.previous_branch_voltage_v = 0.0
        self.heat_capacity_j_per_k = heat_capacity_j_per_k
        self.thermal_resistance_k_per_w = thermal_resistance_k_per_w
        self.contact_thermal_resistance_k_per_w = 82.0
        self.calibrate_thermal_network(case_fraction=0.64, junction_fraction=0.28)

    def effective_inductance(self) -> float:
        unsaturated = self.air_core_inductance_h * self.relative_permeability
        return max(unsaturated * saturation_curve(self.magnetic_current_a, self.saturation_current_a, floor=0.12), 1.0e-9)

    def effective_resistance(self) -> float:
        return max(self.dc_resistance_ohm * (1.0 + 0.0039 * (self.temperature_c - self.reference_temperature_c)), 1.0e-6)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        dt = max(dt_s, 1.0e-12)
        inductance = self.effective_inductance()
        resistance = self.effective_resistance()
        g_ind = 1.0 / (resistance + inductance / dt)
        i_eq_ind = (inductance / dt * self.magnetic_current_a) / (resistance + inductance / dt)
        g_cap = self.interwinding_capacitance_f / dt
        i_eq_cap = -g_cap * self.previous_branch_voltage_v
        current = (g_ind + g_cap) * voltage_v + i_eq_ind + i_eq_cap
        return current, g_ind + g_cap

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        dt = max(dt_s, 1.0e-12)
        inductance = self.effective_inductance()
        resistance = self.effective_resistance()
        g_ind = 1.0 / (resistance + inductance / dt)
        i_eq_ind = (inductance / dt * self.magnetic_current_a) / (resistance + inductance / dt)
        self.magnetic_current_a = g_ind * self.last_voltage_v + i_eq_ind
        self.previous_branch_voltage_v = self.last_voltage_v
        self.integrate_temperature(self.magnetic_current_a * self.magnetic_current_a * resistance, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "inductance_h": float(self.effective_inductance()),
                "magnetic_current_a": float(self.magnetic_current_a),
                "flux_linkage_wb": float(self.effective_inductance() * self.magnetic_current_a),
            }
        )
        return data


class PhysiWire(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        length_m: float,
        area_mm2: float = 0.75,
        material: str = "copper",
        skin_effect_gain: float = 0.015,
        inductance_per_m_h: float = 7.5e-7,
        shunt_capacitance_f_per_m: float = 6.0e-11,
        dielectric_conductance_s_per_m: float = 2.0e-10,
        proximity_gain: float = 0.003,
        internal_inductance_ratio: float = 0.35,
        diffusion_time_constant_s_per_m: float = 2.5e-7,
        contact_resistance_ohm: float = 0.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.length_m = length_m
        self.area_mm2 = area_mm2
        self.material = MATERIALS.get(material.lower(), MATERIALS["copper"])
        self.skin_effect_gain = skin_effect_gain
        self.inductance_per_m_h = inductance_per_m_h
        self.shunt_capacitance_f_per_m = shunt_capacitance_f_per_m
        self.dielectric_conductance_s_per_m = dielectric_conductance_s_per_m
        self.proximity_gain = proximity_gain
        self.internal_inductance_ratio = clamp(internal_inductance_ratio, 0.05, 0.9)
        self.diffusion_time_constant_s_per_m = diffusion_time_constant_s_per_m
        self.contact_resistance_ohm = max(contact_resistance_ohm, 0.0)
        self.line_current_a = 0.0
        self.skin_memory = 0.0
        self.previous_branch_voltage_v = 0.0
        volume = max(length_m, 1.0e-6) * max(area_mm2, 1.0e-6) * 1.0e-6
        mass = volume * self.material.density_kg_m3
        self.heat_capacity_j_per_k = max(mass * self.material.specific_heat_j_kgk, 1.0)
        self.thermal_resistance_k_per_w = max(20.0 / max(length_m, 0.05), 3.0)
        self.contact_thermal_resistance_k_per_w = max(20.0 / max(math.sqrt(area_mm2), 0.2), 6.0)
        self.calibrate_thermal_network(case_fraction=0.7, junction_fraction=0.16)

    def base_resistance(self) -> float:
        return wire_resistance(self.length_m, self.area_mm2, self.material, self.temperature_c) + self.contact_resistance_ohm

    def effective_resistance(self, dt_s: float, voltage_v: float) -> float:
        base = self.base_resistance()
        dt = max(dt_s, 1.0e-12)
        slew = abs((voltage_v - self.previous_branch_voltage_v) / dt)
        current_density = abs(self.line_current_a) / max(self.area_mm2, 1.0e-6)
        skin_factor = 1.0 + self.skin_effect_gain * math.sqrt(slew + 1.0) * 1.0e-3
        proximity_factor = 1.0 + self.proximity_gain * current_density
        diffusion_factor = 1.0 + 0.08 * self.skin_memory
        return max(base * skin_factor * proximity_factor * diffusion_factor, 1.0e-6)

    def effective_inductance(self, dt_s: float, voltage_v: float) -> float:
        external_inductance = max(self.length_m * self.inductance_per_m_h, 1.0e-10)
        dt = max(dt_s, 1.0e-12)
        slew = abs((voltage_v - self.previous_branch_voltage_v) / dt)
        hf_scale = 1.0 / (1.0 + 4.0e-4 * math.sqrt(slew + 1.0))
        internal_inductance = external_inductance * self.internal_inductance_ratio * hf_scale
        return max(external_inductance + internal_inductance, 1.0e-10)

    def propagation_delay_s(self) -> float:
        return max(self.length_m * math.sqrt(max(self.inductance_per_m_h * self.shunt_capacitance_f_per_m, 1.0e-18)), 0.0)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        dt = max(dt_s, 1.0e-12)
        resistance = self.effective_resistance(dt_s, voltage_v)
        inductance = self.effective_inductance(dt_s, voltage_v)
        g_series = 1.0 / (resistance + inductance / dt)
        i_eq_series = (inductance / dt * self.line_current_a) / (resistance + inductance / dt)
        g_cap = (self.length_m * self.shunt_capacitance_f_per_m) / dt
        g_dielectric = self.length_m * self.dielectric_conductance_s_per_m
        history_shift = self.previous_branch_voltage_v * (1.0 - 0.08 * min(self.skin_memory, 2.0))
        i_eq_cap = -g_cap * history_shift
        current = (g_series + g_cap + g_dielectric) * voltage_v + i_eq_series + i_eq_cap
        return current, g_series + g_cap + g_dielectric

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        dt = max(dt_s, 1.0e-12)
        resistance = self.effective_resistance(dt_s, self.last_voltage_v)
        inductance = self.effective_inductance(dt_s, self.last_voltage_v)
        g_series = 1.0 / (resistance + inductance / dt)
        i_eq_series = (inductance / dt * self.line_current_a) / (resistance + inductance / dt)
        self.line_current_a = g_series * self.last_voltage_v + i_eq_series
        diffusion_tau = max(self.length_m * self.diffusion_time_constant_s_per_m, dt)
        alpha = dt / (diffusion_tau + dt)
        slew_marker = abs((self.last_voltage_v - self.previous_branch_voltage_v) / dt) * 1.0e-6
        self.skin_memory += alpha * (slew_marker - self.skin_memory)
        self.previous_branch_voltage_v = self.last_voltage_v
        dielectric_power = self.last_voltage_v * self.last_voltage_v * self.length_m * self.dielectric_conductance_s_per_m
        self.integrate_temperature(self.line_current_a * self.line_current_a * resistance + dielectric_power, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "resistance_ohm": float(self.effective_resistance(1.0e-3, self.last_voltage_v)),
                "inductance_h": float(self.effective_inductance(1.0e-3, self.last_voltage_v)),
                "length_m": float(self.length_m),
                "material": self.material.name,
                "propagation_delay_s": float(self.propagation_delay_s()),
                "contact_resistance_ohm": float(self.contact_resistance_ohm),
            }
        )
        return data


class PhysiBattery(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        nominal_voltage_v: float = 9.0,
        capacity_mah: float = 550.0,
        chemistry: str = "alkaline",
        internal_resistance_ohm: float = 1.2,
        initial_soc: float = 1.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.nominal_voltage_v = nominal_voltage_v
        self.capacity_mah = capacity_mah
        self.chemistry = chemistry.lower()
        self.internal_resistance_ohm = internal_resistance_ohm
        self.state_of_charge = clamp(initial_soc, 0.0, 1.0)
        self.heat_capacity_j_per_k = 35.0
        self.thermal_resistance_k_per_w = 8.0
        self.contact_thermal_resistance_k_per_w = 70.0
        self.calibrate_thermal_network(case_fraction=0.72, junction_fraction=0.18)

    def open_circuit_voltage(self) -> float:
        curve = CHEMISTRY_CURVES.get(self.chemistry, CHEMISTRY_CURVES["alkaline"])
        soc_term = curve["soc_floor"] + curve["soc_gain"] * self.state_of_charge
        return self.nominal_voltage_v * soc_term

    def effective_internal_resistance(self) -> float:
        curve = CHEMISTRY_CURVES.get(self.chemistry, CHEMISTRY_CURVES["alkaline"])
        soc_penalty = 1.0 + 1.8 * (1.0 - self.state_of_charge) ** 2
        temp_penalty = 1.0 + curve["cold_gain"] * max(0.0, self.reference_temperature_c - self.temperature_c)
        current_penalty = 1.0 + 0.08 * abs(self.last_current_a)
        return max(self.internal_resistance_ohm * soc_penalty * temp_penalty * current_penalty, 1.0e-4)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        resistance = self.effective_internal_resistance()
        emf = self.open_circuit_voltage()
        conductance = 1.0 / resistance
        current = conductance * voltage_v - conductance * emf
        return current, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        discharge_current = max(0.0, -self.last_current_a)
        capacity_c = max(self.capacity_mah, 1.0) * 3.6
        self.state_of_charge = clamp(self.state_of_charge - discharge_current * dt_s / capacity_c, 0.0, 1.0)
        self.integrate_temperature(self.last_current_a * self.last_current_a * self.effective_internal_resistance(), dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "soc": float(self.state_of_charge),
                "open_circuit_voltage_v": float(self.open_circuit_voltage()),
                "internal_resistance_ohm": float(self.effective_internal_resistance()),
            }
        )
        return data


class RealACGenerator(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        amplitude_v: float = 5.0,
        frequency_hz: float = 1000.0,
        phase_rad: float = 0.0,
        internal_resistance_ohm: float = 0.5,
        phase_noise_rad: float = 0.01,
        frequency_error: float = 0.0,
        harmonic_2_ratio: float = 0.03,
        harmonic_3_ratio: float = 0.01,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.amplitude_v = amplitude_v
        self.frequency_hz = frequency_hz
        self.phase_rad = phase_rad
        self.internal_resistance_ohm = internal_resistance_ohm
        self.phase_noise_rad = phase_noise_rad
        self.frequency_error = frequency_error
        self.harmonic_2_ratio = harmonic_2_ratio
        self.harmonic_3_ratio = harmonic_3_ratio
        self.instantaneous_emf_v = 0.0

    def emf(self, time_s: float) -> float:
        omega = 2.0 * math.pi * self.frequency_hz * (1.0 + self.frequency_error)
        phase = omega * time_s + self.phase_rad + self.phase_noise_rad * math.sin(2.0 * math.pi * 0.37 * time_s)
        fundamental = self.amplitude_v * math.sin(phase)
        second = self.amplitude_v * self.harmonic_2_ratio * math.sin(2.0 * phase + 0.4)
        third = self.amplitude_v * self.harmonic_3_ratio * math.sin(3.0 * phase - 0.3)
        return fundamental + second + third

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del dt_s
        self.instantaneous_emf_v = self.emf(time_s)
        conductance = 1.0 / max(self.internal_resistance_ohm, 1.0e-6)
        current = conductance * voltage_v - conductance * self.instantaneous_emf_v
        return current, conductance

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"emf_v": float(self.instantaneous_emf_v), "frequency_hz": float(self.frequency_hz)})
        return data


class PulseGenerator(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        high_voltage_v: float = 5.0,
        low_voltage_v: float = 0.0,
        period_s: float = 1.0,
        duty_cycle: float = 0.5,
        pulse_width_s: float | None = None,
        rise_time_s: float = 1.0e-3,
        fall_time_s: float = 1.0e-3,
        internal_resistance_ohm: float = 0.8,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.high_voltage_v = high_voltage_v
        self.low_voltage_v = low_voltage_v
        self.period_s = max(period_s, 1.0e-6)
        self.duty_cycle = clamp(duty_cycle, 0.0, 1.0)
        self.pulse_width_s = None if pulse_width_s is None else max(min(pulse_width_s, self.period_s), 0.0)
        self.rise_time_s = max(rise_time_s, 1.0e-9)
        self.fall_time_s = max(fall_time_s, 1.0e-9)
        self.internal_resistance_ohm = max(internal_resistance_ohm, 1.0e-6)
        self.instantaneous_emf_v = low_voltage_v
        self.heat_capacity_j_per_k = 6.5
        self.thermal_resistance_k_per_w = 18.0
        self.contact_thermal_resistance_k_per_w = 95.0
        self.calibrate_thermal_network(case_fraction=0.58, junction_fraction=0.22)

    def emf(self, time_s: float) -> float:
        local_time = time_s % self.period_s
        on_time = self.period_s * self.duty_cycle if self.pulse_width_s is None else self.pulse_width_s
        on_time = min(max(on_time, 0.0), self.period_s)
        level = 0.0
        if on_time > 0.0:
            if local_time < min(self.rise_time_s, on_time):
                ratio = local_time / max(self.rise_time_s, 1.0e-12)
                level = 0.5 - 0.5 * math.cos(math.pi * clamp(ratio, 0.0, 1.0))
            elif local_time < max(on_time - self.fall_time_s, self.rise_time_s):
                level = 1.0
            elif local_time < on_time:
                ratio = (local_time - max(on_time - self.fall_time_s, 0.0)) / max(self.fall_time_s, 1.0e-12)
                level = 0.5 + 0.5 * math.cos(math.pi * clamp(ratio, 0.0, 1.0))
        return self.low_voltage_v + (self.high_voltage_v - self.low_voltage_v) * level

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del dt_s
        self.instantaneous_emf_v = self.emf(time_s)
        conductance = 1.0 / self.internal_resistance_ohm
        current = conductance * voltage_v - conductance * self.instantaneous_emf_v
        return current, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.integrate_temperature(self.last_current_a * self.last_current_a * self.internal_resistance_ohm, dt_s)

    def observe(self) -> dict[str, Any]:
        effective_pulse_width = self.period_s * self.duty_cycle if self.pulse_width_s is None else self.pulse_width_s
        data = super().observe()
        data.update(
            {
                "emf_v": float(self.instantaneous_emf_v),
                "period_s": float(self.period_s),
                "duty_cycle": float(self.duty_cycle),
                "pulse_width_s": float(effective_pulse_width),
            }
        )
        return data


class SchockleyDiode(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        saturation_current_a: float = 1.0e-12,
        emission_coefficient: float = 1.9,
        barrier_capacitance_f: float = 4.0e-11,
        forward_drop_v: float = 0.72,
        breakdown_voltage_v: float = 70.0,
        avalanche_softness_v: float = 3.0,
        shunt_resistance_ohm: float = 5.0e7,
        transit_time_s: float = 1.5e-8,
        reverse_recovery_tau_s: float = 7.5e-8,
        junction_area_um2: float = 60000.0,
        doping_p_cm3: float = 1.0e17,
        doping_n_cm3: float = 5.0e16,
        intrinsic_carrier_density_cm3: float = 1.0e10,
        carrier_lifetime_s: float = 2.0e-6,
        relative_permittivity: float = 11.7,
        heat_capacity_j_per_k: float = 3.0,
        thermal_resistance_k_per_w: float = 18.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.saturation_current_a = saturation_current_a
        self.emission_coefficient = emission_coefficient
        self.barrier_capacitance_f = barrier_capacitance_f
        self.forward_drop_v = forward_drop_v
        self.breakdown_voltage_v = breakdown_voltage_v
        self.avalanche_softness_v = max(avalanche_softness_v, 1.0e-6)
        self.shunt_resistance_ohm = shunt_resistance_ohm
        self.transit_time_s = max(transit_time_s, 0.0)
        self.reverse_recovery_tau_s = max(reverse_recovery_tau_s, 1.0e-12)
        self.junction_area_um2 = max(junction_area_um2, 1.0)
        self.doping_p_cm3 = max(doping_p_cm3, 1.0)
        self.doping_n_cm3 = max(doping_n_cm3, 1.0)
        self.intrinsic_carrier_density_cm3 = max(intrinsic_carrier_density_cm3, 1.0)
        self.carrier_lifetime_s = max(carrier_lifetime_s, 1.0e-12)
        self.relative_permittivity = max(relative_permittivity, 1.0)
        self.previous_voltage_v = 0.0
        self.previous_forward_current_a = 0.0
        self.stored_charge_c = 0.0
        self.heat_capacity_j_per_k = heat_capacity_j_per_k
        self.thermal_resistance_k_per_w = thermal_resistance_k_per_w
        self.contact_thermal_resistance_k_per_w = 115.0
        self.calibrate_thermal_network(case_fraction=0.52, junction_fraction=0.38)

    def _junction_area_m2(self) -> float:
        return self.junction_area_um2 * 1.0e-12

    def _ni_m3(self) -> float:
        return self.intrinsic_carrier_density_cm3 * 1.0e6

    def _na_m3(self) -> float:
        return self.doping_p_cm3 * 1.0e6

    def _nd_m3(self) -> float:
        return self.doping_n_cm3 * 1.0e6

    def built_in_potential_v(self) -> float:
        vt = max(thermal_voltage(self.temperature_c), 1.0e-6)
        ratio = max(self._na_m3() * self._nd_m3() / max(self._ni_m3() ** 2, 1.0), 1.000001)
        return vt * math.log(ratio)

    def depletion_width_m(self, voltage_v: float) -> float:
        permittivity = self.relative_permittivity * EPSILON_0
        depletion_potential = self.built_in_potential_v() - min(voltage_v, self.built_in_potential_v() * 0.92)
        depletion_potential = max(depletion_potential, 1.0e-4)
        doping_term = 1.0 / max(self._na_m3(), 1.0) + 1.0 / max(self._nd_m3(), 1.0)
        return math.sqrt(2.0 * permittivity * depletion_potential * doping_term / ELEMENTARY_CHARGE)

    def peak_field_v_m(self, voltage_v: float) -> float:
        width = max(self.depletion_width_m(voltage_v), 1.0e-12)
        depletion_potential = max(self.built_in_potential_v() - voltage_v, 0.0)
        return 2.0 * depletion_potential / width

    def _device_junction_capacitance_f(self, voltage_v: float) -> float:
        width = max(self.depletion_width_m(voltage_v), 1.0e-12)
        area = self._junction_area_m2()
        permittivity = self.relative_permittivity * EPSILON_0
        physical_cap = permittivity * area / width
        compact_cap = junction_capacitance(voltage_v, self.barrier_capacitance_f)
        return max(0.35 * compact_cap + 0.65 * physical_cap, 1.0e-18)

    def _recombination_current(self, voltage_v: float) -> tuple[float, float]:
        vt = max(thermal_voltage(self.temperature_c), 1.0e-6)
        width = self.depletion_width_m(voltage_v)
        generation_scale = ELEMENTARY_CHARGE * self._junction_area_m2() * self._ni_m3() * width / (2.0 * self.carrier_lifetime_s)
        expo = safe_exp(voltage_v / max(2.0 * vt, 1.0e-6))
        current = generation_scale * (expo - 1.0)
        conductance = generation_scale * expo / max(2.0 * vt, 1.0e-6)
        return current, conductance

    def _diode_forward_branch(self, voltage_v: float) -> tuple[float, float]:
        vt = max(thermal_voltage(self.temperature_c) * self.emission_coefficient, 1.0e-6)
        kelvin = celsius_to_kelvin(self.temperature_c)
        reference_kelvin = celsius_to_kelvin(self.reference_temperature_c)
        saturation_scale = (kelvin / max(reference_kelvin, 1.0)) ** 2
        activation = safe_exp((self.forward_drop_v / max(self.emission_coefficient, 1.0e-6)) * (1.0 / thermal_voltage(self.reference_temperature_c) - 1.0 / max(thermal_voltage(self.temperature_c), 1.0e-6)))
        effective_saturation = max(self.saturation_current_a * saturation_scale * activation, 1.0e-18)
        expo = safe_exp(voltage_v / vt)
        diode_current = effective_saturation * (expo - 1.0)
        diode_conductance = effective_saturation * expo / vt
        return diode_current, diode_conductance

    def _static_current(self, voltage_v: float) -> tuple[float, float]:
        diode_current, diode_conductance = self._diode_forward_branch(voltage_v)
        recombination_current, recombination_conductance = self._recombination_current(voltage_v)
        shunt_conductance = 0.0 if math.isinf(self.shunt_resistance_ohm) else 1.0 / max(self.shunt_resistance_ohm, 1.0)
        breakdown_current = 0.0
        breakdown_conductance = 0.0
        if voltage_v < -self.breakdown_voltage_v:
            overdrive = -(voltage_v + self.breakdown_voltage_v)
            breakdown_conductance = 1.0 / max(4.0 * self.avalanche_softness_v, 1.0e-6)
            breakdown_current = -breakdown_conductance * overdrive * (1.0 + overdrive / (self.avalanche_softness_v + overdrive))
        current = diode_current + recombination_current + shunt_conductance * voltage_v + breakdown_current
        conductance = diode_conductance + recombination_conductance + shunt_conductance + breakdown_conductance + GMIN
        return current, conductance

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        current, conductance = self._static_current(voltage_v)
        dt = max(dt_s, 1.0e-12)
        cap = self._device_junction_capacitance_f(voltage_v)
        g_cap = cap / dt
        i_eq = -g_cap * self.previous_voltage_v
        forward_current, forward_conductance = self._diode_forward_branch(voltage_v)
        g_diffusion = self.transit_time_s * forward_conductance / dt
        i_diffusion = self.transit_time_s * (max(forward_current, 0.0) - self.previous_forward_current_a) / dt
        recovery_current = -self.stored_charge_c / self.reverse_recovery_tau_s
        return current + g_cap * voltage_v + i_eq + i_diffusion + recovery_current, conductance + g_cap + g_diffusion

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.previous_voltage_v = self.last_voltage_v
        forward_current, _ = self._diode_forward_branch(self.last_voltage_v)
        self.previous_forward_current_a = max(forward_current, 0.0)
        target_charge = self.transit_time_s * self.previous_forward_current_a
        charge_alpha = dt_s / (self.reverse_recovery_tau_s + dt_s)
        self.stored_charge_c += charge_alpha * (target_charge - self.stored_charge_c)
        if self.last_voltage_v < 0.0:
            self.stored_charge_c *= math.exp(-dt_s / self.reverse_recovery_tau_s)
        static_current, _ = self._static_current(self.last_voltage_v)
        self.integrate_temperature(abs(self.last_voltage_v * static_current), dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "junction_capacitance_f": float(self._device_junction_capacitance_f(self.last_voltage_v)),
                "forward_drop_v": float(self.forward_drop_v),
                "stored_charge_c": float(self.stored_charge_c),
                "built_in_potential_v": float(self.built_in_potential_v()),
                "depletion_width_m": float(self.depletion_width_m(self.last_voltage_v)),
                "peak_field_v_m": float(self.peak_field_v_m(self.last_voltage_v)),
            }
        )
        return data


class LED_ImageActive(SchockleyDiode):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        color: str = "red",
        max_forward_current_a: float = 0.02,
        luminous_efficiency: float = 0.25,
        burn_energy_j: float = 0.03,
        ambient_c: float = 25.0,
        **kwargs: Any,
    ) -> None:
        defaults = {
            "saturation_current_a": 2.0e-12,
            "emission_coefficient": 2.1,
            "barrier_capacitance_f": 8.0e-11,
            "forward_drop_v": 2.0 if color.lower() != "infrared" else 1.35,
            "breakdown_voltage_v": 5.0,
            "shunt_resistance_ohm": 1.0e8,
        }
        defaults.update(kwargs)
        super().__init__(name, positive, negative, ambient_c=ambient_c, **defaults)
        self.color = color
        self.max_forward_current_a = max_forward_current_a
        self.luminous_efficiency = luminous_efficiency
        self.burn_energy_j = burn_energy_j
        self.damage_j = 0.0
        self.brightness = 0.0
        self.failed = False
        self.flash = 0.0

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        if self.failed:
            conductance = 1.0 / 1.0e9
            return conductance * voltage_v, conductance
        return super().branch_current(voltage_v, time_s, dt_s)

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        previously_failed = self.failed
        super().commit(terminal_voltages, time_s, dt_s)
        if self.failed:
            self.brightness = 0.0
            self.flash = 0.0
            return
        forward_current = max(0.0, self.last_current_a)
        self.brightness = clamp((forward_current / max(self.max_forward_current_a, 1.0e-6)) ** 0.85, 0.0, 1.0)
        overstress = max(0.0, forward_current - self.max_forward_current_a)
        self.damage_j += overstress * max(self.last_voltage_v, 0.0) * dt_s * 25.0
        if forward_current > self.max_forward_current_a * 3.0 or self.damage_j > self.burn_energy_j:
            self.failed = True
            self.brightness = 0.0
        self.flash = 1.0 if self.failed and not previously_failed else self.brightness

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "brightness": float(self.brightness),
                "failed": float(self.failed),
                "flash": float(self.flash),
                "color": self.color,
            }
        )
        return data


class PhysiOpAmp(Component):
    terminal_labels = ("plus", "minus", "out")

    def __init__(
        self,
        name: str,
        plus: str,
        minus: str,
        out: str,
        open_loop_gain: float = 2.0e5,
        input_resistance_ohm: float = 2.0e6,
        output_resistance_ohm: float = 60.0,
        slew_rate_v_s: float = 6.0e5,
        dominant_pole_hz: float = 12.0,
        output_current_limit_a: float = 0.035,
        input_bias_current_a: float = 8.0e-8,
        common_mode_rejection: float = 9.0e4,
        power_supply_rejection: float = 1.5e5,
        input_offset_v: float = 0.0,
        supply_min_v: float = -12.0,
        supply_max_v: float = 12.0,
        quiescent_current_a: float = 0.002,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, [plus, minus, out], ambient_c)
        self.open_loop_gain = open_loop_gain
        self.input_resistance_ohm = input_resistance_ohm
        self.output_resistance_ohm = output_resistance_ohm
        self.slew_rate_v_s = slew_rate_v_s
        self.dominant_pole_hz = dominant_pole_hz
        self.output_current_limit_a = output_current_limit_a
        self.input_bias_current_a = input_bias_current_a
        self.common_mode_rejection = common_mode_rejection
        self.power_supply_rejection = power_supply_rejection
        self.input_offset_v = input_offset_v
        self.supply_min_v = supply_min_v
        self.supply_max_v = supply_max_v
        self.quiescent_current_a = quiescent_current_a
        self.internal_drive_v = 0.0
        self.target_output_v = 0.0
        self.current_limit_engaged = False
        self.heat_capacity_j_per_k = 9.0
        self.thermal_resistance_k_per_w = 15.0
        self.contact_thermal_resistance_k_per_w = 100.0
        self.calibrate_thermal_network(case_fraction=0.6, junction_fraction=0.3)

    def _desired_output(self, vp: float, vm: float) -> float:
        supply_mid = 0.5 * (self.supply_max_v + self.supply_min_v)
        supply_half_span = max(0.5 * (self.supply_max_v - self.supply_min_v), 1.0e-6)
        common_mode = 0.5 * (vp + vm)
        error = vp - vm + self.input_offset_v
        error -= common_mode / max(self.common_mode_rejection, 1.0)
        error -= supply_mid / max(self.power_supply_rejection, 1.0)
        return supply_mid + supply_half_span * math.tanh(self.open_loop_gain * error / supply_half_span)

    def _target(self, vp: float, vm: float, dt_s: float) -> float:
        desired = self._desired_output(vp, vm)
        dt = max(dt_s, 1.0e-12)
        pole_tau = 1.0 / max(2.0 * math.pi * self.dominant_pole_hz, 1.0e-9)
        alpha = dt / (pole_tau + dt)
        desired_step = self.internal_drive_v + alpha * (desired - self.internal_drive_v)
        max_delta = self.slew_rate_v_s * dt
        return clamp(self.internal_drive_v + clamp(desired_step - self.internal_drive_v, -max_delta, max_delta), self.supply_min_v, self.supply_max_v)

    def currents(
        self,
        terminal_voltages: np.ndarray,
        time_s: float,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        del time_s
        vp, vm, vo = terminal_voltages
        g_in = 1.0 / max(self.input_resistance_ohm, 1.0)
        target = self._target(vp, vm, dt_s)

        def current_fn(voltages: np.ndarray) -> np.ndarray:
            target_local = self._target(float(voltages[0]), float(voltages[1]), dt_s)
            differential_input = (voltages[0] - voltages[1]) * g_in
            bias_plus = self.input_bias_current_a * (1.0 + 0.02 * math.tanh((self.temperature_c - self.reference_temperature_c) / 15.0))
            bias_minus = self.input_bias_current_a * (1.0 - 0.02 * math.tanh((self.temperature_c - self.reference_temperature_c) / 15.0))
            raw_output = (voltages[2] - target_local) / max(self.output_resistance_ohm, 1.0e-6)
            i_out = self.output_current_limit_a * math.tanh(raw_output / max(self.output_current_limit_a, 1.0e-9))
            return np.array(
                [
                    0.5 * differential_input + g_in * voltages[0] + bias_plus,
                    -0.5 * differential_input + g_in * voltages[1] + bias_minus,
                    i_out,
                ],
                dtype=float,
            )

        currents = current_fn(terminal_voltages)
        jacobian = numerical_jacobian(current_fn, terminal_voltages)
        return currents, jacobian

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.last_currents = self.currents(terminal_voltages, time_s, dt_s)[0]
        self.target_output_v = self._target(float(terminal_voltages[0]), float(terminal_voltages[1]), dt_s)
        self.internal_drive_v = self.target_output_v
        self.current_limit_engaged = abs(self.last_currents[2]) >= 0.98 * self.output_current_limit_a
        supply_span = self.supply_max_v - self.supply_min_v
        dynamic_power = abs((terminal_voltages[2] - self.target_output_v) * self.last_currents[2])
        self.integrate_temperature(dynamic_power + self.quiescent_current_a * supply_span, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "output_target_v": float(self.target_output_v),
                "output_current_a": float(self.last_currents[2]),
                "dominant_node_v": float(self.internal_drive_v),
                "current_limit": float(self.current_limit_engaged),
            }
        )
        return data


class RealFuse(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        current_rating_a: float = 1.0,
        cold_resistance_ohm: float = 0.05,
        melting_temperature_c: float = 220.0,
        i2t_trip: float = 1.6,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.current_rating_a = current_rating_a
        self.cold_resistance_ohm = cold_resistance_ohm
        self.melting_temperature_c = melting_temperature_c
        self.i2t_trip = i2t_trip
        self.blown = False
        self.stress_i2t = 0.0
        self.heat_capacity_j_per_k = 0.6
        self.thermal_resistance_k_per_w = 10.0
        self.contact_thermal_resistance_k_per_w = 38.0
        self.calibrate_thermal_network(case_fraction=0.42, junction_fraction=0.5)

    def effective_resistance(self) -> float:
        if self.blown:
            return 1.0e9
        return max(self.cold_resistance_ohm * (1.0 + 0.004 * (self.temperature_c - self.reference_temperature_c)), 1.0e-5)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        resistance = self.effective_resistance()
        conductance = 1.0 / resistance
        return conductance * voltage_v, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        if self.blown:
            self.last_current_a = 0.0
            self.last_power_w = 0.0
            return
        resistance = self.effective_resistance()
        self.stress_i2t += (abs(self.last_current_a) / max(self.current_rating_a, 1.0e-6)) ** 2 * dt_s
        self.integrate_temperature(self.last_current_a * self.last_current_a * resistance, dt_s)
        if self.temperature_c >= self.melting_temperature_c or self.stress_i2t >= self.i2t_trip:
            self.blown = True

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"blown": float(self.blown), "stress_i2t": float(self.stress_i2t)})
        return data


class IncandescentBulb(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        rated_voltage_v: float = 12.0,
        rated_power_w: float = 21.0,
        cold_ratio: float = 10.0,
        filament_operating_temp_c: float = 2400.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.rated_voltage_v = rated_voltage_v
        self.rated_power_w = rated_power_w
        self.cold_ratio = cold_ratio
        self.filament_operating_temp_c = filament_operating_temp_c
        self.hot_resistance_ohm = rated_voltage_v * rated_voltage_v / max(rated_power_w, 1.0e-6)
        self.cold_resistance_ohm = self.hot_resistance_ohm / max(cold_ratio, 1.0)
        span = max(self.filament_operating_temp_c - self.reference_temperature_c, 1.0)
        self.temperature_coefficient = (self.hot_resistance_ohm / self.cold_resistance_ohm - 1.0) / span
        self.heat_capacity_j_per_k = 1.8
        self.thermal_resistance_k_per_w = 6.5
        self.contact_thermal_resistance_k_per_w = 32.0
        self.glow = 0.0
        self.calibrate_thermal_network(case_fraction=0.36, junction_fraction=0.46)

    def effective_resistance(self) -> float:
        factor = 1.0 + self.temperature_coefficient * (self.temperature_c - self.reference_temperature_c)
        return max(self.cold_resistance_ohm * factor, 1.0e-4)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        resistance = self.effective_resistance()
        conductance = 1.0 / resistance
        return conductance * voltage_v, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        resistance = self.effective_resistance()
        self.integrate_temperature(self.last_current_a * self.last_current_a * resistance, dt_s)
        self.glow = clamp((self.temperature_c - self.reference_temperature_c) / (self.filament_operating_temp_c - self.reference_temperature_c), 0.0, 1.0)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"resistance_ohm": float(self.effective_resistance()), "glow": float(self.glow)})
        return data


class Ammeter(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        shunt_resistance_ohm: float = 0.01,
        lead_inductance_h: float = 2.5e-8,
        max_display_current_a: float = 10.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.shunt_resistance_ohm = shunt_resistance_ohm
        self.lead_inductance_h = lead_inductance_h
        self.max_display_current_a = max_display_current_a
        self.shunt_current_a = 0.0
        self.overload = False
        self.heat_capacity_j_per_k = 4.0
        self.thermal_resistance_k_per_w = 14.0
        self.contact_thermal_resistance_k_per_w = 85.0
        self.calibrate_thermal_network(case_fraction=0.62, junction_fraction=0.25)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        dt = max(dt_s, 1.0e-12)
        resistance = max(self.shunt_resistance_ohm, 1.0e-6)
        inductance = max(self.lead_inductance_h, 0.0)
        conductance = 1.0 / max(resistance + inductance / dt, 1.0e-9)
        history = conductance * inductance / dt * self.shunt_current_a
        return conductance * voltage_v + history, conductance

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.shunt_current_a = self.last_current_a
        resistance = max(self.shunt_resistance_ohm, 1.0e-6)
        self.overload = abs(self.last_current_a) > self.max_display_current_a
        self.integrate_temperature(self.last_current_a * self.last_current_a * resistance, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"reading_a": float(self.last_current_a), "overload": float(self.overload)})
        return data


class Voltmeter(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        input_resistance_ohm: float = 1.0e7,
        input_capacitance_f: float = 1.8e-11,
        max_display_voltage_v: float = 300.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.input_resistance_ohm = input_resistance_ohm
        self.input_capacitance_f = input_capacitance_f
        self.max_display_voltage_v = max_display_voltage_v
        self.previous_voltage_v = 0.0
        self.overload = False
        self.input_current_a = 0.0
        self.heat_capacity_j_per_k = 2.5
        self.thermal_resistance_k_per_w = 18.0
        self.contact_thermal_resistance_k_per_w = 120.0
        self.calibrate_thermal_network(case_fraction=0.68, junction_fraction=0.2)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        dt = max(dt_s, 1.0e-12)
        g_res = 0.0 if math.isinf(self.input_resistance_ohm) else 1.0 / max(self.input_resistance_ohm, 1.0)
        g_cap = max(self.input_capacitance_f, 0.0) / dt
        i_eq = -g_cap * self.previous_voltage_v
        return (g_res + g_cap) * voltage_v + i_eq, g_res + g_cap

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        resistive_current = 0.0 if math.isinf(self.input_resistance_ohm) else self.last_voltage_v / max(self.input_resistance_ohm, 1.0)
        capacitive_current = self.last_current_a - resistive_current
        self.input_current_a = resistive_current + capacitive_current
        self.previous_voltage_v = self.last_voltage_v
        self.overload = abs(self.last_voltage_v) > self.max_display_voltage_v
        power = 0.0 if math.isinf(self.input_resistance_ohm) else (self.last_voltage_v ** 2) / max(self.input_resistance_ohm, 1.0)
        self.integrate_temperature(power, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"reading_v": float(self.last_voltage_v), "input_current_a": float(self.input_current_a), "overload": float(self.overload)})
        return data


class ToggleSwitch(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        closed: bool = False,
        on_resistance_ohm: float = 0.01,
        off_resistance_ohm: float = 1.0e9,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.closed = closed
        self.on_resistance_ohm = on_resistance_ohm
        self.off_resistance_ohm = off_resistance_ohm

    def toggle(self) -> None:
        self.closed = not self.closed

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        resistance = self.on_resistance_ohm if self.closed else self.off_resistance_ohm
        conductance = 1.0 / max(resistance, 1.0e-9)
        return conductance * voltage_v, conductance

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"closed": float(self.closed)})
        return data


COMPONENT_LIBRARY: dict[str, tuple[type[Component], dict[str, Any]]] = {
    "Battery": (PhysiBattery, {"nominal_voltage_v": 9.0, "capacity_mah": 550.0, "chemistry": "alkaline", "internal_resistance_ohm": 1.2}),
    "AC Generator": (RealACGenerator, {"amplitude_v": 5.0, "frequency_hz": 1000.0, "internal_resistance_ohm": 0.5}),
    "Pulse Generator": (
        PulseGenerator,
        {
            "high_voltage_v": 5.0,
            "low_voltage_v": 0.0,
            "period_s": 1.0,
            "duty_cycle": 0.5,
            "pulse_width_s": 0.2,
            "rise_time_s": 1.0e-3,
            "fall_time_s": 1.0e-3,
            "internal_resistance_ohm": 0.8,
        },
    ),
    "Resistor": (RealResistor, {"resistance_ohm": 220.0}),
    "Thermistor": (Thermistor, {"resistance_at_25c_ohm": 10000.0, "beta_k": 3950.0}),
    "Capacitor": (RealCapacitor, {"capacitance_f": 100e-6, "max_voltage_v": 16.0}),
    "Inductor": (RealInductor, {"inductance_h": 220e-6, "dc_resistance_ohm": 0.2}),
    "Wire": (
        PhysiWire,
        {
            "length_m": 0.3,
            "area_mm2": 0.75,
            "material": "copper",
            "dielectric_conductance_s_per_m": 2.0e-10,
            "proximity_gain": 0.003,
            "auto_length_from_path": True,
            "meters_per_pixel": 0.002,
            "segment_length_target_m": 0.06,
            "max_segments": 12,
            "coupling_gain": 1.0,
            "permittivity_scale": 1.0,
            "mutual_inductance_gain": 1.0,
            "thermal_coupling_gain": 1.0,
            "contact_resistance_ohm": 0.0,
        },
    ),
    "Diode": (
        SchockleyDiode,
        {
            "transit_time_s": 1.5e-8,
            "reverse_recovery_tau_s": 7.5e-8,
            "junction_area_um2": 60000.0,
            "doping_p_cm3": 1.0e17,
            "doping_n_cm3": 5.0e16,
            "carrier_lifetime_s": 2.0e-6,
        },
    ),
    "LED": (LED_ImageActive, {"color": "red", "max_forward_current_a": 0.02}),
    "OpAmp": (
        PhysiOpAmp,
        {
            "open_loop_gain": 2.0e5,
            "dominant_pole_hz": 12.0,
            "output_current_limit_a": 0.035,
            "input_bias_current_a": 8.0e-8,
        },
    ),
    "Fuse": (RealFuse, {"current_rating_a": 1.0}),
    "Bulb": (IncandescentBulb, {"rated_voltage_v": 12.0, "rated_power_w": 21.0}),
    "Ammeter": (Ammeter, {"shunt_resistance_ohm": 0.01, "max_display_current_a": 10.0}),
    "Voltmeter": (Voltmeter, {"input_resistance_ohm": 1.0e7, "max_display_voltage_v": 300.0}),
    "Switch": (ToggleSwitch, {"closed": False}),
}


COMPONENT_TERMINALS: dict[str, tuple[str, ...]] = {
    "Battery": ("positive", "negative"),
    "AC Generator": ("positive", "negative"),
    "Pulse Generator": ("positive", "negative"),
    "Resistor": ("positive", "negative"),
    "Thermistor": ("positive", "negative"),
    "Photoresistor": ("positive", "negative"),
    "Capacitor": ("positive", "negative"),
    "Inductor": ("positive", "negative"),
    "Wire": ("positive", "negative"),
    "Diode": ("positive", "negative"),
    "LED": ("positive", "negative"),
    "Varistor": ("positive", "negative"),
    "MOSFET": ("drain", "gate", "source"),
    "OpAmp": ("plus", "minus", "out"),
    "Fuse": ("positive", "negative"),
    "Bulb": ("positive", "negative"),
    "Ammeter": ("positive", "negative"),
    "Voltmeter": ("positive", "negative"),
    "Switch": ("positive", "negative"),
    "Ground": ("ground",),
    "Junction": ("node",),
}


def create_component(kind: str, name: str, nodes: list[str], **overrides: Any) -> Component:
    if kind in {"Ground", "Junction"}:
        raise ValueError(f"{kind} не является активным элементом и обрабатывается на этапе сборки сети.")
    cls, defaults = COMPONENT_LIBRARY[kind]
    params = defaults.copy()
    params.update(overrides)
    if kind == "Wire":
        for key in (
            "auto_length_from_path",
            "meters_per_pixel",
            "segment_length_target_m",
            "max_segments",
            "coupling_gain",
            "permittivity_scale",
            "mutual_inductance_gain",
            "thermal_coupling_gain",
        ):
            params.pop(key, None)
    return cls(name, *nodes, **params)
