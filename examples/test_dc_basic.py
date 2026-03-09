from core import Circuit, LED_ImageActive, PhysiBattery, RealResistor

DURATION_S = 0.03
DT_S = 1.0e-4
TITLE = "DC battery, resistor and LED"


def build_circuit() -> Circuit:
    circuit = Circuit(TITLE)
    circuit.add(
        PhysiBattery(
            "BAT1",
            "vcc",
            "0",
            nominal_voltage_v=9.0,
            capacity_mah=550.0,
            chemistry="alkaline",
            internal_resistance_ohm=1.1,
        )
    )
    circuit.add(RealResistor("R1", "vcc", "n_led", resistance_ohm=330.0, tolerance=0.01))
    circuit.add(LED_ImageActive("LED1", "n_led", "0", color="red", max_forward_current_a=0.02))
    return circuit
