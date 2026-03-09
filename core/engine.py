from __future__ import annotations

import copy
import importlib.util
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import root

from .component import Component, TwoTerminalComponent
from .physics import EPSILON_0, GMIN, MU_0


GROUND_NAMES = {"0", "gnd", "GND", "ground", "GROUND"}


@dataclass
class SimulationResult:
    time_s: np.ndarray
    node_voltages: dict[str, np.ndarray]
    component_observables: dict[str, dict[str, np.ndarray]]
    metadata: dict[str, Any]

    def final_node_voltage(self, node: str) -> float:
        return float(self.node_voltages[node][-1])

    def final_observable(self, component: str, key: str) -> float:
        return float(self.component_observables[component][key][-1])


@dataclass(slots=True)
class ElectromagneticLink:
    left: int
    right: int
    mutual_capacitance_f: float
    mutual_inductance_h: float


class Circuit:
    def __init__(self, name: str = "Untitled Circuit") -> None:
        self.name = name
        self.components: list[Component] = []
        self.nodes: set[str] = {"0"}

    def add(self, component: Component) -> Component:
        self.components.append(component)
        for node in component.nodes:
            if node not in GROUND_NAMES:
                self.nodes.add(node)
        return component

    def node_order(self) -> list[str]:
        return sorted(node for node in self.nodes if node not in GROUND_NAMES)

    def _node_index(self, node: str, order: list[str]) -> int | None:
        if node in GROUND_NAMES:
            return None
        return order.index(node)

    def _terminal_voltages(self, solution: np.ndarray, order: list[str], component: Component) -> np.ndarray:
        values = []
        for node in component.nodes:
            if node in GROUND_NAMES:
                values.append(0.0)
            else:
                values.append(float(solution[order.index(node)]))
        return np.array(values, dtype=float)

    def _component_group_name(self, component: Component) -> str:
        return str(getattr(component, "group_name", component.name))

    def _branch_profile(self, component: Component) -> dict[str, Any] | None:
        if not isinstance(component, TwoTerminalComponent):
            return None
        points = getattr(component, "layout_points_px", [])
        if len(points) < 2 or float(getattr(component, "electromagnetic_gain", 0.0)) <= 0.0:
            return None
        start = (float(points[0][0]), float(points[0][1]))
        end = (float(points[-1][0]), float(points[-1][1]))
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_px = math.hypot(dx, dy)
        if length_px <= 1.0e-9:
            return None
        scale = max(float(getattr(component, "geometry_scale_m_per_px", 0.002)), 1.0e-9)
        return {
            "start": start,
            "end": end,
            "center": ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5),
            "direction": (dx / length_px, dy / length_px),
            "length_m": max(length_px * scale, 1.0e-9),
            "scale_m_per_px": scale,
            "electromagnetic_gain": float(getattr(component, "electromagnetic_gain", 0.0)),
            "permittivity_scale": float(getattr(component, "permittivity_scale", 1.0)),
            "mutual_inductance_gain": float(getattr(component, "mutual_inductance_gain", 1.0)),
        }

    def _electromagnetic_links(self) -> list[ElectromagneticLink]:
        candidates = [(index, self._branch_profile(component)) for index, component in enumerate(self.components)]
        candidates = [(index, profile) for index, profile in candidates if profile is not None]
        links: list[ElectromagneticLink] = []
        for left in range(len(candidates)):
            left_index, left_profile = candidates[left]
            assert left_profile is not None
            for right in range(left + 1, len(candidates)):
                right_index, right_profile = candidates[right]
                assert right_profile is not None
                if self._component_group_name(self.components[left_index]) == self._component_group_name(self.components[right_index]):
                    continue
                dx = right_profile["center"][0] - left_profile["center"][0]
                dy = right_profile["center"][1] - left_profile["center"][1]
                distance_px = math.hypot(dx, dy)
                distance_m = max(distance_px * 0.5 * (left_profile["scale_m_per_px"] + right_profile["scale_m_per_px"]), 2.5e-4)
                if distance_m > 0.08:
                    continue
                orientation = abs(
                    left_profile["direction"][0] * right_profile["direction"][0]
                    + left_profile["direction"][1] * right_profile["direction"][1]
                )
                if orientation < 0.25:
                    continue
                overlap_length = min(left_profile["length_m"], right_profile["length_m"])
                coupling_gain = math.sqrt(left_profile["electromagnetic_gain"] * right_profile["electromagnetic_gain"])
                shielding = 1.0 / (1.0 + distance_m / max(overlap_length, 1.0e-6))
                mutual_capacitance_f = (
                    EPSILON_0
                    * 0.18
                    * coupling_gain
                    * 0.5
                    * (left_profile["permittivity_scale"] + right_profile["permittivity_scale"])
                    * orientation
                    * overlap_length
                    / distance_m
                    * shielding
                )
                mutual_inductance_h = (
                    MU_0
                    / (2.0 * math.pi)
                    * 0.06
                    * coupling_gain
                    * 0.5
                    * (left_profile["mutual_inductance_gain"] + right_profile["mutual_inductance_gain"])
                    * orientation
                    * overlap_length
                    * math.log1p(overlap_length / distance_m)
                    * shielding
                )
                if mutual_capacitance_f < 1.0e-15 and mutual_inductance_h < 1.0e-12:
                    continue
                links.append(ElectromagneticLink(left_index, right_index, mutual_capacitance_f, mutual_inductance_h))
        return links

    def _stamp_differential_pair(
        self,
        residual: np.ndarray,
        jacobian: np.ndarray,
        index_map: dict[str, int],
        left: TwoTerminalComponent,
        right: TwoTerminalComponent,
        conductance_s: float,
        current_a: float,
    ) -> None:
        derivatives = {
            left.nodes[0]: conductance_s,
            left.nodes[1]: -conductance_s,
            right.nodes[0]: -conductance_s,
            right.nodes[1]: conductance_s,
        }
        row_signs = (
            (left.nodes[0], 1.0),
            (left.nodes[1], -1.0),
            (right.nodes[0], -1.0),
            (right.nodes[1], 1.0),
        )
        for node, sign in row_signs:
            row_index = index_map.get(node)
            if row_index is None:
                continue
            residual[row_index] += sign * current_a
            for var_node, derivative in derivatives.items():
                col_index = index_map.get(var_node)
                if col_index is None:
                    continue
                jacobian[row_index, col_index] += sign * derivative

    def _residual_and_jacobian(
        self,
        solution: np.ndarray,
        order: list[str],
        time_s: float,
        dt_s: float,
        electromagnetic_links: list[ElectromagneticLink] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        size = len(order)
        residual = np.zeros(size, dtype=float)
        jacobian = np.eye(size, dtype=float) * GMIN
        index_map = {node: idx for idx, node in enumerate(order)}
        for component in self.components:
            voltages = []
            for node in component.nodes:
                voltages.append(0.0 if node in GROUND_NAMES else float(solution[index_map[node]]))
            terminal_voltages = np.array(voltages, dtype=float)
            currents, local_jacobian = component.currents(terminal_voltages, time_s, dt_s)
            for row_local, node_row in enumerate(component.nodes):
                row_global = index_map.get(node_row)
                if row_global is None:
                    continue
                residual[row_global] += currents[row_local]
                for col_local, node_col in enumerate(component.nodes):
                    col_global = index_map.get(node_col)
                    if col_global is None:
                        continue
                    jacobian[row_global, col_global] += local_jacobian[row_local, col_local]
        if electromagnetic_links:
            dt = max(dt_s, 1.0e-12)
            for link in electromagnetic_links:
                left = self.components[link.left]
                right = self.components[link.right]
                if not isinstance(left, TwoTerminalComponent) or not isinstance(right, TwoTerminalComponent):
                    continue
                mutual_g = link.mutual_capacitance_f / dt
                left_voltage = (0.0 if left.nodes[0] in GROUND_NAMES else float(solution[index_map[left.nodes[0]]])) - (
                    0.0 if left.nodes[1] in GROUND_NAMES else float(solution[index_map[left.nodes[1]]])
                )
                right_voltage = (0.0 if right.nodes[0] in GROUND_NAMES else float(solution[index_map[right.nodes[0]]])) - (
                    0.0 if right.nodes[1] in GROUND_NAMES else float(solution[index_map[right.nodes[1]]])
                )
                voltage_history = (left.history_voltage_v_1 - right.history_voltage_v_1)
                history_current = -mutual_g * voltage_history
                delta_i_left = (left.history_current_a_1 - left.history_current_a_2) / dt
                delta_i_right = (right.history_current_a_1 - right.history_current_a_2) / dt
                base_resistance_left = max(abs(getattr(left, "base_resistance", lambda: 0.1)()), 1.0e-4)
                base_resistance_right = max(abs(getattr(right, "base_resistance", lambda: 0.1)()), 1.0e-4)
                induced_current = link.mutual_inductance_h * (delta_i_right - delta_i_left) / (base_resistance_left + base_resistance_right)
                coupled_current = mutual_g * (left_voltage - right_voltage) + history_current + induced_current
                self._stamp_differential_pair(residual, jacobian, index_map, left, right, mutual_g, coupled_current)
        return residual, jacobian

    def _solve_step(
        self,
        guess: np.ndarray,
        order: list[str],
        time_s: float,
        dt_s: float,
        max_iters: int,
        tol: float,
        electromagnetic_links: list[ElectromagneticLink] | None = None,
    ) -> np.ndarray:
        solution = guess.copy()
        for component in self.components:
            component.start_timestep(time_s, dt_s)
        converged = False
        for _ in range(max_iters):
            residual, jacobian = self._residual_and_jacobian(solution, order, time_s, dt_s, electromagnetic_links)
            if np.linalg.norm(residual, ord=np.inf) < tol:
                converged = True
                break
            try:
                step = np.linalg.solve(jacobian, -residual)
            except np.linalg.LinAlgError:
                step = np.linalg.lstsq(jacobian, -residual, rcond=None)[0]
            step = np.clip(step, -5.0, 5.0)
            solution += 0.65 * step
            if np.linalg.norm(step, ord=np.inf) < tol:
                converged = True
                break
        if not converged:
            def fun(values: np.ndarray) -> np.ndarray:
                return self._residual_and_jacobian(values, order, time_s, dt_s, electromagnetic_links)[0]

            def jac(values: np.ndarray) -> np.ndarray:
                return self._residual_and_jacobian(values, order, time_s, dt_s, electromagnetic_links)[1]

            outcome = root(fun, solution, jac=jac, method="hybr")
            if not outcome.success:
                raise RuntimeError(f"Solver failed at t={time_s:.6f}s: {outcome.message}")
            solution = outcome.x.astype(float)
        return solution

    def _thermal_links(self) -> list[tuple[int, int, float]]:
        node_to_components: dict[str, list[int]] = defaultdict(list)
        for index, component in enumerate(self.components):
            for node in set(component.nodes):
                if node in GROUND_NAMES:
                    continue
                node_to_components[node].append(index)

        pair_strength: dict[tuple[int, int], float] = {}
        for indices in node_to_components.values():
            for left in range(len(indices)):
                for right in range(left + 1, len(indices)):
                    pair = tuple(sorted((indices[left], indices[right])))
                    pair_strength[pair] = pair_strength.get(pair, 0.0) + 1.0
        for left in range(len(self.components)):
            left_component = self.components[left]
            left_position = getattr(left_component, "layout_position_px", None)
            if left_position is None:
                continue
            for right in range(left + 1, len(self.components)):
                right_component = self.components[right]
                right_position = getattr(right_component, "layout_position_px", None)
                if right_position is None:
                    continue
                dx = float(right_position[0]) - float(left_position[0])
                dy = float(right_position[1]) - float(left_position[1])
                scale = 0.5 * (
                    float(getattr(left_component, "geometry_scale_m_per_px", 0.002))
                    + float(getattr(right_component, "geometry_scale_m_per_px", 0.002))
                )
                distance_m = math.hypot(dx, dy) * max(scale, 1.0e-9)
                if distance_m > 0.18:
                    continue
                coupling_gain = math.sqrt(
                    max(float(getattr(left_component, "thermal_coupling_gain", 1.0)), 0.0)
                    * max(float(getattr(right_component, "thermal_coupling_gain", 1.0)), 0.0)
                )
                strength = 0.28 * coupling_gain / (1.0 + distance_m / 0.015)
                if strength <= 0.0:
                    continue
                pair = (left, right)
                pair_strength[pair] = pair_strength.get(pair, 0.0) + strength
        return [(left, right, strength) for (left, right), strength in pair_strength.items()]

    def _apply_thermal_coupling(self, dt_s: float, links: list[tuple[int, int, float]]) -> None:
        if not links:
            return
        delta_temperatures = [0.0 for _ in self.components]
        for left, right, strength in links:
            component_left = self.components[left]
            component_right = self.components[right]
            link_resistance = 0.5 * (
                component_left.contact_thermal_resistance_k_per_w + component_right.contact_thermal_resistance_k_per_w
            ) / max(strength, 1.0e-6)
            heat_flow_w = (component_right.surface_temperature_c - component_left.surface_temperature_c) / max(link_resistance, 1.0e-6)
            delta_temperatures[left] += heat_flow_w * dt_s / max(component_left.surface_heat_capacity_j_per_k, 1.0e-9)
            delta_temperatures[right] -= heat_flow_w * dt_s / max(component_right.surface_heat_capacity_j_per_k, 1.0e-9)
        for index, component in enumerate(self.components):
            component.surface_temperature_c += delta_temperatures[index]

    def _reduce_group_observable(self, components: list[Component], key: str, values: list[float]) -> float:
        if len(values) == 1:
            return values[0]
        if all(isinstance(component, TwoTerminalComponent) and self._component_group_name(component) == self._component_group_name(components[0]) for component in components):
            if key in {"power_w", "voltage_v", "resistance_ohm", "inductance_h", "length_m", "propagation_delay_s", "contact_resistance_ohm"}:
                return float(sum(values))
            if key in {"temperature_c", "surface_temperature_c"}:
                return float(max(values))
            if key in {"current_a"}:
                return float(sum(values) / len(values))
        return float(sum(values) / len(values))

    def _supports_adaptive_retry(self) -> bool:
        for component in self.components:
            if hasattr(component, "rise_time_s") or hasattr(component, "fall_time_s"):
                return True
            if component.__class__.__name__ in {"PulseGenerator", "RealACGenerator", "SchockleyDiode", "LED_ImageActive", "Varistor", "MOSFET_Model"}:
                return True
        return False

    def _snapshot_component_states(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(component.__dict__) for component in self.components]

    def _restore_component_states(self, states: list[dict[str, Any]]) -> None:
        for component, state in zip(self.components, states, strict=False):
            component.__dict__.clear()
            component.__dict__.update(copy.deepcopy(state))

    def _simulate_once(
        self,
        duration_s: float,
        dt_s: float,
        max_iters: int,
        tol: float,
    ) -> SimulationResult:
        order = self.node_order()
        steps = max(1, int(round(duration_s / dt_s)))
        time_points = np.linspace(0.0, steps * dt_s, steps + 1)
        solution = np.zeros(len(order), dtype=float)
        thermal_links = self._thermal_links()
        electromagnetic_links = self._electromagnetic_links()
        node_history = {node: np.zeros(time_points.size, dtype=float) for node in order}
        grouped_components: dict[str, list[Component]] = defaultdict(list)
        for component in self.components:
            grouped_components[self._component_group_name(component)].append(component)
        component_history: dict[str, defaultdict[str, list[float]]] = {
            group_name: defaultdict(list) for group_name in grouped_components
        }
        adaptive_substeps_used = False

        for index, time_s in enumerate(time_points):
            solution, adaptive_substeps = self._advance_step(
                solution,
                order,
                time_s,
                dt_s,
                max_iters=max_iters,
                tol=tol,
                electromagnetic_links=electromagnetic_links,
                thermal_links=thermal_links,
            )
            adaptive_substeps_used = adaptive_substeps_used or adaptive_substeps
            for node_idx, node in enumerate(order):
                node_history[node][index] = solution[node_idx]
            grouped_observables: dict[str, defaultdict[str, list[float]]] = {
                group_name: defaultdict(list) for group_name in grouped_components
            }
            for component in self.components:
                group_name = self._component_group_name(component)
                for key, value in component.observe().items():
                    if isinstance(value, str):
                        continue
                    grouped_observables[group_name][key].append(float(value))
            for group_name, observables in grouped_observables.items():
                group_components = grouped_components[group_name]
                for key, values in observables.items():
                    component_history[group_name][key].append(self._reduce_group_observable(group_components, key, values))

        finalized_component_history = {
            name: {key: np.array(values, dtype=float) for key, values in items.items()}
            for name, items in component_history.items()
        }
        metadata = {
            "name": self.name,
            "duration_s": duration_s,
            "dt_s": dt_s,
            "nodes": order,
            "components": list(grouped_components),
            "electromagnetic_links": len(electromagnetic_links),
            "adaptive_substeps": adaptive_substeps_used,
        }
        return SimulationResult(time_s=time_points, node_voltages=node_history, component_observables=finalized_component_history, metadata=metadata)

    def _advance_step(
        self,
        solution: np.ndarray,
        order: list[str],
        time_s: float,
        dt_s: float,
        *,
        max_iters: int,
        tol: float,
        electromagnetic_links: list[ElectromagneticLink] | None,
        thermal_links: list[tuple[int, int, float]],
        depth: int = 0,
        max_depth: int = 5,
        min_dt_s: float = 1.0e-5,
    ) -> tuple[np.ndarray, bool]:
        saved_states = self._snapshot_component_states()
        base_solution = solution.copy()
        try:
            advanced_solution = self._solve_step(
                solution,
                order,
                time_s,
                dt_s,
                max_iters=max_iters,
                tol=tol,
                electromagnetic_links=electromagnetic_links,
            )
            for component in self.components:
                voltages = self._terminal_voltages(advanced_solution, order, component)
                component.commit(voltages, time_s, dt_s)
            self._apply_thermal_coupling(dt_s, thermal_links)
            return advanced_solution, depth > 0
        except RuntimeError:
            self._restore_component_states(saved_states)
            if depth >= max_depth or dt_s <= min_dt_s or time_s - 0.5 * dt_s < -1.0e-12:
                raise
            midpoint_time_s = time_s - 0.5 * dt_s
            midpoint_solution, _ = self._advance_step(
                base_solution.copy(),
                order,
                midpoint_time_s,
                dt_s * 0.5,
                max_iters=max_iters + 10,
                tol=tol,
                electromagnetic_links=electromagnetic_links,
                thermal_links=thermal_links,
                depth=depth + 1,
                max_depth=max_depth,
                min_dt_s=min_dt_s,
            )
            try:
                final_solution, _ = self._advance_step(
                    midpoint_solution,
                    order,
                    time_s,
                    dt_s * 0.5,
                    max_iters=max_iters + 10,
                    tol=tol,
                    electromagnetic_links=electromagnetic_links,
                    thermal_links=thermal_links,
                    depth=depth + 1,
                    max_depth=max_depth,
                    min_dt_s=min_dt_s,
                )
            except RuntimeError:
                self._restore_component_states(saved_states)
                raise
            return final_solution, True

    def simulate(
        self,
        duration_s: float,
        dt_s: float,
        max_iters: int = 40,
        tol: float = 1.0e-6,
    ) -> SimulationResult:
        retry_factors = [1.0]
        if self._supports_adaptive_retry():
            retry_factors.extend([0.5, 0.25, 0.125])
        base_states = self._snapshot_component_states()
        last_error: Exception | None = None
        for attempt_index, factor in enumerate(retry_factors):
            attempt_dt = dt_s * factor
            try:
                self._restore_component_states(base_states)
                result = self._simulate_once(duration_s, attempt_dt, max_iters=max_iters + attempt_index * 20, tol=tol)
                if attempt_index > 0:
                    result.metadata["requested_dt_s"] = dt_s
                    result.metadata["adaptive_retry"] = True
                    result.metadata["retry_attempt"] = attempt_index
                return result
            except RuntimeError as exc:
                last_error = exc
                continue
        assert last_error is not None
        raise last_error


def load_example_module(path_or_module: str) -> Any:
    candidate = Path(path_or_module)
    if candidate.exists():
        spec = importlib.util.spec_from_file_location(candidate.stem, candidate)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load example from {candidate}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return __import__(path_or_module, fromlist=["*"])
