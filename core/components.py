from __future__ import annotations

import copy
import math
from typing import Any, Callable

import numpy as np

from .audio_io import AudioBuffer, load_audio_file
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


class Photoresistor(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        dark_resistance_ohm: float = 2.0e6,
        light_resistance_ohm: float = 350.0,
        illumination_lux: float = 120.0,
        lux_reference: float = 100.0,
        gamma: float = 0.78,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.dark_resistance_ohm = max(dark_resistance_ohm, 1.0)
        self.light_resistance_ohm = max(light_resistance_ohm, 1.0e-3)
        self.illumination_lux = max(illumination_lux, 0.0)
        self.lux_reference = max(lux_reference, 1.0e-6)
        self.gamma = max(gamma, 0.05)
        self.heat_capacity_j_per_k = 3.2
        self.thermal_resistance_k_per_w = 28.0
        self.contact_thermal_resistance_k_per_w = 120.0
        self.calibrate_thermal_network(case_fraction=0.59, junction_fraction=0.27)

    def effective_resistance(self) -> float:
        illumination_ratio = max(self.illumination_lux / self.lux_reference, 0.0)
        photo_factor = 1.0 / (1.0 + illumination_ratio ** self.gamma)
        temperature_factor = 1.0 - 0.0015 * (self.temperature_c - self.reference_temperature_c)
        temperature_factor = max(temperature_factor, 0.15)
        base_resistance = self.light_resistance_ohm + (self.dark_resistance_ohm - self.light_resistance_ohm) * photo_factor
        return max(base_resistance * temperature_factor, self.light_resistance_ohm * 0.5)

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
                "illumination_lux": float(self.illumination_lux),
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


class AudioFileSource(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        file_path: str = "",
        internal_resistance_ohm: float = 0.2,
        peak_voltage_v: float = 5.0,
        dc_offset_v: float = 0.0,
        channel: str = "mono",
        normalize: bool = True,
        loop: bool = False,
        hold_last_value: bool = False,
        target_sample_rate_hz: int | None = None,
        audio_buffer: AudioBuffer | None = None,
        start_time_s: float = 0.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.file_path = str(file_path)
        self.internal_resistance_ohm = max(internal_resistance_ohm, 1.0e-6)
        self.peak_voltage_v = float(peak_voltage_v)
        self.dc_offset_v = float(dc_offset_v)
        self.channel = str(channel)
        self.normalize = bool(normalize)
        self.loop = bool(loop)
        self.hold_last_value = bool(hold_last_value)
        self.target_sample_rate_hz = None if target_sample_rate_hz in (None, 0) else int(target_sample_rate_hz)
        self.start_time_s = float(start_time_s)
        self.instantaneous_emf_v = float(dc_offset_v)
        self.last_sample_index = 0
        self.source_active = False
        self._audio_buffer: AudioBuffer | None = None
        self._signal_samples = np.zeros(0, dtype=np.float32)
        self._signal_sample_rate_hz = 44100
        self._source_duration_s = 0.0
        self._load_source(audio_buffer=audio_buffer)

    def reload_source(self, file_path: str | None = None, *, audio_buffer: AudioBuffer | None = None) -> None:
        if file_path is not None:
            self.file_path = str(file_path)
        self._load_source(audio_buffer=audio_buffer)

    def _load_source(self, *, audio_buffer: AudioBuffer | None) -> None:
        if audio_buffer is not None:
            buffer = audio_buffer.normalized_copy() if self.normalize else audio_buffer
        elif self.file_path.strip():
            buffer = load_audio_file(
                self.file_path,
                target_sample_rate_hz=self.target_sample_rate_hz,
                mono=False,
                normalize=self.normalize,
            )
        else:
            self._audio_buffer = None
            self._signal_samples = np.zeros(0, dtype=np.float32)
            self._signal_sample_rate_hz = self.target_sample_rate_hz or 44100
            self._source_duration_s = 0.0
            return

        self._audio_buffer = buffer
        self._signal_samples = self._select_channel_samples(buffer, self.channel)
        self._signal_sample_rate_hz = buffer.sample_rate_hz
        self._source_duration_s = float(self._signal_samples.size / max(self._signal_sample_rate_hz, 1))

    def _select_channel_samples(self, buffer: AudioBuffer, channel: str) -> np.ndarray:
        lowered = str(channel).strip().lower()
        if lowered in {"mono", "mix", "avg", "average"}:
            return np.ascontiguousarray(buffer.mono_mix(), dtype=np.float32)
        if lowered in {"left", "l"}:
            index = 0
        elif lowered in {"right", "r"}:
            index = 1 if buffer.channels > 1 else 0
        else:
            try:
                index = int(lowered)
            except ValueError as exc:
                raise ValueError(
                    f"Unsupported channel selector '{channel}'. Use mono, left, right, or an integer index."
                ) from exc
        if not 0 <= index < buffer.channels:
            raise ValueError(f"Channel index {index} is out of range for {buffer.channels} channels.")
        return np.ascontiguousarray(buffer.channel_samples(index), dtype=np.float32)

    def _sample_value(self, time_s: float) -> float:
        if self._signal_samples.size == 0:
            self.last_sample_index = 0
            self.source_active = False
            return 0.0

        relative_time_s = float(time_s) - self.start_time_s
        if relative_time_s < 0.0:
            self.last_sample_index = 0
            self.source_active = False
            return 0.0

        if self.loop and self._source_duration_s > 1.0e-12:
            relative_time_s = relative_time_s % self._source_duration_s
            self.source_active = True
        elif relative_time_s >= self._source_duration_s:
            self.last_sample_index = max(self._signal_samples.size - 1, 0)
            self.source_active = False
            if self.hold_last_value and self._signal_samples.size > 0:
                return float(self._signal_samples[-1])
            return 0.0
        else:
            self.source_active = True

        position = relative_time_s * self._signal_sample_rate_hz
        left_index = int(math.floor(position))
        if left_index >= self._signal_samples.size - 1:
            self.last_sample_index = max(self._signal_samples.size - 1, 0)
            return float(self._signal_samples[self.last_sample_index])

        ratio = position - left_index
        self.last_sample_index = left_index
        left = float(self._signal_samples[left_index])
        right = float(self._signal_samples[left_index + 1])
        return left + (right - left) * ratio

    def emf(self, time_s: float) -> float:
        sample_value = self._sample_value(time_s)
        return self.dc_offset_v + self.peak_voltage_v * sample_value

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del dt_s
        self.instantaneous_emf_v = self.emf(time_s)
        conductance = 1.0 / self.internal_resistance_ohm
        current = conductance * voltage_v - conductance * self.instantaneous_emf_v
        return current, conductance

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "emf_v": float(self.instantaneous_emf_v),
                "source_active": float(self.source_active),
                "playback_progress": (
                    float(self.last_sample_index / max(self._signal_samples.size - 1, 1))
                    if self._signal_samples.size > 0
                    else 0.0
                ),
                "source_duration_s": float(self._source_duration_s),
                "source_sample_rate_hz": float(self._signal_sample_rate_hz),
            }
        )
        return data

    def export_state(self) -> dict[str, Any]:
        state = copy.deepcopy(
            {
                key: value
                for key, value in self.__dict__.items()
                if key not in {"_audio_buffer", "_signal_samples"}
            }
        )
        state["_audio_buffer"] = self._audio_buffer
        state["_signal_samples"] = self._signal_samples
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        payload = copy.deepcopy(
            {
                key: value
                for key, value in state.items()
                if key not in {"_audio_buffer", "_signal_samples"}
            }
        )
        self.__dict__.clear()
        self.__dict__.update(payload)
        self._audio_buffer = state.get("_audio_buffer")
        self._signal_samples = state.get("_signal_samples", np.zeros(0, dtype=np.float32))


class AudioSink(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        input_resistance_ohm: float = 1.0e9,
        input_capacitance_f: float = 0.0,
        output_gain: float = 1.0,
        dc_block: bool = False,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.input_resistance_ohm = max(input_resistance_ohm, 1.0)
        self.input_capacitance_f = max(input_capacitance_f, 0.0)
        self.output_gain = float(output_gain)
        self.dc_block = bool(dc_block)
        self.previous_voltage_v = 0.0
        self.running_mean_v = 0.0
        self.captured_v = 0.0
        self.input_current_a = 0.0
        self.heat_capacity_j_per_k = 1.5
        self.thermal_resistance_k_per_w = 20.0
        self.contact_thermal_resistance_k_per_w = 140.0
        self.calibrate_thermal_network(case_fraction=0.72, junction_fraction=0.16)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s
        dt = max(dt_s, 1.0e-12)
        g_res = 1.0 / max(self.input_resistance_ohm, 1.0)
        g_cap = self.input_capacitance_f / dt
        i_eq = -g_cap * self.previous_voltage_v
        current = (g_res + g_cap) * voltage_v + i_eq
        return current, g_res + g_cap

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        resistive_current = self.last_voltage_v / max(self.input_resistance_ohm, 1.0)
        capacitive_current = self.last_current_a - resistive_current
        self.input_current_a = resistive_current + capacitive_current
        self.previous_voltage_v = self.last_voltage_v
        mean_alpha = dt_s / (0.02 + dt_s)
        self.running_mean_v += mean_alpha * (self.last_voltage_v - self.running_mean_v)
        base_capture = self.last_voltage_v - self.running_mean_v if self.dc_block else self.last_voltage_v
        self.captured_v = self.output_gain * base_capture
        self.integrate_temperature(abs(self.last_voltage_v * self.input_current_a), dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "reading_v": float(self.last_voltage_v),
                "captured_v": float(self.captured_v),
                "input_current_a": float(self.input_current_a),
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


class Varistor(TwoTerminalComponent):
    def __init__(
        self,
        name: str,
        positive: str,
        negative: str,
        clamp_voltage_v: float = 18.0,
        dynamic_resistance_ohm: float = 1.5,
        leakage_current_a: float = 2.0e-6,
        nonlinear_exponent: float = 6.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, positive, negative, ambient_c)
        self.clamp_voltage_v = max(clamp_voltage_v, 1.0e-3)
        self.dynamic_resistance_ohm = max(dynamic_resistance_ohm, 1.0e-6)
        self.leakage_current_a = max(leakage_current_a, 0.0)
        self.nonlinear_exponent = max(nonlinear_exponent, 1.0)
        self.clamping_active = False
        self.heat_capacity_j_per_k = 7.0
        self.thermal_resistance_k_per_w = 15.0
        self.contact_thermal_resistance_k_per_w = 88.0
        self.calibrate_thermal_network(case_fraction=0.61, junction_fraction=0.29)

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        del time_s, dt_s
        sign = 1.0 if voltage_v >= 0.0 else -1.0
        abs_voltage = abs(voltage_v)
        leakage_g = self.leakage_current_a / self.clamp_voltage_v if self.clamp_voltage_v > 0.0 else GMIN
        current = leakage_g * voltage_v
        conductance = leakage_g
        self.clamping_active = abs_voltage > self.clamp_voltage_v
        if self.clamping_active:
            excess = abs_voltage - self.clamp_voltage_v
            ratio = excess / self.clamp_voltage_v
            boost = 1.0 + ratio ** self.nonlinear_exponent
            current = sign * (self.leakage_current_a + excess * boost / self.dynamic_resistance_ohm)
            conductance = leakage_g + (
                boost + self.nonlinear_exponent * excess * max(ratio, 0.0) ** max(self.nonlinear_exponent - 1.0, 0.0) / self.clamp_voltage_v
            ) / self.dynamic_resistance_ohm
        return current, max(conductance, GMIN)

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.integrate_temperature(abs(self.last_power_w), dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "clamp_voltage_v": float(self.clamp_voltage_v),
                "clamping_active": float(self.clamping_active),
            }
        )
        return data


class MOSFET_Model(Component):
    terminal_labels = ("drain", "gate", "source")

    def __init__(
        self,
        name: str,
        drain: str,
        gate: str,
        source: str,
        threshold_v: float = 3.2,
        transconductance_a_v2: float = 1.2,
        channel_length_modulation: float = 0.02,
        gate_capacitance_f: float = 6.0e-10,
        cgs_f: float | None = None,
        cgd_f: float | None = None,
        gate_leakage_ohm: float = 5.0e9,
        subthreshold_current_a: float = 1.0e-9,
        subthreshold_swing_factor: float = 1.45,
        body_diode_saturation_current_a: float = 5.0e-11,
        body_diode_emission: float = 1.8,
        output_conductance_s: float = 2.0e-5,
        cds_f: float = 1.4e-10,
        reverse_recovery_tau_s: float = 8.0e-8,
        trap_relaxation_s: float = 2.0e-5,
        channel_width_um: float = 2500.0,
        channel_length_um: float = 1.2,
        oxide_thickness_nm: float = 35.0,
        mobility_cm2_v_s: float = 420.0,
        overlap_length_um: float = 0.28,
        relative_permittivity_ox: float = 3.9,
        body_doping_cm3: float = 2.5e16,
        rds_on_ohm: float = 0.08,
        max_current_a: float = 20.0,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, [drain, gate, source], ambient_c)
        self.threshold_v = threshold_v
        self.transconductance_a_v2 = transconductance_a_v2
        self.channel_length_modulation = channel_length_modulation
        self.channel_width_um = max(channel_width_um, 1.0e-6)
        self.channel_length_um = max(channel_length_um, 1.0e-6)
        self.oxide_thickness_nm = max(oxide_thickness_nm, 1.0e-6)
        self.mobility_cm2_v_s = max(mobility_cm2_v_s, 1.0e-6)
        self.overlap_length_um = max(overlap_length_um, 0.0)
        self.relative_permittivity_ox = max(relative_permittivity_ox, 1.0)
        self.body_doping_cm3 = max(body_doping_cm3, 1.0)
        if cgs_f is None and cgd_f is None:
            physical_gate_cap = max(self._oxide_capacitance_total_f(), gate_capacitance_f)
            self.cgs_f = physical_gate_cap * 0.68
            self.cgd_f = physical_gate_cap * 0.32
        else:
            self.cgs_f = cgs_f if cgs_f is not None else gate_capacitance_f * 0.68
            self.cgd_f = cgd_f if cgd_f is not None else gate_capacitance_f * 0.32
        self.gate_capacitance_f = self.cgs_f + self.cgd_f
        self.gate_leakage_ohm = gate_leakage_ohm
        self.subthreshold_current_a = subthreshold_current_a
        self.subthreshold_swing_factor = subthreshold_swing_factor
        self.body_diode_saturation_current_a = body_diode_saturation_current_a
        self.body_diode_emission = body_diode_emission
        self.output_conductance_s = output_conductance_s
        self.cds_f = cds_f
        self.reverse_recovery_tau_s = max(reverse_recovery_tau_s, 1.0e-12)
        self.trap_relaxation_s = max(trap_relaxation_s, 1.0e-9)
        self.rds_on_ohm = rds_on_ohm
        self.max_current_a = max_current_a
        self.off_conductance_s = 1.0e-8
        self.previous_vgs_v = 0.0
        self.previous_vgd_v = 0.0
        self.previous_vds_v = 0.0
        self.body_diode_charge_c = 0.0
        self.trap_state = 0.0
        self.inversion_charge_c = 0.0
        self.oxide_field_v_m = 0.0
        self.channel_field_v_m = 0.0
        self.last_mode = "cutoff"
        self.heat_capacity_j_per_k = 14.0
        self.thermal_resistance_k_per_w = 12.0
        self.contact_thermal_resistance_k_per_w = 75.0
        self.calibrate_thermal_network(case_fraction=0.55, junction_fraction=0.34)

    def _channel_width_m(self) -> float:
        return self.channel_width_um * 1.0e-6

    def _channel_length_m(self) -> float:
        return self.channel_length_um * 1.0e-6

    def _overlap_length_m(self) -> float:
        return self.overlap_length_um * 1.0e-6

    def _oxide_thickness_m(self) -> float:
        return self.oxide_thickness_nm * 1.0e-9

    def _mobility_m2_v_s(self) -> float:
        return self.mobility_cm2_v_s * 1.0e-4

    def _oxide_capacitance_density_f_m2(self) -> float:
        return self.relative_permittivity_ox * EPSILON_0 / self._oxide_thickness_m()

    def _gate_area_m2(self) -> float:
        return self._channel_width_m() * (self._channel_length_m() + 2.0 * self._overlap_length_m())

    def _oxide_capacitance_total_f(self) -> float:
        return self._oxide_capacitance_density_f_m2() * self._gate_area_m2()

    def _effective_beta(self) -> float:
        geometry_beta = self._mobility_m2_v_s() * self._oxide_capacitance_density_f_m2() * self._channel_width_m() / self._channel_length_m()
        temperature_scale = max(0.22, 1.0 - 0.004 * (self.temperature_c - self.reference_temperature_c))
        return max(geometry_beta * temperature_scale * max(self.transconductance_a_v2, 1.0e-6), 1.0e-9)

    def _body_factor_v(self) -> float:
        return 0.045 * math.sqrt(self.body_doping_cm3 / 1.0e16)

    def _channel_inversion_charge_c(self, vgs: float, vds: float) -> float:
        overdrive = max(vgs - self.threshold_v, 0.0)
        effective_v = max(overdrive - 0.5 * min(abs(vds), overdrive), 0.0)
        return self._oxide_capacitance_total_f() * effective_v

    def _body_diode(self, voltage_v: float) -> float:
        vt = max(thermal_voltage(self.temperature_c) * self.body_diode_emission, 1.0e-6)
        return self.body_diode_saturation_current_a * (safe_exp(voltage_v / vt) - 1.0)

    def _channel_current(self, voltages: np.ndarray) -> float:
        vd, vg, vs = voltages
        vgs = vg - vs
        vds = vd - vs
        vt = max(thermal_voltage(self.temperature_c), 1.0e-6)
        body_effect = self._body_factor_v() * (math.sqrt(max(abs(vds) + 0.2, 0.2)) - math.sqrt(0.2))
        threshold = self.threshold_v - 0.0022 * (self.temperature_c - self.reference_temperature_c) + 0.18 * self.trap_state + body_effect
        beta = self._effective_beta()
        rdson = max(self.rds_on_ohm * (1.0 + 0.006 * (self.temperature_c - self.reference_temperature_c)), 1.0e-4)
        overdrive = vgs - threshold
        turn_on = 1.0 / (1.0 + safe_exp(-overdrive / max(4.0 * vt, 0.03)))
        subthreshold = self.subthreshold_current_a * safe_exp(min(overdrive, 0.0) / max(self.subthreshold_swing_factor * vt, 0.03))
        subthreshold *= math.tanh(vds / max(6.0 * vt, 0.03))
        abs_vds = abs(vds)
        vds_sign = 1.0 if vds >= 0.0 else -1.0
        if overdrive <= 0.0:
            ids = subthreshold + self.off_conductance_s * vds
            self.last_mode = "subthreshold" if abs(subthreshold) > abs(self.off_conductance_s * vds) else "cutoff"
        else:
            if abs_vds < overdrive:
                strong_channel = beta * (overdrive * abs_vds - 0.5 * abs_vds * abs_vds)
                self.last_mode = "linear" if vds >= 0.0 else "reverse-linear"
            else:
                strong_channel = 0.5 * beta * overdrive * overdrive * (1.0 + self.channel_length_modulation * abs_vds)
                self.last_mode = "saturation" if vds >= 0.0 else "reverse-saturation"
            ids = vds_sign * strong_channel + turn_on * turn_on * vds / rdson + subthreshold
        if vds < 0.0:
            ids += -self._body_diode(-vds)
        ids += self.output_conductance_s * vds
        return smooth_limit(ids, self.max_current_a)

    def currents(
        self,
        terminal_voltages: np.ndarray,
        time_s: float,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        del time_s
        dt = max(dt_s, 1.0e-12)

        def current_fn(voltages: np.ndarray) -> np.ndarray:
            channel = self._channel_current(voltages)
            vds = float(voltages[0] - voltages[2])
            vgs = float(voltages[1] - voltages[2])
            vgd = float(voltages[1] - voltages[0])
            i_gs_cap = self.cgs_f / dt * (vgs - self.previous_vgs_v)
            i_gd_cap = self.cgd_f / dt * (vgd - self.previous_vgd_v)
            i_ds_cap = self.cds_f / dt * (vds - self.previous_vds_v)
            i_gate_source_leak = vgs / max(self.gate_leakage_ohm, 1.0)
            i_gate_drain_leak = vgd / max(self.gate_leakage_ohm * 4.0, 1.0)
            reverse_recovery = -self.body_diode_charge_c / self.reverse_recovery_tau_s
            drain_current = channel - i_gd_cap - i_gate_drain_leak + i_ds_cap + reverse_recovery
            gate_current = i_gs_cap + i_gd_cap + i_gate_source_leak + i_gate_drain_leak
            source_current = -channel - i_gs_cap - i_gate_source_leak - i_ds_cap - reverse_recovery
            return np.array([drain_current, gate_current, source_current], dtype=float)

        currents = current_fn(terminal_voltages)
        jacobian = numerical_jacobian(current_fn, terminal_voltages)
        return currents, jacobian

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.last_currents = self.currents(terminal_voltages, time_s, dt_s)[0]
        self.previous_vgs_v = float(terminal_voltages[1] - terminal_voltages[2])
        self.previous_vgd_v = float(terminal_voltages[1] - terminal_voltages[0])
        self.previous_vds_v = float(terminal_voltages[0] - terminal_voltages[2])
        self.inversion_charge_c = self._channel_inversion_charge_c(self.previous_vgs_v, self.previous_vds_v)
        self.oxide_field_v_m = abs(self.previous_vgs_v) / self._oxide_thickness_m()
        self.channel_field_v_m = abs(self.previous_vds_v) / self._channel_length_m()
        body_forward = max(self._body_diode(float(terminal_voltages[2] - terminal_voltages[0])), 0.0)
        body_alpha = dt_s / (self.reverse_recovery_tau_s + dt_s)
        self.body_diode_charge_c += body_alpha * (self.reverse_recovery_tau_s * body_forward - self.body_diode_charge_c)
        if self.previous_vds_v > 0.0:
            self.body_diode_charge_c *= math.exp(-dt_s / self.reverse_recovery_tau_s)
        trap_target = math.tanh(max(self.previous_vgs_v - self.threshold_v, 0.0) / 4.0)
        self.trap_state += dt_s / (self.trap_relaxation_s + dt_s) * (trap_target - self.trap_state)
        vds = float(terminal_voltages[0] - terminal_voltages[2])
        gate_power = abs((terminal_voltages[1] - terminal_voltages[2]) * self.last_currents[1])
        self.integrate_temperature(abs(vds * self.last_currents[0]) + gate_power, dt_s)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "drain_current_a": float(self.last_currents[0]),
                "gate_current_a": float(self.last_currents[1]),
                "source_current_a": float(self.last_currents[2]),
                "mode": self.last_mode,
                "cgs_f": float(self.cgs_f),
                "cgd_f": float(self.cgd_f),
                "cds_f": float(self.cds_f),
                "trap_state": float(self.trap_state),
                "oxide_capacitance_f": float(self._oxide_capacitance_total_f()),
                "inversion_charge_c": float(self.inversion_charge_c),
                "oxide_field_v_m": float(self.oxide_field_v_m),
                "channel_field_v_m": float(self.channel_field_v_m),
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


class SPDTSwitch(Component):
    terminal_labels = ("common", "throw_a", "throw_b")

    def __init__(
        self,
        name: str,
        common: str,
        throw_a: str,
        throw_b: str,
        position_b: bool = False,
        on_resistance_ohm: float = 0.01,
        off_resistance_ohm: float = 1.0e9,
        ambient_c: float = 25.0,
    ) -> None:
        super().__init__(name, [common, throw_a, throw_b], ambient_c)
        self.position_b = bool(position_b)
        self.on_resistance_ohm = max(on_resistance_ohm, 1.0e-9)
        self.off_resistance_ohm = max(off_resistance_ohm, 1.0e-9)

    def toggle(self) -> None:
        self.position_b = not self.position_b

    def currents(
        self,
        terminal_voltages: np.ndarray,
        time_s: float,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        del time_s, dt_s
        g_on = 1.0 / self.on_resistance_ohm
        g_off = 1.0 / self.off_resistance_ohm
        g_a = g_off if self.position_b else g_on
        g_b = g_on if self.position_b else g_off
        vc, va, vb = (float(value) for value in terminal_voltages)
        currents = np.array(
            [
                g_a * (vc - va) + g_b * (vc - vb),
                g_a * (va - vc),
                g_b * (vb - vc),
            ],
            dtype=float,
        )
        jacobian = np.array(
            [
                [g_a + g_b, -g_a, -g_b],
                [-g_a, g_a, 0.0],
                [-g_b, 0.0, g_b],
            ],
            dtype=float,
        )
        return currents, jacobian

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update({"position_b": float(self.position_b)})
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
    "Audio File Source": (
        AudioFileSource,
        {
            "file_path": "",
            "internal_resistance_ohm": 0.2,
            "peak_voltage_v": 5.0,
            "dc_offset_v": 0.0,
            "channel": "mono",
            "normalize": True,
            "loop": False,
            "hold_last_value": False,
            "target_sample_rate_hz": 22050,
            "start_time_s": 0.0,
        },
    ),
    "Audio Sink": (
        AudioSink,
        {
            "input_resistance_ohm": 1.0e9,
            "input_capacitance_f": 0.0,
            "output_gain": 1.0,
            "dc_block": False,
        },
    ),
    "Resistor": (RealResistor, {"resistance_ohm": 220.0}),
    "Thermistor": (Thermistor, {"resistance_at_25c_ohm": 10000.0, "beta_k": 3950.0}),
    "Photoresistor": (
        Photoresistor,
        {
            "dark_resistance_ohm": 2.0e6,
            "light_resistance_ohm": 350.0,
            "illumination_lux": 120.0,
            "lux_reference": 100.0,
            "gamma": 0.78,
        },
    ),
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
    "Varistor": (Varistor, {"clamp_voltage_v": 18.0, "dynamic_resistance_ohm": 1.5, "leakage_current_a": 2.0e-6, "nonlinear_exponent": 6.0}),
    "MOSFET": (
        MOSFET_Model,
        {
            "threshold_v": 3.2,
            "rds_on_ohm": 0.08,
            "cgs_f": 4.2e-10,
            "cgd_f": 1.8e-10,
            "cds_f": 1.4e-10,
            "reverse_recovery_tau_s": 8.0e-8,
            "trap_relaxation_s": 2.0e-5,
            "channel_width_um": 2500.0,
            "channel_length_um": 1.2,
            "oxide_thickness_nm": 35.0,
            "mobility_cm2_v_s": 420.0,
            "overlap_length_um": 0.28,
            "body_doping_cm3": 2.5e16,
            "max_current_a": 20.0,
        },
    ),
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
    "SPDT Switch": (SPDTSwitch, {"position_b": False, "on_resistance_ohm": 0.01, "off_resistance_ohm": 1.0e9}),
}


COMPONENT_TERMINALS: dict[str, tuple[str, ...]] = {
    "Battery": ("positive", "negative"),
    "AC Generator": ("positive", "negative"),
    "Pulse Generator": ("positive", "negative"),
    "Audio File Source": ("positive", "negative"),
    "Audio Sink": ("positive", "negative"),
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
    "SPDT Switch": ("common", "throw_a", "throw_b"),
    "Ground": ("ground",),
    "Junction": ("node",),
}


def create_component(kind: str, name: str, nodes: list[str], **overrides: Any) -> Component:
    if kind in {"Ground", "Junction"}:
        raise ValueError(f"{kind} не является активным элементом и обрабатывается на этапе сборки сети.")
    cls, defaults = COMPONENT_LIBRARY[kind]
    params = defaults.copy()
    params.update(overrides)
    post_init_overrides: dict[str, Any] = {}
    thermal_override_keys = (
        "heat_capacity_j_per_k",
        "thermal_resistance_k_per_w",
        "contact_thermal_resistance_k_per_w",
    )
    for key in ("freeze_temperature", *thermal_override_keys):
        if key in params:
            post_init_overrides[key] = params.pop(key)
    thermal_case_fraction = params.pop("thermal_case_fraction", None)
    thermal_junction_fraction = params.pop("thermal_junction_fraction", None)
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
    instance = cls(name, *nodes, **params)
    for key, value in post_init_overrides.items():
        setattr(instance, key, value)
    if (
        any(key in post_init_overrides for key in thermal_override_keys)
        or thermal_case_fraction is not None
        or thermal_junction_fraction is not None
    ):
        case_fraction = float(
            thermal_case_fraction
            if thermal_case_fraction is not None
            else getattr(instance, "_thermal_case_fraction", 0.58)
        )
        junction_fraction = float(
            thermal_junction_fraction
            if thermal_junction_fraction is not None
            else getattr(instance, "_thermal_junction_fraction", 0.32)
        )
        instance.calibrate_thermal_network(case_fraction=case_fraction, junction_fraction=junction_fraction)
    return instance
