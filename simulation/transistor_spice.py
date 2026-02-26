"""Lightweight SPICE-like CMOS primitives for transistor-level logic simulation.

This is not a full SPICE solver. It models node voltages with RC relaxation and
MOSFETs as voltage-controlled switches so small digital CPUs stay real-time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpiceConfig:
    vdd: float = 5.0
    vss: float = 0.0
    vth_n: float = 1.2
    vth_p: float = 1.2
    r_on: float = 1_000.0
    r_off: float = 1_000_000_000.0
    node_cap_f: float = 2e-12
    settle_steps: int = 8
    settle_dt_s: float = 2e-9


@dataclass
class Node:
    voltage: float


class NMOS:
    def __init__(self, cfg: SpiceConfig) -> None:
        self.cfg = cfg

    def resistance(self, gate_v: float) -> float:
        return self.cfg.r_on if gate_v >= self.cfg.vth_n else self.cfg.r_off


class PMOS:
    def __init__(self, cfg: SpiceConfig) -> None:
        self.cfg = cfg

    def resistance(self, gate_v: float) -> float:
        return self.cfg.r_on if gate_v <= (self.cfg.vdd - self.cfg.vth_p) else self.cfg.r_off


class SpiceCmos:
    """CMOS gate simulator with RC settling on output node."""

    def __init__(self, cfg: SpiceConfig | None = None) -> None:
        self.cfg = cfg or SpiceConfig()
        self.nmos = NMOS(self.cfg)
        self.pmos = PMOS(self.cfg)

    def bit_to_voltage(self, bit: int) -> float:
        return self.cfg.vdd if bit else self.cfg.vss

    def voltage_to_bit(self, voltage: float) -> int:
        return 1 if voltage >= (self.cfg.vdd * 0.5) else 0

    def _relax_output(self, out: Node, r_pullup: float, r_pulldown: float) -> None:
        g_up = 0.0 if r_pullup <= 0 else 1.0 / r_pullup
        g_dn = 0.0 if r_pulldown <= 0 else 1.0 / r_pulldown
        g_sum = g_up + g_dn
        if g_sum <= 0.0:
            return

        v_target = (self.cfg.vdd * g_up + self.cfg.vss * g_dn) / g_sum
        tau = self.cfg.node_cap_f / g_sum
        alpha = self.cfg.settle_dt_s / max(tau, 1e-18)
        alpha = min(max(alpha, 0.0), 1.0)
        out.voltage += (v_target - out.voltage) * alpha
        out.voltage = min(max(out.voltage, self.cfg.vss), self.cfg.vdd)

    def inverter(self, a: int, out_prev_v: float = 0.0) -> tuple[int, float]:
        a_v = self.bit_to_voltage(a)
        r_up = self.pmos.resistance(a_v)
        r_dn = self.nmos.resistance(a_v)
        out = Node(out_prev_v)
        for _ in range(self.cfg.settle_steps):
            self._relax_output(out, r_up, r_dn)
        return self.voltage_to_bit(out.voltage), out.voltage

    def nand2(self, a: int, b: int, out_prev_v: float = 0.0) -> tuple[int, float]:
        a_v = self.bit_to_voltage(a)
        b_v = self.bit_to_voltage(b)

        # Pull-up: PMOS parallel
        r_up_a = self.pmos.resistance(a_v)
        r_up_b = self.pmos.resistance(b_v)
        g_up = (1.0 / r_up_a) + (1.0 / r_up_b)
        r_up = (1.0 / g_up) if g_up > 0 else self.cfg.r_off

        # Pull-down: NMOS series
        r_dn = self.nmos.resistance(a_v) + self.nmos.resistance(b_v)

        out = Node(out_prev_v)
        for _ in range(self.cfg.settle_steps):
            self._relax_output(out, r_up, r_dn)
        return self.voltage_to_bit(out.voltage), out.voltage

    def nor2(self, a: int, b: int, out_prev_v: float = 0.0) -> tuple[int, float]:
        a_v = self.bit_to_voltage(a)
        b_v = self.bit_to_voltage(b)

        # Pull-up: PMOS series
        r_up = self.pmos.resistance(a_v) + self.pmos.resistance(b_v)

        # Pull-down: NMOS parallel
        r_dn_a = self.nmos.resistance(a_v)
        r_dn_b = self.nmos.resistance(b_v)
        g_dn = (1.0 / r_dn_a) + (1.0 / r_dn_b)
        r_dn = (1.0 / g_dn) if g_dn > 0 else self.cfg.r_off

        out = Node(out_prev_v)
        for _ in range(self.cfg.settle_steps):
            self._relax_output(out, r_up, r_dn)
        return self.voltage_to_bit(out.voltage), out.voltage


GLOBAL_SPICE = SpiceCmos()
