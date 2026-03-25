from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    AudioBuffer,
    AudioFileSource,
    AudioSink,
    Circuit,
    IncandescentBulb,
    RealResistor,
    audio_buffer_from_series,
    load_audio_file,
    save_audio_file,
)


class FrozenIncandescentBulb(IncandescentBulb):
    """Control sample: same electrical law, but with frozen temperature."""

    def integrate_temperature(self, power_w: float, dt_s: float) -> None:
        del dt_s
        self.last_power_w = float(power_w)
        self.temperature_c = self.reference_temperature_c
        self.surface_temperature_c = self.reference_temperature_c
        self.glow = 0.0


@dataclass(slots=True)
class SegmentMetric:
    label: str
    start_s: float
    end_s: float
    input_rms_v: float
    thermal_output_rms_v: float
    frozen_output_rms_v: float
    thermal_gain_v_per_v: float
    frozen_gain_v_per_v: float
    gain_delta_percent: float


@dataclass(slots=True)
class ComparisonMetrics:
    duration_s: float
    sample_rate_hz: int
    source_peak_voltage_v: float
    thermal_temp_max_c: float
    thermal_temp_end_c: float
    thermal_resistance_start_ohm: float
    thermal_resistance_max_ohm: float
    thermal_resistance_end_ohm: float
    frozen_resistance_ohm: float
    thermal_vs_frozen_mae_v: float
    thermal_vs_frozen_rms_diff_v: float
    segments: list[SegmentMetric]


def build_demo_buffer(sample_rate_hz: int, duration_s: float) -> AudioBuffer:
    frame_count = max(int(round(sample_rate_hz * duration_s)), 1)
    time_s = np.arange(frame_count, dtype=float) / float(sample_rate_hz)

    music_bed = (
        0.45 * np.sin(2.0 * math.pi * 220.0 * time_s)
        + 0.22 * np.sin(2.0 * math.pi * 330.0 * time_s)
        + 0.12 * np.sin(2.0 * math.pi * 440.0 * time_s)
    )

    syllabic_envelope = np.zeros_like(time_s)
    for center_s in (0.10, 0.18, 0.25, 0.36, 0.45, 0.56, 0.68, 0.77, 0.89, 0.97, 1.05):
        half_width_s = 0.03
        window = np.clip(1.0 - ((time_s - center_s) / half_width_s) ** 2, 0.0, None)
        syllabic_envelope += window * window

    speech_like = syllabic_envelope * (
        0.30 * np.sin(2.0 * math.pi * 180.0 * time_s)
        + 0.16 * np.sin(2.0 * math.pi * 720.0 * time_s)
    )

    amplitude_profile = np.where(
        time_s < 0.15,
        0.15,
        np.where(time_s < 0.55, 1.0, np.where(time_s < 0.70, 0.20, np.where(time_s < 1.05, 1.0, 0.25))),
    )
    signal = amplitude_profile * (music_bed + speech_like)
    signal = 0.99 * signal / max(float(np.max(np.abs(signal))), 1.0e-9)
    return AudioBuffer(
        sample_rate_hz=sample_rate_hz,
        channels=1,
        samples=signal.astype(np.float32),
        metadata={"signal_type": "synthetic_music_plus_speech_like"},
    )


def prepare_input_buffer(input_path: str | None, sample_rate_hz: int, duration_s: float) -> AudioBuffer:
    if input_path:
        buffer = load_audio_file(
            input_path,
            target_sample_rate_hz=sample_rate_hz,
            mono=True,
            normalize=True,
        )
        frame_count = max(int(round(duration_s * sample_rate_hz)), 1)
        samples = buffer.channel_samples(0)
        if samples.size >= frame_count:
            trimmed = samples[:frame_count]
        else:
            repeats = int(math.ceil(frame_count / max(samples.size, 1)))
            tiled = np.tile(samples if samples.size else np.zeros(1, dtype=np.float32), repeats)
            trimmed = tiled[:frame_count]
        return AudioBuffer(
            sample_rate_hz=sample_rate_hz,
            channels=1,
            samples=np.asarray(trimmed, dtype=np.float32),
            metadata={"signal_type": "external_audio", "source_path": str(Path(input_path).expanduser())},
        )
    return build_demo_buffer(sample_rate_hz, duration_s)


def configure_fast_bulb(bulb: IncandescentBulb) -> IncandescentBulb:
    bulb.heat_capacity_j_per_k = 0.006
    bulb.thermal_resistance_k_per_w = 120.0
    bulb.contact_thermal_resistance_k_per_w = 40.0
    bulb.calibrate_thermal_network(case_fraction=0.30, junction_fraction=0.45)
    return bulb


def build_limiter_circuit(
    name: str,
    *,
    buffer: AudioBuffer,
    peak_voltage_v: float,
    bulb_cls: type[IncandescentBulb],
) -> Circuit:
    circuit = Circuit(name)
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            audio_buffer=buffer,
            peak_voltage_v=peak_voltage_v,
            internal_resistance_ohm=0.30,
            normalize=False,
            target_sample_rate_hz=buffer.sample_rate_hz,
        )
    )
    circuit.add(RealResistor("R_DRIVE", "vin", "vhot", resistance_ohm=1.0, temperature_coefficient=0.0))
    bulb = configure_fast_bulb(
        bulb_cls(
            "LAMP",
            "vhot",
            "vout",
            rated_voltage_v=2.2,
            rated_power_w=0.35,
            cold_ratio=14.0,
            filament_operating_temp_c=240.0,
        )
    )
    circuit.add(bulb)
    circuit.add(RealResistor("R_LOAD", "vout", "0", resistance_ohm=6.0, temperature_coefficient=0.0))
    circuit.add(AudioSink("OUT", "vout", "0", input_resistance_ohm=1.0e9, output_gain=1.0, dc_block=False))
    return circuit


def simulate_pair(
    *,
    buffer: AudioBuffer,
    duration_s: float,
    sample_rate_hz: int,
    peak_voltage_v: float,
):
    dt_s = 1.0 / max(sample_rate_hz, 1)
    thermal = build_limiter_circuit("Thermal bulb limiter", buffer=buffer, peak_voltage_v=peak_voltage_v, bulb_cls=IncandescentBulb)
    frozen = build_limiter_circuit("Frozen bulb limiter", buffer=buffer, peak_voltage_v=peak_voltage_v, bulb_cls=FrozenIncandescentBulb)
    thermal_result = thermal.simulate(duration_s, dt_s)
    frozen_result = frozen.simulate(duration_s, dt_s)
    return thermal_result, frozen_result


def rms(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(array * array)))


def segment_metric(
    label: str,
    start_s: float,
    end_s: float,
    *,
    input_samples: np.ndarray,
    thermal_output: np.ndarray,
    frozen_output: np.ndarray,
    sample_rate_hz: int,
) -> SegmentMetric:
    start_index = max(int(round(start_s * sample_rate_hz)), 0)
    end_index = min(int(round(end_s * sample_rate_hz)), input_samples.size)
    section = slice(start_index, end_index)
    input_rms_v = rms(input_samples[section])
    thermal_output_rms_v = rms(thermal_output[section])
    frozen_output_rms_v = rms(frozen_output[section])
    thermal_gain = thermal_output_rms_v / max(input_rms_v, 1.0e-12)
    frozen_gain = frozen_output_rms_v / max(input_rms_v, 1.0e-12)
    return SegmentMetric(
        label=label,
        start_s=start_s,
        end_s=end_s,
        input_rms_v=input_rms_v,
        thermal_output_rms_v=thermal_output_rms_v,
        frozen_output_rms_v=frozen_output_rms_v,
        thermal_gain_v_per_v=thermal_gain,
        frozen_gain_v_per_v=frozen_gain,
        gain_delta_percent=100.0 * (thermal_gain - frozen_gain) / max(frozen_gain, 1.0e-12),
    )


def align_series(values: np.ndarray, target_size: int) -> np.ndarray:
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


def rolling_rms_gain(input_samples: np.ndarray, output_samples: np.ndarray, *, window_samples: int) -> np.ndarray:
    if window_samples <= 1:
        return np.abs(output_samples) / np.maximum(np.abs(input_samples), 1.0e-9)
    kernel = np.ones(window_samples, dtype=float) / float(window_samples)
    input_power = np.convolve(np.asarray(input_samples, dtype=float) ** 2, kernel, mode="same")
    output_power = np.convolve(np.asarray(output_samples, dtype=float) ** 2, kernel, mode="same")
    return np.sqrt(output_power) / np.maximum(np.sqrt(input_power), 1.0e-9)


def collect_metrics(
    *,
    buffer: AudioBuffer,
    thermal_result,
    frozen_result,
    sample_rate_hz: int,
    duration_s: float,
    peak_voltage_v: float,
) -> ComparisonMetrics:
    thermal_output = np.asarray(thermal_result.component_observables["OUT"]["captured_v"], dtype=float)
    frozen_output = np.asarray(frozen_result.component_observables["OUT"]["captured_v"], dtype=float)
    input_samples = align_series(buffer.channel_samples(0) * float(peak_voltage_v), thermal_output.size)
    lamp_temp = np.asarray(thermal_result.component_observables["LAMP"]["temperature_c"], dtype=float)
    lamp_resistance = np.asarray(thermal_result.component_observables["LAMP"]["resistance_ohm"], dtype=float)
    frozen_resistance = np.asarray(frozen_result.component_observables["LAMP"]["resistance_ohm"], dtype=float)

    segments = [
        segment_metric(
            "loud_burst_1",
            0.18,
            0.32,
            input_samples=input_samples,
            thermal_output=thermal_output,
            frozen_output=frozen_output,
            sample_rate_hz=sample_rate_hz,
        ),
        segment_metric(
            "loud_burst_2",
            0.40,
            0.55,
            input_samples=input_samples,
            thermal_output=thermal_output,
            frozen_output=frozen_output,
            sample_rate_hz=sample_rate_hz,
        ),
        segment_metric(
            "loud_burst_3",
            0.85,
            1.00,
            input_samples=input_samples,
            thermal_output=thermal_output,
            frozen_output=frozen_output,
            sample_rate_hz=sample_rate_hz,
        ),
    ]
    return ComparisonMetrics(
        duration_s=duration_s,
        sample_rate_hz=sample_rate_hz,
        source_peak_voltage_v=peak_voltage_v,
        thermal_temp_max_c=float(np.max(lamp_temp)),
        thermal_temp_end_c=float(lamp_temp[-1]),
        thermal_resistance_start_ohm=float(lamp_resistance[0]),
        thermal_resistance_max_ohm=float(np.max(lamp_resistance)),
        thermal_resistance_end_ohm=float(lamp_resistance[-1]),
        frozen_resistance_ohm=float(frozen_resistance[-1]),
        thermal_vs_frozen_mae_v=float(np.mean(np.abs(thermal_output - frozen_output))),
        thermal_vs_frozen_rms_diff_v=rms(thermal_output - frozen_output),
        segments=segments,
    )


def save_audio_pair(
    output_dir: Path,
    *,
    sample_rate_hz: int,
    thermal_output: np.ndarray,
    frozen_output: np.ndarray,
) -> None:
    common_peak = max(float(np.max(np.abs(thermal_output))), float(np.max(np.abs(frozen_output))), 1.0e-9)
    scale = 0.98 / common_peak
    thermal_buffer = audio_buffer_from_series((thermal_output * scale).astype(np.float32), sample_rate_hz, channels=1, normalize=False)
    frozen_buffer = audio_buffer_from_series((frozen_output * scale).astype(np.float32), sample_rate_hz, channels=1, normalize=False)
    save_audio_file(output_dir / "thermal.wav", thermal_buffer, normalize=False)
    save_audio_file(output_dir / "frozen.wav", frozen_buffer, normalize=False)


def render_plot(
    output_dir: Path,
    *,
    buffer: AudioBuffer,
    thermal_result,
    frozen_result,
    sample_rate_hz: int,
) -> None:
    time_s = np.asarray(thermal_result.time_s, dtype=float)
    thermal_output = np.asarray(thermal_result.component_observables["OUT"]["captured_v"], dtype=float)
    frozen_output = np.asarray(frozen_result.component_observables["OUT"]["captured_v"], dtype=float)
    input_samples = align_series(buffer.channel_samples(0), thermal_output.size)
    lamp_temp = np.asarray(thermal_result.component_observables["LAMP"]["temperature_c"], dtype=float)
    lamp_resistance = np.asarray(thermal_result.component_observables["LAMP"]["resistance_ohm"], dtype=float)
    window_gain_samples = max(int(round(0.040 * sample_rate_hz)), 8)
    thermal_gain = rolling_rms_gain(input_samples, thermal_output, window_samples=window_gain_samples)
    frozen_gain = rolling_rms_gain(input_samples, frozen_output, window_samples=window_gain_samples)

    figure, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)

    early = (time_s >= 0.20) & (time_s <= 0.26)
    late = (time_s >= 0.88) & (time_s <= 0.94)
    axes[0, 0].plot(time_s[early], input_samples[early], label="Input", linewidth=1.2, color="#475569")
    axes[0, 0].plot(time_s[early], thermal_output[early], label="Thermal", linewidth=1.1, color="#b45309")
    axes[0, 0].plot(time_s[early], frozen_output[early], label="Frozen", linewidth=1.0, color="#0f766e")
    axes[0, 0].set_title("Early loud burst")
    axes[0, 0].set_xlabel("Time, s")
    axes[0, 0].set_ylabel("Voltage, V")
    axes[0, 0].legend(loc="upper right")
    axes[0, 0].grid(alpha=0.25)

    axes[0, 1].plot(time_s[late], input_samples[late], label="Input", linewidth=1.2, color="#475569")
    axes[0, 1].plot(time_s[late], thermal_output[late], label="Thermal", linewidth=1.1, color="#b45309")
    axes[0, 1].plot(time_s[late], frozen_output[late], label="Frozen", linewidth=1.0, color="#0f766e")
    axes[0, 1].set_title("Late loud burst")
    axes[0, 1].set_xlabel("Time, s")
    axes[0, 1].set_ylabel("Voltage, V")
    axes[0, 1].legend(loc="upper right")
    axes[0, 1].grid(alpha=0.25)

    axes[1, 0].plot(time_s, lamp_temp, label="Temperature, C", linewidth=1.2, color="#b91c1c")
    second_axis = axes[1, 0].twinx()
    second_axis.plot(time_s, lamp_resistance, label="Resistance, Ohm", linewidth=1.1, color="#1d4ed8")
    axes[1, 0].set_title("Lamp state")
    axes[1, 0].set_xlabel("Time, s")
    axes[1, 0].set_ylabel("Temperature, C")
    second_axis.set_ylabel("Resistance, Ohm")
    axes[1, 0].grid(alpha=0.25)
    lines = axes[1, 0].get_lines() + second_axis.get_lines()
    labels = [line.get_label() for line in lines]
    axes[1, 0].legend(lines, labels, loc="upper left")

    axes[1, 1].plot(time_s, thermal_gain, label="Thermal gain", linewidth=1.2, color="#b45309")
    axes[1, 1].plot(time_s, frozen_gain, label="Frozen gain", linewidth=1.0, color="#0f766e")
    axes[1, 1].set_title("Rolling RMS gain")
    axes[1, 1].set_xlabel("Time, s")
    axes[1, 1].set_ylabel("V/V")
    axes[1, 1].legend(loc="upper right")
    axes[1, 1].grid(alpha=0.25)

    figure.suptitle("Thermal bulb limiter: waveform deformation with and without heating", fontsize=14)
    figure.savefig(output_dir / "comparison.png", dpi=160)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a thermally active filament limiter against a frozen-temperature control and export metrics, WAVs, and a plot.",
    )
    parser.add_argument("--input", help="Optional external audio file. If omitted, a deterministic synthetic test signal is generated.")
    parser.add_argument("--duration", type=float, default=1.2, help="Simulation duration in seconds.")
    parser.add_argument("--sample-rate", type=int, default=8000, help="Simulation sample rate in Hz.")
    parser.add_argument("--peak-voltage", type=float, default=22.0, help="AudioFileSource peak voltage in circuit volts.")
    parser.add_argument("--output-dir", default="examples/generated/thermal_bulb_limiter", help="Directory for metrics, WAVs, and comparison plot.")
    args = parser.parse_args()

    if args.sample_rate <= 0:
        raise SystemExit("--sample-rate must be positive.")
    if args.duration <= 0.0:
        raise SystemExit("--duration must be positive.")
    if args.peak_voltage <= 0.0:
        raise SystemExit("--peak-voltage must be positive.")

    buffer = prepare_input_buffer(args.input, args.sample_rate, args.duration)
    duration_s = float(buffer.duration_s)
    thermal_result, frozen_result = simulate_pair(
        buffer=buffer,
        duration_s=duration_s,
        sample_rate_hz=args.sample_rate,
        peak_voltage_v=args.peak_voltage,
    )
    metrics = collect_metrics(
        buffer=buffer,
        thermal_result=thermal_result,
        frozen_result=frozen_result,
        sample_rate_hz=args.sample_rate,
        duration_s=duration_s,
        peak_voltage_v=args.peak_voltage,
    )

    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(asdict(metrics), indent=2, ensure_ascii=False), encoding="utf-8")

    thermal_output = np.asarray(thermal_result.component_observables["OUT"]["captured_v"], dtype=float)
    frozen_output = np.asarray(frozen_result.component_observables["OUT"]["captured_v"], dtype=float)
    save_audio_pair(output_dir, sample_rate_hz=args.sample_rate, thermal_output=thermal_output, frozen_output=frozen_output)
    render_plot(output_dir, buffer=buffer, thermal_result=thermal_result, frozen_result=frozen_result, sample_rate_hz=args.sample_rate)

    print(f"Saved report artifacts to {output_dir}")
    print(json.dumps(asdict(metrics), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
