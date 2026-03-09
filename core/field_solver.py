from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from .component import Component, TwoTerminalComponent
from .engine import Circuit, GROUND_NAMES, SimulationResult
from .physics import EPSILON_0, MU_0


@dataclass(slots=True)
class FieldSnapshot:
    bounds_px: tuple[float, float, float, float]
    x_grid_px: np.ndarray
    y_grid_px: np.ndarray
    potential_v: np.ndarray
    electric_field_v_m: np.ndarray
    magnetic_flux_density_t: np.ndarray
    conductor_mask: np.ndarray
    metadata: dict[str, Any]

    def layer(self, name: str) -> np.ndarray:
        if name == "potential":
            return self.potential_v
        if name in {"electric", "e"}:
            return self.electric_field_v_m
        if name in {"magnetic", "b"}:
            return self.magnetic_flux_density_t
        raise ValueError(f"Unknown field layer: {name}")

    def to_image(self, layer: str = "potential", scale: int = 3) -> Image.Image:
        values = np.array(self.layer(layer), dtype=float)
        return _layer_to_image(values, self.conductor_mask, layer=layer, scale=scale)


@dataclass(slots=True)
class FieldWaveSequence:
    bounds_px: tuple[float, float, float, float]
    x_grid_px: np.ndarray
    y_grid_px: np.ndarray
    potential_v: np.ndarray
    electric_frames_v_m: np.ndarray
    magnetic_frames_t: np.ndarray
    conductor_mask: np.ndarray
    metadata: dict[str, Any]

    def frame_count(self) -> int:
        return int(self.electric_frames_v_m.shape[0])

    def layer_frame(self, name: str, frame_index: int) -> np.ndarray:
        index = max(0, min(self.frame_count() - 1, int(frame_index)))
        if name == "potential":
            return self.potential_v
        if name in {"electric", "e"}:
            return self.electric_frames_v_m[index]
        if name in {"magnetic", "b"}:
            return self.magnetic_frames_t[index]
        raise ValueError(f"Unknown field layer: {name}")

    def to_image(self, layer: str = "electric", frame_index: int = 0, scale: int = 3) -> Image.Image:
        values = np.array(self.layer_frame(layer, frame_index), dtype=float)
        return _layer_to_image(values, self.conductor_mask, layer=layer, scale=scale)


def _layer_to_image(values: np.ndarray, conductor_mask: np.ndarray, *, layer: str, scale: int) -> Image.Image:
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            finite = np.array([0.0], dtype=float)
        if layer == "potential":
            span = max(np.percentile(np.abs(finite), 96), 1.0e-9)
            normalized = np.clip(0.5 + 0.5 * values / span, 0.0, 1.0)
            image = _gradient_map(normalized, ((0.0, (18, 58, 94)), (0.5, (245, 242, 232)), (1.0, (164, 28, 47))))
        elif layer in {"electric", "e"}:
            scale_ref = max(np.percentile(finite, 97), 1.0e-9)
            normalized = np.clip(np.log1p(values / scale_ref * 4.0) / math.log1p(4.0), 0.0, 1.0)
            image = _gradient_map(normalized, ((0.0, (11, 30, 53)), (0.45, (43, 108, 176)), (1.0, (250, 204, 21))))
        else:
            scale_ref = max(np.percentile(finite, 97), 1.0e-12)
            normalized = np.clip(np.log1p(values / scale_ref * 5.0) / math.log1p(5.0), 0.0, 1.0)
            image = _gradient_map(normalized, ((0.0, (18, 18, 18)), (0.45, (153, 27, 27)), (1.0, (251, 191, 36))))

        image[conductor_mask] = np.array([255, 255, 255], dtype=np.uint8)
        pil = Image.fromarray(image, mode="RGB")
        if scale > 1:
            pil = pil.resize((pil.width * scale, pil.height * scale), Image.Resampling.NEAREST)
        return pil


def _gradient_map(values: np.ndarray, stops: tuple[tuple[float, tuple[int, int, int]], ...]) -> np.ndarray:
    clipped = np.clip(values, 0.0, 1.0)
    result = np.zeros(clipped.shape + (3,), dtype=np.uint8)
    for index in range(len(stops) - 1):
        left_pos, left_color = stops[index]
        right_pos, right_color = stops[index + 1]
        mask = (clipped >= left_pos) & (clipped <= right_pos if index == len(stops) - 2 else clipped < right_pos)
        if not np.any(mask):
            continue
        ratio = (clipped[mask] - left_pos) / max(right_pos - left_pos, 1.0e-9)
        color = np.empty((ratio.size, 3), dtype=np.uint8)
        for channel in range(3):
            color[:, channel] = np.clip(
                left_color[channel] + (right_color[channel] - left_color[channel]) * ratio,
                0,
                255,
            ).astype(np.uint8)
        result[mask] = color
    return result


def _node_voltage(result: SimulationResult, node: str) -> float:
    if node in GROUND_NAMES:
        return 0.0
    values = result.node_voltages.get(node)
    if values is None or len(values) == 0:
        return 0.0
    return float(values[-1])


def _mark_disc(mask: np.ndarray, values: np.ndarray, x_index: int, y_index: int, radius: int, potential_v: float) -> None:
    height, width = mask.shape
    x0 = max(0, x_index - radius)
    x1 = min(width, x_index + radius + 1)
    y0 = max(0, y_index - radius)
    y1 = min(height, y_index + radius + 1)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    local_mask = (xx - x_index) ** 2 + (yy - y_index) ** 2 <= radius * radius
    mask[y0:y1, x0:x1][local_mask] = True
    values[y0:y1, x0:x1][local_mask] = potential_v


def _sample_segment(start: tuple[float, float], end: tuple[float, float], count: int) -> list[tuple[float, float, float]]:
    points = []
    for index in range(count + 1):
        ratio = index / max(count, 1)
        points.append(
            (
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio,
                ratio,
            )
        )
    return points


def solve_quasi_static_field(
    circuit: Circuit,
    result: SimulationResult,
    *,
    grid_width: int = 220,
    grid_height: int = 160,
    padding_px: float = 90.0,
    iterations: int = 420,
    relaxation: float = 0.92,
    conductor_radius_px: float = 7.0,
) -> FieldSnapshot:
    points: list[tuple[float, float]] = []
    for component in circuit.components:
        for point in getattr(component, "layout_points_px", []):
            points.append((float(point[0]), float(point[1])))
        if getattr(component, "layout_position_px", None) is not None:
            position = getattr(component, "layout_position_px")
            points.append((float(position[0]), float(position[1])))
    if not points:
        points = [(0.0, 0.0), (400.0, 300.0)]

    min_x = min(point[0] for point in points) - padding_px
    max_x = max(point[0] for point in points) + padding_px
    min_y = min(point[1] for point in points) - padding_px
    max_y = max(point[1] for point in points) + padding_px

    x_grid = np.linspace(min_x, max_x, grid_width, dtype=float)
    y_grid = np.linspace(min_y, max_y, grid_height, dtype=float)
    xx_px, yy_px = np.meshgrid(x_grid, y_grid)
    conductor_mask = np.zeros((grid_height, grid_width), dtype=bool)
    fixed_values = np.zeros((grid_height, grid_width), dtype=float)
    scale_m_per_px = float(
        np.median([getattr(component, "geometry_scale_m_per_px", 0.002) for component in circuit.components]) if circuit.components else 0.002
    )
    conductor_radius_cells = max(1, int(round(conductor_radius_px / max((max_x - min_x) / max(grid_width - 1, 1), 1.0))))

    current_segments: list[tuple[tuple[float, float], tuple[float, float], float]] = []

    def map_to_grid(point: tuple[float, float]) -> tuple[int, int]:
        x_index = int(round((point[0] - min_x) / max(max_x - min_x, 1.0e-9) * (grid_width - 1)))
        y_index = int(round((point[1] - min_y) / max(max_y - min_y, 1.0e-9) * (grid_height - 1)))
        return max(0, min(grid_width - 1, x_index)), max(0, min(grid_height - 1, y_index))

    for component in circuit.components:
        layout_points = [(float(point[0]), float(point[1])) for point in getattr(component, "layout_points_px", [])]
        if isinstance(component, TwoTerminalComponent) and len(layout_points) >= 2:
            start = layout_points[0]
            end = layout_points[-1]
            start_v = _node_voltage(result, component.nodes[0])
            end_v = _node_voltage(result, component.nodes[1])
            sample_count = max(8, int(round(math.hypot(end[0] - start[0], end[1] - start[1]) / 6.0)))
            for point_x, point_y, ratio in _sample_segment(start, end, sample_count):
                ix, iy = map_to_grid((point_x, point_y))
                potential_v = start_v + (end_v - start_v) * ratio
                _mark_disc(conductor_mask, fixed_values, ix, iy, conductor_radius_cells, potential_v)
            current_segments.append((start, end, float(component.last_current_a)))
            continue

        if len(layout_points) == len(component.nodes):
            for node, point in zip(component.nodes, layout_points, strict=False):
                ix, iy = map_to_grid(point)
                _mark_disc(conductor_mask, fixed_values, ix, iy, conductor_radius_cells, _node_voltage(result, node))
        elif layout_points:
            average_voltage = float(np.mean([_node_voltage(result, node) for node in component.nodes]))
            ix, iy = map_to_grid(layout_points[0])
            _mark_disc(conductor_mask, fixed_values, ix, iy, conductor_radius_cells, average_voltage)

    potential = fixed_values.copy()
    far_field_v = 0.0
    if np.any(conductor_mask):
        far_field_v = float(np.mean(fixed_values[conductor_mask]))
    potential[~conductor_mask] = far_field_v
    conductor_mask[0, :] = True
    conductor_mask[-1, :] = True
    conductor_mask[:, 0] = True
    conductor_mask[:, -1] = True
    fixed_values[0, :] = 0.0
    fixed_values[-1, :] = 0.0
    fixed_values[:, 0] = 0.0
    fixed_values[:, -1] = 0.0
    potential[conductor_mask] = fixed_values[conductor_mask]

    free_mask = ~conductor_mask[1:-1, 1:-1]
    for _ in range(max(iterations, 1)):
        neighbor_average = 0.25 * (
            potential[:-2, 1:-1]
            + potential[2:, 1:-1]
            + potential[1:-1, :-2]
            + potential[1:-1, 2:]
        )
        interior = potential[1:-1, 1:-1]
        interior[free_mask] = (1.0 - relaxation) * interior[free_mask] + relaxation * neighbor_average[free_mask]
        potential[conductor_mask] = fixed_values[conductor_mask]

    dy_m = max((max_y - min_y) * scale_m_per_px / max(grid_height - 1, 1), 1.0e-9)
    dx_m = max((max_x - min_x) * scale_m_per_px / max(grid_width - 1, 1), 1.0e-9)
    grad_y, grad_x = np.gradient(potential, dy_m, dx_m)
    electric_field = np.hypot(grad_x, grad_y)

    magnetic_bz = np.zeros_like(potential)
    for start, end, current_a in current_segments:
        if abs(current_a) < 1.0e-12:
            continue
        mid_x = 0.5 * (start[0] + end[0])
        mid_y = 0.5 * (start[1] + end[1])
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        segment_length_m = max(math.hypot(dx, dy) * scale_m_per_px, 1.0e-9)
        direction_x = dx / max(math.hypot(dx, dy), 1.0e-9)
        direction_y = dy / max(math.hypot(dx, dy), 1.0e-9)
        rx_m = (xx_px - mid_x) * scale_m_per_px
        ry_m = (yy_px - mid_y) * scale_m_per_px
        distance_sq = rx_m * rx_m + ry_m * ry_m + (0.3 * segment_length_m) ** 2
        turn_sign = np.sign(direction_x * ry_m - direction_y * rx_m)
        magnetic_bz += turn_sign * MU_0 * current_a * segment_length_m / (2.0 * math.pi * distance_sq)
    magnetic_flux_density = np.abs(magnetic_bz)

    return FieldSnapshot(
        bounds_px=(float(min_x), float(min_y), float(max_x), float(max_y)),
        x_grid_px=xx_px,
        y_grid_px=yy_px,
        potential_v=potential,
        electric_field_v_m=electric_field,
        magnetic_flux_density_t=magnetic_flux_density,
        conductor_mask=conductor_mask,
        metadata={
            "grid_width": int(grid_width),
            "grid_height": int(grid_height),
            "scale_m_per_px": float(scale_m_per_px),
            "iterations": int(iterations),
        },
    )


def simulate_fdtd_wave(
    circuit: Circuit,
    result: SimulationResult,
    *,
    grid_width: int = 220,
    grid_height: int = 160,
    steps: int = 56,
    padding_px: float = 90.0,
    iterations: int = 420,
    source_period_steps: int = 14,
    damping: float = 0.012,
) -> FieldWaveSequence:
    static = solve_quasi_static_field(
        circuit,
        result,
        grid_width=grid_width,
        grid_height=grid_height,
        padding_px=padding_px,
        iterations=iterations,
    )
    conductor_mask = static.conductor_mask.copy()
    source_pattern = np.array(static.potential_v, dtype=float)
    source_scale = max(float(np.max(np.abs(source_pattern[conductor_mask])) if np.any(conductor_mask) else 0.0), 1.0e-9)
    source_pattern = source_pattern / source_scale
    if not np.any(np.abs(source_pattern[conductor_mask]) > 1.0e-6):
        center_y = source_pattern.shape[0] // 2
        center_x = source_pattern.shape[1] // 2
        source_pattern[center_y - 1:center_y + 2, center_x - 1:center_x + 2] = 1.0

    scale_m_per_px = float(static.metadata.get("scale_m_per_px", 0.002))
    dx_m = max((static.bounds_px[2] - static.bounds_px[0]) * scale_m_per_px / max(grid_width - 1, 1), 1.0e-9)
    dy_m = max((static.bounds_px[3] - static.bounds_px[1]) * scale_m_per_px / max(grid_height - 1, 1), 1.0e-9)
    c0 = 1.0 / math.sqrt(EPSILON_0 * MU_0)
    courant = 0.34
    dt_s = courant * min(dx_m, dy_m) / c0
    cx2 = (c0 * dt_s / dx_m) ** 2
    cy2 = (c0 * dt_s / dy_m) ** 2

    prev = np.zeros_like(static.potential_v)
    current = np.zeros_like(static.potential_v)
    electric_frames = np.zeros((steps, grid_height, grid_width), dtype=float)
    magnetic_frames = np.zeros((steps, grid_height, grid_width), dtype=float)
    outer_boundary = np.zeros_like(conductor_mask)
    outer_boundary[0, :] = True
    outer_boundary[-1, :] = True
    outer_boundary[:, 0] = True
    outer_boundary[:, -1] = True

    for frame_index in range(steps):
        nxt = current.copy()
        laplacian_x = current[1:-1, 2:] - 2.0 * current[1:-1, 1:-1] + current[1:-1, :-2]
        laplacian_y = current[2:, 1:-1] - 2.0 * current[1:-1, 1:-1] + current[:-2, 1:-1]
        nxt[1:-1, 1:-1] = (
            (2.0 - damping) * current[1:-1, 1:-1]
            - (1.0 - damping) * prev[1:-1, 1:-1]
            + cx2 * laplacian_x
            + cy2 * laplacian_y
        )

        envelope = math.exp(-((frame_index - 0.28 * steps) / max(0.18 * steps, 1.0)) ** 2)
        carrier = math.sin(2.0 * math.pi * frame_index / max(source_period_steps, 2))
        source_drive = envelope * carrier
        nxt[conductor_mask] = source_pattern[conductor_mask] * source_drive
        nxt[outer_boundary] = 0.0

        dphi_dy, dphi_dx = np.gradient(nxt, dy_m, dx_m)
        electric_frames[frame_index] = np.hypot(dphi_dx, dphi_dy)
        magnetic_frames[frame_index] = np.abs(nxt - prev) / max(c0 * c0 * dt_s, 1.0e-18)

        prev, current = current, nxt

    return FieldWaveSequence(
        bounds_px=static.bounds_px,
        x_grid_px=static.x_grid_px,
        y_grid_px=static.y_grid_px,
        potential_v=static.potential_v,
        electric_frames_v_m=electric_frames,
        magnetic_frames_t=magnetic_frames,
        conductor_mask=conductor_mask,
        metadata={
            "grid_width": int(grid_width),
            "grid_height": int(grid_height),
            "scale_m_per_px": float(scale_m_per_px),
            "time_step_s": float(dt_s),
            "steps": int(steps),
            "source_period_steps": int(source_period_steps),
        },
    )


def simulate_full_wave_maxwell_2d(
    circuit: Circuit,
    result: SimulationResult,
    *,
    grid_width: int = 220,
    grid_height: int = 160,
    steps: int = 72,
    padding_px: float = 90.0,
    iterations: int = 420,
    source_period_steps: int = 16,
    edge_absorber_cells: int = 16,
    source_gain: float = 1800.0,
) -> FieldWaveSequence:
    static = solve_quasi_static_field(
        circuit,
        result,
        grid_width=grid_width,
        grid_height=grid_height,
        padding_px=padding_px,
        iterations=iterations,
    )
    ny, nx = static.potential_v.shape
    conductor_mask = static.conductor_mask.copy()
    source_pattern = np.array(static.potential_v, dtype=float)
    source_scale = max(float(np.max(np.abs(source_pattern[conductor_mask])) if np.any(conductor_mask) else 0.0), 1.0e-9)
    source_pattern = source_gain * source_pattern / source_scale
    if not np.any(np.abs(source_pattern[conductor_mask]) > 1.0e-6):
        source_pattern[ny // 2 - 1:ny // 2 + 2, nx // 2 - 1:nx // 2 + 2] = source_gain

    scale_m_per_px = float(static.metadata.get("scale_m_per_px", 0.002))
    dx_m = max((static.bounds_px[2] - static.bounds_px[0]) * scale_m_per_px / max(nx - 1, 1), 1.0e-9)
    dy_m = max((static.bounds_px[3] - static.bounds_px[1]) * scale_m_per_px / max(ny - 1, 1), 1.0e-9)
    c0 = 1.0 / math.sqrt(EPSILON_0 * MU_0)
    dt_s = 0.57 / (c0 * math.sqrt((1.0 / dx_m ** 2) + (1.0 / dy_m ** 2)))

    ez = np.zeros((ny, nx), dtype=float)
    hx = np.zeros((ny - 1, nx), dtype=float)
    hy = np.zeros((ny, nx - 1), dtype=float)
    electric_frames = np.zeros((steps, ny, nx), dtype=float)
    magnetic_frames = np.zeros((steps, ny, nx), dtype=float)

    sigma_e = np.zeros((ny, nx), dtype=float)
    sigma_hx = np.zeros((ny - 1, nx), dtype=float)
    sigma_hy = np.zeros((ny, nx - 1), dtype=float)
    absorber_cells = max(edge_absorber_cells, 4)
    sigma_max = 0.9 * EPSILON_0 / max(dt_s, 1.0e-18)
    for y in range(ny):
        for x in range(nx):
            dist = min(x, nx - 1 - x, y, ny - 1 - y)
            if dist < absorber_cells:
                ratio = (absorber_cells - dist) / absorber_cells
                sigma_e[y, x] = sigma_max * ratio * ratio
    sigma_hx[:, :] = 0.5 * (sigma_e[:-1, :] + sigma_e[1:, :])
    sigma_hy[:, :] = 0.5 * (sigma_e[:, :-1] + sigma_e[:, 1:])

    decay_e = (1.0 - sigma_e * dt_s / (2.0 * EPSILON_0)) / np.maximum(1.0 + sigma_e * dt_s / (2.0 * EPSILON_0), 1.0e-9)
    drive_e = dt_s / (EPSILON_0 * np.maximum(1.0 + sigma_e * dt_s / (2.0 * EPSILON_0), 1.0e-9))
    decay_hx = np.exp(-sigma_hx * dt_s / np.maximum(MU_0, 1.0e-18))
    decay_hy = np.exp(-sigma_hy * dt_s / np.maximum(MU_0, 1.0e-18))

    source_mask = conductor_mask.copy()
    source_mask[0, :] = False
    source_mask[-1, :] = False
    source_mask[:, 0] = False
    source_mask[:, -1] = False

    for frame_index in range(steps):
        hx = decay_hx * (hx - (dt_s / (MU_0 * dy_m)) * (ez[1:, :] - ez[:-1, :]))
        hy = decay_hy * (hy + (dt_s / (MU_0 * dx_m)) * (ez[:, 1:] - ez[:, :-1]))

        curl_h = (
            (hy[1:-1, 1:] - hy[1:-1, :-1]) / dx_m
            - (hx[1:, 1:-1] - hx[:-1, 1:-1]) / dy_m
        )
        ez[1:-1, 1:-1] = decay_e[1:-1, 1:-1] * ez[1:-1, 1:-1] + drive_e[1:-1, 1:-1] * curl_h

        carrier = math.sin(2.0 * math.pi * frame_index / max(source_period_steps, 2))
        envelope = 1.0 - math.exp(-frame_index / max(0.12 * steps, 1.0))
        ez[source_mask] = source_pattern[source_mask] * carrier * envelope
        ez[0, :] = 0.0
        ez[-1, :] = 0.0
        ez[:, 0] = 0.0
        ez[:, -1] = 0.0

        hmag = np.zeros_like(ez)
        hmag[:-1, :] += hx * hx
        hmag[1:, :] += hx * hx
        hmag[:, :-1] += hy * hy
        hmag[:, 1:] += hy * hy
        hmag = np.sqrt(hmag * 0.25)
        electric_frames[frame_index] = np.abs(ez)
        magnetic_frames[frame_index] = MU_0 * hmag

    return FieldWaveSequence(
        bounds_px=static.bounds_px,
        x_grid_px=static.x_grid_px,
        y_grid_px=static.y_grid_px,
        potential_v=static.potential_v,
        electric_frames_v_m=electric_frames,
        magnetic_frames_t=magnetic_frames,
        conductor_mask=conductor_mask,
        metadata={
            "grid_width": int(grid_width),
            "grid_height": int(grid_height),
            "scale_m_per_px": float(scale_m_per_px),
            "time_step_s": float(dt_s),
            "steps": int(steps),
            "source_period_steps": int(source_period_steps),
            "solver": "maxwell_2d_tmz",
        },
    )
