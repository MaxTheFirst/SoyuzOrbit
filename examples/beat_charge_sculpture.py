from __future__ import annotations

from core import Circuit, LED_ImageActive, RealACGenerator, RealCapacitor, RealResistor, SchockleyDiode

DURATION_S = 0.12
DT_S = 2.0e-5
TITLE = "Beat-reactive charge sculpture"


def _place_two_terminal(component, center_px: tuple[float, float], span_px: float = 108.0):
    half_span = span_px * 0.5
    x, y = center_px
    component.layout_position_px = center_px
    component.layout_points_px = [(x - half_span, y), (x + half_span, y)]
    component.layout_rotation_deg = 0.0
    return component


def _add_indicator_channel(
    circuit: Circuit,
    *,
    source_node: str,
    prefix: str,
    storage_node: str,
    diode_count: int,
    diode_drop_v: float,
    capacitance_f: float,
    bleed_ohm: float,
    led_color: str,
    led_series_ohm: float,
    led_max_current_a: float,
    x_px: float,
    diode_y_px: float,
    storage_y_px: float,
    led_y_px: float,
) -> None:
    previous = source_node
    for index in range(diode_count):
        next_node = storage_node if index == diode_count - 1 else f"{prefix}_step_{index + 1}"
        circuit.add(
            _place_two_terminal(
                SchockleyDiode(
                    f"{prefix}_D{index + 1}",
                    previous,
                    next_node,
                    forward_drop_v=diode_drop_v,
                    shunt_resistance_ohm=1.0e9,
                    breakdown_voltage_v=100.0,
                ),
                (x_px + index * 180.0, diode_y_px),
            )
        )
        previous = next_node

    circuit.add(
        _place_two_terminal(
            RealCapacitor(
                f"{prefix}_CAP",
                storage_node,
                "0",
                capacitance_f=capacitance_f,
                esr_ohm=0.1,
                leak_resistance_ohm=1.8e6,
                max_voltage_v=25.0,
            ),
            (x_px + (diode_count - 1) * 180.0 + 80.0, storage_y_px),
        )
    )
    circuit.add(
        _place_two_terminal(
            RealResistor(f"{prefix}_BLEED", storage_node, "0", resistance_ohm=bleed_ohm),
            (x_px + (diode_count - 1) * 180.0 + 280.0, storage_y_px),
        )
    )
    circuit.add(
        _place_two_terminal(
            RealResistor(f"{prefix}_LED_R", storage_node, f"{prefix}_led", resistance_ohm=led_series_ohm),
            (x_px + (diode_count - 1) * 180.0 + 80.0, led_y_px),
        )
    )
    circuit.add(
        _place_two_terminal(
            LED_ImageActive(
                f"{prefix}_LED",
                f"{prefix}_led",
                "0",
                color=led_color,
                max_forward_current_a=led_max_current_a,
            ),
            (x_px + (diode_count - 1) * 180.0 + 280.0, led_y_px),
        )
    )


def build_circuit() -> Circuit:
    circuit = Circuit(TITLE)

    # Two nearby frequencies create a slow beat envelope.
    circuit.add(
        _place_two_terminal(
            RealACGenerator(
                "GEN_A",
                "ga",
                "0",
                amplitude_v=5.0,
                frequency_hz=520.0,
                internal_resistance_ohm=0.4,
                phase_noise_rad=0.003,
            ),
            (140.0, 100.0),
        )
    )
    circuit.add(
        _place_two_terminal(
            RealACGenerator(
                "GEN_B",
                "gb",
                "0",
                amplitude_v=4.7,
                frequency_hz=575.0,
                internal_resistance_ohm=0.4,
                phase_noise_rad=0.003,
                phase_rad=0.7,
            ),
            (140.0, 320.0),
        )
    )
    circuit.add(_place_two_terminal(RealResistor("R_MIX_A", "ga", "mix", resistance_ohm=12.0), (340.0, 100.0)))
    circuit.add(_place_two_terminal(RealResistor("R_MIX_B", "gb", "mix", resistance_ohm=12.0), (340.0, 320.0)))

    # Villard/Greinacher-style doubler that lifts the mixed waveform into a DC bus.
    circuit.add(
        _place_two_terminal(
            RealCapacitor(
                "C_PUMP",
                "mix",
                "pump",
                capacitance_f=150e-6,
                esr_ohm=0.08,
                leak_resistance_ohm=5.0e6,
                max_voltage_v=40.0,
            ),
            (760.0, 210.0),
        )
    )
    circuit.add(
        _place_two_terminal(
            SchockleyDiode(
                "D_CLAMP",
                "0",
                "pump",
                forward_drop_v=0.6,
                shunt_resistance_ohm=1.0e9,
                breakdown_voltage_v=100.0,
            ),
            (960.0, 470.0),
        )
    )
    circuit.add(
        _place_two_terminal(
            SchockleyDiode(
                "D_BOOST",
                "pump",
                "bus",
                forward_drop_v=0.6,
                shunt_resistance_ohm=1.0e9,
                breakdown_voltage_v=100.0,
            ),
            (1160.0, 210.0),
        )
    )
    circuit.add(
        _place_two_terminal(
            RealCapacitor(
                "C_BUS",
                "bus",
                "0",
                capacitance_f=470e-6,
                esr_ohm=0.07,
                leak_resistance_ohm=2.0e6,
                max_voltage_v=50.0,
            ),
            (1260.0, 410.0),
        )
    )
    circuit.add(_place_two_terminal(RealResistor("R_BUS_BLEED", "bus", "0", resistance_ohm=18000.0), (1460.0, 410.0)))

    # Three diode/capacitor channels siphon energy from the bus differently:
    # fast reacts to almost every beat, mid needs more headroom, slow integrates longer.
    _add_indicator_channel(
        circuit,
        source_node="bus",
        prefix="FAST",
        storage_node="fast",
        diode_count=1,
        diode_drop_v=0.58,
        capacitance_f=68e-6,
        bleed_ohm=3900.0,
        led_color="amber",
        led_series_ohm=180.0,
        led_max_current_a=0.018,
        x_px=1560.0,
        diode_y_px=80.0,
        storage_y_px=260.0,
        led_y_px=420.0,
    )
    _add_indicator_channel(
        circuit,
        source_node="bus",
        prefix="MID",
        storage_node="mid",
        diode_count=2,
        diode_drop_v=0.62,
        capacitance_f=120e-6,
        bleed_ohm=6800.0,
        led_color="green",
        led_series_ohm=220.0,
        led_max_current_a=0.02,
        x_px=1560.0,
        diode_y_px=210.0,
        storage_y_px=410.0,
        led_y_px=570.0,
    )
    _add_indicator_channel(
        circuit,
        source_node="bus",
        prefix="SLOW",
        storage_node="slow",
        diode_count=2,
        diode_drop_v=0.65,
        capacitance_f=330e-6,
        bleed_ohm=12000.0,
        led_color="red",
        led_series_ohm=270.0,
        led_max_current_a=0.018,
        x_px=1560.0,
        diode_y_px=340.0,
        storage_y_px=560.0,
        led_y_px=760.0,
    )

    return circuit
