from __future__ import annotations

import math
import re
from typing import Callable

import numpy as np
from matplotlib import transforms
from matplotlib.figure import Figure

from .engine import SimulationResult


PLOT_PANEL_ORDER = [
    "nodes",
    "currents",
    "voltages",
    "audio_waveform",
    "audio_zoom",
    "audio_envelope",
    "audio_spectrum",
    "audio_transfer",
    "power_temperature",
    "temperature",
    "surface_temperature",
    "power",
    "energy_storage",
    "charge",
    "iv_xy",
    "state",
]

PLOT_PANEL_LABELS = {
    "nodes": "Напряжения по узлам",
    "currents": "Токи по компонентам",
    "voltages": "Напряжения компонентов",
    "audio_waveform": "Аудио: напряжение вход/выход",
    "audio_zoom": "Аудио: zoom формы волны",
    "audio_envelope": "Аудио: огибающая",
    "audio_spectrum": "Аудио: спектр",
    "audio_transfer": "Аудио: transfer cloud",
    "power_temperature": "Мощность и температура",
    "temperature": "Температуры",
    "surface_temperature": "Температуры корпуса",
    "power": "Мощность",
    "energy_storage": "Накопление энергии",
    "charge": "Заряд",
    "iv_xy": "Нелинейные XY-графики I(U)",
    "state": "Состояния",
}

PLOT_PANEL_TITLES = {
    "nodes": "Напряжения узлов",
    "currents": "Токи компонентов",
    "voltages": "Напряжения и ЭДС",
    "audio_waveform": "Аудио: входное и выходное напряжение",
    "audio_zoom": "Аудио: увеличенный фрагмент волны",
    "audio_envelope": "Аудио: кратковременная огибающая",
    "audio_spectrum": "Аудио: спектр входа и выхода",
    "audio_transfer": "Аудио: вход -> выход",
    "power_temperature": "Мощность и температура",
    "temperature": "Температуры компонентов",
    "surface_temperature": "Температуры корпуса",
    "power": "Мощность компонентов",
    "energy_storage": "Накопление заряда и магнитного потока",
    "charge": "Зарядовые величины",
    "iv_xy": "Нелинейные I(U)-характеристики",
    "state": "Состояния компонентов",
}

PLOT_PANEL_YLABELS = {
    "nodes": "V",
    "currents": "A",
    "voltages": "V",
    "audio_waveform": "V",
    "audio_zoom": "V",
    "audio_envelope": "V RMS",
    "audio_spectrum": "dB",
    "audio_transfer": "V",
    "power_temperature": "degC / W",
    "temperature": "degC",
    "surface_temperature": "degC",
    "power": "W",
    "energy_storage": "C / Wb",
    "charge": "C",
    "iv_xy": "A",
    "state": "ratio / flag",
}

OBSERVABLE_LABELS = {
    "current_a": "ток",
    "reading_a": "показание",
    "input_current_a": "входной ток",
    "output_current_a": "выходной ток",
    "source_current_a": "ток источника",
    "drain_current_a": "ток стока",
    "gate_current_a": "ток затвора",
    "magnetic_current_a": "магнитный ток",
    "voltage_v": "напряжение",
    "emf_v": "ЭДС",
    "reading_v": "показание",
    "capacitor_voltage_v": "напряжение конденсатора",
    "open_circuit_voltage_v": "Uxx",
    "clamp_voltage_v": "Uогр",
    "forward_drop_v": "Uпр",
    "built_in_potential_v": "Vbi",
    "temperature_c": "температура",
    "surface_temperature_c": "температура корпуса",
    "power_w": "мощность",
    "charge_c": "заряд",
    "stored_charge_c": "накопленный заряд",
    "inversion_charge_c": "инверсный заряд",
    "flux_linkage_wb": "потокосцепление",
    "brightness": "яркость",
    "glow": "накал",
    "flash": "вспышка",
    "soc": "SOC",
    "blown": "перегорел",
    "current_limit": "ограничение тока",
    "overload": "перегрузка",
    "breakdown": "пробой",
    "closed": "замкнут",
}

STATE_KEYS = {"brightness", "glow", "flash", "soc", "blown", "current_limit", "overload", "breakdown", "closed"}
CHARGE_KEYS = {"charge_c", "stored_charge_c", "inversion_charge_c"}
ENERGY_STORAGE_CHARGE_KEYS = CHARGE_KEYS
ENERGY_STORAGE_FLUX_KEYS = {"flux_linkage_wb"}
IV_PAIR_CANDIDATES = [
    ("voltage_v", "current_a"),
    ("reading_v", "reading_a"),
]


def display_plot_name(name: str) -> str:
    if name.startswith("__wire__"):
        return f"Провод {name.split('__wire__', 1)[1]}"
    return name


def _display_node_name(name: str) -> str:
    match = re.fullmatch(r"n(\d+)", name)
    if match:
        return f"Узел {int(match.group(1))}"
    return name


def _natural_sort_key(value: str) -> tuple[object, ...]:
    parts = re.split(r"(\d+)", value)
    key: list[object] = []
    for part in parts:
        if not part:
            continue
        key.append(int(part) if part.isdigit() else part.lower())
    return tuple(key)


def _series_label(component_name: str, key: str, primary_key: str) -> str:
    base_name = display_plot_name(component_name)
    if key == primary_key:
        return base_name
    return f"{base_name}:{OBSERVABLE_LABELS.get(key, key)}"


def _component_series(
    result: SimulationResult,
    matcher: Callable[[str], bool],
    *,
    primary_key: str,
    visible_components: set[str] | None = None,
) -> list[tuple[str, np.ndarray]]:
    series: list[tuple[str, np.ndarray]] = []
    for component_name, observables in result.component_observables.items():
        if visible_components is not None and component_name not in visible_components:
            continue
        for key, values in observables.items():
            if matcher(key):
                series.append((_series_label(component_name, key, primary_key), np.asarray(values, dtype=float)))
    return series


def plot_panel_series(
    result: SimulationResult,
    panel_id: str,
    *,
    visible_components: set[str] | None = None,
) -> list[tuple[str, np.ndarray]]:
    if panel_id == "nodes":
        if visible_components is not None:
            return []
        return [
            (_display_node_name(node), np.asarray(values, dtype=float))
            for node, values in sorted(result.node_voltages.items(), key=lambda item: _natural_sort_key(item[0]))
        ]
    if panel_id == "currents":
        return _component_series(result, lambda key: key.endswith("_a"), primary_key="current_a", visible_components=visible_components)
    if panel_id == "voltages":
        return _component_series(result, lambda key: key.endswith("_v"), primary_key="voltage_v", visible_components=visible_components)
    if panel_id == "temperature":
        return _component_series(result, lambda key: key == "temperature_c", primary_key="temperature_c", visible_components=visible_components)
    if panel_id == "surface_temperature":
        return _component_series(
            result,
            lambda key: key == "surface_temperature_c",
            primary_key="surface_temperature_c",
            visible_components=visible_components,
        )
    if panel_id == "power_temperature":
        return (
            _component_series(result, lambda key: key == "temperature_c", primary_key="temperature_c", visible_components=visible_components)
            + _component_series(result, lambda key: key == "power_w", primary_key="power_w", visible_components=visible_components)
        )
    if panel_id == "power":
        return _component_series(result, lambda key: key == "power_w", primary_key="power_w", visible_components=visible_components)
    if panel_id == "energy_storage":
        return _component_series(
            result,
            lambda key: key in ENERGY_STORAGE_CHARGE_KEYS or key in ENERGY_STORAGE_FLUX_KEYS,
            primary_key="charge_c",
            visible_components=visible_components,
        )
    if panel_id == "charge":
        return _component_series(result, lambda key: key in CHARGE_KEYS, primary_key="charge_c", visible_components=visible_components)
    if panel_id == "audio_waveform":
        return _audio_waveform_panel_data(result, visible_components=visible_components)
    if panel_id == "audio_envelope":
        return _audio_envelope_panel_data(result, visible_components=visible_components)
    if panel_id == "iv_xy":
        return []
    if panel_id == "state":
        return _component_series(result, lambda key: key in STATE_KEYS, primary_key="soc", visible_components=visible_components)
    raise ValueError(f"Unknown plot panel: {panel_id}")


def available_plot_component_names(result: SimulationResult) -> list[str]:
    return list(result.component_observables)


def _power_temperature_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[tuple[str, np.ndarray]], list[tuple[str, np.ndarray]]]:
    temperature_series = _component_series(
        result,
        lambda key: key == "temperature_c",
        primary_key="temperature_c",
        visible_components=visible_components,
    )
    power_series = _component_series(
        result,
        lambda key: key == "power_w",
        primary_key="power_w",
        visible_components=visible_components,
    )
    return temperature_series, power_series


def _energy_storage_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[tuple[str, np.ndarray]], list[tuple[str, np.ndarray]]]:
    charge_series = _component_series(
        result,
        lambda key: key in ENERGY_STORAGE_CHARGE_KEYS,
        primary_key="charge_c",
        visible_components=visible_components,
    )
    flux_series = _component_series(
        result,
        lambda key: key in ENERGY_STORAGE_FLUX_KEYS,
        primary_key="flux_linkage_wb",
        visible_components=visible_components,
    )
    return charge_series, flux_series


def _iv_xy_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> list[tuple[str, np.ndarray, np.ndarray]]:
    pairs: list[tuple[str, np.ndarray, np.ndarray]] = []
    for component_name, observables in result.component_observables.items():
        if visible_components is not None and component_name not in visible_components:
            continue
        for voltage_key, current_key in IV_PAIR_CANDIDATES:
            if voltage_key in observables and current_key in observables:
                label = display_plot_name(component_name)
                x_values = np.asarray(observables[voltage_key], dtype=float)
                y_values = np.asarray(observables[current_key], dtype=float)
                pairs.append((label, x_values, y_values))
                break
    return pairs


def _audio_sample_rate_hz(result: SimulationResult) -> int:
    dt_s = float(result.metadata.get("dt_s", 0.0))
    if dt_s <= 0.0 and result.time_s.size >= 2:
        diffs = np.diff(np.asarray(result.time_s, dtype=float))
        positive = diffs[diffs > 0.0]
        if positive.size > 0:
            dt_s = float(np.median(positive))
    if dt_s <= 0.0:
        return 0
    return max(int(round(1.0 / dt_s)), 1)


def _collect_audio_sources(result: SimulationResult) -> list[tuple[str, np.ndarray, str]]:
    sources: list[tuple[str, np.ndarray, str]] = []
    for component_name, observables in result.component_observables.items():
        if "emf_v" in observables and "source_sample_rate_hz" in observables:
            label = f"Input:{display_plot_name(component_name)}"
            sources.append((label, np.asarray(observables["emf_v"], dtype=float), component_name))
    return sources


def _collect_audio_sinks(result: SimulationResult) -> list[tuple[str, np.ndarray, str]]:
    sinks: list[tuple[str, np.ndarray, str]] = []
    for component_name, observables in result.component_observables.items():
        if "captured_v" in observables:
            label = f"Output:{display_plot_name(component_name)}"
            sinks.append((label, np.asarray(observables["captured_v"], dtype=float), component_name))
    return sinks


def _audio_bundle(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[tuple[str, np.ndarray, str]], list[tuple[str, np.ndarray, str]]]:
    all_sources = _collect_audio_sources(result)
    all_sinks = _collect_audio_sinks(result)
    if visible_components is None:
        return all_sources, all_sinks

    selected_sources = [item for item in all_sources if item[2] in visible_components]
    selected_sinks = [item for item in all_sinks if item[2] in visible_components]

    if selected_sources:
        sources = selected_sources
    elif selected_sinks and all_sources:
        sources = all_sources[:1]
    else:
        sources = []
    return sources, selected_sinks


def _audio_active_mask(samples: np.ndarray) -> np.ndarray:
    if samples.size == 0:
        return np.zeros(0, dtype=bool)
    threshold = max(float(np.max(np.abs(samples))) * 0.08, 1.0e-4)
    return np.abs(samples) >= threshold


def _audio_window_by_energy(series: list[tuple[str, np.ndarray]], window_samples: int) -> tuple[int, int]:
    if not series:
        return 0, 0
    window = max(int(window_samples), 32)
    sample_count = min(values.size for _label, values in series)
    if sample_count <= 0:
        return 0, 0
    combined = np.zeros(sample_count, dtype=np.float32)
    for _label, values in series:
        trimmed = np.asarray(values[:sample_count], dtype=np.float32)
        combined += np.square(trimmed, dtype=np.float32)
    energy = np.convolve(combined, np.ones(window, dtype=np.float32), mode="same")
    center = int(np.argmax(energy)) if energy.size else 0
    start = max(center - window // 2, 0)
    stop = min(start + window, sample_count)
    start = max(stop - window, 0)
    return start, stop


def _audio_moving_rms(samples: np.ndarray, window_samples: int) -> np.ndarray:
    window = max(int(window_samples), 1)
    kernel = np.ones(window, dtype=np.float32) / float(window)
    power = np.square(np.asarray(samples, dtype=np.float32), dtype=np.float32)
    return np.sqrt(np.convolve(power, kernel, mode="same")).astype(float)


def _audio_waveform_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> list[tuple[str, np.ndarray]]:
    sources, sinks = _audio_bundle(result, visible_components=visible_components)
    return [(label, values) for label, values, _component_name in sources + sinks]


def _audio_zoom_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
    zoom_ms: float = 45.0,
) -> tuple[np.ndarray, list[tuple[str, np.ndarray]]]:
    sample_rate_hz = _audio_sample_rate_hz(result)
    if sample_rate_hz <= 0:
        return np.zeros(0, dtype=float), []
    series = _audio_waveform_panel_data(result, visible_components=visible_components)
    if not series:
        return np.zeros(0, dtype=float), []
    start, stop = _audio_window_by_energy(series, int(round(sample_rate_hz * zoom_ms / 1000.0)))
    time_axis_ms = np.arange(start, stop, dtype=float) * 1000.0 / float(sample_rate_hz)
    zoom_series = [(label, values[start:stop]) for label, values in series]
    return time_axis_ms, zoom_series


def _audio_envelope_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
    envelope_ms: float = 20.0,
) -> list[tuple[str, np.ndarray]]:
    sample_rate_hz = _audio_sample_rate_hz(result)
    if sample_rate_hz <= 0:
        return []
    window_samples = int(round(sample_rate_hz * envelope_ms / 1000.0))
    return [
        (label, _audio_moving_rms(values, window_samples))
        for label, values in _audio_waveform_panel_data(result, visible_components=visible_components)
    ]


def _audio_spectrum_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[np.ndarray, list[tuple[str, np.ndarray]]]:
    sample_rate_hz = _audio_sample_rate_hz(result)
    if sample_rate_hz <= 0:
        return np.zeros(0, dtype=float), []
    series = _audio_waveform_panel_data(result, visible_components=visible_components)
    if not series:
        return np.zeros(0, dtype=float), []
    start, stop = _audio_window_by_energy(series, max(4096, int(round(sample_rate_hz * 0.256))))
    spectral_series: list[tuple[str, np.ndarray]] = []
    freqs = np.zeros(0, dtype=float)
    for label, values in series:
        segment = np.asarray(values[start:stop], dtype=np.float32)
        if segment.size < 128:
            continue
        window = np.hanning(segment.size).astype(np.float32)
        spectrum = np.fft.rfft(segment * window)
        freqs = np.fft.rfftfreq(segment.size, d=1.0 / float(sample_rate_hz))
        magnitude_db = 20.0 * np.log10(np.maximum(np.abs(spectrum), 1.0e-8))
        spectral_series.append((label, magnitude_db.astype(float)))
    return freqs.astype(float), spectral_series


def _audio_transfer_panel_data(
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> list[tuple[str, np.ndarray, np.ndarray]]:
    sources, sinks = _audio_bundle(result, visible_components=visible_components)
    if not sources or not sinks:
        return []
    input_label, input_values, _source_name = sources[0]
    pairs: list[tuple[str, np.ndarray, np.ndarray]] = []
    input_values = np.asarray(input_values, dtype=float)
    for sink_label, sink_values, _sink_name in sinks:
        output_values = np.asarray(sink_values, dtype=float)
        mask = _audio_active_mask(input_values) | _audio_active_mask(output_values)
        finite_mask = np.isfinite(input_values) & np.isfinite(output_values)
        indices = np.flatnonzero(mask & finite_mask)
        if indices.size < 512:
            indices = np.flatnonzero(finite_mask)
        if indices.size == 0:
            continue
        if indices.size > 5000:
            indices = indices[np.linspace(0, indices.size - 1, 5000, dtype=int)]
        pairs.append((f"{sink_label} <- {input_label}", input_values[indices], output_values[indices]))
    return pairs


def _panel_has_data(
    result: SimulationResult,
    panel_id: str,
    *,
    visible_components: set[str] | None = None,
) -> bool:
    if panel_id == "power_temperature":
        temperature_series, power_series = _power_temperature_panel_data(result, visible_components=visible_components)
        return bool(temperature_series or power_series)
    if panel_id == "energy_storage":
        charge_series, flux_series = _energy_storage_panel_data(result, visible_components=visible_components)
        return bool(charge_series or flux_series)
    if panel_id == "iv_xy":
        return bool(_iv_xy_panel_data(result, visible_components=visible_components))
    if panel_id == "audio_zoom":
        _time_axis_ms, zoom_series = _audio_zoom_panel_data(result, visible_components=visible_components)
        return bool(zoom_series)
    if panel_id == "audio_spectrum":
        _freqs, spectral_series = _audio_spectrum_panel_data(result, visible_components=visible_components)
        return bool(spectral_series)
    if panel_id == "audio_transfer":
        return bool(_audio_transfer_panel_data(result, visible_components=visible_components))
    return bool(plot_panel_series(result, panel_id, visible_components=visible_components))


def available_plot_panel_ids(result: SimulationResult, *, visible_components: set[str] | None = None) -> list[str]:
    return [panel_id for panel_id in PLOT_PANEL_ORDER if _panel_has_data(result, panel_id, visible_components=visible_components)]


def _add_end_labels(ax, rendered_series: list[tuple[str, np.ndarray, object]]) -> None:
    if not rendered_series:
        return
    text_x = 0.985
    text_transform = transforms.blended_transform_factory(ax.transAxes, ax.transData)
    for label, values, line in rendered_series:
        finite_indices = np.flatnonzero(np.isfinite(values))
        if finite_indices.size == 0:
            continue
        color = line.get_color()
        endpoint_y = float(values[int(finite_indices[-1])])
        text = ax.text(
            text_x,
            endpoint_y,
            label,
            fontsize="x-small",
            color=color,
            va="center",
            ha="right",
            clip_on=True,
            transform=text_transform,
            zorder=5,
        )
        text.set_clip_box(ax.bbox)
        text.set_clip_path(ax.patch)


def _legend_layout(labels: list[str]) -> tuple[int, int, float]:
    if not labels:
        return 1, 0, 0.0

    max_label_len = max(len(label) for label in labels)
    if max_label_len <= 8:
        max_columns = 6
    elif max_label_len <= 14:
        max_columns = 4
    elif max_label_len <= 20:
        max_columns = 3
    else:
        max_columns = 2

    target_rows = 10
    columns = max(1, min(max_columns, int(math.ceil(len(labels) / target_rows))))
    rows = int(math.ceil(len(labels) / columns))
    legend_height_in = max(0.78, 0.24 * rows + 0.22)
    return columns, rows, legend_height_in


def _render_standard_time_panel(ax, result: SimulationResult, panel_id: str, series: list[tuple[str, np.ndarray]]) -> tuple[list[object], list[str]]:
    rendered_series: list[tuple[str, np.ndarray, object]] = []
    for label, values in series:
        line = ax.plot(result.time_s, values, label=label)[0]
        rendered_series.append((label, values, line))
    ax.set_title(PLOT_PANEL_TITLES[panel_id], pad=10.0)
    ax.set_xlabel("Time, s")
    ax.set_ylabel(PLOT_PANEL_YLABELS[panel_id])
    ax.grid(True, alpha=0.3)
    ax.margins(x=0.05)
    _add_end_labels(ax, rendered_series)
    handles, labels = ax.get_legend_handles_labels()
    return list(handles), list(labels)


def _render_power_temperature_panel(
    ax,
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[object], list[str]]:
    temperature_series, power_series = _power_temperature_panel_data(result, visible_components=visible_components)
    power_ax = ax.twinx()
    handles: list[object] = []
    labels: list[str] = []

    for label, values in temperature_series:
        line = ax.plot(result.time_s, values, label=f"{label} | T")[0]
        handles.append(line)
        labels.append(line.get_label())
    for label, values in power_series:
        line = power_ax.plot(result.time_s, values, linestyle="--", label=f"{label} | P")[0]
        handles.append(line)
        labels.append(line.get_label())

    ax.set_title(PLOT_PANEL_TITLES["power_temperature"], pad=10.0)
    ax.set_xlabel("Time, s")
    ax.set_ylabel("Temperature, degC")
    power_ax.set_ylabel("Power, W")
    ax.grid(True, alpha=0.3)
    ax.margins(x=0.05)
    power_ax.margins(x=0.05)
    return handles, labels


def _render_energy_storage_panel(
    ax,
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[object], list[str]]:
    charge_series, flux_series = _energy_storage_panel_data(result, visible_components=visible_components)
    flux_ax = ax.twinx() if charge_series and flux_series else ax
    handles: list[object] = []
    labels: list[str] = []

    for label, values in charge_series:
        line = ax.plot(result.time_s, values, label=label)[0]
        handles.append(line)
        labels.append(line.get_label())

    flux_style_cycle = ("--", "-.")
    for index, (label, values) in enumerate(flux_series):
        line = flux_ax.plot(result.time_s, values, linestyle=flux_style_cycle[index % len(flux_style_cycle)], label=label)[0]
        handles.append(line)
        labels.append(line.get_label())

    ax.set_title(PLOT_PANEL_TITLES["energy_storage"], pad=10.0)
    ax.set_xlabel("Time, s")
    if charge_series:
        ax.set_ylabel("Charge, C")
    elif flux_series:
        ax.set_ylabel("Flux linkage, Wb")
    if flux_series and flux_ax is not ax:
        flux_ax.set_ylabel("Flux linkage, Wb")
    ax.grid(True, alpha=0.3)
    ax.margins(x=0.05)
    if flux_ax is not ax:
        flux_ax.margins(x=0.05)
    return handles, labels


def _render_iv_xy_panel(
    ax,
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[object], list[str]]:
    pairs = _iv_xy_panel_data(result, visible_components=visible_components)
    handles: list[object] = []
    labels: list[str] = []

    for label, x_values, y_values in pairs:
        line = ax.plot(x_values, y_values, label=label)[0]
        finite_mask = np.isfinite(x_values) & np.isfinite(y_values)
        if np.any(finite_mask):
            first_index = int(np.flatnonzero(finite_mask)[0])
            last_index = int(np.flatnonzero(finite_mask)[-1])
            ax.scatter([x_values[first_index]], [y_values[first_index]], s=22, color=line.get_color(), marker="o", zorder=4)
            ax.scatter(
                [x_values[last_index]],
                [y_values[last_index]],
                s=28,
                facecolors="none",
                edgecolors=line.get_color(),
                marker="s",
                zorder=4,
            )
        handles.append(line)
        labels.append(line.get_label())

    ax.set_title(PLOT_PANEL_TITLES["iv_xy"], pad=10.0)
    ax.set_xlabel("Voltage, V")
    ax.set_ylabel("Current, A")
    ax.grid(True, alpha=0.3)
    ax.axhline(0.0, color="#666666", linewidth=0.8, alpha=0.5)
    ax.axvline(0.0, color="#666666", linewidth=0.8, alpha=0.5)
    return handles, labels


def _render_audio_time_panel(
    ax,
    time_axis: np.ndarray,
    series: list[tuple[str, np.ndarray]],
    *,
    panel_id: str,
    xlabel: str,
) -> tuple[list[object], list[str]]:
    rendered_series: list[tuple[str, np.ndarray, object]] = []
    for label, values in series:
        trimmed = np.asarray(values[: time_axis.size], dtype=float)
        line = ax.plot(time_axis, trimmed, label=label)[0]
        rendered_series.append((label, trimmed, line))
    ax.set_title(PLOT_PANEL_TITLES[panel_id], pad=10.0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(PLOT_PANEL_YLABELS[panel_id])
    ax.grid(True, alpha=0.3)
    ax.margins(x=0.03)
    _add_end_labels(ax, rendered_series)
    handles, labels = ax.get_legend_handles_labels()
    return list(handles), list(labels)


def _render_audio_spectrum_panel(
    ax,
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[object], list[str]]:
    freqs, spectral_series = _audio_spectrum_panel_data(result, visible_components=visible_components)
    handles: list[object] = []
    labels: list[str] = []
    if freqs.size == 0:
        return handles, labels
    freq_limit_hz = min(_audio_sample_rate_hz(result) / 2.0, 6000.0)
    freq_mask = freqs <= freq_limit_hz
    for label, magnitude_db in spectral_series:
        line = ax.plot(freqs[freq_mask], magnitude_db[freq_mask], label=label)[0]
        handles.append(line)
        labels.append(line.get_label())
    ax.set_title(PLOT_PANEL_TITLES["audio_spectrum"], pad=10.0)
    ax.set_xlabel("Hz")
    ax.set_ylabel(PLOT_PANEL_YLABELS["audio_spectrum"])
    ax.grid(True, alpha=0.3)
    ax.margins(x=0.03)
    return handles, labels


def _render_audio_transfer_panel(
    ax,
    result: SimulationResult,
    *,
    visible_components: set[str] | None = None,
) -> tuple[list[object], list[str]]:
    pairs = _audio_transfer_panel_data(result, visible_components=visible_components)
    handles: list[object] = []
    labels: list[str] = []
    if not pairs:
        return handles, labels
    diagonal_limit = 1.0
    for label, x_values, y_values in pairs:
        diagonal_limit = max(diagonal_limit, float(np.max(np.abs(x_values))), float(np.max(np.abs(y_values))))
        scatter = ax.scatter(x_values, y_values, s=6, alpha=0.22, edgecolors="none", label=label)
        handles.append(scatter)
        labels.append(label)
    ax.plot(
        [-diagonal_limit, diagonal_limit],
        [-diagonal_limit, diagonal_limit],
        linestyle="--",
        linewidth=1.0,
        color="#444444",
        alpha=0.7,
    )
    ax.set_xlim(-diagonal_limit, diagonal_limit)
    ax.set_ylim(-diagonal_limit, diagonal_limit)
    ax.set_title(PLOT_PANEL_TITLES["audio_transfer"], pad=10.0)
    ax.set_xlabel("Input, V")
    ax.set_ylabel("Output, V")
    ax.grid(True, alpha=0.3)
    return handles, labels


def render_result_figure(
    figure: Figure,
    result: SimulationResult,
    panel_ids: list[str],
    *,
    visible_components: set[str] | None = None,
    figure_width_in: float = 12.8,
    panel_height_in: float = 4.8,
) -> list[str]:
    panels: list[tuple[str, object]] = []
    for panel_id in panel_ids:
        if panel_id == "power_temperature":
            panel_data = _power_temperature_panel_data(result, visible_components=visible_components)
            if panel_data[0] or panel_data[1]:
                panels.append((panel_id, panel_data))
            continue
        if panel_id == "energy_storage":
            panel_data = _energy_storage_panel_data(result, visible_components=visible_components)
            if panel_data[0] or panel_data[1]:
                panels.append((panel_id, panel_data))
            continue
        if panel_id == "iv_xy":
            panel_data = _iv_xy_panel_data(result, visible_components=visible_components)
            if panel_data:
                panels.append((panel_id, panel_data))
            continue
        if panel_id == "audio_zoom":
            panel_data = _audio_zoom_panel_data(result, visible_components=visible_components)
            if panel_data[1]:
                panels.append((panel_id, panel_data))
            continue
        if panel_id == "audio_spectrum":
            panel_data = _audio_spectrum_panel_data(result, visible_components=visible_components)
            if panel_data[1]:
                panels.append((panel_id, panel_data))
            continue
        if panel_id == "audio_transfer":
            panel_data = _audio_transfer_panel_data(result, visible_components=visible_components)
            if panel_data:
                panels.append((panel_id, panel_data))
            continue
        panel_data = plot_panel_series(result, panel_id, visible_components=visible_components)
        if panel_data:
            panels.append((panel_id, panel_data))

    figure.clear()
    figure.set_facecolor("white")
    if not panels:
        ax = figure.subplots(1, 1)
        ax.text(0.5, 0.5, "No plot data selected.", ha="center", va="center")
        ax.set_axis_off()
        figure.set_size_inches(figure_width_in, panel_height_in, forward=True)
        return []

    panel_count = len(panels)
    panel_layouts: list[tuple[str, object, int, int, float]] = []
    total_height_in = 0.0
    for panel_id, panel_data in panels:
        if panel_id == "power_temperature":
            temperature_series, power_series = panel_data
            labels = [f"{label} | T" for label, _values in temperature_series] + [f"{label} | P" for label, _values in power_series]
        elif panel_id == "energy_storage":
            charge_series, flux_series = panel_data
            labels = [label for label, _values in charge_series] + [label for label, _values in flux_series]
        elif panel_id == "iv_xy":
            labels = [label for label, _x_values, _y_values in panel_data]
        elif panel_id == "audio_zoom":
            _time_axis_ms, zoom_series = panel_data
            labels = [label for label, _values in zoom_series]
        elif panel_id == "audio_spectrum":
            _freqs, spectral_series = panel_data
            labels = [label for label, _values in spectral_series]
        elif panel_id == "audio_transfer":
            labels = [label for label, _x_values, _y_values in panel_data]
        else:
            labels = [label for label, _values in panel_data]
        legend_columns, legend_rows, legend_height_in = _legend_layout(labels)
        panel_layouts.append((panel_id, panel_data, legend_columns, legend_rows, legend_height_in))
        total_height_in += panel_height_in + legend_height_in

    panel_spacing_in = 0.9 * max(panel_count - 1, 0)
    figure.set_size_inches(figure_width_in, max(total_height_in + panel_spacing_in, panel_height_in + 0.55), forward=True)
    grid = figure.add_gridspec(
        panel_count,
        1,
        left=0.09,
        right=0.985,
        top=0.945,
        bottom=0.05,
        hspace=0.34,
        height_ratios=[panel_height_in + legend_height_in for _panel_id, _panel_data, _legend_columns, _legend_rows, legend_height_in in panel_layouts],
    )

    for index, (panel_id, panel_data, legend_columns, _legend_rows, legend_height_in) in enumerate(panel_layouts):
        panel_grid = grid[index, 0].subgridspec(
            2,
            1,
            height_ratios=[panel_height_in, legend_height_in],
            hspace=0.18,
        )
        ax = figure.add_subplot(panel_grid[0, 0])
        legend_ax = figure.add_subplot(panel_grid[1, 0])
        legend_ax.set_axis_off()

        if panel_id == "power_temperature":
            handles, labels = _render_power_temperature_panel(ax, result, visible_components=visible_components)
        elif panel_id == "energy_storage":
            handles, labels = _render_energy_storage_panel(ax, result, visible_components=visible_components)
        elif panel_id == "iv_xy":
            handles, labels = _render_iv_xy_panel(ax, result, visible_components=visible_components)
        elif panel_id == "audio_waveform":
            handles, labels = _render_audio_time_panel(
                ax,
                np.asarray(result.time_s, dtype=float),
                panel_data,
                panel_id=panel_id,
                xlabel="Time, s",
            )
        elif panel_id == "audio_zoom":
            time_axis_ms, zoom_series = panel_data
            handles, labels = _render_audio_time_panel(
                ax,
                time_axis_ms,
                zoom_series,
                panel_id=panel_id,
                xlabel="Time, ms",
            )
        elif panel_id == "audio_envelope":
            handles, labels = _render_audio_time_panel(
                ax,
                np.asarray(result.time_s, dtype=float),
                panel_data,
                panel_id=panel_id,
                xlabel="Time, s",
            )
        elif panel_id == "audio_spectrum":
            handles, labels = _render_audio_spectrum_panel(ax, result, visible_components=visible_components)
        elif panel_id == "audio_transfer":
            handles, labels = _render_audio_transfer_panel(ax, result, visible_components=visible_components)
        else:
            handles, labels = _render_standard_time_panel(ax, result, panel_id, panel_data)
        if handles and labels:
            legend_ax.legend(
                handles,
                labels,
                loc="upper left",
                ncols=legend_columns,
                fontsize="x-small",
                frameon=True,
                borderaxespad=0.0,
                columnspacing=1.0,
                handlelength=1.6,
                handletextpad=0.5,
                mode="expand",
                bbox_to_anchor=(0.0, 0.9, 1.0, 0.0),
            )

    return [panel_id for panel_id, _series in panels]
