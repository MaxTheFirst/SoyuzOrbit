from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.project import load_project  # noqa: E402


PLOT_IDS = (
    "wave-early",
    "wave-late",
    "bulb-temperature",
    "bulb-resistance",
    "gain-compare",
    "opamp-current",
    "late-difference",
)

PLOT_FILENAMES = {
    "wave-early": "01_wave_early.png",
    "wave-late": "02_wave_late.png",
    "bulb-temperature": "03_bulb_temperature.png",
    "bulb-resistance": "04_bulb_resistance.png",
    "gain-compare": "05_gain_compare.png",
    "opamp-current": "06_opamp_current.png",
    "late-difference": "07_late_difference.png",
}


@dataclass(slots=True)
class WindowMetric:
    label: str
    start_s: float
    end_s: float
    input_rms_v: float
    thermal_output_rms_v: float
    frozen_output_rms_v: float
    thermal_gain_v_per_v: float
    frozen_gain_v_per_v: float
    thermal_minus_frozen_rms_v: float
    thermal_peak_v: float
    frozen_peak_v: float


@dataclass(slots=True)
class ThermalAmpMetrics:
    duration_s: float
    dt_s: float
    adaptive_retry_thermal: bool
    adaptive_retry_frozen: bool
    bulb_temp_start_c: float
    bulb_temp_end_c: float
    bulb_temp_max_c: float
    bulb_surface_temp_end_c: float
    bulb_resistance_start_ohm: float
    bulb_resistance_end_ohm: float
    bulb_resistance_max_ohm: float
    frozen_resistance_ohm: float
    opamp_output_current_peak_thermal_a: float
    opamp_output_current_peak_frozen_a: float
    full_output_mae_v: float
    full_output_rms_diff_v: float
    output_corrcoef: float
    gain_early_thermal_v_per_v: float
    gain_early_frozen_v_per_v: float
    gain_late_thermal_v_per_v: float
    gain_late_frozen_v_per_v: float
    windows: list[WindowMetric]


def _pick_duration(module_or_project, override: float | None) -> float:
    if override is not None:
        return float(override)
    return float(module_or_project.settings.duration_s)


def _pick_dt(module_or_project, override: float | None) -> float:
    if override is not None:
        return float(override)
    return float(module_or_project.settings.dt_s)


def _series(result, component_name: str, key: str) -> np.ndarray:
    values = result.component_observables.get(component_name, {}).get(key)
    if values is None:
        raise KeyError(f"Observable {component_name}.{key} is not available")
    return np.asarray(values, dtype=float)


def _rms(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(array * array)))


def _align(values: np.ndarray, target_size: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.size == target_size:
        return array
    if array.size == target_size - 1 and array.size > 0:
        return np.concatenate([array, array[-1:]])
    if array.size > target_size:
        return array[:target_size]
    if array.size == 0:
        return np.zeros(target_size, dtype=float)
    padding = np.full(target_size - array.size, array[-1], dtype=float)
    return np.concatenate([array, padding])


def _rolling_rms_gain(input_samples: np.ndarray, output_samples: np.ndarray, *, window_samples: int) -> np.ndarray:
    window = max(int(window_samples), 1)
    kernel = np.ones(window, dtype=float) / float(window)
    input_power = np.convolve(np.asarray(input_samples, dtype=float) ** 2, kernel, mode="same")
    output_power = np.convolve(np.asarray(output_samples, dtype=float) ** 2, kernel, mode="same")
    return np.sqrt(output_power) / np.maximum(np.sqrt(input_power), 1.0e-12)


def _window_slice(time_s: np.ndarray, start_s: float, end_s: float) -> np.ndarray:
    mask = (time_s >= start_s) & (time_s <= end_s)
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        return np.array([0, min(time_s.size - 1, 1)], dtype=int)
    return indices


def _window_metric(
    label: str,
    time_s: np.ndarray,
    input_samples: np.ndarray,
    thermal_output: np.ndarray,
    frozen_output: np.ndarray,
    start_s: float,
    end_s: float,
) -> WindowMetric:
    indices = _window_slice(time_s, start_s, end_s)
    input_window = input_samples[indices]
    thermal_window = thermal_output[indices]
    frozen_window = frozen_output[indices]
    input_rms = _rms(input_window)
    thermal_rms = _rms(thermal_window)
    frozen_rms = _rms(frozen_window)
    return WindowMetric(
        label=label,
        start_s=float(time_s[indices[0]]),
        end_s=float(time_s[indices[-1]]),
        input_rms_v=input_rms,
        thermal_output_rms_v=thermal_rms,
        frozen_output_rms_v=frozen_rms,
        thermal_gain_v_per_v=thermal_rms / max(input_rms, 1.0e-12),
        frozen_gain_v_per_v=frozen_rms / max(input_rms, 1.0e-12),
        thermal_minus_frozen_rms_v=_rms(thermal_window - frozen_window),
        thermal_peak_v=float(np.max(np.abs(thermal_window))),
        frozen_peak_v=float(np.max(np.abs(frozen_window))),
    )


def collect_bundle(thermal_result, frozen_result) -> dict[str, np.ndarray | float | list[WindowMetric]]:
    time_s = np.asarray(thermal_result.time_s, dtype=float)
    thermal_output = _series(thermal_result, "OUT_MON", "captured_v")
    frozen_output = _align(_series(frozen_result, "OUT_MON", "captured_v"), thermal_output.size)
    input_wave = _align(_series(thermal_result, "VM_IN", "reading_v"), thermal_output.size)
    bulb_temp = _align(_series(thermal_result, "BULB_FB", "temperature_c"), thermal_output.size)
    bulb_surface = _align(_series(thermal_result, "BULB_FB", "surface_temperature_c"), thermal_output.size)
    bulb_resistance = _align(_series(thermal_result, "BULB_FB", "resistance_ohm"), thermal_output.size)
    frozen_temp = _align(_series(frozen_result, "BULB_FB", "temperature_c"), thermal_output.size)
    frozen_resistance = _align(_series(frozen_result, "BULB_FB", "resistance_ohm"), thermal_output.size)
    thermal_opamp_current = _align(_series(thermal_result, "OA1", "output_current_a"), thermal_output.size)
    frozen_opamp_current = _align(_series(frozen_result, "OA1", "output_current_a"), thermal_output.size)

    gain_window_samples = max(int(round(0.024 / max(float(time_s[1] - time_s[0]), 1.0e-12))), 8)
    thermal_gain = _rolling_rms_gain(input_wave, thermal_output, window_samples=gain_window_samples)
    frozen_gain = _rolling_rms_gain(input_wave, frozen_output, window_samples=gain_window_samples)

    early_window = _window_metric("early", time_s, input_wave, thermal_output, frozen_output, 0.040, 0.072)
    late_window = _window_metric("late", time_s, input_wave, thermal_output, frozen_output, 0.192, 0.224)

    output_corrcoef = float(np.corrcoef(thermal_output, frozen_output)[0, 1]) if thermal_output.size >= 2 else 1.0
    metrics = ThermalAmpMetrics(
        duration_s=float(time_s[-1]) if time_s.size else 0.0,
        dt_s=float(time_s[1] - time_s[0]) if time_s.size >= 2 else 0.0,
        adaptive_retry_thermal=bool(thermal_result.metadata.get("adaptive_retry", False)),
        adaptive_retry_frozen=bool(frozen_result.metadata.get("adaptive_retry", False)),
        bulb_temp_start_c=float(bulb_temp[0]),
        bulb_temp_end_c=float(bulb_temp[-1]),
        bulb_temp_max_c=float(np.max(bulb_temp)),
        bulb_surface_temp_end_c=float(bulb_surface[-1]),
        bulb_resistance_start_ohm=float(bulb_resistance[0]),
        bulb_resistance_end_ohm=float(bulb_resistance[-1]),
        bulb_resistance_max_ohm=float(np.max(bulb_resistance)),
        frozen_resistance_ohm=float(frozen_resistance[-1]),
        opamp_output_current_peak_thermal_a=float(np.max(np.abs(thermal_opamp_current))),
        opamp_output_current_peak_frozen_a=float(np.max(np.abs(frozen_opamp_current))),
        full_output_mae_v=float(np.mean(np.abs(thermal_output - frozen_output))),
        full_output_rms_diff_v=_rms(thermal_output - frozen_output),
        output_corrcoef=output_corrcoef,
        gain_early_thermal_v_per_v=early_window.thermal_gain_v_per_v,
        gain_early_frozen_v_per_v=early_window.frozen_gain_v_per_v,
        gain_late_thermal_v_per_v=late_window.thermal_gain_v_per_v,
        gain_late_frozen_v_per_v=late_window.frozen_gain_v_per_v,
        windows=[early_window, late_window],
    )

    return {
        "time_s": time_s,
        "input_wave": input_wave,
        "thermal_output": thermal_output,
        "frozen_output": frozen_output,
        "bulb_temp": bulb_temp,
        "bulb_surface": bulb_surface,
        "frozen_temp": frozen_temp,
        "bulb_resistance": bulb_resistance,
        "frozen_resistance": frozen_resistance,
        "thermal_gain": thermal_gain,
        "frozen_gain": frozen_gain,
        "thermal_opamp_current": thermal_opamp_current,
        "frozen_opamp_current": frozen_opamp_current,
        "metrics": metrics,
    }


def _plot_time_triplet(
    output_path: Path,
    *,
    time_axis: np.ndarray,
    series_a: tuple[str, np.ndarray, str],
    series_b: tuple[str, np.ndarray, str],
    series_c: tuple[str, np.ndarray, str],
    title: str,
    xlabel: str = "Time, s",
    ylabel: str = "Voltage, V",
) -> None:
    figure, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
    for label, values, color in (series_a, series_b, series_c):
        ax.plot(time_axis, values, label=label, linewidth=1.3, color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _plot_temperature(output_path: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]]) -> None:
    time_s = np.asarray(bundle["time_s"], dtype=float)
    figure, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
    ax.plot(time_s, np.asarray(bundle["bulb_temp"], dtype=float), label="Thermal bulb junction", linewidth=1.35, color="#b91c1c")
    ax.plot(time_s, np.asarray(bundle["bulb_surface"], dtype=float), label="Thermal bulb surface", linewidth=1.25, color="#ea580c")
    ax.plot(time_s, np.asarray(bundle["frozen_temp"], dtype=float), label="Frozen bulb", linewidth=1.2, color="#0f766e")
    ax.set_title("Feedback bulb temperature")
    ax.set_xlabel("Time, s")
    ax.set_ylabel("Temperature, degC")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _plot_resistance(output_path: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]]) -> None:
    time_s = np.asarray(bundle["time_s"], dtype=float)
    figure, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
    ax.plot(time_s, np.asarray(bundle["bulb_resistance"], dtype=float), label="Thermal Rfb", linewidth=1.35, color="#1d4ed8")
    ax.plot(time_s, np.asarray(bundle["frozen_resistance"], dtype=float), label="Frozen Rfb", linewidth=1.25, color="#0f766e")
    ax.set_title("Feedback resistance drift")
    ax.set_xlabel("Time, s")
    ax.set_ylabel("Resistance, Ohm")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _plot_gain(output_path: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]]) -> None:
    time_s = np.asarray(bundle["time_s"], dtype=float)
    figure, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
    ax.plot(time_s, np.asarray(bundle["thermal_gain"], dtype=float), label="Thermal gain", linewidth=1.35, color="#b45309")
    ax.plot(time_s, np.asarray(bundle["frozen_gain"], dtype=float), label="Frozen gain", linewidth=1.25, color="#0f766e")
    ax.set_title("Rolling RMS closed-loop gain")
    ax.set_xlabel("Time, s")
    ax.set_ylabel("Gain, V/V")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _plot_opamp_current(output_path: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]]) -> None:
    time_s = np.asarray(bundle["time_s"], dtype=float)
    figure, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
    ax.plot(time_s, np.asarray(bundle["thermal_opamp_current"], dtype=float), label="Thermal OA1 Iout", linewidth=1.35, color="#7c3aed")
    ax.plot(time_s, np.asarray(bundle["frozen_opamp_current"], dtype=float), label="Frozen OA1 Iout", linewidth=1.25, color="#0f766e")
    ax.set_title("Op-amp output current")
    ax.set_xlabel("Time, s")
    ax.set_ylabel("Current, A")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    figure.savefig(output_path, dpi=160)
    plt.close(figure)


def _plot_wave_window(output_path: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]], *, start_s: float, end_s: float, title: str) -> None:
    time_s = np.asarray(bundle["time_s"], dtype=float)
    indices = _window_slice(time_s, start_s, end_s)
    _plot_time_triplet(
        output_path,
        time_axis=time_s[indices],
        series_a=("Input", np.asarray(bundle["input_wave"], dtype=float)[indices], "#475569"),
        series_b=("Thermal output", np.asarray(bundle["thermal_output"], dtype=float)[indices], "#b45309"),
        series_c=("Frozen output", np.asarray(bundle["frozen_output"], dtype=float)[indices], "#0f766e"),
        title=title,
    )


def _plot_late_difference(output_path: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]]) -> None:
    time_s = np.asarray(bundle["time_s"], dtype=float)
    indices = _window_slice(time_s, 0.192, 0.224)
    thermal_output = np.asarray(bundle["thermal_output"], dtype=float)[indices]
    frozen_output = np.asarray(bundle["frozen_output"], dtype=float)[indices]
    delta = thermal_output - frozen_output
    _plot_time_triplet(
        output_path,
        time_axis=time_s[indices],
        series_a=("Thermal output", thermal_output, "#b45309"),
        series_b=("Frozen output", frozen_output, "#0f766e"),
        series_c=("Thermal - frozen", delta, "#1d4ed8"),
        title="Late-window output difference",
    )


def render_plot(plot_id: str, output_dir: Path, bundle: dict[str, np.ndarray | float | list[WindowMetric]]) -> Path:
    output_path = output_dir / PLOT_FILENAMES[plot_id]
    if plot_id == "wave-early":
        _plot_wave_window(output_path, bundle, start_s=0.040, end_s=0.072, title="Early waveform window")
    elif plot_id == "wave-late":
        _plot_wave_window(output_path, bundle, start_s=0.192, end_s=0.224, title="Late waveform window")
    elif plot_id == "bulb-temperature":
        _plot_temperature(output_path, bundle)
    elif plot_id == "bulb-resistance":
        _plot_resistance(output_path, bundle)
    elif plot_id == "gain-compare":
        _plot_gain(output_path, bundle)
    elif plot_id == "opamp-current":
        _plot_opamp_current(output_path, bundle)
    elif plot_id == "late-difference":
        _plot_late_difference(output_path, bundle)
    else:
        raise ValueError(f"Unknown plot id: {plot_id}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare thermal and frozen feedback-amplifier JSON projects and export separate analysis plots.",
    )
    parser.add_argument("--thermal-project", default="examples/thermal_feedback_amp.json", help="Thermal JSON project.")
    parser.add_argument("--frozen-project", default="examples/thermal_feedback_amp_frozen.json", help="Frozen JSON project.")
    parser.add_argument("--duration", type=float, help="Override simulation duration in seconds.")
    parser.add_argument("--dt", type=float, help="Override timestep in seconds.")
    parser.add_argument("--output-dir", default="examples/generated/thermal_feedback_amp_compare", help="Directory for PNGs and metrics.json.")
    parser.add_argument(
        "--plot",
        choices=("all", *PLOT_IDS),
        default="all",
        help="Export all plots or just one plot.",
    )
    args = parser.parse_args()

    thermal_project_path = Path(args.thermal_project).expanduser()
    frozen_project_path = Path(args.frozen_project).expanduser()
    thermal_project = load_project(thermal_project_path)
    frozen_project = load_project(frozen_project_path)
    duration_s = _pick_duration(thermal_project, args.duration)
    dt_s = _pick_dt(thermal_project, args.dt)
    frozen_duration_s = _pick_duration(frozen_project, args.duration)
    frozen_dt_s = _pick_dt(frozen_project, args.dt)
    if abs(duration_s - frozen_duration_s) > 1.0e-12:
        raise SystemExit("Thermal and frozen projects must use the same duration.")
    if abs(dt_s - frozen_dt_s) > 1.0e-12:
        raise SystemExit("Thermal and frozen projects must use the same dt.")

    thermal_result = thermal_project.to_circuit().simulate(duration_s, dt_s)
    frozen_result = frozen_project.to_circuit().simulate(duration_s, dt_s)
    bundle = collect_bundle(thermal_result, frozen_result)

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = bundle["metrics"]
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(asdict(metrics), indent=2, ensure_ascii=False), encoding="utf-8")

    plot_ids = list(PLOT_IDS) if args.plot == "all" else [args.plot]
    for plot_id in plot_ids:
        render_plot(plot_id, output_dir, bundle)

    print(f"Saved metrics to {metrics_path}")
    for plot_id in plot_ids:
        print(f"Saved plot to {output_dir / PLOT_FILENAMES[plot_id]}")
    print(json.dumps(asdict(metrics), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
