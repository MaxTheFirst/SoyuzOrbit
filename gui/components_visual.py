from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFilter

from core.components import COMPONENT_LIBRARY, COMPONENT_TERMINALS

try:
    from PIL.ImageQt import ImageQt
    from PyQt6.QtGui import QIcon, QPixmap
except Exception:  # noqa: BLE001
    ImageQt = None
    QIcon = None
    QPixmap = None


COLOR_ALIASES = {
    "amber": "#ffbf00",
    "warm_white": "#fff4c2",
    "cool_white": "#dbeafe",
    "infrared": "#b91c1c",
    "uv": "#7c3aed",
    "violet": "#7c3aed",
    "lime": "#84cc16",
}


@dataclass(frozen=True)
class VisualTemplate:
    kind: str
    display_name: str
    core_kind: str
    size: tuple[int, int]
    terminals: tuple[tuple[float, float], ...]
    terminal_labels: tuple[str, ...]
    defaults: dict[str, Any]


TEMPLATES: dict[str, VisualTemplate] = {
    "Ground": VisualTemplate("Ground", "Земля", "Ground", (52, 52), ((0.5, 0.2),), COMPONENT_TERMINALS["Ground"], {}),
    "Junction": VisualTemplate("Junction", "Точка", "Junction", (28, 28), ((0.5, 0.5),), COMPONENT_TERMINALS["Junction"], {}),
    "Battery": VisualTemplate("Battery", "Батарея", "Battery", (128, 72), ((0.1, 0.5), (0.9, 0.5)), COMPONENT_TERMINALS["Battery"], COMPONENT_LIBRARY["Battery"][1].copy()),
    "AC Generator": VisualTemplate("AC Generator", "Генератор AC", "AC Generator", (128, 72), ((0.1, 0.5), (0.9, 0.5)), COMPONENT_TERMINALS["AC Generator"], COMPONENT_LIBRARY["AC Generator"][1].copy()),
    "Pulse Generator": VisualTemplate("Pulse Generator", "Импульсный генератор", "Pulse Generator", (128, 72), ((0.1, 0.5), (0.9, 0.5)), COMPONENT_TERMINALS["Pulse Generator"], COMPONENT_LIBRARY["Pulse Generator"][1].copy()),
    "Audio File Source": VisualTemplate("Audio File Source", "Аудио источник", "Audio File Source", (136, 78), ((0.1, 0.5), (0.9, 0.5)), COMPONENT_TERMINALS["Audio File Source"], COMPONENT_LIBRARY["Audio File Source"][1].copy()),
    "Audio Sink": VisualTemplate("Audio Sink", "Аудио выход", "Audio Sink", (136, 78), ((0.1, 0.5), (0.9, 0.5)), COMPONENT_TERMINALS["Audio Sink"], COMPONENT_LIBRARY["Audio Sink"][1].copy()),
    "Resistor": VisualTemplate("Resistor", "Резистор", "Resistor", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Resistor"], COMPONENT_LIBRARY["Resistor"][1].copy()),
    "Thermistor": VisualTemplate("Thermistor", "Термистор", "Thermistor", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Thermistor"], COMPONENT_LIBRARY["Thermistor"][1].copy()),
    "Photoresistor": VisualTemplate("Photoresistor", "Фоторезистор", "Photoresistor", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Photoresistor"], COMPONENT_LIBRARY["Photoresistor"][1].copy()),
    "Capacitor": VisualTemplate("Capacitor", "Конденсатор", "Capacitor", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Capacitor"], COMPONENT_LIBRARY["Capacitor"][1].copy()),
    "Inductor": VisualTemplate("Inductor", "Катушка", "Inductor", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Inductor"], COMPONENT_LIBRARY["Inductor"][1].copy()),
    "Wire": VisualTemplate("Wire", "Физический провод", "Wire", (128, 44), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Wire"], COMPONENT_LIBRARY["Wire"][1].copy()),
    "Diode": VisualTemplate("Diode", "Диод", "Diode", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Diode"], COMPONENT_LIBRARY["Diode"][1].copy()),
    "LED": VisualTemplate("LED", "Светодиод", "LED", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["LED"], COMPONENT_LIBRARY["LED"][1].copy()),
    "Varistor": VisualTemplate("Varistor", "Варистор", "Varistor", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Varistor"], COMPONENT_LIBRARY["Varistor"][1].copy()),
    "Fuse": VisualTemplate("Fuse", "Предохранитель", "Fuse", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Fuse"], COMPONENT_LIBRARY["Fuse"][1].copy()),
    "Bulb": VisualTemplate("Bulb", "Лампочка", "Bulb", (128, 92), ((0.1, 0.82), (0.9, 0.82)), COMPONENT_TERMINALS["Bulb"], COMPONENT_LIBRARY["Bulb"][1].copy()),
    "Ammeter": VisualTemplate("Ammeter", "Амперметр", "Ammeter", (128, 92), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Ammeter"], COMPONENT_LIBRARY["Ammeter"][1].copy()),
    "Voltmeter": VisualTemplate("Voltmeter", "Вольтметр", "Voltmeter", (128, 92), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Voltmeter"], COMPONENT_LIBRARY["Voltmeter"][1].copy()),
    "Switch": VisualTemplate("Switch", "Переключатель", "Switch", (128, 72), ((0.08, 0.5), (0.92, 0.5)), COMPONENT_TERMINALS["Switch"], COMPONENT_LIBRARY["Switch"][1].copy()),
    "SPDT Switch": VisualTemplate("SPDT Switch", "Перекидной переключатель", "SPDT Switch", (132, 92), ((0.08, 0.5), (0.92, 0.28), (0.92, 0.72)), COMPONENT_TERMINALS["SPDT Switch"], COMPONENT_LIBRARY["SPDT Switch"][1].copy()),
    "MOSFET": VisualTemplate("MOSFET", "MOSFET", "MOSFET", (128, 92), ((0.25, 0.15), (0.12, 0.55), (0.25, 0.85)), COMPONENT_TERMINALS["MOSFET"], COMPONENT_LIBRARY["MOSFET"][1].copy()),
    "OpAmp": VisualTemplate("OpAmp", "ОУ", "OpAmp", (128, 92), ((0.12, 0.3), (0.12, 0.7), (0.88, 0.5)), COMPONENT_TERMINALS["OpAmp"], COMPONENT_LIBRARY["OpAmp"][1].copy()),
}


def template_for(kind: str) -> VisualTemplate:
    return TEMPLATES[kind]


def default_params(kind: str) -> dict[str, Any]:
    return dict(template_for(kind).defaults)


def default_visual_state(kind: str) -> dict[str, Any]:
    state = {"temperature_c": 25.0, "selected": False}
    if kind == "LED":
        state.update({"brightness": 0.0, "failed": 0.0, "color": default_params(kind).get("color", "red")})
    if kind == "Fuse":
        state.update({"blown": 0.0})
    if kind == "Bulb":
        state.update({"glow": 0.0})
    if kind in {"Ammeter", "Voltmeter"}:
        state.update({"reading": 0.0, "overload": 0.0})
    if kind == "Switch":
        state.update({"closed": float(default_params(kind).get("closed", False))})
    if kind == "SPDT Switch":
        state.update({"position_b": float(default_params(kind).get("position_b", False))})
    return state


def _rgba(color: str | tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    if isinstance(color, str):
        normalized = COLOR_ALIASES.get(color.strip().lower(), color)
        try:
            rgb = ImageColor.getrgb(normalized)
        except ValueError:
            rgb = ImageColor.getrgb("#ff0000")
    else:
        rgb = color
    return rgb[0], rgb[1], rgb[2], alpha


def _glow_layer(size: tuple[int, int], bbox: tuple[int, int, int, int], color: str, intensity: float) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    alpha = int(180 * max(0.0, min(1.0, intensity)))
    draw.ellipse(bbox, fill=_rgba(color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(radius=16))


def _base_canvas(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", template.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = "#b45309" if state.get("selected", False) else "#413a33"
    width = 3 if state.get("selected", False) else 2
    draw.rounded_rectangle((2, 2, template.size[0] - 2, template.size[1] - 2), radius=18, fill=_rgba("#f4eee4"), outline=_rgba(outline), width=width)
    return image


def _render_ground(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", template.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    w, _h = template.size
    color = "#b45309" if state.get("selected", False) else "#314d5f"
    draw.line((w / 2, 6, w / 2, 18), fill=color, width=4)
    draw.line((w / 2 - 16, 18, w / 2 + 16, 18), fill=color, width=4)
    draw.line((w / 2 - 10, 26, w / 2 + 10, 26), fill=color, width=4)
    draw.line((w / 2 - 4, 34, w / 2 + 4, 34), fill=color, width=4)
    return image


def _render_junction(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", template.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = "#b45309" if state.get("selected", False) else "#334155"
    accent = "#ffd7aa" if state.get("selected", False) else "#dbeafe"
    draw.ellipse((4, 4, template.size[0] - 4, template.size[1] - 4), fill=color, outline=accent, width=2)
    return image


def _render_battery(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.line((12, h / 2, 28, h / 2), fill="#7b5f49", width=4)
    draw.line((w - 28, h / 2, w - 12, h / 2), fill="#7b5f49", width=4)
    draw.rounded_rectangle((30, 18, w - 30, h - 18), radius=16, fill="#202733", outline="#10131a", width=2)
    draw.rectangle((w - 34, 26, w - 24, h - 26), fill="#d8a86a")
    draw.text((36, 22), "+", fill="#f2d3a5")
    draw.text((w - 48, 22), "-", fill="#f2d3a5")
    return image


def _render_generator(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.line((12, h / 2, 28, h / 2), fill="#6a6f73", width=4)
    draw.line((w - 28, h / 2, w - 12, h / 2), fill="#6a6f73", width=4)
    draw.ellipse((38, 14, w - 38, h - 14), outline="#123b5d", fill="#dae9f3", width=3)
    import math
    points = []
    for step in range(49):
        x = 46 + step * (w - 92) / 48
        y = h / 2 - 12 * math.sin(step / 48 * 2 * math.pi)
        points.append((x, y))
    draw.line(points, fill="#1e5f8a", width=3)
    return image


def _render_pulse_generator(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.line((12, h / 2, 28, h / 2), fill="#6a6f73", width=4)
    draw.line((w - 28, h / 2, w - 12, h / 2), fill="#6a6f73", width=4)
    draw.rounded_rectangle((30, 16, w - 30, h - 16), radius=14, fill="#e6f7ef", outline="#146c43", width=3)
    pulse_points = [
        (40, h / 2 + 10),
        (52, h / 2 + 10),
        (52, h / 2 - 12),
        (80, h / 2 - 12),
        (80, h / 2 + 10),
        (100, h / 2 + 10),
    ]
    draw.line(pulse_points, fill="#15803d", width=4)
    return image


def _render_audio_source(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.line((12, h / 2, 28, h / 2), fill="#6a6f73", width=4)
    draw.line((w - 28, h / 2, w - 12, h / 2), fill="#6a6f73", width=4)
    draw.rounded_rectangle((28, 14, w - 28, h - 14), radius=16, fill="#eef3ff", outline="#1d4ed8", width=3)
    waveform = []
    for step in range(7):
        x = 40 + step * 12
        y = h / 2 + (10 if step % 2 == 0 else -10)
        waveform.append((x, y))
    draw.line(waveform, fill="#1d4ed8", width=3)
    draw.rounded_rectangle((w - 54, 22, w - 34, h - 22), radius=4, fill="#0f172a")
    draw.text((w / 2 + 8, h / 2 - 8), "AUDIO", fill="#0f172a")
    return image


def _render_audio_sink(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.line((12, h / 2, 28, h / 2), fill="#6a6f73", width=4)
    draw.line((w - 28, h / 2, w - 12, h / 2), fill="#6a6f73", width=4)
    draw.rounded_rectangle((28, 14, w - 28, h - 14), radius=16, fill="#fff7ed", outline="#c2410c", width=3)
    draw.polygon(((46, h / 2), (68, h / 2 - 12), (68, h / 2 - 5), (92, h / 2 - 5), (92, h / 2 + 5), (68, h / 2 + 5), (68, h / 2 + 12)), fill="#c2410c")
    draw.text((w / 2 + 2, h / 2 - 8), "REC", fill="#7c2d12")
    return image


def _render_resistor(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 28, cy), fill="#91714f", width=4)
    draw.line((w - 28, cy, w - 12, cy), fill="#91714f", width=4)
    draw.rounded_rectangle((28, 22, w - 28, h - 22), radius=16, fill="#e9d7b8", outline="#7d5f34", width=2)
    for idx, color in enumerate(("#7c2d12", "#c2410c", "#111827", "#7a5b2a")):
        x = 42 + idx * 18
        draw.rectangle((x, 24, x + 8, h - 24), fill=color)
    return image


def _render_thermistor(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _render_resistor(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.line((48, h - 18, 78, 18), fill="#0f766e", width=3)
    draw.text((80, 18), "NTC", fill="#0f766e")
    return image


def _render_photoresistor(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 28, cy), fill="#91714f", width=4)
    draw.line((w - 28, cy, w - 12, cy), fill="#91714f", width=4)
    draw.ellipse((30, 14, w - 30, h - 14), fill=_rgba("#f8fafc", 180), outline="#64748b", width=2)
    draw.rounded_rectangle((42, 22, w - 42, h - 22), radius=16, fill="#e9d7b8", outline="#7d5f34", width=2)
    draw.line((50, 14, 62, 26), fill="#f59e0b", width=3)
    draw.line((66, 10, 78, 22), fill="#f59e0b", width=3)
    draw.polygon(((62, 26), (58, 24), (60, 30)), fill="#f59e0b")
    draw.polygon(((78, 22), (74, 20), (76, 26)), fill="#f59e0b")
    return image


def _render_capacitor(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 42, cy), fill="#7b5f49", width=4)
    draw.line((w - 42, cy, w - 12, cy), fill="#7b5f49", width=4)
    draw.rounded_rectangle((42, 12, w - 42, h - 12), radius=14, fill="#264653", outline="#13222b", width=2)
    draw.rectangle((50, 16, 58, h - 16), fill="#4d7384")
    draw.text((w / 2 - 18, 18), "+", fill="#e5f4ff")
    temperature = float(state.get("temperature_c", 25.0))
    if temperature > 40.0:
        overlay = Image.new("RGBA", template.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        alpha = int(min(140, (temperature - 40.0) * 3.0))
        overlay_draw.rounded_rectangle((42, 12, w - 42, h - 12), radius=14, fill=_rgba("#ff8f5a", alpha))
        image.alpha_composite(overlay)
    return image


def _render_inductor(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 28, cy), fill="#7b5f49", width=4)
    draw.line((w - 28, cy, w - 12, cy), fill="#7b5f49", width=4)
    start_x = 28
    for _ in range(4):
        draw.arc((start_x, 18, start_x + 20, h - 18), start=180, end=0, fill="#a66a28", width=4)
        start_x += 20
    return image


def _render_wire(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", template.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    w, h = template.size
    temperature = float(state.get("temperature_c", 25.0))
    heat = max(0.0, min(1.0, (temperature - 25.0) / 80.0))
    color = "#3b556e" if heat < 0.4 else "#b45309"
    width = 10 if state.get("selected", False) else 8
    draw.line((16, h / 2, w - 16, h / 2), fill=color, width=width)
    return image


def _render_diode(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 36, cy), fill="#7b5f49", width=4)
    draw.line((w - 36, cy, w - 12, cy), fill="#7b5f49", width=4)
    draw.polygon(((40, 18), (40, h - 18), (78, cy)), fill="#7b8ca1", outline="#344257")
    draw.line((88, 18, 88, h - 18), fill="#344257", width=5)
    return image


def _render_varistor(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 34, cy), fill="#7b5f49", width=4)
    draw.line((w - 34, cy, w - 12, cy), fill="#7b5f49", width=4)
    draw.ellipse((42, 16, w - 42, h - 16), fill="#60a5fa", outline="#1d4ed8", width=3)
    draw.text((w / 2 - 16, h / 2 - 8), "MOV", fill="#0f172a")
    return image


def _render_led(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    w, h = template.size
    brightness = float(state.get("brightness", 0.0))
    color = str(state.get("color", "red"))
    failed = bool(state.get("failed", 0.0))
    if brightness > 0.0 and not failed:
        image.alpha_composite(_glow_layer(template.size, (26, 8, w - 26, h - 8), color, brightness))
    draw = ImageDraw.Draw(image)
    cy = h / 2
    draw.line((14, cy, 40, cy), fill="#8c7b65", width=4)
    draw.line((w - 40, cy, w - 14, cy), fill="#8c7b65", width=4)
    body_fill = "#3f4248" if failed else color
    draw.rounded_rectangle((38, 16, w - 38, h - 16), radius=18, fill=_rgba(body_fill, 200), outline="#2a2e34", width=2)
    if failed:
        draw.line((44, 20, w - 44, h - 20), fill="#111111", width=4)
        draw.line((44, h - 20, w - 44, 20), fill="#111111", width=4)
    return image


def _render_fuse(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 30, cy), fill="#7b5f49", width=4)
    draw.line((w - 30, cy, w - 12, cy), fill="#7b5f49", width=4)
    draw.rounded_rectangle((30, 24, 46, h - 24), radius=6, fill="#b8b8bb")
    draw.rounded_rectangle((w - 46, 24, w - 30, h - 24), radius=6, fill="#b8b8bb")
    draw.rounded_rectangle((44, 20, w - 44, h - 20), radius=14, fill=_rgba("#d8eef5", 120), outline="#7a8f96")
    if state.get("blown", 0.0):
        draw.line((56, 22, 64, h - 22), fill="#7f1d1d", width=3)
        draw.line((64, h - 22, 72, 22), fill="#7f1d1d", width=3)
    else:
        draw.line((50, cy, w - 50, cy), fill="#965c14", width=2)
    return image


def _render_bulb(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", template.size, (0, 0, 0, 0))
    w, h = template.size
    glow = float(state.get("glow", 0.0))
    if glow > 0.0:
        image.alpha_composite(_glow_layer(template.size, (22, 4, w - 22, h - 18), "#ffb347", glow))
    draw = ImageDraw.Draw(image)
    outline = "#b45309" if state.get("selected", False) else "#63717b"
    draw.ellipse((24, 6, w - 24, h - 22), fill=_rgba("#eef4f8", 170), outline=outline, width=2)
    draw.rectangle((w / 2 - 14, h - 28, w / 2 + 14, h - 8), fill="#887058", outline="#4d3e31")
    draw.line((w / 2 - 28, h - 8, 14, h - 8), fill="#7b5f49", width=4)
    draw.line((w - 14, h - 8, w / 2 + 28, h - 8), fill="#7b5f49", width=4)
    filament = "#ff9d2e" if glow > 0.05 else "#6b7280"
    draw.line((w / 2 - 12, h / 2 + 4, w / 2 + 12, h / 2 + 4), fill=filament, width=3)
    draw.line((w / 2 - 20, h - 28, w / 2 - 12, h / 2 + 4), fill="#6b7280", width=2)
    draw.line((w / 2 + 20, h - 28, w / 2 + 12, h / 2 + 4), fill="#6b7280", width=2)
    return image


def _render_meter(template: VisualTemplate, state: dict[str, Any], symbol: str, unit: str) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    draw.line((12, cy, 28, cy), fill="#7b5f49", width=4)
    draw.line((w - 28, cy, w - 12, cy), fill="#7b5f49", width=4)
    fill = "#fee2e2" if state.get("overload", 0.0) else "#eff6ff"
    outline = "#b91c1c" if state.get("overload", 0.0) else "#1d4ed8"
    draw.rounded_rectangle((28, 14, w - 28, h - 14), radius=20, fill=fill, outline=outline, width=3)
    draw.ellipse((38, 24, 74, 60), fill="#f8fafc", outline="#475569", width=2)
    draw.text((50, 34), symbol, fill="#0f172a")
    reading = float(state.get("reading", 0.0))
    text = f"{reading:6.3f} {unit}"
    draw.rounded_rectangle((78, 28, w - 38, 58), radius=8, fill="#0f172a")
    draw.text((84, 36), text, fill="#86efac" if not state.get("overload", 0.0) else "#fca5a5")
    return image


def _render_ammeter(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    return _render_meter(template, state, "A", "A")


def _render_voltmeter(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    return _render_meter(template, state, "V", "V")


def _render_switch(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    closed = bool(state.get("closed", 0.0))
    draw.line((12, cy, 40, cy), fill="#7b5f49", width=4)
    draw.line((w - 40, cy, w - 12, cy), fill="#7b5f49", width=4)
    draw.ellipse((34, cy - 6, 46, cy + 6), fill="#475569")
    draw.ellipse((w - 46, cy - 6, w - 34, cy + 6), fill="#475569")
    if closed:
        draw.line((44, cy, w - 44, cy), fill="#84a98c", width=5)
    else:
        draw.line((44, cy, w - 48, cy - 18), fill="#64748b", width=5)
    return image


def _render_spdt_switch(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    cy = h / 2
    top_y = h * 0.28
    bottom_y = h * 0.72
    right_x = w - 18
    left_x = 18
    contact_left = 44
    contact_right = w - 42
    position_b = bool(state.get("position_b", 0.0))
    draw.line((left_x, cy, contact_left, cy), fill="#7b5f49", width=4)
    draw.line((contact_right, top_y, right_x, top_y), fill="#7b5f49", width=4)
    draw.line((contact_right, bottom_y, right_x, bottom_y), fill="#7b5f49", width=4)
    draw.ellipse((contact_left - 6, cy - 6, contact_left + 6, cy + 6), fill="#475569")
    draw.ellipse((contact_right - 6, top_y - 6, contact_right + 6, top_y + 6), fill="#475569")
    draw.ellipse((contact_right - 6, bottom_y - 6, contact_right + 6, bottom_y + 6), fill="#475569")
    target_y = bottom_y if position_b else top_y
    arm_color = "#84a98c" if position_b else "#64748b"
    draw.line((contact_left, cy, contact_right - 2, target_y), fill=arm_color, width=5)
    draw.text((w / 2 - 10, 14), "A", fill="#334155")
    draw.text((w / 2 - 10, h - 28), "B", fill="#334155")
    return image


def _render_mosfet(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.rounded_rectangle((36, 16, w - 20, h - 16), radius=12, fill="#1f2937", outline="#111827", width=2)
    draw.line((32, 18, 32, h - 18), fill="#334155", width=3)
    draw.line((12, h / 2, 32, h / 2), fill="#7b5f49", width=4)
    draw.line((44, 8, 44, 16), fill="#7b5f49", width=4)
    draw.line((44, h - 16, 44, h - 8), fill="#7b5f49", width=4)
    draw.line((58, 24, 58, h - 24), fill="#e2e8f0", width=3)
    draw.line((58, h / 2, 88, h / 2), fill="#e2e8f0", width=3)
    if float(state.get("temperature_c", 25.0)) > 55.0:
        alpha = int(min(120, (float(state.get("temperature_c", 25.0)) - 55.0) * 2.0))
        overlay = Image.new("RGBA", template.size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle((36, 16, w - 20, h - 16), radius=12, fill=_rgba("#ef4444", alpha))
        image.alpha_composite(overlay)
    return image


def _render_opamp(template: VisualTemplate, state: dict[str, Any]) -> Image.Image:
    image = _base_canvas(template, state)
    draw = ImageDraw.Draw(image)
    w, h = template.size
    draw.polygon(((34, 12), (34, h - 12), (w - 18, h / 2)), fill="#f1d6ab", outline="#7c5c2c")
    draw.line((12, h * 0.3, 34, h * 0.3), fill="#7b5f49", width=4)
    draw.line((12, h * 0.7, 34, h * 0.7), fill="#7b5f49", width=4)
    draw.line((w - 18, h / 2, w - 8, h / 2), fill="#7b5f49", width=4)
    draw.text((20, int(h * 0.25) - 8), "+", fill="#4b3a2a")
    draw.text((20, int(h * 0.65) - 8), "-", fill="#4b3a2a")
    if state.get("current_limit", 0.0):
        image.alpha_composite(_glow_layer(template.size, (16, 10, w - 16, h - 10), "#f97316", 0.5))
    return image


RENDERERS = {
    "Ground": _render_ground,
    "Junction": _render_junction,
    "Battery": _render_battery,
    "AC Generator": _render_generator,
    "Pulse Generator": _render_pulse_generator,
    "Audio File Source": _render_audio_source,
    "Audio Sink": _render_audio_sink,
    "Resistor": _render_resistor,
    "Thermistor": _render_thermistor,
    "Photoresistor": _render_photoresistor,
    "Capacitor": _render_capacitor,
    "Inductor": _render_inductor,
    "Wire": _render_wire,
    "Diode": _render_diode,
    "LED": _render_led,
    "Varistor": _render_varistor,
    "Fuse": _render_fuse,
    "Bulb": _render_bulb,
    "Ammeter": _render_ammeter,
    "Voltmeter": _render_voltmeter,
    "Switch": _render_switch,
    "SPDT Switch": _render_spdt_switch,
    "MOSFET": _render_mosfet,
    "OpAmp": _render_opamp,
}


def render_component(kind: str, state: dict[str, Any] | None = None) -> Image.Image:
    template = template_for(kind)
    return RENDERERS[kind](template, state or default_visual_state(kind))


def build_qpixmap(kind: str, state: dict[str, Any] | None = None):
    if ImageQt is None or QPixmap is None:
        raise RuntimeError("PyQt6 support is not available.")
    return QPixmap.fromImage(ImageQt(render_component(kind, state)))


def build_qicon(kind: str, state: dict[str, Any] | None = None):
    if QIcon is None:
        raise RuntimeError("PyQt6 support is not available.")
    return QIcon(build_qpixmap(kind, state))
