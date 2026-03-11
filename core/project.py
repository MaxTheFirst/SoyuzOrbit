from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .components import COMPONENT_LIBRARY, COMPONENT_TERMINALS, create_component
from .engine import Circuit

GROUND_KIND = "Ground"
NON_ACTIVE_KINDS = {"Ground", "Junction"}
GROUND_NAMES = {"0", "gnd", "GND", "ground", "GROUND"}
SCHEMA_VERSION = 3
WIRE_KIND = "Wire"


@dataclass(slots=True)
class PinRef:
    component_id: int
    terminal_index: int


@dataclass(slots=True)
class WireRecord:
    wire_id: int
    a: PinRef
    b: PinRef
    params: dict[str, Any] = field(default_factory=dict)
    route_points: list[tuple[float, float]] = field(default_factory=list)
    path_length_px: float = 0.0
    a_position: tuple[float, float] = (0.0, 0.0)
    b_position: tuple[float, float] = (0.0, 0.0)


@dataclass(slots=True)
class ComponentRecord:
    component_id: int
    kind: str
    name: str
    x: float
    y: float
    rotation_deg: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)
    terminal_positions: list[tuple[float, float]] = field(default_factory=list)


@dataclass(slots=True)
class MaterialRegionRecord:
    region_id: int
    name: str
    x: float
    y: float
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FieldPortRecord:
    port_id: int
    name: str
    x: float
    y: float
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectSettings:
    duration_s: float = 0.03
    dt_s: float = 1.0e-4


def wire_component_name(wire_id: int) -> str:
    return f"__wire__{wire_id}"


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(_distance(points[index], points[index + 1]) for index in range(len(points) - 1))


def _sample_polyline(points: list[tuple[float, float]], samples: int) -> list[tuple[float, float]]:
    if samples <= 1 or len(points) < 2:
        return [points[0], points[-1]]
    total_length = _polyline_length(points)
    if total_length <= 1.0e-9:
        return [points[0] for _ in range(samples + 1)]
    targets = [total_length * index / samples for index in range(samples + 1)]
    result = [points[0]]
    traversed = 0.0
    segment_index = 0
    for target in targets[1:-1]:
        while segment_index < len(points) - 2:
            segment_length = _distance(points[segment_index], points[segment_index + 1])
            if traversed + segment_length >= target:
                break
            traversed += segment_length
            segment_index += 1
        start = points[segment_index]
        end = points[segment_index + 1]
        segment_length = max(_distance(start, end), 1.0e-12)
        ratio = (target - traversed) / segment_length
        result.append((start[0] + (end[0] - start[0]) * ratio, start[1] + (end[1] - start[1]) * ratio))
    result.append(points[-1])
    return result


@dataclass(slots=True)
class CircuitProject:
    name: str
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    components: list[ComponentRecord] = field(default_factory=list)
    wires: list[WireRecord] = field(default_factory=list)
    material_regions: list[MaterialRegionRecord] = field(default_factory=list)
    field_ports: list[FieldPortRecord] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    source_path: str | None = field(default=None, repr=False, compare=False)

    def validate(self) -> None:
        component_by_id = {component.component_id: component for component in self.components}
        component_ids = set(component_by_id)
        if len(component_ids) != len(self.components):
            raise ValueError("В проекте обнаружены повторяющиеся идентификаторы компонентов.")
        material_ids = {region.region_id for region in self.material_regions}
        if len(material_ids) != len(self.material_regions):
            raise ValueError("В проекте обнаружены повторяющиеся идентификаторы областей среды.")
        port_ids = {port.port_id for port in self.field_ports}
        if len(port_ids) != len(self.field_ports):
            raise ValueError("В проекте обнаружены повторяющиеся идентификаторы полевых портов.")
        for component in component_by_id.values():
            if component.kind not in COMPONENT_TERMINALS:
                raise ValueError(f"Неизвестный тип компонента: {component.kind}")
        for wire in self.wires:
            if wire.a.component_id not in component_ids or wire.b.component_id not in component_ids:
                raise ValueError(f"Провод {wire.wire_id} ссылается на отсутствующий компонент.")
            a_kind = component_by_id[wire.a.component_id].kind
            b_kind = component_by_id[wire.b.component_id].kind
            if wire.a.terminal_index >= len(COMPONENT_TERMINALS[a_kind]) or wire.b.terminal_index >= len(COMPONENT_TERMINALS[b_kind]):
                raise ValueError(f"Провод {wire.wire_id} ссылается на несуществующий вывод.")
        if self.settings.duration_s <= 0.0 or self.settings.dt_s <= 0.0:
            raise ValueError("Параметры симуляции должны быть положительными.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "settings": asdict(self.settings),
            "components": [asdict(component) for component in self.components],
            "material_regions": [asdict(region) for region in self.material_regions],
            "field_ports": [asdict(port) for port in self.field_ports],
            "wires": [
                {
                    "wire_id": wire.wire_id,
                    "a": asdict(wire.a),
                    "b": asdict(wire.b),
                    "params": dict(wire.params),
                    "route_points": [list(point) for point in wire.route_points],
                    "path_length_px": float(wire.path_length_px),
                    "a_position": list(wire.a_position),
                    "b_position": list(wire.b_position),
                }
                for wire in self.wires
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CircuitProject":
        settings = ProjectSettings(**data.get("settings", {}))
        components = [
            ComponentRecord(
                component_id=item["component_id"],
                kind=item["kind"],
                name=item["name"],
                x=float(item["x"]),
                y=float(item["y"]),
                rotation_deg=float(item.get("rotation_deg", 0.0)),
                params=dict(item.get("params", {})),
                terminal_positions=[
                    (float(point[0]), float(point[1]))
                    for point in item.get("terminal_positions", [])
                ],
            )
            for item in data.get("components", [])
        ]
        material_regions = [
            MaterialRegionRecord(
                region_id=item["region_id"],
                name=item["name"],
                x=float(item["x"]),
                y=float(item["y"]),
                params=dict(item.get("params", {})),
            )
            for item in data.get("material_regions", [])
        ]
        field_ports = [
            FieldPortRecord(
                port_id=item["port_id"],
                name=item["name"],
                x=float(item["x"]),
                y=float(item["y"]),
                params=dict(item.get("params", {})),
            )
            for item in data.get("field_ports", [])
        ]
        wires = [
            WireRecord(
                wire_id=item["wire_id"],
                a=PinRef(**item["a"]),
                b=PinRef(**item["b"]),
                params=dict(item.get("params", {})),
                route_points=[(float(point[0]), float(point[1])) for point in item.get("route_points", [])],
                path_length_px=float(item.get("path_length_px", 0.0)),
                a_position=tuple(float(value) for value in item.get("a_position", (0.0, 0.0))),
                b_position=tuple(float(value) for value in item.get("b_position", (0.0, 0.0))),
            )
            for item in data.get("wires", [])
        ]
        project = cls(
            name=data.get("name", "Новый проект"),
            settings=settings,
            components=components,
            wires=wires,
            material_regions=material_regions,
            field_ports=field_ports,
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
        )
        project.validate()
        return project

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "CircuitProject":
        source = Path(path)
        project = cls.from_dict(json.loads(source.read_text(encoding="utf-8")))
        project.source_path = str(source.resolve())
        return project

    def to_circuit(self) -> Circuit:
        self.validate()
        circuit = Circuit(self.name)
        circuit.field_material_regions = [
            {
                "name": region.name,
                "center_px": (float(region.x), float(region.y)),
                **dict(region.params),
            }
            for region in self.material_regions
        ]
        circuit.field_ports = [
            {
                "name": port.name,
                "center_px": (float(port.x), float(port.y)),
                **dict(port.params),
            }
            for port in self.field_ports
        ]
        pin_nodes: dict[tuple[int, int], str] = {}
        component_centers: dict[int, tuple[float, float]] = {}
        next_node_index = 1
        has_explicit_ground = any(component.kind == GROUND_KIND for component in self.components)
        first_non_ground_pin: tuple[int, int] | None = None

        for component in sorted(self.components, key=lambda entry: entry.component_id):
            terminal_count = len(COMPONENT_TERMINALS[component.kind])
            for terminal_index in range(terminal_count):
                pin = (component.component_id, terminal_index)
                if component.kind == GROUND_KIND:
                    pin_nodes[pin] = "0"
                    continue
                if first_non_ground_pin is None:
                    first_non_ground_pin = pin
                pin_nodes[pin] = f"n{next_node_index}"
                next_node_index += 1

        if not has_explicit_ground and first_non_ground_pin is not None:
            pin_nodes[first_non_ground_pin] = "0"

        for component in self.components:
            component_centers[component.component_id] = (component.x, component.y)
            if component.kind in NON_ACTIVE_KINDS:
                continue
            terminal_count = len(COMPONENT_TERMINALS[component.kind])
            node_list = [pin_nodes[(component.component_id, terminal_index)] for terminal_index in range(terminal_count)]
            params = dict(component.params)
            if component.kind == "WAV Source":
                raw_path = params.get("audio_path", params.get("wav_path"))
                if isinstance(raw_path, str) and raw_path and not Path(raw_path).is_absolute() and self.source_path is not None:
                    project_relative = (Path(self.source_path).parent / raw_path).resolve()
                    cwd_relative = Path(raw_path).resolve()
                    if project_relative.exists() or not cwd_relative.exists():
                        resolved_path = str(project_relative)
                    else:
                        resolved_path = str(cwd_relative)
                    if "audio_path" in params:
                        params["audio_path"] = resolved_path
                    else:
                        params["wav_path"] = resolved_path
            instance = create_component(component.kind, component.name, node_list, **params)
            instance.group_name = component.name
            instance.layout_position_px = (component.x, component.y)
            instance.layout_points_px = component.terminal_positions or [(component.x, component.y)]
            instance.layout_rotation_deg = component.rotation_deg
            circuit.add(instance)

        wire_defaults = COMPONENT_LIBRARY[WIRE_KIND][1]
        for wire in sorted(self.wires, key=lambda entry: entry.wire_id):
            node_a = pin_nodes[(wire.a.component_id, wire.a.terminal_index)]
            node_b = pin_nodes[(wire.b.component_id, wire.b.terminal_index)]
            params = dict(wire_defaults)
            params.update(wire.params)
            meters_per_pixel = float(params.get("meters_per_pixel", wire_defaults.get("meters_per_pixel", 0.002)))
            a_position = wire.a_position if any(abs(value) > 1.0e-9 for value in wire.a_position) else component_centers[wire.a.component_id]
            b_position = wire.b_position if any(abs(value) > 1.0e-9 for value in wire.b_position) else component_centers[wire.b.component_id]
            full_points = [a_position, *wire.route_points, b_position]
            if params.get("auto_length_from_path", True):
                effective_path_px = wire.path_length_px if wire.path_length_px > 0.0 else _polyline_length(full_points)
                params["length_m"] = max(effective_path_px * meters_per_pixel, 1.0e-6)

            total_length_m = max(float(params.get("length_m", 0.3)), 1.0e-6)
            target_segment_m = max(float(params.get("segment_length_target_m", total_length_m)), 1.0e-6)
            max_segments = max(int(params.get("max_segments", 1)), 1)
            segment_count = max(1, min(max_segments, int(math.ceil(total_length_m / target_segment_m))))
            sampled_points = _sample_polyline(full_points, segment_count)
            sampled_length_px = max(_polyline_length(sampled_points), 1.0e-9)
            segment_defaults = dict(params)
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
                segment_defaults.pop(key, None)

            previous_node = node_a
            group_name = wire_component_name(wire.wire_id)
            for segment_index in range(segment_count):
                next_node = node_b if segment_index == segment_count - 1 else f"n{next_node_index}"
                if segment_index != segment_count - 1:
                    next_node_index += 1
                start_point = sampled_points[segment_index]
                end_point = sampled_points[segment_index + 1]
                segment_length_px = _distance(start_point, end_point)
                segment_length_m = max(total_length_m * segment_length_px / sampled_length_px, total_length_m / segment_count)
                segment_params = dict(segment_defaults)
                segment_params["length_m"] = segment_length_m
                segment = create_component(WIRE_KIND, f"{group_name}__seg{segment_index + 1}", [previous_node, next_node], **segment_params)
                segment.group_name = group_name
                segment.layout_position_px = ((start_point[0] + end_point[0]) * 0.5, (start_point[1] + end_point[1]) * 0.5)
                segment.layout_points_px = [start_point, end_point]
                segment.geometry_scale_m_per_px = meters_per_pixel
                segment.electromagnetic_gain = float(params.get("coupling_gain", 1.0))
                segment.permittivity_scale = float(params.get("permittivity_scale", 1.0))
                segment.mutual_inductance_gain = float(params.get("mutual_inductance_gain", 1.0))
                segment.thermal_coupling_gain = float(params.get("thermal_coupling_gain", 1.0))
                circuit.add(segment)
                previous_node = next_node
        return circuit


def save_project(path: str | Path, project: CircuitProject) -> Path:
    return project.save(path)


def load_project(path: str | Path) -> CircuitProject:
    return CircuitProject.load(path)
