"""
Physical CPU Model: Gates, Adders, and Registers.
"""

import time
from simulation.transistor_spice import GLOBAL_SPICE

# ==========================================
# Level 1: Basic Stateful Gates
# ==========================================

class StatefulNand:
    def __init__(self): self._last_v = 0.0
    def out(self, a: int, b: int) -> int:
        bit, self._last_v = GLOBAL_SPICE.nand2(a, b, self._last_v)
        return bit

class StatefulNor:
    def __init__(self): self._last_v = 0.0
    def out(self, a: int, b: int) -> int:
        bit, self._last_v = GLOBAL_SPICE.nor2(a, b, self._last_v)
        return bit

class StatefulNot:
    def __init__(self): self._last_v = 0.0
    def out(self, a: int) -> int:
        bit, self._last_v = GLOBAL_SPICE.inverter(a, self._last_v)
        return bit

# ==========================================
# Level 2: Composite Gates
# ==========================================

class StatefulAnd:
    def __init__(self):
        self.nand = StatefulNand()
        self.inv = StatefulNot()
    def out(self, a: int, b: int) -> int:
        return self.inv.out(self.nand.out(a, b))

class StatefulOr:
    def __init__(self):
        self.nor = StatefulNor()
        self.inv = StatefulNot()
    def out(self, a: int, b: int) -> int:
        return self.inv.out(self.nor.out(a, b))

class StatefulXor:
    def __init__(self):
        self.n1 = StatefulNand(); self.n2 = StatefulNand()
        self.n3 = StatefulNand(); self.n4 = StatefulNand()
    def out(self, a: int, b: int) -> int:
        ab_bar = self.n1.out(a, b)
        return self.n4.out(self.n2.out(a, ab_bar), self.n3.out(b, ab_bar))

# ==========================================
# Level 3: Arithmetic Units
# ==========================================

class FullAdder:
    def __init__(self):
        self.xor1 = StatefulXor(); self.xor2 = StatefulXor()
        self.and1 = StatefulAnd(); self.and2 = StatefulAnd(); self.or1 = StatefulOr()

    def calculate(self, a: int, b: int, c_in: int) -> tuple[int, int]:
        half_sum = self.xor1.out(a, b)
        sum_bit = self.xor2.out(half_sum, c_in)
        c1 = self.and1.out(a, b)
        c2 = self.and2.out(c_in, half_sum)
        c_out = self.or1.out(c1, c2)
        return sum_bit, c_out

class RippleCarryAdder8:
    def __init__(self):
        self.adders = [FullAdder() for _ in range(8)]

    def add(self, val_a: int, val_b: int, c_in: int = 0) -> tuple[int, int]:
        carry = c_in
        result = 0
        for i in range(8):
            bit_a = (val_a >> i) & 1
            bit_b = (val_b >> i) & 1
            s, carry = self.adders[i].calculate(bit_a, bit_b, carry)
            result |= (s << i)
        return result, carry

# ==========================================
# Level 4: Memory (Sequential Logic)
# ==========================================

class D_Latch:
    def __init__(self):
        self.nand1 = StatefulNand(); self.nand2 = StatefulNand()
        self.nand3 = StatefulNand(); self.nand4 = StatefulNand()
        self.inv = StatefulNot()
        self.q = 0; self.q_bar = 1

    def update(self, d: int, e: int) -> int:
        dn = self.inv.out(d)
        s_bar = self.nand1.out(d, e)
        r_bar = self.nand2.out(dn, e)
        for _ in range(2):
            self.q = self.nand3.out(s_bar, self.q_bar)
            self.q_bar = self.nand4.out(r_bar, self.q)
        return self.q

class D_FlipFlop:
    def __init__(self):
        self.master = D_Latch()
        self.slave = D_Latch()
        self.inv_clk = StatefulNot()

    def update(self, d: int, clk: int) -> int:
        clk_bar = self.inv_clk.out(clk)
        master_q = self.master.update(d, clk_bar)
        slave_q = self.slave.update(master_q, clk)
        return slave_q

class Register8:
    """Standard 8-bit Register."""
    def __init__(self):
        self.dffs = [D_FlipFlop() for _ in range(8)]
        self.current_value = 0

    def tick(self, input_val: int, clk: int) -> int:
        out_val = 0
        for i in range(8):
            bit_in = (input_val >> i) & 1
            bit_out = self.dffs[i].update(bit_in, clk)
            out_val |= (bit_out << i)
        self.current_value = out_val
        return out_val

class LoadableRegister8(Register8):
    """
    8-bit Register with a LOAD ENABLE pin.
    If load_enable is 0, the register recirculates its old value (ignores input).
    This is implemented using a 2-to-1 Multiplexer on each bit input.
    """
    def __init__(self):
        super().__init__()
        # We need 8 Muxes (one per bit)
        # Mux logic: Out = (A & Sel) | (B & !Sel)
        # Here: Input = (NewData & Load) | (OldData & !Load)
        self.ands_new = [StatefulAnd() for _ in range(8)]
        self.ands_old = [StatefulAnd() for _ in range(8)]
        self.ors      = [StatefulOr() for _ in range(8)]
        self.inv_load = StatefulNot()

    def tick_enabled(self, input_val: int, load_enable: int, clk: int) -> int:
        # 1. Calculate Input for DFFs based on Load Enable
        not_load = self.inv_load.out(load_enable)
        dff_inputs = 0
        
        for i in range(8):
            bit_new = (input_val >> i) & 1
            bit_old = (self.current_value >> i) & 1
            
            # Mux Logic
            pass_new = self.ands_new[i].out(bit_new, load_enable)
            pass_old = self.ands_old[i].out(bit_old, not_load)
            bit_in = self.ors[i].out(pass_new, pass_old)

            dff_inputs |= (bit_in << i)

        # 2. Clock the DFFs with the selected input
        return super().tick(dff_inputs, clk)
