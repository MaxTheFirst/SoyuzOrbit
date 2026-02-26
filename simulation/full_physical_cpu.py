"""
A fully physical, structural CPU model.
NOW FEATURING:
1. Gate-Level Control Unit (Physical Decoder).
2. Loadable Registers (No more magic writes).
3. Bus Logic (Tri-state buffer simulation).
4. PHYSICAL ROM (Diode/Transistor Matrix Memory).
5. I/O Ports for interaction.
6. PHYSICAL CLOCK GENERATOR (Phase Counter).
"""

import time
from collections import namedtuple
from typing import List, Dict, Callable

from simulation.physical_cpu import (
    StatefulNot, StatefulAnd, StatefulOr, StatefulXor,
    RippleCarryAdder8, Register8, LoadableRegister8, StatefulNand,
    D_FlipFlop
)

# --- CPU Architecture ---
Instruction = namedtuple("Instruction", ["opcode", "operand"])

class PhysicalDecoder:
    """The 'Brain' of the CPU implemented purely with Logic Gates."""
    def __init__(self):
        self.inv_o0 = StatefulNot(); self.inv_o1 = StatefulNot()
        self.inv_o2 = StatefulNot(); self.inv_o3 = StatefulNot()
        self.and4_mov_a = self._make_4input_and()
        self.and4_mov_b = self._make_4input_and()
        self.and4_add   = self._make_4input_and()
        self.and4_out   = self._make_4input_and()
        self.and4_in    = self._make_4input_and()
        self.and4_halt  = self._make_4input_and()

        # Phase inputs are now physical wires from the Phase Generator
        # No more integer 'phase' argument!

        self.and_rom_read = StatefulAnd(); self.and_ir_write = StatefulAnd(); self.and_pc_inc = StatefulAnd()
        self.and_exec_mov_a = StatefulAnd(); self.and_exec_mov_b = StatefulAnd()
        self.and_exec_add   = StatefulAnd(); self.and_exec_out = StatefulAnd(); self.and_exec_in = StatefulAnd()
        self.or_op_to_bus = StatefulOr(); self.or_reg_a_write = StatefulOr()
        self.control_signals = {}

    def _make_4input_and(self):
        class And4:
            def __init__(self):
                self.a1 = StatefulAnd(); self.a2 = StatefulAnd(); self.a3 = StatefulAnd()
            def out(self, i0, i1, i2, i3): return self.a3.out(self.a1.out(i0, i1), self.a2.out(i2, i3))
        return And4()

    def decode(self, opcode: int, p0: int, p1: int, p2: int, p3: int):
        """
        Decodes Opcode + 4 Phase Wires into Control Signals.
        """
        o0 = (opcode >> 0) & 1; o1 = (opcode >> 1) & 1; o2 = (opcode >> 2) & 1; o3 = (opcode >> 3) & 1

        not_o0 = self.inv_o0.out(o0); not_o1 = self.inv_o1.out(o1)
        not_o2 = self.inv_o2.out(o2); not_o3 = self.inv_o3.out(o3)

        # Instruction Decoding
        is_mov_a = self.and4_mov_a.out(not_o3, not_o2, not_o1, o0) # 1
        is_mov_b = self.and4_mov_b.out(not_o3, not_o2, o1, not_o0) # 2
        is_add   = self.and4_add.out(not_o3, not_o2, o1, o0)     # 3
        is_out   = self.and4_out.out(not_o3, o2, not_o1, not_o0) # 4
        is_in    = self.and4_in.out(not_o3, o2, not_o1, o0)      # 5
        is_halt  = self.and4_halt.out(not_o3, not_o2, not_o1, not_o0) # 0

        # Control Signal Matrix
        # Phase 0: Fetch
        rom_read = self.and_rom_read.out(p0, 1)
        ir_write = self.and_ir_write.out(p0, 1)

        # Phase 1: Increment PC
        pc_inc = self.and_pc_inc.out(p1, 1)

        # Phase 2: Execute
        do_mov_a = self.and_exec_mov_a.out(p2, is_mov_a)
        do_mov_b = self.and_exec_mov_b.out(p2, is_mov_b)
        do_add   = self.and_exec_add.out(p2, is_add)
        do_out   = self.and_exec_out.out(p2, is_out)
        do_in    = self.and_exec_in.out(p2, is_in)

        operand_to_bus = self.or_op_to_bus.out(do_mov_a, do_mov_b)
        reg_a_write = self.or_reg_a_write.out(do_mov_a, self.or_op_to_bus.out(do_add, do_in))

        self.control_signals = {
            'rom_read_enable': rom_read, 'ir_write_enable': ir_write, 'pc_increment_enable': pc_inc,
            'operand_to_bus_enable': operand_to_bus, 'reg_a_write_enable': reg_a_write,
            'reg_b_write_enable': do_mov_b, 'reg_b_to_alu_enable': do_add,
            'alu_to_bus_enable': do_add, 'halt_signal': is_halt,
            'io_write_enable': do_out, 'io_read_enable': do_in,
        }

class TriStateBuffer8:
    def __init__(self): self.ands = [StatefulAnd() for _ in range(8)]
    def out(self, val: int, enable: int) -> int:
        res = 0
        for i in range(8): res |= (self.ands[i].out((val >> i) & 1, enable) << i)
        return res

class AddressDecoder4x16:
    def __init__(self):
        self.invs = [StatefulNot() for _ in range(4)]
        self.rows = [self._make_4input_and() for _ in range(16)]
    def _make_4input_and(self):
        class And4:
            def __init__(self): self.a1 = StatefulAnd(); self.a2 = StatefulAnd(); self.a3 = StatefulAnd()
            def out(self, i0, i1, i2, i3): return self.a3.out(self.a1.out(i0, i1), self.a2.out(i2, i3))
        return And4()
    def decode(self, addr: int) -> int:
        bits = [(addr >> i) & 1 for i in range(4)]; inv_bits = [self.invs[i].out(bits[i]) for i in range(4)]
        row_selects = 0
        for i in range(16):
            inputs = [bits[j] if (i >> j) & 1 else inv_bits[j] for j in range(4)]
            if self.rows[i].out(inputs[0], inputs[1], inputs[2], inputs[3]): row_selects |= (1 << i)
        return row_selects

class PhysicalROM:
    def __init__(self):
        self.decoder = AddressDecoder4x16()
        self.matrix = [0] * 16
        self.output_buffer = TriStateBuffer8()
    def flash(self, data: List[int]):
        for i in range(min(len(data), 16)): self.matrix[i] = data[i]
    def read(self, addr: int, enable: int) -> int:
        if not enable: return 0
        row_mask = self.decoder.decode(addr & 0x0F)
        raw_data = 0
        for i in range(16):
            if (row_mask >> i) & 1: raw_data = self.matrix[i]; break
        return self.output_buffer.out(raw_data, enable)

# --- PHYSICAL CLOCK GENERATOR ---

class PhaseGenerator:
    """
    A 2-bit counter that generates 4 distinct phase signals (T0, T1, T2, T3).
    Built from 2 D-FlipFlops and some logic.
    """
    def __init__(self):
        self.dff0 = D_FlipFlop()
        self.dff1 = D_FlipFlop()
        self.inv0 = StatefulNot()
        self.inv1 = StatefulNot()
        self.xor = StatefulXor()

        # Decoders for the 4 phases
        self.and_ph0 = StatefulAnd()
        self.and_ph1 = StatefulAnd()
        self.and_ph2 = StatefulAnd()
        self.and_ph3 = StatefulAnd()

        self.q0 = 0
        self.q1 = 0

    def tick(self, master_clk: int) -> tuple[int, int, int, int]:
        # 2-bit Counter Logic:
        # Q0_next = !Q0
        # Q1_next = Q0 ^ Q1

        d0 = self.inv0.out(self.q0)
        d1 = self.xor.out(self.q0, self.q1)

        # Update Flip-Flops on Master Clock Edge
        self.q0 = self.dff0.update(d0, master_clk)
        self.q1 = self.dff1.update(d1, master_clk)

        # Decode State (Q1, Q0) into 4 wires
        not_q0 = self.inv0.out(self.q0) # Re-using inverter for simplicity
        not_q1 = self.inv1.out(self.q1)

        p0 = self.and_ph0.out(not_q1, not_q0) # 00
        p1 = self.and_ph1.out(not_q1, self.q0) # 01
        p2 = self.and_ph2.out(self.q1, not_q0) # 10
        p3 = self.and_ph3.out(self.q1, self.q0) # 11

        return p0, p1, p2, p3

class FullPhysicalCPU:
    def __init__(self):
        self.pc = LoadableRegister8(); self.ir = LoadableRegister8()
        self.reg_a = LoadableRegister8(); self.reg_b = LoadableRegister8()
        self.alu = RippleCarryAdder8(); self.decoder = PhysicalDecoder()
        self.rom_opcode = PhysicalROM(); self.rom_operand = PhysicalROM()
        self.alu_driver = TriStateBuffer8(); self.io_driver = TriStateBuffer8()

        # REPLACED: Integer phase counter -> Physical Phase Generator
        self.phase_gen = PhaseGenerator()

        self.halted = False; self.bus = 0
        self.program: List[Instruction] = []

        self.io_ports: Dict[int, Callable[[int, str], int]] = {}
        self.is_waiting_for_input = False
        self.input_port = 0
        self.input_value = 0

        # Master Clock State (High/Low)
        self.master_clk = 0

    def register_io_port(self, port_id: int, handler: Callable[[int, str], int]):
        self.io_ports[port_id] = handler

    def provide_input(self, value: int):
        self.input_value = value
        self.is_waiting_for_input = False

    def load_program(self, program: List[Instruction]):
        opcodes = [instr.opcode for instr in program]; operands = [instr.operand for instr in program]
        self.rom_opcode.flash(opcodes); self.rom_operand.flash(operands)
        self.reset()

    def reset(self):
        self.pc = LoadableRegister8(); self.ir = LoadableRegister8()
        self.reg_a = LoadableRegister8(); self.reg_b = LoadableRegister8()
        self.halted = False; self.bus = 0
        self.is_waiting_for_input = False
        self.phase_gen = PhaseGenerator() # Reset clock
        self.master_clk = 0

    def tick(self):
        """
        Advances the simulation by one MASTER CLOCK EDGE.
        This is now a sub-instruction step.
        It takes 4 calls to tick() to complete one full instruction cycle (4 phases).
        """
        if self.halted or self.is_waiting_for_input: return

        # Toggle Master Clock (0->1->0)
        self.master_clk = 1 - self.master_clk

        # 1. Generate Phase Signals
        p0, p1, p2, p3 = self.phase_gen.tick(self.master_clk)

        # 2. Decode & Execute based on current Phase Wires
        self._execute_logic(p0, p1, p2, p3)

    def _execute_logic(self, p0, p1, p2, p3):
        current_instruction_opcode = self.ir.current_value

        # Pass physical phase wires to decoder
        self.decoder.decode(current_instruction_opcode, p0, p1, p2, p3)
        cs = self.decoder.control_signals

        operand_addr = (self.pc.current_value - 1) & 0xFF

        # --- I/O Handling ---
        if cs.get('io_write_enable'):
            port = self.rom_operand.read(operand_addr, 1)
            if port in self.io_ports: self.io_ports[port](self.reg_a.current_value, 'write')

        if cs.get('io_read_enable'):
            port = self.rom_operand.read(operand_addr, 1)
            if port in self.io_ports:
                self.is_waiting_for_input = True
                self.input_port = port
                return

        # --- BUS ARBITRATION ---
        bus_val = 0
        bus_val |= self.rom_opcode.read(self.pc.current_value, cs.get('rom_read_enable'))
        bus_val |= self.rom_operand.read(operand_addr, cs.get('operand_to_bus_enable'))
        alu_input_b = self.reg_b.current_value if cs.get('reg_b_to_alu_enable') else 0
        alu_result, _ = self.alu.add(self.reg_a.current_value, alu_input_b)
        bus_val |= self.alu_driver.out(alu_result, cs.get('alu_to_bus_enable'))
        bus_val |= self.io_driver.out(self.input_value, cs.get('io_read_enable'))
        self.bus = bus_val

        # --- LATCHING ---
        # Note: In a real circuit, latches are transparent when Enable is high.
        # Here we simulate this by ticking them.
        self.ir.tick_enabled(self.bus, cs.get('ir_write_enable'), 1); self.ir.tick_enabled(self.bus, cs.get('ir_write_enable'), 0)
        if cs.get('pc_increment_enable'):
            new_pc, _ = self.alu.add(self.pc.current_value, 1)
            self.pc.tick_enabled(new_pc, 1, 1); self.pc.tick_enabled(new_pc, 1, 0)
        self.reg_a.tick_enabled(self.bus, cs.get('reg_a_write_enable'), 1); self.reg_a.tick_enabled(self.bus, cs.get('reg_a_write_enable'), 0)
        self.reg_b.tick_enabled(self.bus, cs.get('reg_b_write_enable'), 1); self.reg_b.tick_enabled(self.bus, cs.get('reg_b_write_enable'), 0)

        if cs.get('halt_signal') and p2: self.halted = True

    def get_state_str(self) -> str:
        # Helper to see current phase
        p0, p1, p2, p3 = self.phase_gen.tick(self.master_clk) # Peek state
        phase = 0
        if p1: phase = 1
        elif p2: phase = 2
        elif p3: phase = 3

        return (f"PH:{phase} PC:{self.pc.current_value:02X} IR:{self.ir.current_value:02X} "
                f"A:{self.reg_a.current_value:02X} B:{self.reg_b.current_value:02X} "
                f"BUS:{self.bus:02X}")
