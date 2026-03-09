from core import Circuit, PhysiWire, RealACGenerator, RealCapacitor, RealInductor, RealResistor

DURATION_S = 0.01
DT_S = 5.0e-6
TITLE = "AC LC low-pass filter with wire parasitics"


def build_circuit() -> Circuit:
    circuit = Circuit(TITLE)
    circuit.add(
        RealACGenerator(
            "GEN1",
            "src",
            "0",
            amplitude_v=8.0,
            frequency_hz=1800.0,
            internal_resistance_ohm=0.8,
            phase_noise_rad=0.015,
            harmonic_2_ratio=0.05,
        )
    )
    circuit.add(PhysiWire("WIRE1", "src", "pre_l", length_m=0.8, area_mm2=0.5))
    circuit.add(
        RealInductor(
            "L1",
            "pre_l",
            "vout",
            inductance_h=18e-6,
            relative_permeability=12.0,
            dc_resistance_ohm=0.18,
            saturation_current_a=2.4,
        )
    )
    circuit.add(RealCapacitor("C1", "vout", "0", capacitance_f=47e-6, esr_ohm=0.08, max_voltage_v=25.0))
    circuit.add(RealResistor("RLOAD", "vout", "0", resistance_ohm=18.0))
    return circuit
