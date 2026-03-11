from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

GROUND_NAMES = {"0", "gnd", "GND", "ground", "GROUND"}


def _wav_to_float(data: np.ndarray) -> np.ndarray:
    if data.dtype.kind == "f":
        return np.asarray(data, dtype=float)
    if data.dtype.kind == "i":
        info = np.iinfo(data.dtype)
        scale = float(max(info.max, -info.min))
        return np.asarray(data, dtype=float) / max(scale, 1.0)
    if data.dtype.kind == "u":
        info = np.iinfo(data.dtype)
        midpoint = (info.max + 1) * 0.5
        return (np.asarray(data, dtype=float) - midpoint) / max(midpoint, 1.0)
    raise TypeError(f"Unsupported WAV sample type: {data.dtype}")


def _read_audio_container(path: str | Path) -> tuple[int, np.ndarray]:
    source = Path(path)
    if source.suffix.lower() == ".wav":
        return wavfile.read(source)
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise RuntimeError("ffmpeg is required to import mp3/flac/ogg/m4a audio files.")
    with tempfile.TemporaryDirectory(prefix="soyuzorbit-audio-") as tmp_dir:
        decoded_path = Path(tmp_dir) / "decoded.wav"
        command = [
            ffmpeg_path,
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            str(decoded_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg failed to decode the audio file."
            raise RuntimeError(message)
        return wavfile.read(decoded_path)


def load_audio_mono(
    path: str | Path,
    *,
    channel: int = 0,
    remove_dc: bool = True,
) -> tuple[int, np.ndarray]:
    sample_rate_hz, data = _read_audio_container(path)
    signal = np.asarray(data)
    if signal.ndim == 0:
        raise ValueError("Audio file does not contain sample data.")
    if signal.ndim == 1:
        mono = signal
    else:
        channel_index = max(0, min(int(channel), signal.shape[1] - 1))
        mono = signal[:, channel_index]
    samples = _wav_to_float(mono).reshape(-1)
    if remove_dc and samples.size:
        samples = samples - float(samples.mean())
    return int(sample_rate_hz), samples


def load_wav_mono(
    path: str | Path,
    *,
    channel: int = 0,
    remove_dc: bool = True,
) -> tuple[int, np.ndarray]:
    return load_audio_mono(path, channel=channel, remove_dc=remove_dc)


def save_wav_mono(
    path: str | Path,
    *,
    sample_rate_hz: int,
    samples: np.ndarray,
    normalize: bool = True,
) -> Path:
    if sample_rate_hz <= 0:
        raise ValueError("Sample rate must be positive.")
    signal = np.asarray(samples, dtype=float).reshape(-1)
    if signal.size == 0:
        raise ValueError("Cannot save an empty waveform.")
    if normalize:
        peak = float(np.max(np.abs(signal)))
        if peak > 1.0e-12:
            signal = signal / peak
    signal = np.clip(signal, -1.0, 1.0)
    pcm = np.asarray(np.rint(signal * 32767.0), dtype=np.int16)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(target, sample_rate_hz, pcm)
    return target


def result_node_trace(result, node: str) -> np.ndarray:
    if node in GROUND_NAMES:
        return np.zeros_like(result.time_s, dtype=float)
    if node not in result.node_voltages:
        available = ", ".join(sorted(result.node_voltages))
        raise ValueError(f"Unknown node '{node}'. Available nodes: {available}")
    return np.asarray(result.node_voltages[node], dtype=float)


def result_node_waveform(result, *, node: str, reference_node: str = "0") -> tuple[int, np.ndarray]:
    dt_s = float(result.metadata["dt_s"])
    if dt_s <= 0.0:
        raise ValueError("Simulation timestep must be positive for audio export.")
    sample_rate_hz = int(round(1.0 / dt_s))
    waveform = result_node_trace(result, node) - result_node_trace(result, reference_node)
    return sample_rate_hz, waveform


def export_result_node_wav(
    result,
    path: str | Path,
    *,
    node: str,
    reference_node: str = "0",
    normalize: bool = True,
) -> Path:
    sample_rate_hz, waveform = result_node_waveform(result, node=node, reference_node=reference_node)
    return save_wav_mono(path, sample_rate_hz=sample_rate_hz, samples=waveform, normalize=normalize)
