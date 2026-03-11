from __future__ import annotations

from pathlib import Path

from core import Circuit, RealCapacitor, RealResistor, SchockleyDiode, WavSource

TITLE = "WAV tone shaper"
SAMPLE_RATE_HZ = 22050
DURATION_S = 0.72
DT_S = 1.0 / SAMPLE_RATE_HZ
INPUT_ASSET = Path(__file__).with_name("audio_assets") / "test_tone.wav"
OUTPUT_NODE = "out"
REFERENCE_NODE = "0"


def _place_two_terminal(component, center_px: tuple[float, float], span_px: float = 108.0):
    half_span = span_px * 0.5
    x, y = center_px
    component.layout_position_px = center_px
    component.layout_points_px = [(x - half_span, y), (x + half_span, y)]
    component.layout_rotation_deg = 0.0
    return component


def build_circuit() -> Circuit:
    circuit = Circuit(TITLE)

    circuit.add(
        _place_two_terminal(
            WavSource(
                "WAV_IN",
                "src",
                "0",
                wav_path=str(INPUT_ASSET),
                amplitude_v=2.8,
                internal_resistance_ohm=0.35,
                remove_dc=True,
            ),
            (160.0, 180.0),
        )
    )
    circuit.add(_place_two_terminal(RealResistor("R_IN", "src", "shape", resistance_ohm=330.0), (360.0, 180.0)))

    # RC section softens the upper harmonics of the input test tone.
    circuit.add(
        _place_two_terminal(
            RealCapacitor(
                "C_SHAPE",
                "shape",
                "0",
                capacitance_f=330.0e-9,
                esr_ohm=0.05,
                leak_resistance_ohm=3.0e6,
                max_voltage_v=12.0,
            ),
            (360.0, 360.0),
        )
    )

    circuit.add(_place_two_terminal(RealResistor("R_DRIVE", "shape", "out", resistance_ohm=120.0), (600.0, 180.0)))

    # Antiparallel diodes limit the peak swing and create audible soft clipping.
    circuit.add(
        _place_two_terminal(
            SchockleyDiode(
                "D_CLIP_POS",
                "out",
                "0",
                forward_drop_v=0.48,
                shunt_resistance_ohm=1.0e9,
                breakdown_voltage_v=100.0,
            ),
            (820.0, 120.0),
        )
    )
    circuit.add(
        _place_two_terminal(
            SchockleyDiode(
                "D_CLIP_NEG",
                "0",
                "out",
                forward_drop_v=0.48,
                shunt_resistance_ohm=1.0e9,
                breakdown_voltage_v=100.0,
            ),
            (820.0, 320.0),
        )
    )
    circuit.add(_place_two_terminal(RealResistor("R_LOAD", "out", "0", resistance_ohm=1800.0), (1040.0, 260.0)))
    circuit.add(
        _place_two_terminal(
            RealCapacitor(
                "C_OUT",
                "out",
                "0",
                capacitance_f=100.0e-9,
                esr_ohm=0.05,
                leak_resistance_ohm=4.0e6,
                max_voltage_v=12.0,
            ),
            (1220.0, 260.0),
        )
    )
    return circuit
