from __future__ import annotations

import json
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import numpy as np


SUPPORTED_AUDIO_EXTENSIONS = {".flac", ".flac2", ".m4a", ".mp3", ".ogg", ".wav"}
SUPPORTED_AUDIO_EXPORT_EXTENSIONS = {".flac", ".flac2", ".m4a", ".mp3", ".ogg", ".wav"}


class AudioImportError(RuntimeError):
    pass


class AudioExportError(RuntimeError):
    pass


if TYPE_CHECKING:
    from .engine import SimulationResult


@dataclass(slots=True, frozen=True)
class AudioFileInfo:
    path: Path
    format_name: str
    codec_name: str
    sample_rate_hz: int
    channels: int
    duration_s: float
    bit_rate: int | None = None


@dataclass(slots=True)
class AudioBuffer:
    sample_rate_hz: int
    channels: int
    samples: np.ndarray
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive.")
        if self.channels <= 0:
            raise ValueError("channels must be positive.")
        array = np.asarray(self.samples, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(-1, 1)
        if array.ndim != 2:
            raise ValueError("samples must be a 1D or 2D array.")
        if array.shape[1] != self.channels:
            raise ValueError("samples channel dimension does not match channels.")
        self.samples = np.ascontiguousarray(array, dtype=np.float32)

    @property
    def frame_count(self) -> int:
        return int(self.samples.shape[0])

    @property
    def duration_s(self) -> float:
        return float(self.frame_count / self.sample_rate_hz)

    def channel_samples(self, index: int) -> np.ndarray:
        if not 0 <= index < self.channels:
            raise IndexError(f"Channel index {index} is out of range for {self.channels} channels.")
        return np.array(self.samples[:, index], dtype=np.float32, copy=True)

    def mono_mix(self) -> np.ndarray:
        return np.array(np.mean(self.samples, axis=1), dtype=np.float32, copy=True)

    def normalized_copy(self) -> "AudioBuffer":
        peak = float(np.max(np.abs(self.samples))) if self.samples.size else 0.0
        if peak <= 1.0e-12:
            normalized = np.array(self.samples, dtype=np.float32, copy=True)
        else:
            normalized = np.array(self.samples / peak, dtype=np.float32, copy=True)
        metadata = dict(self.metadata)
        metadata["normalized"] = True
        metadata["peak_before_normalize"] = peak
        return AudioBuffer(
            sample_rate_hz=self.sample_rate_hz,
            channels=self.channels,
            samples=normalized,
            metadata=metadata,
        )


def is_supported_audio_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def ffmpeg_available(ffmpeg_binary: str = "ffmpeg", ffprobe_binary: str = "ffprobe") -> bool:
    return _resolve_binary(ffmpeg_binary) is not None and _resolve_binary(ffprobe_binary) is not None


def is_supported_audio_export_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_AUDIO_EXPORT_EXTENSIONS


def probe_audio_file(path: str | Path, *, ffprobe_binary: str = "ffprobe") -> AudioFileInfo:
    source = Path(path).expanduser()
    _validate_audio_path(source)

    resolved_ffprobe = _resolve_binary(ffprobe_binary)
    if resolved_ffprobe is None:
        if source.suffix.lower() == ".wav":
            return _probe_wave_fallback(source)
        raise AudioImportError(
            "ffprobe was not found. Only WAV fallback probing is available without ffprobe."
        )

    command = [
        resolved_ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise AudioImportError(f"ffprobe failed for {source}: {exc.stderr.strip() or exc}") from exc

    payload = json.loads(completed.stdout or "{}")
    stream = next((item for item in payload.get("streams", []) if item.get("codec_type") == "audio"), None)
    if stream is None:
        raise AudioImportError(f"No audio stream found in {source}.")

    format_info = payload.get("format", {})
    sample_rate_hz = int(float(stream.get("sample_rate", 0.0) or 0.0))
    channels = int(stream.get("channels", 0) or 0)
    duration_s = float(stream.get("duration") or format_info.get("duration") or 0.0)
    if sample_rate_hz <= 0 or channels <= 0:
        raise AudioImportError(f"Could not determine audio format parameters for {source}.")

    bit_rate_raw = stream.get("bit_rate") or format_info.get("bit_rate")
    bit_rate = int(bit_rate_raw) if bit_rate_raw not in (None, "", "N/A") else None
    return AudioFileInfo(
        path=source.resolve(),
        format_name=str(format_info.get("format_name", source.suffix.lower().lstrip("."))),
        codec_name=str(stream.get("codec_name", "unknown")),
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        duration_s=duration_s,
        bit_rate=bit_rate,
    )


def load_audio_file(
    path: str | Path,
    *,
    target_sample_rate_hz: int | None = None,
    mono: bool = False,
    normalize: bool = False,
    ffmpeg_binary: str = "ffmpeg",
    ffprobe_binary: str = "ffprobe",
) -> AudioBuffer:
    source = Path(path).expanduser()
    info = probe_audio_file(source, ffprobe_binary=ffprobe_binary)

    target_channels = 1 if mono else info.channels
    target_rate = target_sample_rate_hz if target_sample_rate_hz is not None else info.sample_rate_hz
    if target_rate <= 0:
        raise ValueError("target_sample_rate_hz must be positive when provided.")

    resolved_ffmpeg = _resolve_binary(ffmpeg_binary)
    if resolved_ffmpeg is None:
        if source.suffix.lower() == ".wav":
            buffer = _load_wave_fallback(source, target_channels=target_channels, target_rate=target_rate)
        else:
            raise AudioImportError(
                "ffmpeg was not found. Non-WAV audio import requires ffmpeg."
            )
    else:
        buffer = _load_via_ffmpeg(
            source,
            info=info,
            ffmpeg_binary=resolved_ffmpeg,
            target_channels=target_channels,
            target_rate=target_rate,
        )

    if normalize:
        buffer = buffer.normalized_copy()
    return buffer


def audio_buffer_from_series(
    samples: np.ndarray | list[float],
    sample_rate_hz: int,
    *,
    channels: int = 1,
    normalize: bool = False,
    metadata: dict[str, Any] | None = None,
) -> AudioBuffer:
    array = np.asarray(samples, dtype=np.float32)
    if channels <= 0:
        raise ValueError("channels must be positive.")
    if array.ndim == 1 and channels > 1:
        raise ValueError("1D samples can only be used with channels=1.")
    buffer = AudioBuffer(
        sample_rate_hz=int(sample_rate_hz),
        channels=int(channels),
        samples=array,
        metadata=dict(metadata or {}),
    )
    return buffer.normalized_copy() if normalize else buffer


def audio_buffer_from_simulation_result(
    result: "SimulationResult",
    component_name: str,
    *,
    observable_key: str = "captured_v",
    normalize: bool = False,
    scale: float = 1.0,
    metadata: dict[str, Any] | None = None,
) -> AudioBuffer:
    observables = result.component_observables.get(component_name)
    if observables is None:
        raise KeyError(f"Component '{component_name}' was not found in the simulation result.")
    if observable_key not in observables:
        raise KeyError(
            f"Observable '{observable_key}' was not found for component '{component_name}'. "
            f"Available: {', '.join(sorted(observables))}"
        )

    dt_s = float(result.metadata.get("dt_s", 0.0))
    if dt_s <= 0.0 and len(result.time_s) >= 2:
        diffs = np.diff(np.asarray(result.time_s, dtype=float))
        positive = diffs[diffs > 0.0]
        if positive.size > 0:
            dt_s = float(np.median(positive))
    if dt_s <= 0.0:
        raise AudioExportError("Could not determine sample rate from simulation result.")

    sample_rate_hz = max(int(round(1.0 / dt_s)), 1)
    samples = np.asarray(observables[observable_key], dtype=np.float32) * float(scale)
    combined_metadata = {
        "source": "simulation_result",
        "component_name": component_name,
        "observable_key": observable_key,
        "simulation_name": result.metadata.get("name"),
        "dt_s": dt_s,
    }
    if metadata:
        combined_metadata.update(metadata)
    return audio_buffer_from_series(
        samples,
        sample_rate_hz,
        channels=1,
        normalize=normalize,
        metadata=combined_metadata,
    )


def save_audio_file(
    path: str | Path,
    buffer: AudioBuffer,
    *,
    normalize: bool = False,
    ffmpeg_binary: str = "ffmpeg",
    bit_rate_kbps: int = 192,
) -> Path:
    target = Path(path).expanduser()
    extension = target.suffix.lower()
    if extension not in SUPPORTED_AUDIO_EXPORT_EXTENSIONS:
        raise AudioExportError(
            f"Unsupported audio export extension '{target.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXPORT_EXTENSIONS))}."
        )

    export_buffer = buffer.normalized_copy() if normalize else buffer
    target.parent.mkdir(parents=True, exist_ok=True)

    resolved_ffmpeg = _resolve_binary(ffmpeg_binary)
    if resolved_ffmpeg is None:
        if extension == ".wav":
            _save_wave_fallback(target, export_buffer)
            return target
        raise AudioExportError("ffmpeg was not found. Only WAV export is available without ffmpeg.")

    command = _ffmpeg_export_command(
        resolved_ffmpeg,
        target,
        sample_rate_hz=export_buffer.sample_rate_hz,
        channels=export_buffer.channels,
        bit_rate_kbps=bit_rate_kbps,
    )
    try:
        subprocess.run(
            command,
            check=True,
            input=np.ascontiguousarray(export_buffer.samples, dtype=np.float32).astype("<f4").tobytes(),
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise AudioExportError(f"ffmpeg failed while writing {target}: {stderr or exc}") from exc
    return target


def _load_via_ffmpeg(
    path: Path,
    *,
    info: AudioFileInfo,
    ffmpeg_binary: str,
    target_channels: int,
    target_rate: int,
) -> AudioBuffer:
    command = [
        ffmpeg_binary,
        "-v",
        "error",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        str(target_channels),
        "-ar",
        str(target_rate),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise AudioImportError(f"ffmpeg failed for {path}: {stderr or exc}") from exc

    samples = np.frombuffer(completed.stdout, dtype="<f4")
    if samples.size == 0:
        raise AudioImportError(f"ffmpeg produced no audio samples for {path}.")
    if samples.size % target_channels != 0:
        raise AudioImportError(
            f"Decoded audio sample count is not divisible by channel count for {path}."
        )
    samples = np.array(samples.reshape(-1, target_channels), dtype=np.float32, copy=True)
    return AudioBuffer(
        sample_rate_hz=target_rate,
        channels=target_channels,
        samples=samples,
        metadata={
            "source_path": str(path.resolve()),
            "source_extension": path.suffix.lower(),
            "source_format_name": info.format_name,
            "source_codec_name": info.codec_name,
            "source_sample_rate_hz": info.sample_rate_hz,
            "source_channels": info.channels,
            "source_duration_s": info.duration_s,
            "source_bit_rate": info.bit_rate,
            "backend": "ffmpeg",
            "normalized": False,
            "mono": target_channels == 1,
        },
    )


def _probe_wave_fallback(path: Path) -> AudioFileInfo:
    try:
        with wave.open(str(path), "rb") as handle:
            frame_rate = handle.getframerate()
            channels = handle.getnchannels()
            frame_count = handle.getnframes()
    except (wave.Error, OSError) as exc:
        raise AudioImportError(f"Could not read WAV file {path}: {exc}") from exc
    duration_s = frame_count / frame_rate if frame_rate > 0 else 0.0
    return AudioFileInfo(
        path=path.resolve(),
        format_name="wav",
        codec_name="pcm",
        sample_rate_hz=frame_rate,
        channels=channels,
        duration_s=duration_s,
        bit_rate=None,
    )


def _load_wave_fallback(path: Path, *, target_channels: int, target_rate: int) -> AudioBuffer:
    info = _probe_wave_fallback(path)
    if target_rate != info.sample_rate_hz:
        raise AudioImportError(
            "WAV fallback loader does not support resampling. Install/use ffmpeg for resampling."
        )

    try:
        with wave.open(str(path), "rb") as handle:
            sample_width = handle.getsampwidth()
            frame_count = handle.getnframes()
            channels = handle.getnchannels()
            raw = handle.readframes(frame_count)
    except (wave.Error, OSError) as exc:
        raise AudioImportError(f"Could not read WAV file {path}: {exc}") from exc

    dtype_map = {
        1: np.uint8,
        2: np.int16,
        4: np.int32,
    }
    dtype = dtype_map.get(sample_width)
    if dtype is None:
        raise AudioImportError(
            f"WAV fallback loader supports only 8/16/32-bit PCM, got sample width {sample_width}."
        )

    data = np.frombuffer(raw, dtype=dtype)
    if data.size % channels != 0:
        raise AudioImportError(f"Invalid WAV frame layout in {path}.")
    data = data.reshape(-1, channels)
    if sample_width == 1:
        samples = (data.astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        samples = data.astype(np.float32) / 32768.0
    else:
        samples = data.astype(np.float32) / 2147483648.0

    if target_channels == 1 and channels > 1:
        samples = np.mean(samples, axis=1, keepdims=True, dtype=np.float32)
    elif target_channels != channels:
        raise AudioImportError(
            "WAV fallback loader can only keep original channels or mix down to mono."
        )

    return AudioBuffer(
        sample_rate_hz=target_rate,
        channels=target_channels,
        samples=np.array(samples, dtype=np.float32, copy=True),
        metadata={
            "source_path": str(path.resolve()),
            "source_extension": path.suffix.lower(),
            "source_format_name": info.format_name,
            "source_codec_name": info.codec_name,
            "source_sample_rate_hz": info.sample_rate_hz,
            "source_channels": info.channels,
            "source_duration_s": info.duration_s,
            "source_bit_rate": info.bit_rate,
            "backend": "wave",
            "normalized": False,
            "mono": target_channels == 1,
        },
    )


def _save_wave_fallback(path: Path, buffer: AudioBuffer) -> None:
    samples = np.clip(np.asarray(buffer.samples, dtype=np.float32), -1.0, 1.0)
    pcm = (samples * 32767.0).astype("<i2")
    try:
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(buffer.channels)
            handle.setsampwidth(2)
            handle.setframerate(buffer.sample_rate_hz)
            handle.writeframes(pcm.tobytes())
    except (wave.Error, OSError) as exc:
        raise AudioExportError(f"Could not write WAV file {path}: {exc}") from exc


def _ffmpeg_export_command(
    ffmpeg_binary: str,
    target: Path,
    *,
    sample_rate_hz: int,
    channels: int,
    bit_rate_kbps: int,
) -> list[str]:
    extension = target.suffix.lower()
    codec_args: list[str]
    if extension == ".wav":
        codec_args = ["-f", "wav", "-c:a", "pcm_s16le"]
    elif extension in {".flac", ".flac2"}:
        codec_args = ["-f", "flac", "-c:a", "flac"]
    elif extension == ".mp3":
        codec_args = ["-f", "mp3", "-c:a", "libmp3lame", "-b:a", f"{max(bit_rate_kbps, 32)}k"]
    elif extension == ".m4a":
        codec_args = ["-f", "ipod", "-c:a", "aac", "-b:a", f"{max(bit_rate_kbps, 32)}k"]
    elif extension == ".ogg":
        codec_args = ["-f", "ogg", "-c:a", "libopus", "-b:a", f"{max(bit_rate_kbps, 32)}k"]
    else:
        raise AudioExportError(f"Unsupported export extension '{target.suffix}'.")

    return [
        ffmpeg_binary,
        "-v",
        "error",
        "-y",
        "-f",
        "f32le",
        "-ar",
        str(sample_rate_hz),
        "-ac",
        str(channels),
        "-i",
        "-",
        *codec_args,
        str(target),
    ]


def _resolve_binary(name: str) -> str | None:
    if "/" in name:
        return name if Path(name).exists() else None
    return shutil.which(name)


def _validate_audio_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise AudioImportError(f"{path} is not a file.")
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise AudioImportError(
            f"Unsupported audio extension '{path.suffix}'. Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}."
        )
