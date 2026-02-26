from __future__ import annotations

import unittest

from simulation.calculator_system import SpiceCalculatorTerminal
from simulation.electrical import ElectricalSystem
from simulation.logic_cpu import ALU8, SimpleLogicCPU


class LogicCpuTest(unittest.TestCase):
    def test_alu_add(self) -> None:
        value, carry = ALU8.add(0xFF, 0x01)
        self.assertEqual(value, 0x00)
        self.assertEqual(carry, 1)

    def test_cpu_advances_on_ticks(self) -> None:
        cpu = SimpleLogicCPU()
        for _ in range(8):
            cpu.tick_rising_edge()
        self.assertGreaterEqual(cpu.cycle_count, 2)
        self.assertEqual(cpu.acc.value, 2)
        self.assertEqual(cpu.pc.value, 2)


class ElectricalTest(unittest.TestCase):
    def test_boot_depends_on_current(self) -> None:
        cpu = SimpleLogicCPU()
        system = ElectricalSystem(cpu)
        system.toggle_power()
        system.set_available_current(0.4)
        system.update(0.2)
        self.assertFalse(system.boot_ready)

        system.set_available_current(1.0)
        system.update(0.2)
        self.assertTrue(system.boot_ready)

    def test_memory_devices_tick_when_booted(self) -> None:
        cpu = SimpleLogicCPU()
        system = ElectricalSystem(cpu)
        system.toggle_power()
        system.set_available_current(1.2)
        for _ in range(400):
            system.update(0.05)

        self.assertTrue(system.boot_ready)
        self.assertGreater(system.ram_reads + system.ram_writes, 0)
        self.assertGreater(system.hdd_writes, 0)
        self.assertIn("RAM/HDD monitor:", system.memory_screen_lines()[0])


class CalculatorTerminalTest(unittest.TestCase):
    def test_prompt_and_help(self) -> None:
        t = SpiceCalculatorTerminal()
        self.assertEqual(t.prompt, "calc> ")
        out = t.handle_line("help")
        self.assertTrue(any("Формат" in line for line in out))

    def test_addition_with_3_digit_inputs(self) -> None:
        t = SpiceCalculatorTerminal()
        out = t.handle_line("999+999")
        self.assertEqual(out, ["999 + 999 = 1998"])

    def test_invalid_expression(self) -> None:
        t = SpiceCalculatorTerminal()
        out = t.handle_line("12*3")
        self.assertTrue(any("Ошибка" in line for line in out))


if __name__ == "__main__":
    unittest.main()
