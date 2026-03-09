from core import Circuit, IncandescentBulb, PhysiBattery, RealFuse

DURATION_S = 0.2
DT_S = 2.0e-4
TITLE = "Fuse overload with incandescent bulb inrush"


def build_circuit() -> Circuit:
    circuit = Circuit(TITLE)
    circuit.add(
        PhysiBattery(
            "BAT12",
            "vcc",
            "0",
            nominal_voltage_v=12.0,
            capacity_mah=7000.0,
            chemistry="leadacid",
            internal_resistance_ohm=0.04,
        )
    )
    circuit.add(RealFuse("F1", "vcc", "n_load", current_rating_a=1.0, cold_resistance_ohm=0.025, i2t_trip=0.16))
    circuit.add(
        IncandescentBulb(
            "LAMP1",
            "n_load",
            "0",
            rated_voltage_v=12.0,
            rated_power_w=21.0,
            cold_ratio=11.5,
        )
    )
    return circuit
