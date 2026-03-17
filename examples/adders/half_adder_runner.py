from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import load_project  # noqa: E402


PROJECT_PATH = Path(__file__).resolve().with_name("half_adder_switches.json")
SUM_THRESHOLD = 0.05


def _set_inputs(project, a: bool, b: bool) -> None:
    for component in project.components:
        if component.name == "X_A":
            component.params["position_b"] = bool(a)
        elif component.name == "X_B":
            component.params["position_b"] = bool(b)
        elif component.name == "SW_A":
            component.params["closed"] = bool(a)
        elif component.name == "SW_B":
            component.params["closed"] = bool(b)


def _simulate_case(a: bool, b: bool) -> dict[str, float]:
    project = load_project(PROJECT_PATH)
    _set_inputs(project, a, b)
    circuit = project.to_circuit()
    result = circuit.simulate(project.settings.duration_s, project.settings.dt_s)
    sum_brightness = float(result.component_observables["LED_SUM"]["brightness"][-1])
    carry_brightness = float(result.component_observables["LED_CARRY"]["brightness"][-1])
    sum_current = float(result.component_observables["LED_SUM"]["current_a"][-1])
    carry_current = float(result.component_observables["LED_CARRY"]["current_a"][-1])
    return {
        "sum_brightness": sum_brightness,
        "carry_brightness": carry_brightness,
        "sum_current_a": sum_current,
        "carry_current_a": carry_current,
        "sum_bit": float(sum_brightness >= SUM_THRESHOLD),
        "carry_bit": float(carry_brightness >= SUM_THRESHOLD),
    }


def _print_case(a: bool, b: bool, data: dict[str, float]) -> None:
    print(f"A={int(a)} B={int(b)}")
    print(f"  SUM   = {int(data['sum_bit'])} | brightness={data['sum_brightness']:.4f} | current={data['sum_current_a']:.6f} A")
    print(f"  CARRY = {int(data['carry_bit'])} | brightness={data['carry_brightness']:.4f} | current={data['carry_current_a']:.6f} A")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the half-adder example with chosen input bits A and B.")
    parser.add_argument("--a", type=int, choices=(0, 1), help="Input bit A")
    parser.add_argument("--b", type=int, choices=(0, 1), help="Input bit B")
    parser.add_argument("--truth-table", action="store_true", help="Print all four input combinations")
    parser.add_argument("--dump-json", action="store_true", help="Print results as JSON for the selected case or the truth table")
    args = parser.parse_args()

    if args.truth_table or args.a is None or args.b is None:
        rows: list[dict[str, float | int]] = []
        for a in (0, 1):
            for b in (0, 1):
                data = _simulate_case(bool(a), bool(b))
                row = {
                    "a": a,
                    "b": b,
                    "sum": int(data["sum_bit"]),
                    "carry": int(data["carry_bit"]),
                    "sum_brightness": data["sum_brightness"],
                    "carry_brightness": data["carry_brightness"],
                }
                rows.append(row)
                if not args.dump_json:
                    _print_case(bool(a), bool(b), data)
        if args.dump_json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    data = _simulate_case(bool(args.a), bool(args.b))
    if args.dump_json:
        print(
            json.dumps(
                {
                    "a": int(args.a),
                    "b": int(args.b),
                    "sum": int(data["sum_bit"]),
                    "carry": int(data["carry_bit"]),
                    "sum_brightness": data["sum_brightness"],
                    "carry_brightness": data["carry_brightness"],
                    "sum_current_a": data["sum_current_a"],
                    "carry_current_a": data["carry_current_a"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    _print_case(bool(args.a), bool(args.b), data)


if __name__ == "__main__":
    main()
