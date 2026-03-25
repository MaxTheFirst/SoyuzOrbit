from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

cache_root = Path(tempfile.gettempdir()) / "soyuzorbit-cache"
cache_root.mkdir(parents=True, exist_ok=True)
matplotlib_cache = cache_root / "matplotlib"
matplotlib_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))

import matplotlib
import numpy as np

from core import load_audio_file, probe_audio_file

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def _safe_float(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(value)


def _mono_series(path: str | Path, sample_rate_hz: int, *, normalize: bool = False) -> np.ndarray:
    buffer = load_audio_file(path, target_sample_rate_hz=sample_rate_hz, mono=True, normalize=normalize)
    return np.asarray(buffer.channel_samples(0), dtype=np.float32)


def _moving_rms(samples: np.ndarray, window_samples: int) -> np.ndarray:
    window = max(int(window_samples), 1)
    kernel = np.ones(window, dtype=np.float32) / float(window)
    power = np.square(samples, dtype=np.float32)
    return np.sqrt(np.convolve(power, kernel, mode="same"), dtype=np.float32)


def _zero_crossings_per_s(samples: np.ndarray, sample_rate_hz: int) -> float:
    if samples.size < 2:
        return 0.0
    signs = np.signbit(samples)
    crossings = np.count_nonzero(signs[1:] != signs[:-1])
    duration_s = max(samples.size / float(sample_rate_hz), 1.0e-9)
    return crossings / duration_s


def _active_mask(reference: np.ndarray) -> np.ndarray:
    if reference.size == 0:
        return np.zeros(0, dtype=bool)
    threshold = max(float(np.max(np.abs(reference))) * 0.08, 1.0e-4)
    return np.abs(reference) >= threshold


def _spectral_metrics(samples: np.ndarray, sample_rate_hz: int) -> dict[str, float]:
    if samples.size == 0:
        return {
            "spectral_centroid_hz": 0.0,
            "spectral_rolloff_95_hz": 0.0,
            "high_band_ratio": 0.0,
        }
    window = np.hanning(samples.size).astype(np.float32)
    spectrum = np.fft.rfft(samples * window)
    power = np.square(np.abs(spectrum), dtype=np.float64)
    freqs = np.fft.rfftfreq(samples.size, d=1.0 / float(sample_rate_hz))
    total_power = float(np.sum(power))
    if total_power <= 1.0e-20:
        return {
            "spectral_centroid_hz": 0.0,
            "spectral_rolloff_95_hz": 0.0,
            "high_band_ratio": 0.0,
        }
    centroid = float(np.sum(freqs * power) / total_power)
    cumulative = np.cumsum(power)
    rolloff_index = int(np.searchsorted(cumulative, 0.95 * total_power, side="left"))
    rolloff_hz = float(freqs[min(max(rolloff_index, 0), len(freqs) - 1)])
    high_band_ratio = float(np.sum(power[freqs >= 2500.0]) / total_power)
    return {
        "spectral_centroid_hz": centroid,
        "spectral_rolloff_95_hz": rolloff_hz,
        "high_band_ratio": high_band_ratio,
    }


def _signal_metrics(samples: np.ndarray, sample_rate_hz: int, envelope: np.ndarray) -> dict[str, float]:
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if samples.size else 0.0
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    active_envelope = envelope[envelope > max(peak * 0.05, 1.0e-5)]
    if active_envelope.size >= 8:
        high = float(np.percentile(active_envelope, 95))
        low = float(np.percentile(active_envelope, 10))
        dynamic_range_db = 20.0 * math.log10(max(high, 1.0e-12) / max(low, 1.0e-12))
    else:
        dynamic_range_db = 0.0
    metrics = {
        "rms": rms,
        "peak": peak,
        "crest_factor": peak / max(rms, 1.0e-12),
        "zero_crossings_per_s": _zero_crossings_per_s(samples, sample_rate_hz),
        "dynamic_range_db": dynamic_range_db,
    }
    metrics.update(_spectral_metrics(samples, sample_rate_hz))
    return {key: _safe_float(value) for key, value in metrics.items()}


def _pick_zoom_window(input_samples: np.ndarray, output_samples: np.ndarray, window_samples: int) -> tuple[int, int]:
    window = max(int(window_samples), 32)
    combined = np.square(input_samples, dtype=np.float32) + np.square(output_samples, dtype=np.float32)
    energy = np.convolve(combined, np.ones(window, dtype=np.float32), mode="same")
    center = int(np.argmax(energy)) if energy.size else 0
    start = max(center - window // 2, 0)
    stop = min(start + window, input_samples.size)
    start = max(stop - window, 0)
    return start, stop


def _plot_comparison(
    input_samples: np.ndarray,
    output_samples: np.ndarray,
    *,
    sample_rate_hz: int,
    envelope_ms: float,
    zoom_ms: float,
    output_path: Path,
    title: str,
) -> dict[str, float]:
    envelope_window = max(int(round(sample_rate_hz * envelope_ms / 1000.0)), 1)
    zoom_window = max(int(round(sample_rate_hz * zoom_ms / 1000.0)), 64)
    input_envelope = _moving_rms(input_samples, envelope_window)
    output_envelope = _moving_rms(output_samples, envelope_window)
    zoom_start, zoom_stop = _pick_zoom_window(input_samples, output_samples, zoom_window)

    zoom_input = input_samples[zoom_start:zoom_stop]
    zoom_output = output_samples[zoom_start:zoom_stop]
    zoom_time_ms = (np.arange(zoom_input.size, dtype=np.float32) + zoom_start) * 1000.0 / float(sample_rate_hz)
    full_time_s = np.arange(input_samples.size, dtype=np.float32) / float(sample_rate_hz)

    scatter_mask = _active_mask(input_samples) | _active_mask(output_samples)
    if np.count_nonzero(scatter_mask) < 1024:
        scatter_mask = np.ones(input_samples.size, dtype=bool)
    scatter_indices = np.flatnonzero(scatter_mask)
    if scatter_indices.size > 5000:
        scatter_indices = scatter_indices[np.linspace(0, scatter_indices.size - 1, 5000, dtype=int)]
    scatter_input = input_samples[scatter_indices]
    scatter_output = output_samples[scatter_indices]

    spectral_start, spectral_stop = _pick_zoom_window(input_envelope, output_envelope, max(4096, zoom_window * 3))
    spectral_input = input_samples[spectral_start:spectral_stop]
    spectral_output = output_samples[spectral_start:spectral_stop]
    spectral_len = max(min(len(spectral_input), len(spectral_output)), 128)
    spectral_input = spectral_input[:spectral_len]
    spectral_output = spectral_output[:spectral_len]
    window = np.hanning(spectral_len).astype(np.float32)
    freqs = np.fft.rfftfreq(spectral_len, d=1.0 / float(sample_rate_hz))
    input_db = 20.0 * np.log10(np.maximum(np.abs(np.fft.rfft(spectral_input * window)), 1.0e-8))
    output_db = 20.0 * np.log10(np.maximum(np.abs(np.fft.rfft(spectral_output * window)), 1.0e-8))
    freq_limit_hz = min(sample_rate_hz / 2.0, 6000.0)
    freq_mask = freqs <= freq_limit_hz

    figure, axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
    figure.suptitle(title, fontsize=14)

    axes[0, 0].plot(full_time_s, input_envelope, label="input", linewidth=1.2, alpha=0.95)
    axes[0, 0].plot(full_time_s, output_envelope, label="output", linewidth=1.2, alpha=0.85)
    axes[0, 0].set_title("Envelope / short-time RMS")
    axes[0, 0].set_xlabel("s")
    axes[0, 0].set_ylabel("V")
    axes[0, 0].grid(alpha=0.25)
    axes[0, 0].legend()

    axes[0, 1].plot(zoom_time_ms, zoom_input, label="input", linewidth=1.1, alpha=0.95)
    axes[0, 1].plot(zoom_time_ms, zoom_output, label="output", linewidth=1.1, alpha=0.85)
    axes[0, 1].set_title(f"Waveform zoom ({zoom_ms:.0f} ms active window)")
    axes[0, 1].set_xlabel("ms")
    axes[0, 1].set_ylabel("V")
    axes[0, 1].grid(alpha=0.25)
    axes[0, 1].legend()

    axes[1, 0].plot(freqs[freq_mask], input_db[freq_mask], label="input", linewidth=1.2, alpha=0.95)
    axes[1, 0].plot(freqs[freq_mask], output_db[freq_mask], label="output", linewidth=1.2, alpha=0.85)
    axes[1, 0].set_title("Magnitude spectrum")
    axes[1, 0].set_xlabel("Hz")
    axes[1, 0].set_ylabel("dB")
    axes[1, 0].grid(alpha=0.25)
    axes[1, 0].legend()

    diagonal_limit = max(
        float(np.max(np.abs(scatter_input))) if scatter_input.size else 0.0,
        float(np.max(np.abs(scatter_output))) if scatter_output.size else 0.0,
        1.0,
    )
    axes[1, 1].scatter(scatter_input, scatter_output, s=6, alpha=0.22, edgecolors="none")
    axes[1, 1].plot(
        [-diagonal_limit, diagonal_limit],
        [-diagonal_limit, diagonal_limit],
        linestyle="--",
        linewidth=1.0,
        color="black",
        alpha=0.6,
    )
    axes[1, 1].set_xlim(-diagonal_limit, diagonal_limit)
    axes[1, 1].set_ylim(-diagonal_limit, diagonal_limit)
    axes[1, 1].set_title("Transfer cloud: input -> output")
    axes[1, 1].set_xlabel("input V")
    axes[1, 1].set_ylabel("output V")
    axes[1, 1].grid(alpha=0.25)

    figure.savefig(output_path, dpi=150)
    plt.close(figure)

    return {
        "zoom_start_s": _safe_float(zoom_start / float(sample_rate_hz)),
        "zoom_stop_s": _safe_float(zoom_stop / float(sample_rate_hz)),
        "spectrum_start_s": _safe_float(spectral_start / float(sample_rate_hz)),
        "spectrum_stop_s": _safe_float(spectral_stop / float(sample_rate_hz)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build comparison plots and metrics for input/output audio pairs rendered by the simulator."
    )
    parser.add_argument("input_path", help="Original audio file path.")
    parser.add_argument("output_path", help="Processed audio file path.")
    parser.add_argument("analysis_dir", help="Directory where comparison.png and metrics.json will be saved.")
    parser.add_argument("--sample-rate", type=int, help="Analysis sample rate. Defaults to the processed file sample rate.")
    parser.add_argument("--envelope-ms", type=float, default=20.0, help="Envelope RMS window in milliseconds.")
    parser.add_argument("--zoom-ms", type=float, default=45.0, help="Waveform zoom window in milliseconds.")
    parser.add_argument("--normalize-input", action="store_true", help="Normalize the original file before comparison, matching AudioFileSource(normalize=true).")
    parser.add_argument("--title", help="Optional plot title override.")
    args = parser.parse_args()

    output_info = probe_audio_file(args.output_path)
    analysis_rate_hz = int(args.sample_rate or output_info.sample_rate_hz)
    if analysis_rate_hz <= 0:
        raise SystemExit("--sample-rate must be positive.")

    input_samples = _mono_series(args.input_path, analysis_rate_hz, normalize=args.normalize_input)
    output_samples = _mono_series(args.output_path, analysis_rate_hz)
    frame_count = min(input_samples.size, output_samples.size)
    if frame_count == 0:
        raise SystemExit("Both files must contain audio samples.")
    input_samples = input_samples[:frame_count]
    output_samples = output_samples[:frame_count]

    analysis_dir = Path(args.analysis_dir).expanduser()
    analysis_dir.mkdir(parents=True, exist_ok=True)
    comparison_png = analysis_dir / "comparison.png"
    metrics_json = analysis_dir / "metrics.json"

    window_metadata = _plot_comparison(
        input_samples,
        output_samples,
        sample_rate_hz=analysis_rate_hz,
        envelope_ms=args.envelope_ms,
        zoom_ms=args.zoom_ms,
        output_path=comparison_png,
        title=args.title or f"Audio comparison: {Path(args.input_path).name} -> {Path(args.output_path).name}",
    )

    envelope_window = max(int(round(analysis_rate_hz * args.envelope_ms / 1000.0)), 1)
    input_envelope = _moving_rms(input_samples, envelope_window)
    output_envelope = _moving_rms(output_samples, envelope_window)
    input_metrics = _signal_metrics(input_samples, analysis_rate_hz, input_envelope)
    output_metrics = _signal_metrics(output_samples, analysis_rate_hz, output_envelope)

    fit_gain = float(np.dot(input_samples, output_samples) / max(np.dot(input_samples, input_samples), 1.0e-12))
    linear_fit_error = output_samples - fit_gain * input_samples
    correlation = float(np.corrcoef(input_samples, output_samples)[0, 1]) if frame_count >= 2 else 0.0

    metrics = {
        "analysis_sample_rate_hz": analysis_rate_hz,
        "input_normalized": bool(args.normalize_input),
        "duration_s": _safe_float(frame_count / float(analysis_rate_hz)),
        "input_file": str(Path(args.input_path).expanduser()),
        "output_file": str(Path(args.output_path).expanduser()),
        "input": input_metrics,
        "output": output_metrics,
        "comparison": {
            "correlation": _safe_float(correlation),
            "best_linear_gain": _safe_float(fit_gain),
            "difference_rms": _safe_float(float(np.sqrt(np.mean(np.square(output_samples - input_samples, dtype=np.float64))))),
            "linear_fit_rmse": _safe_float(float(np.sqrt(np.mean(np.square(linear_fit_error, dtype=np.float64))))),
            "spectral_centroid_shift_hz": _safe_float(output_metrics["spectral_centroid_hz"] - input_metrics["spectral_centroid_hz"]),
            "high_band_ratio_shift": _safe_float(output_metrics["high_band_ratio"] - input_metrics["high_band_ratio"]),
            "zero_crossings_shift_per_s": _safe_float(output_metrics["zero_crossings_per_s"] - input_metrics["zero_crossings_per_s"]),
        },
        "windows": window_metadata,
    }

    metrics_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved comparison plot to {comparison_png}")
    print(f"Saved metrics JSON to {metrics_json}")


if __name__ == "__main__":
    main()
