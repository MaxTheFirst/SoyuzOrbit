"""Gate-level primitives and a minimal CPU model."""

from __future__ import annotations

from dataclasses import dataclass

from simulation.transistor_spice import GLOBAL_SPICE


class NandGate:
    _last_out_v: float = 0.0

    @staticmethod
    def out(a: int, b: int) -> int:
        out, NandGate._last_out_v = GLOBAL_SPICE.nand2(a, b, NandGate._last_out_v)
        return out


class NotGate:
    _last_out_v: float = 0.0

    @staticmethod
    def out(a: int) -> int:
        out, NotGate._last_out_v = GLOBAL_SPICE.inverter(a, NotGate._last_out_v)
        return out


class AndGate:
    @staticmethod
    def out(a: int, b: int) -> int:
        return NotGate.out(NandGate.out(a, b))


class OrGate:
    _last_nor_v: float = 0.0

    @staticmethod
    def out(a: int, b: int) -> int:
        nor, OrGate._last_nor_v = GLOBAL_SPICE.nor2(a, b, OrGate._last_nor_v)
        return NotGate.out(nor)


class XorGate:
    @staticmethod
    def out(a: int, b: int) -> int:
        n1 = NandGate.out(a, b)
        n2 = NandGate.out(a, n1)
        n3 = NandGate.out(b, n1)
        return NandGate.out(n2, n3)


class FullAdder:
    @staticmethod
    def add(a: int, b: int, c_in: int) -> tuple[int, int]:
        x1 = XorGate.out(a, b)
        sum_bit = XorGate.out(x1, c_in)
        c1 = AndGate.out(a, b)
        c2 = AndGate.out(x1, c_in)
        c_out = OrGate.out(c1, c2)
        return sum_bit, c_out


class ALU8:
    """8-bit adder built from 1-bit full adders."""

    @staticmethod
    def add(a: int, b: int) -> tuple[int, int]:
        carry = 0
        value = 0
        for i in range(8):
            bit_a = (a >> i) & 1
            bit_b = (b >> i) & 1
            sum_bit, carry = FullAdder.add(bit_a, bit_b, carry)
            value |= (sum_bit << i)
        return value & 0xFF, carry


@dataclass
class Register8:
    value: int = 0

    def load(self, value: int) -> None:
        self.value = value & 0xFF


class SimpleLogicCPU:
    """Very small CPU assembled from simple gate-based blocks.

    This CPU cycles through phases:
      FETCH -> DECODE -> EXECUTE -> WRITEBACK
    and performs one toy operation:
      ACC = ACC + 1
      PC = PC + 1
    """

    PHASES = ("FETCH", "DECODE", "EXECUTE", "WRITEBACK")

    def __init__(self) -> None:
        self.pc = Register8(0)
        self.acc = Register8(0)
        self.ir = Register8(0)
        self.phase_index = 0
        self.cycle_count = 0
        self.last_carry = 0
        self.halted = False

    @property
    def phase(self) -> str:
        return self.PHASES[self.phase_index]

    def reset(self) -> None:
        self.pc.load(0)
        self.acc.load(0)
        self.ir.load(0)
        self.phase_index = 0
        self.cycle_count = 0
        self.last_carry = 0
        self.halted = False

    def tick_rising_edge(self) -> None:
        if self.halted:
            return

        phase = self.phase
        if phase == "FETCH":
            # Fake instruction stream: encode a synthetic instruction from PC.
            self.ir.load((0x10 + self.pc.value) & 0xFF)
        elif phase == "DECODE":
            # In this simple model there is only one ALU operation.
            pass
        elif phase == "EXECUTE":
            acc, carry = ALU8.add(self.acc.value, 1)
            self.acc.load(acc)
            self.last_carry = carry
        elif phase == "WRITEBACK":
            pc, _ = ALU8.add(self.pc.value, 1)
            self.pc.load(pc)
            self.cycle_count += 1

        self.phase_index = (self.phase_index + 1) % len(self.PHASES)
