from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QTransform
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from core import (
    CircuitProject,
    ComponentRecord,
    FieldPortRecord,
    MaterialRegionRecord,
    PinRef,
    ProjectSettings,
    WireRecord,
    wire_component_name,
)
from core.physics import MATERIALS, wire_resistance

from .components_visual import build_qpixmap, default_params, default_visual_state, template_for


NAME_PREFIXES = {
    "Ground": "Земля",
    "Junction": "Точка",
    "Battery": "Батарея",
    "AC Generator": "Генератор",
    "Pulse Generator": "ИмпГен",
    "Resistor": "Резистор",
    "Thermistor": "Термистор",
    "Photoresistor": "Фоторезистор",
    "Capacitor": "Конденсатор",
    "Inductor": "Катушка",
    "Wire": "Провод",
    "Diode": "Диод",
    "LED": "Светодиод",
    "Varistor": "Варистор",
    "Fuse": "Предохранитель",
    "Bulb": "Лампа",
    "Ammeter": "Амперметр",
    "Voltmeter": "Вольтметр",
    "Switch": "Переключатель",
    "MOSFET": "MOSFET",
    "OpAmp": "ОУ",
    "FieldMaterial": "Среда",
    "FieldPort": "Порт",
}

FIELD_MATERIAL_DEFAULTS = {
    "width_px": 220.0,
    "height_px": 140.0,
    "rotation_deg": 0.0,
    "z_center_m": -0.0012,
    "thickness_m": 0.0016,
    "layer_mode": "volume",
    "epsilon_r": 4.2,
    "sigma_s_per_m": 0.0,
    "mu_r": 1.0,
}

FIELD_PORT_DEFAULTS = {
    "width_px": 90.0,
    "height_px": 18.0,
    "rotation_deg": 0.0,
    "z_center_m": 0.0,
    "thickness_m": 0.0009,
    "source_kind": "voltage",
    "waveform": "sine",
    "amplitude_v": 5.0,
    "amplitude_a": 0.2,
    "frequency_hz": 1.0e6,
    "phase_rad": 0.0,
    "impedance_ohm": 50.0,
}


def _point_distance(a: QPointF, b: QPointF) -> float:
    return math.hypot(b.x() - a.x(), b.y() - a.y())


def _distance_to_segment(point: QPointF, a: QPointF, b: QPointF) -> float:
    dx = b.x() - a.x()
    dy = b.y() - a.y()
    if abs(dx) < 1.0e-9 and abs(dy) < 1.0e-9:
        return _point_distance(point, a)
    t = ((point.x() - a.x()) * dx + (point.y() - a.y()) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    projection = QPointF(a.x() + t * dx, a.y() + t * dy)
    return _point_distance(point, projection)


class TerminalItem(QGraphicsEllipseItem):
    def __init__(self, component_item: "ComponentItem", terminal_index: int, x: float, y: float) -> None:
        super().__init__(-6.0, -6.0, 12.0, 12.0, component_item)
        self.component_item = component_item
        self.terminal_index = terminal_index
        self.wires: list[WireItem] = []
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#164e63")))
        self.setPen(QPen(QColor("#d9f2ff"), 2.0))
        self.setZValue(20)

    def highlight(self, active: bool) -> None:
        self.setBrush(QBrush(QColor("#f97316") if active else QColor("#164e63")))

    def center_in_scene(self) -> QPointF:
        return self.mapToScene(self.rect().center())

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.component_item.scene_controller is not None:
            self.component_item.scene_controller.handle_terminal_click(self)
        event.accept()


class WireHandleItem(QGraphicsEllipseItem):
    def __init__(self, wire_item: "WireItem", index: int, position: QPointF) -> None:
        super().__init__(-6.0, -6.0, 12.0, 12.0, wire_item)
        self.wire_item = wire_item
        self.index = index
        self.setPos(position)
        self.setZValue(12)
        self.setBrush(QBrush(QColor("#f97316")))
        self.setPen(QPen(QColor("#fff7ed"), 2.0))
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.wire_item.move_route_point(self.index, value)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.wire_item.remove_route_point(self.index)
        event.accept()


class RectTransformHandleItem(QGraphicsEllipseItem):
    def __init__(self, owner: QGraphicsRectItem, role: str, position: QPointF, color: str) -> None:
        super().__init__(-6.0, -6.0, 12.0, 12.0, owner)
        self.owner = owner
        self.role = role
        self.setPos(position)
        self.setZValue(16)
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#fff7ed"), 2.0))
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and hasattr(self.owner, "handle_transform_drag"):
            self.owner.handle_transform_drag(self.role, value)
        return super().itemChange(change, value)


class WireItem(QGraphicsPathItem):
    def __init__(
        self,
        wire_id: int,
        a_terminal: TerminalItem,
        b_terminal: TerminalItem,
        params: dict[str, Any] | None = None,
        route_points: list[tuple[float, float]] | None = None,
    ) -> None:
        super().__init__()
        self.wire_id = wire_id
        self.a_terminal = a_terminal
        self.b_terminal = b_terminal
        self.params = default_params("Wire")
        if params:
            self.params.update(params)
        self.route_points = [QPointF(float(point[0]), float(point[1])) for point in (route_points or [])]
        self.route_handles: list[WireHandleItem] = []
        self.temperature_c = 25.0
        self.component_name = wire_component_name(wire_id)
        self.info_item = QGraphicsSimpleTextItem("", self)
        self.info_item.setZValue(11)
        self.info_item.setBrush(QBrush(QColor("#475569")))
        self.setZValue(-10)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._apply_pen()
        self.update_path()
        a_terminal.wires.append(self)
        b_terminal.wires.append(self)

    def path_points(self) -> list[QPointF]:
        return [self.a_terminal.center_in_scene(), *self.route_points, self.b_terminal.center_in_scene()]

    def path_length_px(self) -> float:
        points = self.path_points()
        return sum(_point_distance(points[index], points[index + 1]) for index in range(len(points) - 1))

    def effective_length_m(self) -> float:
        if bool(self.params.get("auto_length_from_path", True)):
            meters_per_pixel = max(float(self.params.get("meters_per_pixel", 0.002)), 1.0e-6)
            return max(self.path_length_px() * meters_per_pixel, 1.0e-6)
        return max(float(self.params.get("length_m", 0.3)), 1.0e-6)

    def estimated_resistance_ohm(self) -> float:
        material_key = str(self.params.get("material", "copper")).lower()
        material = MATERIALS.get(material_key, MATERIALS["copper"])
        area_mm2 = max(float(self.params.get("area_mm2", 0.75)), 1.0e-6)
        contact = max(float(self.params.get("contact_resistance_ohm", 0.0)), 0.0)
        return wire_resistance(self.effective_length_m(), area_mm2, material, self.temperature_c) + contact

    def _sync_route_handles(self) -> None:
        while len(self.route_handles) < len(self.route_points):
            self.route_handles.append(WireHandleItem(self, len(self.route_handles), QPointF()))
        while len(self.route_handles) > len(self.route_points):
            handle = self.route_handles.pop()
            if handle.scene() is not None:
                handle.scene().removeItem(handle)
        visible = self.isSelected()
        for index, handle in enumerate(self.route_handles):
            handle.index = index
            if _point_distance(handle.pos(), self.route_points[index]) > 0.1:
                handle.setPos(self.route_points[index])
            handle.setVisible(visible)

    def _update_info_label(self) -> None:
        length_m = self.effective_length_m()
        area_mm2 = float(self.params.get("area_mm2", 0.75))
        resistance = self.estimated_resistance_ohm()
        text = f"L={length_m:.3f} м | S={area_mm2:.3g} мм² | R≈{resistance:.4f} Ω"
        if bool(self.params.get("auto_length_from_path", True)):
            text += " | auto"
        self.info_item.setText(text)
        midpoint = self.path().pointAtPercent(0.5) if not self.path().isEmpty() else self.a_terminal.center_in_scene()
        rect = self.info_item.boundingRect()
        self.info_item.setPos(midpoint.x() - rect.width() / 2, midpoint.y() - rect.height() - 10)
        self.info_item.setVisible(self.isSelected())

    def _line_width(self) -> float:
        area_mm2 = max(float(self.params.get("area_mm2", 0.75)), 0.01)
        base = 2.4 + 2.2 * min(math.sqrt(area_mm2), 4.0)
        return base + (1.2 if self.isSelected() else 0.0)

    def _apply_pen(self) -> None:
        heat = max(0.0, min(1.0, (self.temperature_c - 25.0) / 120.0))
        cold = QColor("#314d5f")
        warm = QColor("#b45309")
        hot = QColor("#b91c1c")
        if heat < 0.6:
            mix = heat / 0.6 if heat > 0.0 else 0.0
            color = QColor(
                int(cold.red() + (warm.red() - cold.red()) * mix),
                int(cold.green() + (warm.green() - cold.green()) * mix),
                int(cold.blue() + (warm.blue() - cold.blue()) * mix),
            )
        else:
            mix = (heat - 0.6) / 0.4
            color = QColor(
                int(warm.red() + (hot.red() - warm.red()) * mix),
                int(warm.green() + (hot.green() - warm.green()) * mix),
                int(warm.blue() + (hot.blue() - warm.blue()) * mix),
            )
        if self.isSelected():
            color = QColor("#d97706") if heat < 0.85 else QColor("#dc2626")
        self.setPen(QPen(color, self._line_width(), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    def apply_params(self, updated: dict[str, Any]) -> None:
        self.params.update(updated)
        self.refresh_visuals()

    def apply_observables(self, observables: dict[str, float]) -> None:
        self.temperature_c = float(observables.get("temperature_c", self.temperature_c))
        self.refresh_visuals()

    def refresh_visuals(self) -> None:
        self._apply_pen()
        self.update_path()

    def update_path(self) -> None:
        points = self.path_points()
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        self.setPath(path)
        self._sync_route_handles()
        self._update_info_label()

    def move_route_point(self, index: int, value: QPointF) -> None:
        if 0 <= index < len(self.route_points):
            self.route_points[index] = QPointF(value)
            self.update_path()

    def add_route_point(self, point: QPointF) -> None:
        points = self.path_points()
        best_segment = 0
        best_distance = float("inf")
        for index in range(len(points) - 1):
            distance = _distance_to_segment(point, points[index], points[index + 1])
            if distance < best_distance:
                best_distance = distance
                best_segment = index
        self.route_points.insert(best_segment, QPointF(point))
        self.update_path()

    def remove_route_point(self, index: int) -> None:
        if 0 <= index < len(self.route_points):
            self.route_points.pop(index)
            self.update_path()

    def clear_route_points(self) -> None:
        self.route_points.clear()
        self.update_path()

    def route_points_data(self) -> list[tuple[float, float]]:
        return [(float(point.x()), float(point.y())) for point in self.route_points]

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._apply_pen()
            self._sync_route_handles()
            self._update_info_label()
        return super().itemChange(change, value)


class MaterialRegionItem(QGraphicsRectItem):
    def __init__(
        self,
        scene_controller: "CircuitScene",
        region_id: int,
        name: str,
        position: QPointF,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.scene_controller = scene_controller
        self.region_id = region_id
        self.kind = "FieldMaterial"
        self.name = name
        self.params = dict(FIELD_MATERIAL_DEFAULTS)
        if params:
            self.params.update(params)
        self.label_item = QGraphicsSimpleTextItem(self.name, self)
        self.label_item.setZValue(2)
        self.transform_handles: dict[str, RectTransformHandleItem] = {}
        self._updating_handles = False
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(-35)
        self.setPos(position)
        self.refresh_visuals()

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.label_item.setText(new_name)
        self.refresh_visuals()

    def refresh_visuals(self) -> None:
        width = max(float(self.params.get("width_px", 220.0)), 18.0)
        height = max(float(self.params.get("height_px", 140.0)), 18.0)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setRotation(float(self.params.get("rotation_deg", 0.0)))
        layer_mode = str(self.params.get("layer_mode", "volume")).lower()
        epsilon_r = max(float(self.params.get("epsilon_r", 1.0)), 1.0)
        sigma = max(float(self.params.get("sigma_s_per_m", 0.0)), 0.0)
        mu_r = max(float(self.params.get("mu_r", 1.0)), 0.1)
        alpha = min(120 + int(12 * epsilon_r), 185)
        border = QColor("#0f766e") if not self.isSelected() else QColor("#d97706")
        fill = QColor(62, 142, 197, alpha)
        if sigma > 1.0e3:
            fill = QColor(90, 94, 99, min(210, alpha + 35))
        if mu_r > 1.5:
            fill = QColor(117, 76, 36, min(200, alpha + 18))
        pen = QPen(border, 2.0, Qt.PenStyle.DashLine if layer_mode == "stack" else Qt.PenStyle.SolidLine)
        self.setPen(pen)
        self.setBrush(QBrush(fill))
        text_color = QColor("#7c2d12") if self.isSelected() else QColor("#134e4a")
        self.label_item.setBrush(QBrush(text_color))
        text_rect = self.label_item.boundingRect()
        suffix = " [Layer]" if layer_mode == "stack" else ""
        self.label_item.setText(f"{self.name}{suffix}")
        text_rect = self.label_item.boundingRect()
        self.label_item.setPos(-text_rect.width() / 2, -height / 2 - text_rect.height() - 6)
        self._sync_transform_handles()
        self.update()

    def apply_params(self, updated: dict[str, Any]) -> None:
        self.params.update(updated)
        self.refresh_visuals()

    def to_record(self) -> MaterialRegionRecord:
        pos = self.pos()
        return MaterialRegionRecord(
            region_id=self.region_id,
            name=self.name,
            x=float(pos.x()),
            y=float(pos.y()),
            params=dict(self.params),
        )

    def _sync_transform_handles(self) -> None:
        if "resize" not in self.transform_handles:
            self.transform_handles["resize"] = RectTransformHandleItem(self, "resize", QPointF(), "#22c55e")
            self.transform_handles["rotate"] = RectTransformHandleItem(self, "rotate", QPointF(), "#2563eb")
        width = max(float(self.params.get("width_px", 220.0)), 18.0)
        height = max(float(self.params.get("height_px", 140.0)), 18.0)
        visible = self.isSelected()
        self._updating_handles = True
        self.transform_handles["resize"].setPos(QPointF(width * 0.5, height * 0.5))
        self.transform_handles["rotate"].setPos(QPointF(0.0, -height * 0.5 - 24.0))
        self._updating_handles = False
        for handle in self.transform_handles.values():
            handle.setVisible(visible)

    def handle_transform_drag(self, role: str, value: QPointF) -> None:
        if self._updating_handles:
            return
        point = QPointF(value)
        if role == "resize":
            self.params["width_px"] = max(abs(point.x()) * 2.0, 18.0)
            self.params["height_px"] = max(abs(point.y()) * 2.0, 18.0)
        elif role == "rotate":
            scene_center = self.mapToScene(QPointF(0.0, 0.0))
            scene_point = self.mapToScene(point)
            self.params["rotation_deg"] = math.degrees(math.atan2(scene_point.y() - scene_center.y(), scene_point.x() - scene_center.x())) + 90.0
        self.refresh_visuals()

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.refresh_visuals()
        return super().itemChange(change, value)


class FieldPortItem(QGraphicsRectItem):
    def __init__(
        self,
        scene_controller: "CircuitScene",
        port_id: int,
        name: str,
        position: QPointF,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.scene_controller = scene_controller
        self.port_id = port_id
        self.kind = "FieldPort"
        self.name = name
        self.params = dict(FIELD_PORT_DEFAULTS)
        if params:
            self.params.update(params)
        self.label_item = QGraphicsSimpleTextItem(self.name, self)
        self.label_item.setZValue(2)
        self.transform_handles: dict[str, RectTransformHandleItem] = {}
        self._updating_handles = False
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(-18)
        self.setPos(position)
        self.refresh_visuals()

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.label_item.setText(new_name)
        self.refresh_visuals()

    def refresh_visuals(self) -> None:
        width = max(float(self.params.get("width_px", 90.0)), 10.0)
        height = max(float(self.params.get("height_px", 18.0)), 6.0)
        self.setRect(-width / 2, -height / 2, width, height)
        self.setRotation(float(self.params.get("rotation_deg", 0.0)))
        source_kind = str(self.params.get("source_kind", "voltage")).lower()
        fill = QColor("#7c3aed" if source_kind == "current" else "#0f766e")
        if self.isSelected():
            fill = QColor("#d97706")
        fill.setAlpha(185)
        self.setPen(QPen(QColor("#f8fafc"), 1.6))
        self.setBrush(QBrush(fill))
        self.label_item.setBrush(QBrush(QColor("#5b21b6") if source_kind == "current" else QColor("#064e3b")))
        if self.isSelected():
            self.label_item.setBrush(QBrush(QColor("#92400e")))
        text_rect = self.label_item.boundingRect()
        self.label_item.setPos(-text_rect.width() / 2, -height / 2 - text_rect.height() - 6)
        self._sync_transform_handles()
        self.update()

    def apply_params(self, updated: dict[str, Any]) -> None:
        self.params.update(updated)
        self.refresh_visuals()

    def to_record(self) -> FieldPortRecord:
        pos = self.pos()
        return FieldPortRecord(
            port_id=self.port_id,
            name=self.name,
            x=float(pos.x()),
            y=float(pos.y()),
            params=dict(self.params),
        )

    def _sync_transform_handles(self) -> None:
        if "resize" not in self.transform_handles:
            self.transform_handles["resize"] = RectTransformHandleItem(self, "resize", QPointF(), "#22c55e")
            self.transform_handles["rotate"] = RectTransformHandleItem(self, "rotate", QPointF(), "#2563eb")
        width = max(float(self.params.get("width_px", 90.0)), 10.0)
        height = max(float(self.params.get("height_px", 18.0)), 6.0)
        visible = self.isSelected()
        self._updating_handles = True
        self.transform_handles["resize"].setPos(QPointF(width * 0.5, height * 0.5))
        self.transform_handles["rotate"].setPos(QPointF(0.0, -height * 0.5 - 24.0))
        self._updating_handles = False
        for handle in self.transform_handles.values():
            handle.setVisible(visible)

    def handle_transform_drag(self, role: str, value: QPointF) -> None:
        if self._updating_handles:
            return
        point = QPointF(value)
        if role == "resize":
            self.params["width_px"] = max(abs(point.x()) * 2.0, 10.0)
            self.params["height_px"] = max(abs(point.y()) * 2.0, 6.0)
        elif role == "rotate":
            scene_center = self.mapToScene(QPointF(0.0, 0.0))
            scene_point = self.mapToScene(point)
            self.params["rotation_deg"] = math.degrees(math.atan2(scene_point.y() - scene_center.y(), scene_point.x() - scene_center.x())) + 90.0
        self.refresh_visuals()

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.refresh_visuals()
        return super().itemChange(change, value)


class ComponentItem(QGraphicsObject):
    def __init__(
        self,
        scene_controller: "CircuitScene",
        component_id: int,
        kind: str,
        name: str,
        position: QPointF,
        rotation_deg: float = 0.0,
        params: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.scene_controller = scene_controller
        self.component_id = component_id
        self.kind = kind
        self.name = name
        self.template = template_for(kind)
        self.params = default_params(kind)
        if params:
            self.params.update(params)
        self.state = default_visual_state(kind)
        if state:
            self.state.update(state)
        if kind == "LED":
            self.state["color"] = self.params.get("color", self.state.get("color", "red"))
        if kind == "Switch":
            self.state["closed"] = float(bool(self.params.get("closed", self.state.get("closed", 0.0))))
        self.pixmap = build_qpixmap(self.kind, self.state)
        self.label_item = QGraphicsSimpleTextItem(self.name, self)
        self.label_item.setZValue(30)
        self.label_item.setBrush(QBrush(QColor("#2b211a")))
        self.value_item = QGraphicsSimpleTextItem("", self)
        self.value_item.setZValue(31)
        self.terminals: list[TerminalItem] = []
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPos(position)
        self.setRotation(float(rotation_deg))
        self._build_terminals()
        self._update_overlay_text()
        self.setZValue(5)

    def _build_terminals(self) -> None:
        width, height = self.template.size
        for index, (tx, ty) in enumerate(self.template.terminals):
            local_x = -width / 2 + tx * width
            local_y = -height / 2 + ty * height
            self.terminals.append(TerminalItem(self, index, local_x, local_y))

    def _layout_label(self) -> None:
        width, height = self.template.size
        text_rect = self.label_item.boundingRect()
        self.label_item.setPos(-text_rect.width() / 2, height / 2 + 6)

    def _format_meter_reading(self) -> str:
        if self.kind == "Ammeter":
            if self.state.get("overload", 0.0):
                return "OL A"
            return f"{float(self.state.get('reading', 0.0)):.3f} A"
        if self.kind == "Voltmeter":
            if self.state.get("overload", 0.0):
                return "OL V"
            return f"{float(self.state.get('reading', 0.0)):.3f} V"
        return ""

    def _update_overlay_text(self) -> None:
        self._layout_label()
        if self.kind not in {"Ammeter", "Voltmeter"}:
            self.value_item.setVisible(False)
            return
        self.value_item.setVisible(True)
        self.value_item.setText(self._format_meter_reading())
        value_rect = self.value_item.boundingRect()
        width, height = self.template.size
        self.value_item.setPos(-value_rect.width() / 2, -height / 2 - value_rect.height() - 8)

    def rename(self, new_name: str) -> None:
        self.name = new_name
        self.label_item.setText(new_name)
        self._update_overlay_text()

    def boundingRect(self) -> QRectF:  # noqa: N802
        width, height = self.template.size
        return QRectF(-width / 2 - 12, -height / 2 - 34, width + 24, height + 70)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: N802
        del option, widget
        width, height = self.template.size
        painter.drawPixmap(int(-width / 2), int(-height / 2), self.pixmap)

    def update_render(self) -> None:
        self.state["selected"] = self.isSelected()
        self.pixmap = build_qpixmap(self.kind, self.state)
        self.label_item.setBrush(QBrush(QColor("#8b5e34") if self.isSelected() else QColor("#2b211a")))
        value_color = "#b45309" if self.isSelected() else "#0f5132"
        if self.state.get("overload", 0.0):
            value_color = "#b91c1c"
        self.value_item.setBrush(QBrush(QColor(value_color)))
        self._update_overlay_text()
        self.update()

    def apply_params(self, updated: dict[str, Any]) -> None:
        self.params.update(updated)
        if self.kind == "LED" and "color" in updated:
            self.state["color"] = updated["color"]
        if self.kind == "Switch" and "closed" in updated:
            self.state["closed"] = float(bool(updated["closed"]))
        self.update_render()

    def apply_rotation(self, rotation_deg: float) -> None:
        self.setRotation(float(rotation_deg))
        for terminal in self.terminals:
            for wire in terminal.wires:
                wire.update_path()
        self.update_render()

    def to_record(self) -> ComponentRecord:
        pos = self.pos()
        return ComponentRecord(
            component_id=self.component_id,
            kind=self.kind,
            name=self.name,
            x=float(pos.x()),
            y=float(pos.y()),
            rotation_deg=float(self.rotation()),
            params=dict(self.params),
            terminal_positions=[
                (float(terminal.center_in_scene().x()), float(terminal.center_in_scene().y()))
                for terminal in self.terminals
            ],
        )

    def itemChange(self, change, value):  # noqa: N802
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for terminal in self.terminals:
                for wire in terminal.wires:
                    wire.update_path()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update_render()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if self.kind == "Switch":
            closed = not bool(self.params.get("closed", False))
            self.params["closed"] = closed
            self.state["closed"] = float(closed)
            self.update_render()
            if self.scene_controller is not None:
                state_name = "замкнут" if closed else "разомкнут"
                self.scene_controller.status_changed.emit(f"{self.name}: переключатель {state_name}.")
        super().mouseDoubleClickEvent(event)


class CircuitScene(QGraphicsScene):
    selection_changed = pyqtSignal(object)
    status_changed = pyqtSignal(str)
    animation_state_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSceneRect(0.0, 0.0, 2200.0, 1400.0)
        self.place_kind: str | None = None
        self.connect_mode = False
        self.route_mode = False
        self.selected_terminal: TerminalItem | None = None
        self.component_items: dict[int, ComponentItem] = {}
        self.wire_items: dict[int, WireItem] = {}
        self.material_items: dict[int, MaterialRegionItem] = {}
        self.port_items: dict[int, FieldPortItem] = {}
        self.component_counters: dict[str, int] = {}
        self.next_component_id = 1
        self.next_wire_id = 1
        self.next_material_id = 1
        self.next_port_id = 1
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._advance_animation)
        self.animation_result = None
        self.animation_frame = 0
        self.component_name_map: dict[str, ComponentItem] = {}
        self.selectionChanged.connect(self._emit_selection_change)

    def set_place_mode(self, kind: str) -> None:
        self.place_kind = kind
        self.connect_mode = False
        self.route_mode = False
        self._clear_terminal_highlight()
        self.status_changed.emit(f"Режим добавления: {template_for(kind).display_name}. Нажми на холст, чтобы поставить элемент.")

    def set_place_material_mode(self) -> None:
        self.place_kind = "FieldMaterial"
        self.connect_mode = False
        self.route_mode = False
        self._clear_terminal_highlight()
        self.status_changed.emit("Режим добавления среды: нажми на холст, чтобы поставить область материала.")

    def set_place_port_mode(self) -> None:
        self.place_kind = "FieldPort"
        self.connect_mode = False
        self.route_mode = False
        self._clear_terminal_highlight()
        self.status_changed.emit("Режим добавления порта: нажми на холст, чтобы поставить полевой порт.")

    def set_connect_mode(self) -> None:
        self.place_kind = None
        self.connect_mode = True
        self.route_mode = False
        self._clear_terminal_highlight()
        self.status_changed.emit("Режим соединения: выбери два вывода, чтобы провести провод.")

    def set_route_mode(self) -> None:
        self.place_kind = None
        self.connect_mode = False
        self.route_mode = True
        self._clear_terminal_highlight()
        self.status_changed.emit("Режим трассировки: выбери провод и нажимай на холст, чтобы добавлять точки маршрута. Точки можно перетаскивать мышкой.")
        for wire in self.wire_items.values():
            wire.refresh_visuals()

    def cancel_interaction(self) -> None:
        self.place_kind = None
        self.connect_mode = False
        self.route_mode = False
        self._clear_terminal_highlight()
        for wire in self.wire_items.values():
            wire.refresh_visuals()
        self.status_changed.emit("Режим действия сброшен.")

    def stop_animation(self) -> None:
        self.animation_timer.stop()
        self.animation_state_changed.emit()

    def toggle_animation(self) -> bool:
        if self.animation_result is None or len(self.animation_result.time_s) <= 1:
            return False
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self.animation_state_changed.emit()
            return False
        if self.animation_frame >= len(self.animation_result.time_s) - 1:
            self.animation_frame = 0
            self.apply_result_frame(0)
        self.animation_timer.start(25)
        self.animation_state_changed.emit()
        return True

    def clear_circuit(self) -> None:
        self.stop_animation()
        self.animation_result = None
        self.animation_frame = 0
        self.clear()
        self.component_items.clear()
        self.wire_items.clear()
        self.material_items.clear()
        self.port_items.clear()
        self.component_counters.clear()
        self.component_name_map.clear()
        self.next_component_id = 1
        self.next_wire_id = 1
        self.next_material_id = 1
        self.next_port_id = 1
        self.route_mode = False
        self.selected_terminal = None
        self.selection_changed.emit(None)

    def _emit_selection_change(self) -> None:
        self.selection_changed.emit(
            self.selected_component()
            or self.selected_wire()
            or self.selected_material()
            or self.selected_port()
        )

    def _clear_terminal_highlight(self) -> None:
        if self.selected_terminal is not None:
            self.selected_terminal.highlight(False)
        self.selected_terminal = None

    def selected_component(self) -> ComponentItem | None:
        for item in self.selectedItems():
            if isinstance(item, ComponentItem):
                return item
        return None

    def selected_wire(self) -> WireItem | None:
        for item in self.selectedItems():
            if isinstance(item, WireItem):
                return item
        return None

    def selected_material(self) -> MaterialRegionItem | None:
        for item in self.selectedItems():
            if isinstance(item, MaterialRegionItem):
                return item
        return None

    def selected_port(self) -> FieldPortItem | None:
        for item in self.selectedItems():
            if isinstance(item, FieldPortItem):
                return item
        return None

    def _next_name(self, kind: str) -> str:
        self.component_counters[kind] = self.component_counters.get(kind, 0) + 1
        prefix = NAME_PREFIXES.get(kind, kind.replace(" ", ""))
        return f"{prefix}{self.component_counters[kind]}"

    def _register_name(self, kind: str, name: str) -> None:
        suffix = ""
        for char in reversed(name):
            if char.isdigit():
                suffix = char + suffix
            else:
                break
        if suffix:
            self.component_counters[kind] = max(self.component_counters.get(kind, 0), int(suffix))

    def add_component(
        self,
        kind: str,
        position: QPointF,
        *,
        component_id: int | None = None,
        name: str | None = None,
        rotation_deg: float = 0.0,
        params: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
        select_new: bool = True,
    ) -> ComponentItem:
        component_id = self.next_component_id if component_id is None else component_id
        self.next_component_id = max(self.next_component_id, component_id + 1)
        name = self._next_name(kind) if name is None else name
        self._register_name(kind, name)
        item = ComponentItem(self, component_id, kind, name, position, rotation_deg=rotation_deg, params=params, state=state)
        self.addItem(item)
        self.component_items[component_id] = item
        self.component_name_map[name] = item
        if select_new:
            self.clearSelection()
            item.setSelected(True)
        self.status_changed.emit(f"Добавлен элемент: {name}.")
        return item

    def rename_component(self, component_item: ComponentItem, new_name: str) -> None:
        candidate = new_name.strip()
        if not candidate:
            raise ValueError("Имя элемента не может быть пустым.")
        if candidate.startswith("__wire__"):
            raise ValueError("Такое имя зарезервировано для внутренних объектов.")
        if candidate == component_item.name:
            return
        existing = self.component_name_map.get(candidate)
        if existing is not None and existing is not component_item:
            raise ValueError(f"Имя '{candidate}' уже используется.")
        for item in list(self.material_items.values()) + list(self.port_items.values()):
            if item.name == candidate:
                raise ValueError(f"Имя '{candidate}' уже используется.")
        self.component_name_map.pop(component_item.name, None)
        component_item.rename(candidate)
        self.component_name_map[candidate] = component_item
        self._register_name(component_item.kind, candidate)
        self.status_changed.emit(f"Элемент переименован: {candidate}.")

    def rename_material(self, material_item: MaterialRegionItem, new_name: str) -> None:
        candidate = new_name.strip()
        if not candidate:
            raise ValueError("Имя области не может быть пустым.")
        if candidate == material_item.name:
            return
        if candidate in self.component_name_map or any(item.name == candidate for item in self.port_items.values()):
            raise ValueError(f"Имя '{candidate}' уже используется.")
        for item in self.material_items.values():
            if item is not material_item and item.name == candidate:
                raise ValueError(f"Имя '{candidate}' уже используется.")
        material_item.rename(candidate)
        self._register_name("FieldMaterial", candidate)
        self.status_changed.emit(f"Область переименована: {candidate}.")

    def rename_port(self, port_item: FieldPortItem, new_name: str) -> None:
        candidate = new_name.strip()
        if not candidate:
            raise ValueError("Имя порта не может быть пустым.")
        if candidate == port_item.name:
            return
        if candidate in self.component_name_map or any(item.name == candidate for item in self.material_items.values()):
            raise ValueError(f"Имя '{candidate}' уже используется.")
        for item in self.port_items.values():
            if item is not port_item and item.name == candidate:
                raise ValueError(f"Имя '{candidate}' уже используется.")
        port_item.rename(candidate)
        self._register_name("FieldPort", candidate)
        self.status_changed.emit(f"Порт переименован: {candidate}.")

    def add_material_region(
        self,
        position: QPointF,
        *,
        region_id: int | None = None,
        name: str | None = None,
        params: dict[str, Any] | None = None,
        select_new: bool = True,
    ) -> MaterialRegionItem:
        region_id = self.next_material_id if region_id is None else region_id
        self.next_material_id = max(self.next_material_id, region_id + 1)
        name = self._next_name("FieldMaterial") if name is None else name
        self._register_name("FieldMaterial", name)
        item = MaterialRegionItem(self, region_id, name, position, params=params)
        self.addItem(item)
        self.material_items[region_id] = item
        if select_new:
            self.clearSelection()
            item.setSelected(True)
        self.status_changed.emit(f"Добавлена область среды: {name}.")
        return item

    def add_field_port(
        self,
        position: QPointF,
        *,
        port_id: int | None = None,
        name: str | None = None,
        params: dict[str, Any] | None = None,
        select_new: bool = True,
    ) -> FieldPortItem:
        port_id = self.next_port_id if port_id is None else port_id
        self.next_port_id = max(self.next_port_id, port_id + 1)
        name = self._next_name("FieldPort") if name is None else name
        self._register_name("FieldPort", name)
        item = FieldPortItem(self, port_id, name, position, params=params)
        self.addItem(item)
        self.port_items[port_id] = item
        if select_new:
            self.clearSelection()
            item.setSelected(True)
        self.status_changed.emit(f"Добавлен полевой порт: {name}.")
        return item

    def remove_material(self, material_item: MaterialRegionItem) -> None:
        self.material_items.pop(material_item.region_id, None)
        self.removeItem(material_item)
        self.status_changed.emit(f"Удалена область среды: {material_item.name}.")

    def remove_port(self, port_item: FieldPortItem) -> None:
        self.port_items.pop(port_item.port_id, None)
        self.removeItem(port_item)
        self.status_changed.emit(f"Удален полевой порт: {port_item.name}.")

    def add_wire(
        self,
        a_terminal: TerminalItem,
        b_terminal: TerminalItem,
        *,
        wire_id: int | None = None,
        params: dict[str, Any] | None = None,
        route_points: list[tuple[float, float]] | None = None,
    ) -> WireItem | None:
        if a_terminal is b_terminal:
            return None
        for wire in self.wire_items.values():
            if {wire.a_terminal, wire.b_terminal} == {a_terminal, b_terminal}:
                return None
        wire_id = self.next_wire_id if wire_id is None else wire_id
        self.next_wire_id = max(self.next_wire_id, wire_id + 1)
        wire = WireItem(wire_id, a_terminal, b_terminal, params=params, route_points=route_points)
        self.addItem(wire)
        self.wire_items[wire_id] = wire
        self.status_changed.emit("Провод между выводами создан.")
        return wire

    def remove_component(self, component_item: ComponentItem) -> None:
        removable_wires = []
        for wire_id, wire in self.wire_items.items():
            if wire.a_terminal.component_item is component_item or wire.b_terminal.component_item is component_item:
                removable_wires.append(wire_id)
        for wire_id in removable_wires:
            self.remove_wire(self.wire_items[wire_id])
        self.component_name_map.pop(component_item.name, None)
        self.component_items.pop(component_item.component_id, None)
        self.removeItem(component_item)
        self.status_changed.emit(f"Удален элемент: {component_item.name}.")

    def remove_wire(self, wire_item: WireItem) -> None:
        if wire_item in wire_item.a_terminal.wires:
            wire_item.a_terminal.wires.remove(wire_item)
        if wire_item in wire_item.b_terminal.wires:
            wire_item.b_terminal.wires.remove(wire_item)
        self.wire_items.pop(wire_item.wire_id, None)
        self.removeItem(wire_item)

    def delete_selected(self) -> None:
        selected_components = [item for item in self.selectedItems() if isinstance(item, ComponentItem)]
        selected_wires = [item for item in self.selectedItems() if isinstance(item, WireItem)]
        selected_materials = [item for item in self.selectedItems() if isinstance(item, MaterialRegionItem)]
        selected_ports = [item for item in self.selectedItems() if isinstance(item, FieldPortItem)]
        if not selected_components and not selected_wires and not selected_materials and not selected_ports:
            return
        self._clear_terminal_highlight()
        for wire in list(selected_wires):
            if wire.wire_id in self.wire_items:
                self.remove_wire(wire)
        for component in list(selected_components):
            if component.component_id in self.component_items:
                self.remove_component(component)
        for material in list(selected_materials):
            if material.region_id in self.material_items:
                self.remove_material(material)
        for port in list(selected_ports):
            if port.port_id in self.port_items:
                self.remove_port(port)
        self.clearSelection()
        self.status_changed.emit("Выделенные объекты удалены.")
        self.selection_changed.emit(None)

    def handle_terminal_click(self, terminal: TerminalItem) -> None:
        terminal.component_item.setSelected(True)
        if not self.connect_mode:
            self.selection_changed.emit(terminal.component_item)
            return
        if self.selected_terminal is None:
            self.selected_terminal = terminal
            terminal.highlight(True)
            self.status_changed.emit("Первый вывод выбран. Теперь выбери второй.")
            return
        if terminal is self.selected_terminal:
            self._clear_terminal_highlight()
            return
        first = self.selected_terminal
        self._clear_terminal_highlight()
        self.add_wire(first, terminal)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        item = self.itemAt(event.scenePos(), QTransform())
        if self.route_mode:
            selected_wire = self.selected_wire()
            if isinstance(item, WireHandleItem):
                super().mousePressEvent(event)
                return
            if isinstance(item, WireItem):
                if selected_wire is not item:
                    self.clearSelection()
                    item.setSelected(True)
                    self.status_changed.emit(f"Выбран провод {item.wire_id}. Нажми еще раз по холсту или проводу, чтобы добавить точку маршрута.")
                    event.accept()
                    return
                item.add_route_point(event.scenePos())
                self.status_changed.emit(f"Добавлена точка маршрута для провода {item.wire_id}.")
                event.accept()
                return
            if item is None and selected_wire is not None:
                selected_wire.add_route_point(event.scenePos())
                self.status_changed.emit(f"Добавлена точка маршрута для провода {selected_wire.wire_id}.")
                event.accept()
                return
        if self.place_kind == "FieldMaterial" and item is None:
            self.add_material_region(event.scenePos())
            event.accept()
            return
        if self.place_kind == "FieldPort" and item is None:
            self.add_field_port(event.scenePos())
            event.accept()
            return
        if self.place_kind is not None and item is None:
            self.add_component(self.place_kind, event.scenePos())
            event.accept()
            return
        super().mousePressEvent(event)

    def build_project(self, name: str, duration_s: float, dt_s: float) -> CircuitProject:
        components = [item.to_record() for item in sorted(self.component_items.values(), key=lambda entry: entry.component_id)]
        material_regions = [item.to_record() for item in sorted(self.material_items.values(), key=lambda entry: entry.region_id)]
        field_ports = [item.to_record() for item in sorted(self.port_items.values(), key=lambda entry: entry.port_id)]
        wires = []
        for wire in sorted(self.wire_items.values(), key=lambda entry: entry.wire_id):
            wires.append(
                WireRecord(
                    wire_id=wire.wire_id,
                    a=PinRef(component_id=wire.a_terminal.component_item.component_id, terminal_index=wire.a_terminal.terminal_index),
                    b=PinRef(component_id=wire.b_terminal.component_item.component_id, terminal_index=wire.b_terminal.terminal_index),
                    params=dict(wire.params),
                    route_points=wire.route_points_data(),
                    path_length_px=float(wire.path_length_px()),
                    a_position=(float(wire.a_terminal.center_in_scene().x()), float(wire.a_terminal.center_in_scene().y())),
                    b_position=(float(wire.b_terminal.center_in_scene().x()), float(wire.b_terminal.center_in_scene().y())),
                )
            )
        return CircuitProject(
            name=name,
            settings=ProjectSettings(duration_s=duration_s, dt_s=dt_s),
            components=components,
            wires=wires,
            material_regions=material_regions,
            field_ports=field_ports,
        )

    def load_project(self, project: CircuitProject) -> None:
        self.clear_circuit()
        component_lookup: dict[tuple[int, int], TerminalItem] = {}
        for record in sorted(project.components, key=lambda entry: entry.component_id):
            item = self.add_component(
                record.kind,
                QPointF(record.x, record.y),
                component_id=record.component_id,
                name=record.name,
                rotation_deg=record.rotation_deg,
                params=record.params,
                select_new=False,
            )
            for terminal in item.terminals:
                component_lookup[(record.component_id, terminal.terminal_index)] = terminal
        for wire in sorted(project.wires, key=lambda entry: entry.wire_id):
            self.add_wire(
                component_lookup[(wire.a.component_id, wire.a.terminal_index)],
                component_lookup[(wire.b.component_id, wire.b.terminal_index)],
                wire_id=wire.wire_id,
                params=wire.params,
                route_points=wire.route_points,
            )
        for region in sorted(project.material_regions, key=lambda entry: entry.region_id):
            self.add_material_region(
                QPointF(region.x, region.y),
                region_id=region.region_id,
                name=region.name,
                params=region.params,
                select_new=False,
            )
        for port in sorted(project.field_ports, key=lambda entry: entry.port_id):
            self.add_field_port(
                QPointF(port.x, port.y),
                port_id=port.port_id,
                name=port.name,
                params=port.params,
                select_new=False,
            )
        self.status_changed.emit(f"Проект загружен: {project.name}")

    def apply_result_frame(self, frame_index: int) -> None:
        if self.animation_result is None:
            return
        for component_name, observables in self.animation_result.component_observables.items():
            item = self.component_name_map.get(component_name)
            if item is not None:
                for key, values in observables.items():
                    item.state[key] = float(values[frame_index])
                if item.kind == "Ammeter" and "reading_a" in observables:
                    item.state["reading"] = float(observables["reading_a"][frame_index])
                if item.kind == "Voltmeter" and "reading_v" in observables:
                    item.state["reading"] = float(observables["reading_v"][frame_index])
                item.update_render()
                continue
            for wire_item in self.wire_items.values():
                if wire_item.component_name == component_name:
                    wire_item.apply_observables({key: float(values[frame_index]) for key, values in observables.items()})
                    break

    def play_result(self, result) -> None:
        self.stop_animation()
        self.animation_result = result
        self.animation_frame = 0
        self.apply_result_frame(0)
        if len(result.time_s) > 1:
            self.animation_timer.start(25)
        self.animation_state_changed.emit()

    def _advance_animation(self) -> None:
        if self.animation_result is None:
            self.animation_timer.stop()
            self.animation_state_changed.emit()
            return
        self.animation_frame += 1
        if self.animation_frame >= len(self.animation_result.time_s):
            self.animation_frame = len(self.animation_result.time_s) - 1
        self.apply_result_frame(self.animation_frame)
        if self.animation_frame >= len(self.animation_result.time_s) - 1:
            self.animation_timer.stop()
            self.animation_state_changed.emit()
            return


class CircuitView(QGraphicsView):
    def __init__(self, scene: CircuitScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#f8f4ed")))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.12 if event.angleDelta().y() > 0 else 1 / 1.12
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            scene = self.scene()
            if isinstance(scene, CircuitScene):
                scene.delete_selected()
                event.accept()
                return
        if event.key() == Qt.Key.Key_Escape:
            scene = self.scene()
            if isinstance(scene, CircuitScene):
                scene.cancel_interaction()
                event.accept()
                return
        super().keyPressEvent(event)
