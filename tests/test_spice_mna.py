from __future__ import annotations

import unittest

from simulation.full_spice_mna import SpiceMNA, build_cmos_inverter_chain_1000


class SpiceMnaTest(unittest.TestCase):
    def test_simple_resistive_divider(self) -> None:
        c = SpiceMNA()
        c.add_voltage_source("VDD", "vdd", "0", 10.0)
        c.add_resistor("vdd", "mid", 1000.0)
        c.add_resistor("mid", "0", 1000.0)

        res = c.solve_operating_point()
        self.assertTrue(res.converged)
        self.assertAlmostEqual(res.voltages["mid"], 5.0, places=3)

    def test_mna_1000_transistors_operating_point(self) -> None:
        c = build_cmos_inverter_chain_1000(vdd_volt=5.0)
        self.assertEqual(c.transistor_count, 1000)

        guess: dict[str, float] = {"vdd": 5.0, "in0": 5.0}
        for i in range(500):
            guess[f"n{i}"] = 0.0 if (i % 2 == 0) else 5.0

        res = c.solve_operating_point(initial_guess=guess)
        self.assertTrue(res.converged)
        # 500 inverters: even number, so output should follow high input.
        self.assertGreater(res.voltages["n499"], 3.0)


if __name__ == "__main__":
    unittest.main()
