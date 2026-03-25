from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import (
    AudioFileSource,
    AudioSink,
    Circuit,
    audio_buffer_from_simulation_result,
    probe_audio_file,
    save_audio_file,
)


def build_circuit(input_path: str, *, peak_voltage_v: float, target_sample_rate_hz: int) -> Circuit:
    circuit = Circuit("Audio passthrough demo")
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            file_path=input_path,
            peak_voltage_v=peak_voltage_v,
            target_sample_rate_hz=target_sample_rate_hz,
            internal_resistance_ohm=0.2,
        )
    )
    circuit.add(
        AudioSink(
            "OUT",
            "vin",
            "0",
            input_resistance_ohm=1.0e9,
            output_gain=1.0 / max(peak_voltage_v, 1.0e-9),
            dc_block=False,
        )
    )
    return circuit


def main() -> None:
    parser = argparse.ArgumentParser(description="Load an audio file, feed it into AudioFileSource, and save the captured output.")
    parser.add_argument("input_path", help="Path to the input audio file.")
    parser.add_argument("output_path", help="Path to the exported audio file.")
    parser.add_argument("--peak-voltage", type=float, default=1.0, help="Peak voltage scaling for AudioFileSource.")
    parser.add_argument("--sample-rate", type=int, default=8000, help="Simulation sample rate in Hz.")
    parser.add_argument("--normalize-output", action="store_true", help="Normalize the exported audio.")
    args = parser.parse_args()

    circuit = build_circuit(args.input_path, peak_voltage_v=args.peak_voltage, target_sample_rate_hz=args.sample_rate)
    duration_s = probe_audio_file(args.input_path).duration_s
    result = circuit.simulate(float(duration_s), 1.0 / max(args.sample_rate, 1))
    output_buffer = audio_buffer_from_simulation_result(
        result,
        "OUT",
        observable_key="captured_v",
        normalize=args.normalize_output,
    )
    save_audio_file(Path(args.output_path), output_buffer, normalize=False)
    print(f"Saved processed audio to {args.output_path}")


if __name__ == "__main__":
    main()
