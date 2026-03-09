from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

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
        canonical = _canonical_layer_name(name)
        if canonical == "potential":
            return self.potential_v
        if canonical == "electric":
            return self.electric_field_v_m
        if canonical == "magnetic":
            return self.magnetic_flux_density_t
        raise ValueError(f"Unknown field layer: {name}")

    def to_image(self, layer: str = "potential", scale: int = 3) -> Image.Image:
        values = np.array(self.layer(layer), dtype=float)
        canonical = _canonical_layer_name(layer)
        return _layer_to_image(
            values,
            self.conductor_mask,
            layer=canonical,
            scale=scale,
            scale_ref=self._display_scale(canonical),
            noise_floor=self._noise_floor(canonical),
        )

    def _display_scale(self, layer: str) -> float:
        key = f"render_scale_{layer}"
        if key not in self.metadata:
            self.metadata[key] = _estimate_display_scale(self.layer(layer), layer)
        return float(self.metadata[key])

    def _noise_floor(self, layer: str) -> float:
        if layer == "potential":
            return 0.0
        key = f"render_noise_floor_{layer}"
        if key not in self.metadata:
            self.metadata[key] = _estimate_noise_floor(self.layer(layer), layer, self._display_scale(layer))
        return float(self.metadata[key])


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
        canonical = _canonical_layer_name(name)
        if canonical == "potential":
            return self.potential_v
        if canonical == "electric":
            return self.electric_frames_v_m[index]
        if canonical == "magnetic":
            return self.magnetic_frames_t[index]
        raise ValueError(f"Unknown field layer: {name}")

    def to_image(self, layer: str = "electric", frame_index: int = 0, scale: int = 3) -> Image.Image:
        values = np.array(self.layer_frame(layer, frame_index), dtype=float)
        canonical = _canonical_layer_name(layer)
        return _layer_to_image(
            values,
            self.conductor_mask,
            layer=canonical,
            scale=scale,
            scale_ref=self._display_scale(canonical),
            noise_floor=self._noise_floor(canonical),
        )

    def _display_scale(self, layer: str) -> float:
        key = f"render_scale_{layer}"
        if key not in self.metadata:
            if layer == "potential":
                values = self.potential_v
            elif layer == "electric":
                values = self.electric_frames_v_m
            else:
                values = self.magnetic_frames_t
            self.metadata[key] = _estimate_display_scale(values, layer)
        return float(self.metadata[key])

    def _noise_floor(self, layer: str) -> float:
        if layer == "potential":
            return 0.0
        key = f"render_noise_floor_{layer}"
        if key not in self.metadata:
            if layer == "electric":
                values = self.electric_frames_v_m
            else:
                values = self.magnetic_frames_t
            self.metadata[key] = _estimate_noise_floor(values, layer, self._display_scale(layer))
        return float(self.metadata[key])


@dataclass(slots=True)
class FieldVolumeSequence:
    bounds_px: tuple[float, float, float, float]
    z_bounds_m: tuple[float, float]
    x_coords_px: np.ndarray
    y_coords_px: np.ndarray
    z_coords_m: np.ndarray
    potential_v: np.ndarray
    electric_frames_v_m: np.ndarray
    magnetic_frames_t: np.ndarray
    conductor_mask: np.ndarray
    metadata: dict[str, Any]

    def frame_count(self) -> int:
        return int(self.electric_frames_v_m.shape[0])

    def slice_count(self, plane: str) -> int:
        canonical = _canonical_plane_name(plane)
        if canonical == "xy":
            return int(self.potential_v.shape[0])
        if canonical == "xz":
            return int(self.potential_v.shape[1])
        return int(self.potential_v.shape[2])

    def layer_frame(self, name: str, frame_index: int) -> np.ndarray:
        index = max(0, min(self.frame_count() - 1, int(frame_index)))
        canonical = _canonical_layer_name(name)
        if canonical == "potential":
            return self.potential_v
        if canonical == "electric":
            return self.electric_frames_v_m[index]
        if canonical == "magnetic":
            return self.magnetic_frames_t[index]
        raise ValueError(f"Unknown field layer: {name}")

    def slice_to_image(
        self,
        layer: str = "electric",
        *,
        plane: str = "xy",
        frame_index: int = 0,
        slice_index: int | None = None,
        scale: int = 3,
    ) -> Image.Image:
        canonical_layer = _canonical_layer_name(layer)
        canonical_plane = _canonical_plane_name(plane)
        volume = np.array(self.layer_frame(layer, frame_index), dtype=float)
        conductor_volume = np.array(self.conductor_mask, dtype=bool)
        values_2d, conductor_mask_2d = _volume_slice(
            volume,
            conductor_volume,
            plane=canonical_plane,
            slice_index=self._slice_index(canonical_plane, slice_index),
        )
        return _layer_to_image(
            values_2d,
            conductor_mask_2d,
            layer=canonical_layer,
            scale=scale,
            scale_ref=self._display_scale(canonical_layer),
            noise_floor=self._noise_floor(canonical_layer),
        )

    def isosurface_to_image(
        self,
        layer: str = "electric",
        *,
        frame_index: int = 0,
        iso_ratio: float = 0.58,
        scale: int = 3,
    ) -> Image.Image:
        canonical_layer = _canonical_layer_name(layer)
        volume = np.array(self.layer_frame(layer, frame_index), dtype=float)
        return _volume_isosurface_to_image(
            volume,
            self.conductor_mask,
            layer=canonical_layer,
            scale=scale,
            scale_ref=self._display_scale(canonical_layer),
            noise_floor=self._noise_floor(canonical_layer),
            iso_ratio=iso_ratio,
        )

    def _slice_index(self, plane: str, slice_index: int | None) -> int:
        count = self.slice_count(plane)
        if slice_index is None:
            return count // 2
        return max(0, min(count - 1, int(slice_index)))

    def _display_scale(self, layer: str) -> float:
        key = f"render_scale_{layer}"
        if key not in self.metadata:
            if layer == "potential":
                values = self.potential_v
            elif layer == "electric":
                values = self.electric_frames_v_m
            else:
                values = self.magnetic_frames_t
            self.metadata[key] = _estimate_display_scale(values, layer)
        return float(self.metadata[key])

    def _noise_floor(self, layer: str) -> float:
        if layer == "potential":
            return 0.0
        key = f"render_noise_floor_{layer}"
        if key not in self.metadata:
            if layer == "electric":
                values = self.electric_frames_v_m
            else:
                values = self.magnetic_frames_t
            self.metadata[key] = _estimate_noise_floor(values, layer, self._display_scale(layer))
        return float(self.metadata[key])


@dataclass(slots=True)
class _FieldContext:
    snapshot: FieldSnapshot
    epsilon_r: np.ndarray
    sigma_s_per_m: np.ndarray
    mu_r: np.ndarray
    ports: list[dict[str, Any]]
    port_mask: np.ndarray
    pec_mask: np.ndarray
    dx_m: float
    dy_m: float
    scale_m_per_px: float
    materials_count: int
    ports_count: int


def _canonical_layer_name(name: str) -> str:
    lowered = str(name).lower()
    if lowered == "potential":
        return "potential"
    if lowered in {"electric", "e"}:
        return "electric"
    if lowered in {"magnetic", "b"}:
        return "magnetic"
    raise ValueError(f"Unknown field layer: {name}")


def _canonical_plane_name(name: str) -> str:
    lowered = str(name).lower()
    if lowered in {"xy", "top"}:
        return "xy"
    if lowered in {"xz", "front"}:
        return "xz"
    if lowered in {"yz", "side"}:
        return "yz"
    raise ValueError(f"Unknown volume plane: {name}")


def _estimate_display_scale(values: np.ndarray, layer: str) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return 1.0 if layer == "potential" else 1.0e-12
    magnitude = np.abs(finite) if layer == "potential" else finite
    percentile = 96.0 if layer == "potential" else 99.2
    floor = 1.0e-9 if layer == "potential" else 1.0e-12
    return max(float(np.percentile(magnitude, percentile)), floor)


def _estimate_noise_floor(values: np.ndarray, layer: str, scale_ref: float) -> float:
    if layer == "potential":
        return 0.0
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return 0.0
    baseline = float(np.percentile(finite, 70.0))
    return min(scale_ref * 0.12, max(baseline, scale_ref * 0.015))


def _low_pass_field(values: np.ndarray, conductor_mask: np.ndarray | None = None, *, strength: float = 0.18, passes: int = 1) -> np.ndarray:
    if strength <= 0.0 or passes <= 0:
        return np.array(values, dtype=float, copy=True)
    result = np.array(values, dtype=float, copy=True)
    if result.ndim != 2 or result.shape[0] < 3 or result.shape[1] < 3:
        return result
    if conductor_mask is None:
        conductor_mask = np.zeros(result.shape, dtype=bool)
    frozen = conductor_mask.astype(bool)
    for _ in range(passes):
        updated = result.copy()
        interior = result[1:-1, 1:-1]
        neighbour_average = 0.25 * (
            result[:-2, 1:-1]
            + result[2:, 1:-1]
            + result[1:-1, :-2]
            + result[1:-1, 2:]
        )
        updated[1:-1, 1:-1] = (1.0 - strength) * interior + strength * neighbour_average
        if np.any(frozen):
            updated[frozen] = result[frozen]
        result = updated
    return result


def _low_pass_volume(values: np.ndarray, frozen_mask: np.ndarray | None = None, *, strength: float = 0.12, passes: int = 1) -> np.ndarray:
    if strength <= 0.0 or passes <= 0:
        return np.array(values, dtype=float, copy=True)
    result = np.array(values, dtype=float, copy=True)
    if result.ndim != 3 or min(result.shape) < 3:
        return result
    if frozen_mask is None:
        frozen_mask = np.zeros(result.shape, dtype=bool)
    frozen = frozen_mask.astype(bool)
    for _ in range(passes):
        updated = result.copy()
        interior = result[1:-1, 1:-1, 1:-1]
        neighbours = (
            result[:-2, 1:-1, 1:-1]
            + result[2:, 1:-1, 1:-1]
            + result[1:-1, :-2, 1:-1]
            + result[1:-1, 2:, 1:-1]
            + result[1:-1, 1:-1, :-2]
            + result[1:-1, 1:-1, 2:]
        ) / 6.0
        updated[1:-1, 1:-1, 1:-1] = (1.0 - strength) * interior + strength * neighbours
        if np.any(frozen):
            updated[frozen] = result[frozen]
        result = updated
    return result


def _volume_slice(
    values: np.ndarray,
    conductor_mask: np.ndarray,
    *,
    plane: str,
    slice_index: int,
) -> tuple[np.ndarray, np.ndarray]:
    if plane == "xy":
        index = max(0, min(values.shape[0] - 1, slice_index))
        return values[index, :, :], conductor_mask[index, :, :]
    if plane == "xz":
        index = max(0, min(values.shape[1] - 1, slice_index))
        return values[:, index, :], conductor_mask[:, index, :]
    index = max(0, min(values.shape[2] - 1, slice_index))
    return values[:, :, index], conductor_mask[:, :, index]


def _volume_isosurface_to_image(
    values: np.ndarray,
    conductor_mask: np.ndarray,
    *,
    layer: str,
    scale: int,
    scale_ref: float,
    noise_floor: float,
    iso_ratio: float,
) -> Image.Image:
    if values.ndim != 3:
        raise ValueError("Isosurface rendering expects a 3D volume.")
    display_values = _low_pass_volume(values, conductor_mask, strength=0.14, passes=2)
    threshold = noise_floor + max(scale_ref - noise_floor, 1.0e-18) * min(max(iso_ratio, 0.05), 0.98)
    active = display_values >= threshold
    conductor = conductor_mask.astype(bool)
    occupied = active | conductor
    if not np.any(occupied):
        empty = Image.new("RGB", (320, 220), (10, 21, 33))
        return empty.resize((empty.width * max(scale, 1), empty.height * max(scale, 1)), Image.Resampling.BICUBIC)

    depth, height, width = occupied.shape
    tile_w = 8
    tile_h = 4
    z_step = 6
    canvas_w = int((width + height) * tile_w + 80)
    canvas_h = int((width + height) * tile_h + depth * z_step + 80)
    image = Image.new("RGB", (canvas_w, canvas_h), (10, 21, 33))
    draw = ImageDraw.Draw(image, "RGBA")
    center_x = canvas_w // 2
    base_y = canvas_h - 36
    normalized_scale = max(scale_ref - noise_floor, 1.0e-18)

    def project(x: int, y: int, z: int) -> tuple[float, float]:
        screen_x = center_x + (x - y) * tile_w
        screen_y = base_y - (x + y) * tile_h - z * z_step
        return float(screen_x), float(screen_y)

    for depth_key in range(width + height + depth):
        for z in range(depth):
            for y in range(height):
                x = depth_key - y - z
                if x < 0 or x >= width or not occupied[z, y, x]:
                    continue
                if not conductor[z, y, x]:
                    if (
                        x > 0
                        and x < width - 1
                        and y > 0
                        and y < height - 1
                        and z > 0
                        and z < depth - 1
                        and occupied[z, y, x - 1]
                        and occupied[z, y, x + 1]
                        and occupied[z, y - 1, x]
                        and occupied[z, y + 1, x]
                        and occupied[z - 1, y, x]
                        and occupied[z + 1, y, x]
                    ):
                        continue
                px, py = project(x, y, z)
                if conductor[z, y, x]:
                    top = (242, 239, 233, 255)
                    left = (218, 214, 208, 255)
                    right = (204, 200, 196, 255)
                else:
                    value = max(display_values[z, y, x] - noise_floor, 0.0)
                    intensity = min(max(value / normalized_scale, 0.0), 1.0)
                    rgb = tuple(int(channel) for channel in _gradient_map(np.array([[intensity]], dtype=float), _layer_stops(layer))[0, 0])
                    top = (rgb[0], rgb[1], rgb[2], 228)
                    left = (max(int(rgb[0] * 0.72), 0), max(int(rgb[1] * 0.72), 0), max(int(rgb[2] * 0.72), 0), 210)
                    right = (max(int(rgb[0] * 0.56), 0), max(int(rgb[1] * 0.56), 0), max(int(rgb[2] * 0.56), 0), 210)
                draw.polygon([(px, py - z_step), (px + tile_w, py - tile_h - z_step), (px, py - 2 * tile_h - z_step), (px - tile_w, py - tile_h - z_step)], fill=top)
                draw.polygon([(px - tile_w, py - tile_h - z_step), (px, py), (px, py - 2 * tile_h), (px, py - 2 * tile_h - z_step)], fill=left)
                draw.polygon([(px + tile_w, py - tile_h - z_step), (px, py), (px, py - 2 * tile_h), (px, py - 2 * tile_h - z_step)], fill=right)

    if scale > 1:
        image = image.resize((image.width * scale, image.height * scale), Image.Resampling.BICUBIC)
    return image


def _layer_stops(layer: str) -> tuple[tuple[float, tuple[int, int, int]], ...]:
    if layer == "potential":
        return ((0.0, (18, 58, 94)), (0.5, (245, 242, 232)), (1.0, (164, 28, 47)))
    if layer in {"electric", "e"}:
        return ((0.0, (11, 30, 53)), (0.45, (43, 108, 176)), (1.0, (250, 204, 21)))
    return ((0.0, (18, 18, 18)), (0.45, (153, 27, 27)), (1.0, (251, 191, 36)))


def _layer_to_image(
    values: np.ndarray,
    conductor_mask: np.ndarray,
    *,
    layer: str,
    scale: int,
    scale_ref: float | None = None,
    noise_floor: float = 0.0,
) -> Image.Image:
    display_values = np.array(values, dtype=float, copy=True)
    if layer != "potential":
        display_values = _low_pass_field(display_values, conductor_mask, strength=0.18, passes=2)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        finite = np.array([0.0], dtype=float)
    if layer == "potential":
        span = max(float(scale_ref if scale_ref is not None else np.percentile(np.abs(finite), 96)), 1.0e-9)
        normalized = np.clip(0.5 + 0.5 * display_values / span, 0.0, 1.0)
        image = _gradient_map(normalized, _layer_stops(layer))
    elif layer in {"electric", "e"}:
        span = max(float(scale_ref if scale_ref is not None else np.percentile(finite, 97)), 1.0e-9)
        visible = np.maximum(display_values - noise_floor, 0.0)
        normalized = np.clip(np.log1p(visible / max(span - noise_floor, 1.0e-18) * 4.0) / math.log1p(4.0), 0.0, 1.0)
        image = _gradient_map(normalized, _layer_stops(layer))
    else:
        span = max(float(scale_ref if scale_ref is not None else np.percentile(finite, 97)), 1.0e-12)
        visible = np.maximum(display_values - noise_floor, 0.0)
        normalized = np.clip(np.log1p(visible / max(span - noise_floor, 1.0e-18) * 5.0) / math.log1p(5.0), 0.0, 1.0)
        image = _gradient_map(normalized, _layer_stops(layer))

    pil = Image.fromarray(image, mode="RGB")
    if scale > 1:
        pil = pil.resize((pil.width * scale, pil.height * scale), Image.Resampling.BICUBIC)
    if np.any(conductor_mask):
        mask = Image.fromarray((conductor_mask.astype(np.uint8) * 255), mode="L")
        if scale > 1:
            mask = mask.resize((pil.width, pil.height), Image.Resampling.NEAREST)
        conductor_overlay = Image.new("RGB", pil.size, (247, 244, 238))
        pil.paste(conductor_overlay, mask=mask)
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


def _rect_corners(center: tuple[float, float], width: float, height: float, rotation_deg: float) -> list[tuple[float, float]]:
    half_w = width * 0.5
    half_h = height * 0.5
    angle = math.radians(rotation_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    corners = []
    for dx, dy in ((-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h)):
        corners.append(
            (
                center[0] + dx * cos_a - dy * sin_a,
                center[1] + dx * sin_a + dy * cos_a,
            )
        )
    return corners


def _rect_mask(
    x_grid_px: np.ndarray,
    y_grid_px: np.ndarray,
    center: tuple[float, float],
    width_px: float,
    height_px: float,
    rotation_deg: float = 0.0,
) -> np.ndarray:
    angle = math.radians(rotation_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dx = x_grid_px - center[0]
    dy = y_grid_px - center[1]
    local_x = dx * cos_a + dy * sin_a
    local_y = -dx * sin_a + dy * cos_a
    return (np.abs(local_x) <= width_px * 0.5) & (np.abs(local_y) <= height_px * 0.5)


def _extract_material_regions(circuit: Circuit) -> list[dict[str, Any]]:
    regions = []
    for raw in getattr(circuit, "field_material_regions", []):
        regions.append(
            {
                "name": str(raw.get("name", "Среда")),
                "center_px": tuple(float(v) for v in raw.get("center_px", (0.0, 0.0))),
                "width_px": max(float(raw.get("width_px", 220.0)), 2.0),
                "height_px": max(float(raw.get("height_px", 140.0)), 2.0),
                "rotation_deg": float(raw.get("rotation_deg", 0.0)),
                "z_center_m": float(raw.get("z_center_m", -0.0012)),
                "thickness_m": max(float(raw.get("thickness_m", 0.0016)), 1.0e-6),
                "layer_mode": str(raw.get("layer_mode", "volume")).lower(),
                "epsilon_r": max(float(raw.get("epsilon_r", 1.0)), 1.0),
                "sigma_s_per_m": max(float(raw.get("sigma_s_per_m", 0.0)), 0.0),
                "mu_r": max(float(raw.get("mu_r", 1.0)), 1.0e-3),
            }
        )
    return regions


def _source_component_port(component: Component, result: SimulationResult) -> dict[str, Any] | None:
    class_name = component.__class__.__name__
    if class_name not in {"PhysiBattery", "RealACGenerator", "PulseGenerator"}:
        return None
    layout_points = [(float(point[0]), float(point[1])) for point in getattr(component, "layout_points_px", [])]
    if not isinstance(component, TwoTerminalComponent):
        return None
    if len(layout_points) >= 2:
        start = layout_points[0]
        end = layout_points[-1]
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance_px = max(math.hypot(dx, dy), 10.0)
        center = ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5)
        rotation_deg = math.degrees(math.atan2(dy, dx))
    else:
        center = tuple(float(value) for value in getattr(component, "layout_position_px", (0.0, 0.0)))
        distance_px = 88.0
        rotation_deg = float(getattr(component, "layout_rotation_deg", 0.0))
    voltage_v = abs(_node_voltage(result, component.nodes[0]) - _node_voltage(result, component.nodes[1]))
    if class_name == "RealACGenerator":
        amplitude_v = max(float(getattr(component, "amplitude_v", voltage_v if voltage_v > 0.0 else 1.0)), 1.0e-6)
        frequency_hz = max(float(getattr(component, "frequency_hz", 1.0e6)), 1.0)
        waveform = "sine"
    elif class_name == "PulseGenerator":
        high_level_v = float(getattr(component, "high_voltage_v", 5.0))
        low_level_v = float(getattr(component, "low_voltage_v", 0.0))
        period_s = max(float(getattr(component, "period_s", 1.0)), 1.0e-12)
        configured_pulse_width = getattr(component, "pulse_width_s", None)
        pulse_width_s = period_s * float(getattr(component, "duty_cycle", 0.5)) if configured_pulse_width is None else float(configured_pulse_width)
        return {
            "name": f"auto:{component.name}",
            "center_px": center,
            "width_px": max(distance_px * 0.86, 24.0),
            "height_px": 18.0,
            "rotation_deg": rotation_deg,
            "origin": "auto:PulseGenerator",
            "z_center_m": _component_layout_z_center_m(component),
            "thickness_m": max(_component_layout_thickness_m(component), 5.0e-4),
            "source_kind": "voltage",
            "waveform": "pulse",
            "amplitude_v": max(abs(high_level_v - low_level_v), 1.0e-9),
            "low_level_v": low_level_v,
            "amplitude_a": max(abs(float(getattr(component, "last_current_a", 0.0))), 0.05),
            "frequency_hz": 1.0 / period_s,
            "period_s": period_s,
            "pulse_width_s": max(min(pulse_width_s, period_s), 0.0),
            "rise_time_s": max(float(getattr(component, "rise_time_s", 1.0e-9)), 1.0e-12),
            "fall_time_s": max(float(getattr(component, "fall_time_s", 1.0e-9)), 1.0e-12),
            "phase_rad": 0.0,
            "impedance_ohm": max(float(getattr(component, "internal_resistance_ohm", 50.0)), 1.0e-6),
        }
    else:
        amplitude_v = max(voltage_v, float(getattr(component, "nominal_voltage_v", 1.5)))
        frequency_hz = 0.0
        waveform = "step"
    return {
        "name": f"auto:{component.name}",
        "center_px": center,
        "width_px": max(distance_px * 0.78, 18.0),
        "height_px": 16.0,
        "rotation_deg": rotation_deg,
        "origin": f"auto:{class_name}",
        "z_center_m": _component_layout_z_center_m(component),
        "thickness_m": max(_component_layout_thickness_m(component), 5.0e-4),
        "source_kind": "voltage",
        "waveform": waveform,
        "amplitude_v": amplitude_v,
        "amplitude_a": max(abs(float(getattr(component, "last_current_a", 0.0))), 0.1),
        "frequency_hz": frequency_hz,
        "phase_rad": float(getattr(component, "phase_rad", 0.0)),
        "impedance_ohm": max(float(getattr(component, "internal_resistance_ohm", 50.0)), 1.0e-6),
    }


def _extract_ports(circuit: Circuit, result: SimulationResult) -> list[dict[str, Any]]:
    ports: list[dict[str, Any]] = []
    for raw in getattr(circuit, "field_ports", []):
        ports.append(
            {
                "name": str(raw.get("name", "Порт")),
                "center_px": tuple(float(v) for v in raw.get("center_px", (0.0, 0.0))),
                "width_px": max(float(raw.get("width_px", 90.0)), 4.0),
                "height_px": max(float(raw.get("height_px", 18.0)), 4.0),
                "rotation_deg": float(raw.get("rotation_deg", 0.0)),
                "z_center_m": float(raw.get("z_center_m", 0.0)),
                "thickness_m": max(float(raw.get("thickness_m", 0.0009)), 1.0e-6),
                "source_kind": str(raw.get("source_kind", "voltage")).lower(),
                "waveform": str(raw.get("waveform", "sine")).lower(),
                "amplitude_v": float(raw.get("amplitude_v", 5.0)),
                "amplitude_a": float(raw.get("amplitude_a", 0.2)),
                "frequency_hz": max(float(raw.get("frequency_hz", 0.0)), 0.0),
                "phase_rad": float(raw.get("phase_rad", 0.0)),
                "impedance_ohm": max(float(raw.get("impedance_ohm", 50.0)), 1.0e-6),
                "origin": "explicit",
            }
        )
    if ports:
        return ports
    for component in circuit.components:
        port = _source_component_port(component, result)
        if port is not None:
            ports.append(port)
    return ports


def _layout_extent_points(circuit: Circuit, materials: list[dict[str, Any]], ports: list[dict[str, Any]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for component in circuit.components:
        for point in getattr(component, "layout_points_px", []):
            points.append((float(point[0]), float(point[1])))
        if getattr(component, "layout_position_px", None) is not None:
            position = getattr(component, "layout_position_px")
            points.append((float(position[0]), float(position[1])))
    for region in materials:
        points.extend(_rect_corners(region["center_px"], region["width_px"], region["height_px"], region["rotation_deg"]))
    for port in ports:
        points.extend(_rect_corners(port["center_px"], port["width_px"], port["height_px"], port["rotation_deg"]))
    return points


def _reference_frequency_hz(ports: list[dict[str, Any]]) -> float:
    positive = [float(port.get("frequency_hz", 0.0)) for port in ports if float(port.get("frequency_hz", 0.0)) > 0.0]
    if positive:
        return max(np.median(np.array(positive, dtype=float)), 1.0)
    return 1.0e5


def _build_material_maps(
    x_grid_px: np.ndarray,
    y_grid_px: np.ndarray,
    materials: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    epsilon_r = np.ones_like(x_grid_px, dtype=float)
    sigma_s = np.zeros_like(x_grid_px, dtype=float)
    mu_r = np.ones_like(x_grid_px, dtype=float)
    for region in materials:
        mask = _rect_mask(
            x_grid_px,
            y_grid_px,
            region["center_px"],
            region["width_px"],
            region["height_px"],
            region["rotation_deg"],
        )
        epsilon_r[mask] = float(region["epsilon_r"])
        sigma_s[mask] = float(region["sigma_s_per_m"])
        mu_r[mask] = float(region["mu_r"])
    return epsilon_r, sigma_s, mu_r


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
    materials = _extract_material_regions(circuit)
    ports = _extract_ports(circuit, result)
    points = _layout_extent_points(circuit, materials, ports)
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

    epsilon_r, sigma_s, mu_r = _build_material_maps(xx_px, yy_px, materials)
    omega_ref = 2.0 * math.pi * _reference_frequency_hz(ports)
    conductivity_equivalent = np.clip(sigma_s / max(EPSILON_0 * omega_ref, 1.0e-18), 0.0, 2.0e5)
    relaxation_weight = epsilon_r + conductivity_equivalent

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
    far_field_v = float(np.mean(fixed_values[conductor_mask])) if np.any(conductor_mask) else 0.0
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

    weight = relaxation_weight
    east = 0.5 * (weight[1:-1, 1:-1] + weight[1:-1, 2:])
    west = 0.5 * (weight[1:-1, 1:-1] + weight[1:-1, :-2])
    north = 0.5 * (weight[1:-1, 1:-1] + weight[:-2, 1:-1])
    south = 0.5 * (weight[1:-1, 1:-1] + weight[2:, 1:-1])
    total = np.maximum(east + west + north + south, 1.0e-12)
    free_mask = ~conductor_mask[1:-1, 1:-1]
    for _ in range(max(iterations, 1)):
        weighted_average = (
            east * potential[1:-1, 2:]
            + west * potential[1:-1, :-2]
            + north * potential[:-2, 1:-1]
            + south * potential[2:, 1:-1]
        ) / total
        interior = potential[1:-1, 1:-1]
        interior[free_mask] = (1.0 - relaxation) * interior[free_mask] + relaxation * weighted_average[free_mask]
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
        magnetic_bz += turn_sign * MU_0 * mu_r * current_a * segment_length_m / (2.0 * math.pi * distance_sq)
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
            "materials_count": len(materials),
            "ports_count": len(ports),
            "reference_frequency_hz": float(_reference_frequency_hz(ports)),
            "solver": "quasi_static_weighted",
        },
    )


def _build_field_context(
    circuit: Circuit,
    result: SimulationResult,
    *,
    grid_width: int,
    grid_height: int,
    padding_px: float,
    iterations: int,
) -> _FieldContext:
    snapshot = solve_quasi_static_field(
        circuit,
        result,
        grid_width=grid_width,
        grid_height=grid_height,
        padding_px=padding_px,
        iterations=iterations,
    )
    materials = _extract_material_regions(circuit)
    ports = _extract_ports(circuit, result)
    epsilon_r, sigma_s, mu_r = _build_material_maps(snapshot.x_grid_px, snapshot.y_grid_px, materials)
    port_entries: list[dict[str, Any]] = []
    port_mask = np.zeros_like(snapshot.conductor_mask, dtype=bool)
    for port in ports:
        mask = _rect_mask(
            snapshot.x_grid_px,
            snapshot.y_grid_px,
            port["center_px"],
            port["width_px"],
            port["height_px"],
            port["rotation_deg"],
        )
        if not np.any(mask):
            continue
        entry = dict(port)
        entry["mask"] = mask
        port_entries.append(entry)
        port_mask |= mask
    if not port_entries:
        raise ValueError(
            "Для Maxwell/FDTD нужен Порт поля или подходящий источник. "
            "Для медленных схем без полевого порта используй 'Старт' или 'Карта поля'."
        )
    pec_mask = snapshot.conductor_mask.copy()
    for region in materials:
        if float(region["sigma_s_per_m"]) >= 5.0e5:
            pec_mask |= _rect_mask(
                snapshot.x_grid_px,
                snapshot.y_grid_px,
                region["center_px"],
                region["width_px"],
                region["height_px"],
                region["rotation_deg"],
            )
    if np.any(port_mask):
        pec_mask &= ~port_mask
    ny, nx = snapshot.potential_v.shape
    scale_m_per_px = float(snapshot.metadata.get("scale_m_per_px", 0.002))
    dx_m = max((snapshot.bounds_px[2] - snapshot.bounds_px[0]) * scale_m_per_px / max(nx - 1, 1), 1.0e-9)
    dy_m = max((snapshot.bounds_px[3] - snapshot.bounds_px[1]) * scale_m_per_px / max(ny - 1, 1), 1.0e-9)
    return _FieldContext(
        snapshot=snapshot,
        epsilon_r=epsilon_r,
        sigma_s_per_m=sigma_s,
        mu_r=mu_r,
        ports=port_entries,
        port_mask=port_mask,
        pec_mask=pec_mask,
        dx_m=dx_m,
        dy_m=dy_m,
        scale_m_per_px=scale_m_per_px,
        materials_count=len(materials),
        ports_count=len(port_entries),
    )


def _port_signal(port: dict[str, Any], time_s: float, ramp_s: float) -> float:
    waveform = str(port.get("waveform", "sine")).lower()
    source_kind = str(port.get("source_kind", "voltage")).lower()
    amplitude = float(port.get("amplitude_a", 0.0) if source_kind == "current" else port.get("amplitude_v", 0.0))
    frequency_hz = max(float(port.get("frequency_hz", 0.0)), 0.0)
    phase_rad = float(port.get("phase_rad", 0.0))
    impedance = max(float(port.get("impedance_ohm", 50.0)), 1.0e-6)
    impedance_scale = math.sqrt(50.0 / impedance)
    if waveform == "step":
        base = amplitude * (1.0 - math.exp(-time_s / max(ramp_s, 1.0e-12)))
    elif waveform == "pulse":
        period_s = max(float(port.get("period_s", 1.0 / max(frequency_hz, 1.0))), 1.0e-12)
        pulse_width_s = max(min(float(port.get("pulse_width_s", 0.5 * period_s)), period_s), 0.0)
        rise_time_s = max(float(port.get("rise_time_s", ramp_s)), 1.0e-12)
        fall_time_s = max(float(port.get("fall_time_s", ramp_s)), 1.0e-12)
        low_level = float(port.get("low_level_v", 0.0)) if source_kind == "voltage" else 0.0
        local_time = time_s % period_s
        level = 0.0
        if pulse_width_s > 0.0:
            if local_time < min(rise_time_s, pulse_width_s):
                ratio = local_time / rise_time_s
                level = 0.5 - 0.5 * math.cos(math.pi * min(max(ratio, 0.0), 1.0))
            elif local_time < max(pulse_width_s - fall_time_s, rise_time_s):
                level = 1.0
            elif local_time < pulse_width_s:
                ratio = (local_time - max(pulse_width_s - fall_time_s, 0.0)) / fall_time_s
                level = 0.5 + 0.5 * math.cos(math.pi * min(max(ratio, 0.0), 1.0))
        base = low_level + amplitude * level
    elif waveform == "gaussian":
        center = 4.0 * ramp_s
        width = max(1.5 * ramp_s, 1.0e-12)
        base = amplitude * math.exp(-((time_s - center) / width) ** 2)
    else:
        envelope = 1.0 - math.exp(-time_s / max(ramp_s, 1.0e-12))
        if frequency_hz <= 0.0:
            base = amplitude * envelope
        else:
            base = amplitude * envelope * math.sin(2.0 * math.pi * frequency_hz * time_s + phase_rad)
    return base * impedance_scale


def _field_mode_note(context: _FieldContext, total_time_s: float) -> str | None:
    if not context.ports:
        return None
    origins = {str(port.get("origin", "")) for port in context.ports}
    if origins and origins <= {"auto:PulseGenerator"}:
        slowest_transition = min(
            max(
                min(
                    float(port.get("rise_time_s", 1.0)),
                    float(port.get("fall_time_s", 1.0)),
                    max(float(port.get("pulse_width_s", 1.0)), 1.0e-12),
                ),
                1.0e-12,
            )
            for port in context.ports
        )
        if slowest_transition > total_time_s * 1.0e6:
            return "Низкочастотная схема: Maxwell показывает только сверхбыстрый ЭМ-отклик, не мигание LED."
    return None


def _equivalent_diameter_m(area_mm2: float) -> float:
    area_m2 = max(area_mm2, 1.0e-9) * 1.0e-6
    return 2.0 * math.sqrt(area_m2 / math.pi)


def _component_layout_z_center_m(component: Component) -> float:
    return float(getattr(component, "layout_z_center_m", 0.0))


def _component_layout_thickness_m(component: Component) -> float:
    explicit = getattr(component, "layout_thickness_m", None)
    if explicit is not None:
        return max(float(explicit), 1.0e-6)
    class_name = component.__class__.__name__
    if class_name == "PhysiWire":
        return max(_equivalent_diameter_m(float(getattr(component, "area_mm2", 0.75))) * 1.25, 2.5e-4)
    if class_name in {"LED_ImageActive", "SchockleyDiode", "RealFuse", "ToggleSwitch", "Ammeter", "Voltmeter"}:
        return 0.0018
    if class_name in {"RealResistor", "Thermistor", "Photoresistor", "RealCapacitor", "RealInductor", "PulseGenerator", "RealACGenerator"}:
        return 0.0022
    if class_name == "PhysiBattery":
        return 0.010
    if class_name == "MOSFET_Model":
        return 0.0025
    if class_name == "PhysiOpAmp":
        return 0.0032
    if class_name == "IncandescentBulb":
        return 0.0045
    return 0.002


def _z_index_window(z_coords_m: np.ndarray, center_m: float, thickness_m: float) -> tuple[int, int]:
    half = 0.5 * max(thickness_m, 1.0e-6)
    lower = center_m - half
    upper = center_m + half
    start = int(np.searchsorted(z_coords_m, lower, side="left"))
    end = int(np.searchsorted(z_coords_m, upper, side="right"))
    start = max(0, min(len(z_coords_m) - 1, start))
    end = max(start + 1, min(len(z_coords_m), end))
    return start, end


def _z_mask(z_coords_m: np.ndarray, center_m: float, thickness_m: float) -> np.ndarray:
    start, end = _z_index_window(z_coords_m, center_m, thickness_m)
    mask = np.zeros(len(z_coords_m), dtype=bool)
    mask[start:end] = True
    return mask


def _map_point_to_grid_indices(
    point: tuple[float, float],
    bounds_px: tuple[float, float, float, float],
    nx: int,
    ny: int,
) -> tuple[int, int]:
    min_x, min_y, max_x, max_y = bounds_px
    x_index = int(round((point[0] - min_x) / max(max_x - min_x, 1.0e-9) * (nx - 1)))
    y_index = int(round((point[1] - min_y) / max(max_y - min_y, 1.0e-9) * (ny - 1)))
    return max(0, min(nx - 1, x_index)), max(0, min(ny - 1, y_index))


def _mark_disc_3d(mask: np.ndarray, x_index: int, y_index: int, z_slice: slice, radius_cells: int) -> None:
    depth, height, width = mask.shape
    x0 = max(0, x_index - radius_cells)
    x1 = min(width, x_index + radius_cells + 1)
    y0 = max(0, y_index - radius_cells)
    y1 = min(height, y_index + radius_cells + 1)
    z0 = max(0, z_slice.start if z_slice.start is not None else 0)
    z1 = min(depth, z_slice.stop if z_slice.stop is not None else depth)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    local_mask = (xx - x_index) ** 2 + (yy - y_index) ** 2 <= radius_cells * radius_cells
    mask[z0:z1, y0:y1, x0:x1][:, local_mask] = True


def _build_material_maps_3d(
    circuit: Circuit,
    context: _FieldContext,
    x_coords_px: np.ndarray,
    y_coords_px: np.ndarray,
    z_coords_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    nz = len(z_coords_m)
    ny = len(y_coords_px)
    nx = len(x_coords_px)
    xx_px, yy_px = np.meshgrid(x_coords_px, y_coords_px)
    epsilon_3d = np.ones((nz, ny, nx), dtype=float)
    sigma_3d = np.zeros((nz, ny, nx), dtype=float)
    mu_3d = np.ones((nz, ny, nx), dtype=float)
    materials = _extract_material_regions(circuit)
    for region in materials:
        layer_mode = str(region.get("layer_mode", "volume")).lower()
        if layer_mode == "stack":
            xy_mask = np.ones((ny, nx), dtype=bool)
        else:
            xy_mask = _rect_mask(
                xx_px,
                yy_px,
                region["center_px"],
                region["width_px"],
                region["height_px"],
                region["rotation_deg"],
            )
        z_mask = _z_mask(z_coords_m, float(region.get("z_center_m", -0.0012)), float(region.get("thickness_m", 0.0016)))
        for z_index, enabled in enumerate(z_mask):
            if not enabled:
                continue
            epsilon_3d[z_index][xy_mask] = float(region["epsilon_r"])
            sigma_3d[z_index][xy_mask] = float(region["sigma_s_per_m"])
            mu_3d[z_index][xy_mask] = float(region["mu_r"])
    return epsilon_3d, sigma_3d, mu_3d, materials


def _build_conductor_mask_3d(
    circuit: Circuit,
    context: _FieldContext,
    z_coords_m: np.ndarray,
    bounds_px: tuple[float, float, float, float],
    nx: int,
    ny: int,
) -> np.ndarray:
    mask = np.zeros((len(z_coords_m), ny, nx), dtype=bool)
    px_per_cell_x = max((bounds_px[2] - bounds_px[0]) / max(nx - 1, 1), 1.0e-9)
    for component in circuit.components:
        layout_points = [(float(point[0]), float(point[1])) for point in getattr(component, "layout_points_px", [])]
        if not layout_points:
            position = getattr(component, "layout_position_px", None)
            if position is not None:
                layout_points = [(float(position[0]), float(position[1]))]
        if not layout_points:
            continue
        z_center = _component_layout_z_center_m(component)
        thickness_m = _component_layout_thickness_m(component)
        z_start, z_end = _z_index_window(z_coords_m, z_center, thickness_m)
        radius_px = max(0.5 * thickness_m / max(context.scale_m_per_px, 1.0e-12), 3.0)
        radius_cells = max(1, int(round(radius_px / px_per_cell_x)))
        if isinstance(component, TwoTerminalComponent) and len(layout_points) >= 2:
            polyline = layout_points
        else:
            polyline = layout_points
        if len(polyline) == 1:
            ix, iy = _map_point_to_grid_indices(polyline[0], bounds_px, nx, ny)
            _mark_disc_3d(mask, ix, iy, slice(z_start, z_end), radius_cells)
            continue
        sampled: list[tuple[float, float]] = []
        for index in range(len(polyline) - 1):
            start = polyline[index]
            end = polyline[index + 1]
            count = max(1, int(round(math.hypot(end[0] - start[0], end[1] - start[1]) / 8.0)))
            sampled.extend((x, y) for x, y, _ in _sample_segment(start, end, count))
        sampled.append(polyline[-1])
        for point in sampled:
            ix, iy = _map_point_to_grid_indices(point, bounds_px, nx, ny)
            _mark_disc_3d(mask, ix, iy, slice(z_start, z_end), radius_cells)
    return mask


def _build_port_masks_3d(
    ports: list[dict[str, Any]],
    x_coords_px: np.ndarray,
    y_coords_px: np.ndarray,
    z_coords_m: np.ndarray,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    nz = len(z_coords_m)
    ny = len(y_coords_px)
    nx = len(x_coords_px)
    xx_px, yy_px = np.meshgrid(x_coords_px, y_coords_px)
    port_mask_3d = np.zeros((nz, ny, nx), dtype=bool)
    entries: list[dict[str, Any]] = []
    for port in ports:
        xy_mask = _rect_mask(
            xx_px,
            yy_px,
            port["center_px"],
            port["width_px"],
            port["height_px"],
            port["rotation_deg"],
        )
        z_mask = _z_mask(z_coords_m, float(port.get("z_center_m", 0.0)), float(port.get("thickness_m", 0.0009)))
        mask_3d = np.zeros((nz, ny, nx), dtype=bool)
        for z_index, enabled in enumerate(z_mask):
            if enabled:
                mask_3d[z_index][xy_mask] = True
        if not np.any(mask_3d):
            continue
        entry = dict(port)
        entry["mask_3d"] = mask_3d
        entries.append(entry)
        port_mask_3d |= mask_3d
    return entries, port_mask_3d


def _central_diff_axis(values: np.ndarray, spacing: float, axis: int) -> np.ndarray:
    result = np.zeros_like(values, dtype=float)
    if values.shape[axis] < 3:
        return result
    source = [slice(None)] * values.ndim
    left = [slice(None)] * values.ndim
    right = [slice(None)] * values.ndim
    source[axis] = slice(1, -1)
    left[axis] = slice(0, -2)
    right[axis] = slice(2, None)
    result[tuple(source)] = (values[tuple(right)] - values[tuple(left)]) / max(2.0 * spacing, 1.0e-18)
    return result


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
    context = _build_field_context(
        circuit,
        result,
        grid_width=grid_width,
        grid_height=grid_height,
        padding_px=padding_px,
        iterations=iterations,
    )
    static = context.snapshot
    ny, nx = static.potential_v.shape
    c0 = 1.0 / math.sqrt(EPSILON_0 * MU_0)
    c_map = c0 / np.sqrt(np.maximum(context.epsilon_r * context.mu_r, 1.0e-9))
    dt_s = 0.34 * min(context.dx_m, context.dy_m) / max(float(np.max(c_map)), 1.0e-9)
    note = _field_mode_note(context, dt_s * steps)
    prev = np.zeros_like(static.potential_v)
    current = np.zeros_like(static.potential_v)
    electric_frames = np.zeros((steps, ny, nx), dtype=float)
    magnetic_frames = np.zeros((steps, ny, nx), dtype=float)
    outer_boundary = np.zeros_like(static.conductor_mask)
    outer_boundary[0, :] = True
    outer_boundary[-1, :] = True
    outer_boundary[:, 0] = True
    outer_boundary[:, -1] = True
    coeff_x = (c_map[1:-1, 1:-1] * dt_s / context.dx_m) ** 2
    coeff_y = (c_map[1:-1, 1:-1] * dt_s / context.dy_m) ** 2
    local_damping = np.clip(
        damping + context.sigma_s_per_m[1:-1, 1:-1] * dt_s / np.maximum(EPSILON_0 * context.epsilon_r[1:-1, 1:-1], 1.0e-18),
        0.0,
        0.42,
    )

    for frame_index in range(steps):
        nxt = current.copy()
        laplacian_x = current[1:-1, 2:] - 2.0 * current[1:-1, 1:-1] + current[1:-1, :-2]
        laplacian_y = current[2:, 1:-1] - 2.0 * current[1:-1, 1:-1] + current[:-2, 1:-1]
        nxt[1:-1, 1:-1] = (
            (2.0 - local_damping) * current[1:-1, 1:-1]
            - (1.0 - local_damping) * prev[1:-1, 1:-1]
            + coeff_x * laplacian_x
            + coeff_y * laplacian_y
        )

        time_s = frame_index * dt_s
        ramp_s = max(source_period_steps, 2) * dt_s
        for port in context.ports:
            drive = _port_signal(port, time_s, ramp_s)
            mask = port["mask"]
            if str(port.get("source_kind", "voltage")).lower() == "current":
                nxt[mask] += drive * dt_s / np.maximum(EPSILON_0 * context.epsilon_r[mask], 1.0e-18)
            else:
                nxt[mask] = drive
        nxt[context.pec_mask] = 0.0
        nxt[outer_boundary] = 0.0

        dphi_dy, dphi_dx = np.gradient(nxt, context.dy_m, context.dx_m)
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
        conductor_mask=context.pec_mask,
        metadata={
            "grid_width": int(grid_width),
            "grid_height": int(grid_height),
            "scale_m_per_px": float(context.scale_m_per_px),
            "time_step_s": float(dt_s),
            "steps": int(steps),
            "source_period_steps": int(source_period_steps),
            "materials_count": int(context.materials_count),
            "ports_count": int(context.ports_count),
            "solver": "fdtd_scalar_materials",
            "note": note,
        },
    )


def _simulate_tmz(context: _FieldContext, *, steps: int, edge_absorber_cells: int) -> FieldWaveSequence:
    static = context.snapshot
    ny, nx = static.potential_v.shape
    c0 = 1.0 / math.sqrt(EPSILON_0 * MU_0)
    max_phase_velocity = c0 / math.sqrt(max(float(np.min(context.epsilon_r * context.mu_r)), 1.0e-9))
    dt_s = 0.57 / (max_phase_velocity * math.sqrt((1.0 / context.dx_m ** 2) + (1.0 / context.dy_m ** 2)))
    note = _field_mode_note(context, dt_s * steps)

    ez = np.zeros((ny, nx), dtype=float)
    hx = np.zeros((ny - 1, nx), dtype=float)
    hy = np.zeros((ny, nx - 1), dtype=float)
    electric_frames = np.zeros((steps, ny, nx), dtype=float)
    magnetic_frames = np.zeros((steps, ny, nx), dtype=float)

    absorber_cells = max(edge_absorber_cells, 4)
    sigma_absorb = np.zeros((ny, nx), dtype=float)
    sigma_max = 0.9 * EPSILON_0 / max(dt_s, 1.0e-18)
    for y in range(ny):
        for x in range(nx):
            dist = min(x, nx - 1 - x, y, ny - 1 - y)
            if dist < absorber_cells:
                ratio = (absorber_cells - dist) / absorber_cells
                sigma_absorb[y, x] = sigma_max * ratio * ratio
    sigma_e = context.sigma_s_per_m + sigma_absorb
    eps = EPSILON_0 * context.epsilon_r
    mu_hx = MU_0 * 0.5 * (context.mu_r[:-1, :] + context.mu_r[1:, :])
    mu_hy = MU_0 * 0.5 * (context.mu_r[:, :-1] + context.mu_r[:, 1:])
    sigma_hx = 0.5 * (sigma_absorb[:-1, :] + sigma_absorb[1:, :])
    sigma_hy = 0.5 * (sigma_absorb[:, :-1] + sigma_absorb[:, 1:])

    decay_e = (1.0 - sigma_e * dt_s / (2.0 * eps)) / np.maximum(1.0 + sigma_e * dt_s / (2.0 * eps), 1.0e-9)
    drive_e = dt_s / np.maximum(eps * (1.0 + sigma_e * dt_s / (2.0 * eps)), 1.0e-18)
    decay_hx = np.exp(-sigma_hx * dt_s / np.maximum(mu_hx, 1.0e-18))
    decay_hy = np.exp(-sigma_hy * dt_s / np.maximum(mu_hy, 1.0e-18))

    for frame_index in range(steps):
        hx = decay_hx * (hx - (dt_s / np.maximum(mu_hx, 1.0e-18) / context.dy_m) * (ez[1:, :] - ez[:-1, :]))
        hy = decay_hy * (hy + (dt_s / np.maximum(mu_hy, 1.0e-18) / context.dx_m) * (ez[:, 1:] - ez[:, :-1]))

        curl_h = (
            (hy[1:-1, 1:] - hy[1:-1, :-1]) / context.dx_m
            - (hx[1:, 1:-1] - hx[:-1, 1:-1]) / context.dy_m
        )
        ez[1:-1, 1:-1] = decay_e[1:-1, 1:-1] * ez[1:-1, 1:-1] + drive_e[1:-1, 1:-1] * curl_h

        time_s = frame_index * dt_s
        ramp_s = max(8.0 * dt_s, 1.0e-12)
        for port in context.ports:
            drive = _port_signal(port, time_s, ramp_s)
            mask = port["mask"]
            if str(port.get("source_kind", "voltage")).lower() == "current":
                ez[mask] += drive * dt_s / np.maximum(eps[mask], 1.0e-18)
            else:
                ez[mask] = drive
        ez[context.pec_mask] = 0.0
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
        magnetic_frames[frame_index] = MU_0 * context.mu_r * hmag

    return FieldWaveSequence(
        bounds_px=static.bounds_px,
        x_grid_px=static.x_grid_px,
        y_grid_px=static.y_grid_px,
        potential_v=static.potential_v,
        electric_frames_v_m=electric_frames,
        magnetic_frames_t=magnetic_frames,
        conductor_mask=context.pec_mask,
        metadata={
            "grid_width": int(nx),
            "grid_height": int(ny),
            "scale_m_per_px": float(context.scale_m_per_px),
            "time_step_s": float(dt_s),
            "steps": int(steps),
            "materials_count": int(context.materials_count),
            "ports_count": int(context.ports_count),
            "solver": "maxwell_2d_tmz",
            "note": note,
        },
    )


def _simulate_tez(context: _FieldContext, *, steps: int, edge_absorber_cells: int) -> FieldWaveSequence:
    static = context.snapshot
    ny, nx = static.potential_v.shape
    c0 = 1.0 / math.sqrt(EPSILON_0 * MU_0)
    max_phase_velocity = c0 / math.sqrt(max(float(np.min(context.epsilon_r * context.mu_r)), 1.0e-9))
    dt_s = 0.28 / (max_phase_velocity * math.sqrt((1.0 / context.dx_m ** 2) + (1.0 / context.dy_m ** 2)))
    note = _field_mode_note(context, dt_s * steps)

    ex = np.zeros((ny, nx), dtype=float)
    ey = np.zeros((ny, nx), dtype=float)
    hz = np.zeros((ny, nx), dtype=float)
    electric_frames = np.zeros((steps, ny, nx), dtype=float)
    magnetic_frames = np.zeros((steps, ny, nx), dtype=float)

    absorber_cells = max(edge_absorber_cells, 4)
    sigma_absorb = np.zeros((ny, nx), dtype=float)
    sigma_max = 0.9 * EPSILON_0 / max(dt_s, 1.0e-18)
    for y in range(ny):
        for x in range(nx):
            dist = min(x, nx - 1 - x, y, ny - 1 - y)
            if dist < absorber_cells:
                ratio = (absorber_cells - dist) / absorber_cells
                sigma_absorb[y, x] = sigma_max * ratio * ratio
    eps = EPSILON_0 * context.epsilon_r
    mu = MU_0 * context.mu_r
    sigma_e = context.sigma_s_per_m + sigma_absorb
    sigma_h = sigma_absorb
    decay_e = (1.0 - sigma_e * dt_s / (2.0 * eps)) / np.maximum(1.0 + sigma_e * dt_s / (2.0 * eps), 1.0e-9)
    drive_e = dt_s / np.maximum(eps * (1.0 + sigma_e * dt_s / (2.0 * eps)), 1.0e-18)
    decay_h = np.exp(-sigma_h * dt_s / np.maximum(mu, 1.0e-18))
    port_masks = [port["mask"] for port in context.ports]
    smoothing_mask = context.pec_mask.copy()
    for mask in port_masks:
        smoothing_mask |= mask
    electric_interior_decay = 0.996
    magnetic_interior_decay = 0.997

    for frame_index in range(steps):
        ex[1:, :] = decay_e[1:, :] * ex[1:, :] + drive_e[1:, :] * (hz[1:, :] - hz[:-1, :]) / context.dy_m
        ey[:, 1:] = decay_e[:, 1:] * ey[:, 1:] - drive_e[:, 1:] * (hz[:, 1:] - hz[:, :-1]) / context.dx_m
        curl_e = np.zeros_like(hz)
        curl_e[:-1, :-1] = (
            (ex[:-1, 1:] - ex[:-1, :-1]) / context.dx_m
            - (ey[1:, :-1] - ey[:-1, :-1]) / context.dy_m
        )
        hz = decay_h * (hz + dt_s * curl_e / np.maximum(mu, 1.0e-18))

        time_s = frame_index * dt_s
        ramp_s = max(8.0 * dt_s, 1.0e-12)
        for port in context.ports:
            drive = _port_signal(port, time_s, ramp_s)
            mask = port["mask"]
            angle = math.radians(float(port.get("rotation_deg", 0.0)))
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            if str(port.get("source_kind", "voltage")).lower() == "current":
                hz[mask] += 0.18 * drive * dt_s / np.maximum(mu[mask], 1.0e-18)
            else:
                ex[mask] = 0.82 * ex[mask] + 0.18 * drive * dir_x
                ey[mask] = 0.82 * ey[mask] + 0.18 * drive * dir_y
        ex = _low_pass_field(ex, smoothing_mask, strength=0.12, passes=1)
        ey = _low_pass_field(ey, smoothing_mask, strength=0.12, passes=1)
        hz = _low_pass_field(hz, smoothing_mask, strength=0.08, passes=1)
        ex[1:-1, 1:-1] *= electric_interior_decay
        ey[1:-1, 1:-1] *= electric_interior_decay
        hz[1:-1, 1:-1] *= magnetic_interior_decay
        ex[context.pec_mask] = 0.0
        ey[context.pec_mask] = 0.0
        hz[0, :] = 0.0
        hz[-1, :] = 0.0
        hz[:, 0] = 0.0
        hz[:, -1] = 0.0
        ex[0, :] = 0.0
        ex[-1, :] = 0.0
        ey[:, 0] = 0.0
        ey[:, -1] = 0.0

        electric_frames[frame_index] = np.hypot(ex, ey)
        magnetic_frames[frame_index] = MU_0 * context.mu_r * np.abs(hz)

    return FieldWaveSequence(
        bounds_px=static.bounds_px,
        x_grid_px=static.x_grid_px,
        y_grid_px=static.y_grid_px,
        potential_v=static.potential_v,
        electric_frames_v_m=electric_frames,
        magnetic_frames_t=magnetic_frames,
        conductor_mask=context.pec_mask,
        metadata={
            "grid_width": int(nx),
            "grid_height": int(ny),
            "scale_m_per_px": float(context.scale_m_per_px),
            "time_step_s": float(dt_s),
            "steps": int(steps),
            "materials_count": int(context.materials_count),
            "ports_count": int(context.ports_count),
            "solver": "maxwell_2d_tez",
            "note": note,
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
    mode: str = "tmz",
) -> FieldWaveSequence:
    del source_period_steps, source_gain
    context = _build_field_context(
        circuit,
        result,
        grid_width=grid_width,
        grid_height=grid_height,
        padding_px=padding_px,
        iterations=iterations,
    )
    selected_mode = str(mode).lower()
    if selected_mode == "tmz":
        return _simulate_tmz(context, steps=steps, edge_absorber_cells=edge_absorber_cells)
    if selected_mode == "tez":
        return _simulate_tez(context, steps=steps, edge_absorber_cells=edge_absorber_cells)
    raise ValueError(f"Unsupported Maxwell mode: {mode}")


def simulate_full_wave_maxwell_2d_tez(
    circuit: Circuit,
    result: SimulationResult,
    **kwargs: Any,
) -> FieldWaveSequence:
    return simulate_full_wave_maxwell_2d(circuit, result, mode="tez", **kwargs)


def simulate_full_wave_maxwell_3d(
    circuit: Circuit,
    result: SimulationResult,
    *,
    grid_width: int = 108,
    grid_height: int = 84,
    grid_depth: int = 17,
    steps: int = 40,
    padding_px: float = 90.0,
    iterations: int = 420,
    edge_absorber_cells: int = 6,
    conductor_thickness_cells: int = 2,
) -> FieldVolumeSequence:
    del conductor_thickness_cells
    context = _build_field_context(
        circuit,
        result,
        grid_width=grid_width,
        grid_height=grid_height,
        padding_px=padding_px,
        iterations=iterations,
    )
    static = context.snapshot
    ny, nx = static.potential_v.shape
    nz = max(int(grid_depth), 7)
    x_extent_m = max((static.bounds_px[2] - static.bounds_px[0]) * context.scale_m_per_px, context.dx_m)
    y_extent_m = max((static.bounds_px[3] - static.bounds_px[1]) * context.scale_m_per_px, context.dy_m)
    z_extent_m = max(min(x_extent_m, y_extent_m) * 0.42, 12.0 * min(context.dx_m, context.dy_m))
    z_min_m = -0.5 * z_extent_m
    z_max_m = 0.5 * z_extent_m
    z_coords_m = np.linspace(z_min_m, z_max_m, nz, dtype=float)
    dz_m = max((z_max_m - z_min_m) / max(nz - 1, 1), 1.0e-9)

    x_coords_px = static.x_grid_px[0, :].copy()
    y_coords_px = static.y_grid_px[:, 0].copy()
    epsilon_3d, sigma_3d, mu_3d, materials = _build_material_maps_3d(circuit, context, x_coords_px, y_coords_px, z_coords_m)
    conductor_mask_3d = _build_conductor_mask_3d(circuit, context, z_coords_m, static.bounds_px, nx, ny)
    port_entries, port_mask_3d = _build_port_masks_3d(context.ports, x_coords_px, y_coords_px, z_coords_m)
    conductor_mask_3d &= ~port_mask_3d

    potential_volume = np.zeros((nz, ny, nx), dtype=float)
    material_weight = np.clip(np.sqrt(epsilon_3d / np.maximum(mu_3d, 1.0e-9)), 0.4, 3.0)
    for z_index, z_coord in enumerate(z_coords_m):
        surface_weight = 0.0
        if np.any(conductor_mask_3d[z_index]):
            surface_weight = 1.0
        else:
            distance_to_plane = min(abs(z_coord - _component_layout_z_center_m(component)) for component in circuit.components) if circuit.components else abs(z_coord)
            surface_weight = math.exp(-distance_to_plane / max(0.18 * z_extent_m, 1.0e-9))
        potential_volume[z_index] = static.potential_v * surface_weight / material_weight[z_index]
        if np.any(conductor_mask_3d[z_index]):
            potential_volume[z_index][conductor_mask_3d[z_index]] = static.potential_v[conductor_mask_3d[z_index]]

    c0 = 1.0 / math.sqrt(EPSILON_0 * MU_0)
    max_phase_velocity = c0 / math.sqrt(max(float(np.min(epsilon_3d * mu_3d)), 1.0e-9))
    dt_s = 0.16 / (max_phase_velocity * math.sqrt((1.0 / context.dx_m ** 2) + (1.0 / context.dy_m ** 2) + (1.0 / dz_m ** 2)))
    note = _field_mode_note(context, dt_s * steps)
    layer_count = sum(1 for region in materials if str(region.get("layer_mode", "volume")).lower() == "stack")
    extrude_note = (
        "3D-объем из 2D сцены: учтены толщина проводников, порты и материальные слои по Z."
        if layer_count
        else "3D-объем из 2D сцены: учтены толщина проводников и портов по Z."
    )
    if note:
        note = f"{note} {extrude_note}"
    else:
        note = extrude_note

    ex = np.zeros((nz, ny, nx), dtype=float)
    ey = np.zeros((nz, ny, nx), dtype=float)
    ez = np.zeros((nz, ny, nx), dtype=float)
    hx = np.zeros((nz, ny, nx), dtype=float)
    hy = np.zeros((nz, ny, nx), dtype=float)
    hz = np.zeros((nz, ny, nx), dtype=float)
    electric_frames = np.zeros((steps, nz, ny, nx), dtype=float)
    magnetic_frames = np.zeros((steps, nz, ny, nx), dtype=float)

    absorber_cells = max(edge_absorber_cells, 3)
    sigma_absorb = np.zeros((nz, ny, nx), dtype=float)
    sigma_max = 0.75 * EPSILON_0 / max(dt_s, 1.0e-18)
    for z in range(nz):
        for y in range(ny):
            for x in range(nx):
                dist = min(x, nx - 1 - x, y, ny - 1 - y, z, nz - 1 - z)
                if dist < absorber_cells:
                    ratio = (absorber_cells - dist) / absorber_cells
                    sigma_absorb[z, y, x] = sigma_max * ratio * ratio

    eps = EPSILON_0 * epsilon_3d
    mu = MU_0 * mu_3d
    sigma_e = sigma_3d + sigma_absorb
    sigma_h = sigma_absorb
    decay_e = (1.0 - sigma_e * dt_s / (2.0 * eps)) / np.maximum(1.0 + sigma_e * dt_s / (2.0 * eps), 1.0e-9)
    drive_e = dt_s / np.maximum(eps * (1.0 + sigma_e * dt_s / (2.0 * eps)), 1.0e-18)
    decay_h = np.exp(-sigma_h * dt_s / np.maximum(mu, 1.0e-18))
    frozen_mask = conductor_mask_3d | port_mask_3d

    for frame_index in range(steps):
        curl_h_x = _central_diff_axis(hz, context.dy_m, 1) - _central_diff_axis(hy, dz_m, 0)
        curl_h_y = _central_diff_axis(hx, dz_m, 0) - _central_diff_axis(hz, context.dx_m, 2)
        curl_h_z = _central_diff_axis(hy, context.dx_m, 2) - _central_diff_axis(hx, context.dy_m, 1)
        ex = decay_e * ex + drive_e * curl_h_x
        ey = decay_e * ey + drive_e * curl_h_y
        ez = decay_e * ez + drive_e * curl_h_z

        time_s = frame_index * dt_s
        ramp_s = max(8.0 * dt_s, 1.0e-12)
        for port in port_entries:
            drive = _port_signal(port, time_s, ramp_s)
            mask = port["mask_3d"]
            angle = math.radians(float(port.get("rotation_deg", 0.0)))
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            if str(port.get("source_kind", "voltage")).lower() == "current":
                ez[mask] += 0.12 * drive * dt_s / np.maximum(eps[mask], 1.0e-18)
            else:
                ex[mask] = 0.88 * ex[mask] + 0.12 * drive * dir_x
                ey[mask] = 0.88 * ey[mask] + 0.12 * drive * dir_y
                ez[mask] = 0.92 * ez[mask]

        ex = _low_pass_volume(ex, frozen_mask, strength=0.07, passes=1)
        ey = _low_pass_volume(ey, frozen_mask, strength=0.07, passes=1)
        ez = _low_pass_volume(ez, frozen_mask, strength=0.07, passes=1)

        ex[conductor_mask_3d] = 0.0
        ey[conductor_mask_3d] = 0.0
        ez[conductor_mask_3d] = 0.0
        ex[0, :, :] = 0.0
        ex[-1, :, :] = 0.0
        ex[:, 0, :] = 0.0
        ex[:, -1, :] = 0.0
        ex[:, :, 0] = 0.0
        ex[:, :, -1] = 0.0
        ey[0, :, :] = 0.0
        ey[-1, :, :] = 0.0
        ey[:, 0, :] = 0.0
        ey[:, -1, :] = 0.0
        ey[:, :, 0] = 0.0
        ey[:, :, -1] = 0.0
        ez[0, :, :] = 0.0
        ez[-1, :, :] = 0.0
        ez[:, 0, :] = 0.0
        ez[:, -1, :] = 0.0
        ez[:, :, 0] = 0.0
        ez[:, :, -1] = 0.0

        curl_e_x = _central_diff_axis(ez, context.dy_m, 1) - _central_diff_axis(ey, dz_m, 0)
        curl_e_y = _central_diff_axis(ex, dz_m, 0) - _central_diff_axis(ez, context.dx_m, 2)
        curl_e_z = _central_diff_axis(ey, context.dx_m, 2) - _central_diff_axis(ex, context.dy_m, 1)
        hx = decay_h * (hx - dt_s * curl_e_x / np.maximum(mu, 1.0e-18))
        hy = decay_h * (hy - dt_s * curl_e_y / np.maximum(mu, 1.0e-18))
        hz = decay_h * (hz - dt_s * curl_e_z / np.maximum(mu, 1.0e-18))
        hx = _low_pass_volume(hx, frozen_mask, strength=0.05, passes=1)
        hy = _low_pass_volume(hy, frozen_mask, strength=0.05, passes=1)
        hz = _low_pass_volume(hz, frozen_mask, strength=0.05, passes=1)
        hx[0, :, :] = 0.0
        hx[-1, :, :] = 0.0
        hx[:, 0, :] = 0.0
        hx[:, -1, :] = 0.0
        hx[:, :, 0] = 0.0
        hx[:, :, -1] = 0.0
        hy[0, :, :] = 0.0
        hy[-1, :, :] = 0.0
        hy[:, 0, :] = 0.0
        hy[:, -1, :] = 0.0
        hy[:, :, 0] = 0.0
        hy[:, :, -1] = 0.0
        hz[0, :, :] = 0.0
        hz[-1, :, :] = 0.0
        hz[:, 0, :] = 0.0
        hz[:, -1, :] = 0.0
        hz[:, :, 0] = 0.0
        hz[:, :, -1] = 0.0

        electric_frames[frame_index] = np.sqrt(ex * ex + ey * ey + ez * ez)
        magnetic_frames[frame_index] = MU_0 * mu_3d * np.sqrt(hx * hx + hy * hy + hz * hz)

    return FieldVolumeSequence(
        bounds_px=static.bounds_px,
        z_bounds_m=(float(z_min_m), float(z_max_m)),
        x_coords_px=x_coords_px,
        y_coords_px=y_coords_px,
        z_coords_m=z_coords_m,
        potential_v=potential_volume,
        electric_frames_v_m=electric_frames,
        magnetic_frames_t=magnetic_frames,
        conductor_mask=conductor_mask_3d,
        metadata={
            "grid_width": int(nx),
            "grid_height": int(ny),
            "grid_depth": int(nz),
            "scale_m_per_px": float(context.scale_m_per_px),
            "time_step_s": float(dt_s),
            "steps": int(steps),
            "materials_count": int(context.materials_count),
            "material_layers_count": int(layer_count),
            "ports_count": int(context.ports_count),
            "solver": "maxwell_3d_extruded",
            "note": note,
        },
    )
