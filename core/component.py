from __future__ import annotations

import copy
from typing import Any, Sequence

import numpy as np

from .physics import ROOM_TEMPERATURE_C, thermal_step


class Component:
    terminal_labels: tuple[str, ...] = ()

    def __init__(self, name: str, nodes: Sequence[str], ambient_c: float = ROOM_TEMPERATURE_C) -> None:
        self.name = name
        self.nodes = list(nodes)
        self.ambient_c = ambient_c
        self.temperature_c = ambient_c
        self.surface_temperature_c = ambient_c
        self.reference_temperature_c = ambient_c
        self.heat_capacity_j_per_k = 10.0
        self.surface_heat_capacity_j_per_k = 12.0
        self.thermal_resistance_k_per_w = 25.0
        self.junction_thermal_resistance_k_per_w = 7.5
        self.contact_thermal_resistance_k_per_w = 140.0
        self.last_terminal_voltages = np.zeros(len(self.nodes), dtype=float)
        self.last_currents = np.zeros(len(self.nodes), dtype=float)
        self.last_power_w = 0.0
        self.layout_position_px: tuple[float, float] | None = None
        self.layout_points_px: list[tuple[float, float]] = []
        self.geometry_scale_m_per_px = 0.002
        self.group_name = name
        self.thermal_coupling_gain = 1.0
        self.electromagnetic_gain = 0.0
        self.permittivity_scale = 1.0
        self.mutual_inductance_gain = 1.0
        self.freeze_temperature = False
        self._thermal_case_fraction = 0.58
        self._thermal_junction_fraction = 0.32

    def start_timestep(self, time_s: float, dt_s: float) -> None:
        del time_s, dt_s

    def currents(
        self,
        terminal_voltages: np.ndarray,
        time_s: float,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        del time_s, dt_s
        self.last_terminal_voltages = terminal_voltages.copy()

    def observe(self) -> dict[str, Any]:
        return {
            "temperature_c": float(self.temperature_c),
            "surface_temperature_c": float(self.surface_temperature_c),
            "power_w": float(self.last_power_w),
            "freeze_temperature": float(self.freeze_temperature),
        }

    def set_parameter(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def export_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    def restore_state(self, state: dict[str, Any]) -> None:
        self.__dict__.clear()
        self.__dict__.update(copy.deepcopy(state))

    def calibrate_thermal_network(self, case_fraction: float = 0.58, junction_fraction: float = 0.32) -> None:
        total_heat_capacity = max(self.heat_capacity_j_per_k, 1.0e-9)
        case_fraction = min(max(case_fraction, 0.1), 0.9)
        junction_fraction = min(max(junction_fraction, 0.05), 0.95)
        self._thermal_case_fraction = case_fraction
        self._thermal_junction_fraction = junction_fraction
        self.surface_heat_capacity_j_per_k = max(total_heat_capacity * case_fraction, 1.0e-9)
        self.heat_capacity_j_per_k = max(total_heat_capacity - self.surface_heat_capacity_j_per_k, 1.0e-9)
        self.junction_thermal_resistance_k_per_w = max(self.thermal_resistance_k_per_w * junction_fraction, 1.0e-6)

    def integrate_temperature(self, power_w: float, dt_s: float) -> None:
        self.last_power_w = float(power_w)
        if self.freeze_temperature:
            self.temperature_c = self.reference_temperature_c
            self.surface_temperature_c = self.reference_temperature_c
            return
        junction_capacity = max(self.heat_capacity_j_per_k, 1.0e-9)
        surface_capacity = max(self.surface_heat_capacity_j_per_k, 1.0e-9)
        heat_to_surface_w = (self.temperature_c - self.surface_temperature_c) / max(self.junction_thermal_resistance_k_per_w, 1.0e-9)
        self.temperature_c += (power_w - heat_to_surface_w) * dt_s / junction_capacity
        self.surface_temperature_c = thermal_step(
            self.surface_temperature_c,
            heat_to_surface_w,
            dt_s,
            surface_capacity,
            self.thermal_resistance_k_per_w,
            self.ambient_c,
        )


class TwoTerminalComponent(Component):
    terminal_labels = ("positive", "negative")

    def __init__(self, name: str, positive: str, negative: str, ambient_c: float = ROOM_TEMPERATURE_C) -> None:
        super().__init__(name, [positive, negative], ambient_c)
        self.last_voltage_v = 0.0
        self.last_current_a = 0.0
        self.history_voltage_v_1 = 0.0
        self.history_voltage_v_2 = 0.0
        self.history_current_a_1 = 0.0
        self.history_current_a_2 = 0.0

    def branch_current(self, voltage_v: float, time_s: float, dt_s: float) -> tuple[float, float]:
        raise NotImplementedError

    def currents(
        self,
        terminal_voltages: np.ndarray,
        time_s: float,
        dt_s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        voltage_v = float(terminal_voltages[0] - terminal_voltages[1])
        current_a, conductance_s = self.branch_current(voltage_v, time_s, dt_s)
        jacobian = np.array(
            [[conductance_s, -conductance_s], [-conductance_s, conductance_s]],
            dtype=float,
        )
        currents = np.array([current_a, -current_a], dtype=float)
        return currents, jacobian

    def commit(self, terminal_voltages: np.ndarray, time_s: float, dt_s: float) -> None:
        super().commit(terminal_voltages, time_s, dt_s)
        self.history_voltage_v_2 = self.history_voltage_v_1
        self.history_voltage_v_1 = self.last_voltage_v
        self.history_current_a_2 = self.history_current_a_1
        self.history_current_a_1 = self.last_current_a
        self.last_voltage_v = float(terminal_voltages[0] - terminal_voltages[1])
        self.last_current_a, _ = self.branch_current(self.last_voltage_v, time_s, dt_s)
        self.last_currents = np.array([self.last_current_a, -self.last_current_a], dtype=float)
        self.last_power_w = float(self.last_voltage_v * self.last_current_a)

    def observe(self) -> dict[str, Any]:
        data = super().observe()
        data.update(
            {
                "voltage_v": float(self.last_voltage_v),
                "current_a": float(self.last_current_a),
            }
        )
        return data
