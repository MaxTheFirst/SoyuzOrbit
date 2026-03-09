from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from core.field_solver import simulate_fdtd_wave, simulate_full_wave_maxwell_2d, solve_quasi_static_field
from core.project import load_project
from core.engine import load_example_module


def _pick_duration(module_or_project, override: float | None) -> float:
    if override is not None:
        return override
    if hasattr(module_or_project, "settings"):
        return float(module_or_project.settings.duration_s)
    return float(getattr(module_or_project, "DURATION_S", 0.02))


def _pick_dt(module_or_project, override: float | None) -> float:
    if override is not None:
        return override
    if hasattr(module_or_project, "settings"):
        return float(module_or_project.settings.dt_s)
    return float(getattr(module_or_project, "DT_S", 1.0e-4))


def _load_circuit_source(source: str):
    path = Path(source)
    if path.suffix.lower() == ".json" and path.exists():
        project = load_project(path)
        return project, project.to_circuit()
    module = load_example_module(source)
    if not hasattr(module, "build_circuit"):
        raise SystemExit(f"{source} does not export build_circuit()")
    return module, module.build_circuit()


def _iter_current_keys(observables: dict[str, Iterable[float]]) -> list[str]:
    preferred = [key for key in observables if key == "current_a"]
    extra = [key for key in observables if key.endswith("current_a") and key not in preferred]
    return preferred + extra


def _display_name(name: str) -> str:
    if name.startswith("__wire__"):
        return f"Провод {name.split('__wire__', 1)[1]}"
    return name


def _print_summary(result) -> None:
    print(f"Circuit: {result.metadata['name']}")
    print(f"Duration: {result.metadata['duration_s']:.6f} s | dt: {result.metadata['dt_s']:.6e} s")
    print("\nFinal node voltages:")
    for node, values in result.node_voltages.items():
        print(f"  {node:>12s}: {values[-1]: .5f} V")
    print("\nFinal component observables:")
    for component_name, observables in result.component_observables.items():
        chunks = []
        for key in ("current_a", "voltage_v", "temperature_c", "brightness", "glow", "soc", "blown"):
            if key in observables:
                chunks.append(f"{key}={observables[key][-1]:.5g}")
        print(f"  {_display_name(component_name)}: " + (", ".join(chunks) if chunks else "no scalar observables"))


def _save_field(circuit, result, layer: str, target: str) -> None:
    snapshot = solve_quasi_static_field(circuit, result)
    image = snapshot.to_image(layer=layer, scale=4)
    path = Path(target)
    image.save(path)
    print(f"Saved field map to {path} ({layer})")
    print(
        f"Field stats: potential_max={float(snapshot.potential_v.max()):.5g}, "
        f"E_max={float(snapshot.electric_field_v_m.max()):.5g}, "
        f"B_max={float(snapshot.magnetic_flux_density_t.max()):.5g}"
    )


def _save_fdtd(circuit, result, layer: str, target: str) -> None:
    sequence = simulate_fdtd_wave(circuit, result)
    frames = [sequence.to_image(layer=layer, frame_index=index, scale=3) for index in range(sequence.frame_count())]
    path = Path(target)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=70, loop=0)
    print(f"Saved FDTD animation to {path} ({layer})")
    print(
        f"FDTD stats: frames={sequence.frame_count()}, "
        f"E_max={float(sequence.electric_frames_v_m.max()):.5g}, "
        f"B_max={float(sequence.magnetic_frames_t.max()):.5g}"
    )


def _save_maxwell(circuit, result, layer: str, target: str) -> None:
    sequence = simulate_full_wave_maxwell_2d(circuit, result)
    frames = [sequence.to_image(layer=layer, frame_index=index, scale=3) for index in range(sequence.frame_count())]
    path = Path(target)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=70, loop=0)
    print(f"Saved Maxwell 2D animation to {path} ({layer})")
    print(
        f"Maxwell stats: frames={sequence.frame_count()}, "
        f"E_max={float(sequence.electric_frames_v_m.max()):.5g}, "
        f"B_max={float(sequence.magnetic_frames_t.max()):.5g}"
    )


def _plot_result(result, plot_currents: bool, plot_temp: bool, plot_nodes: bool, save_plot: str | None) -> None:
    import matplotlib.pyplot as plt

    panels = []
    if plot_nodes:
        panels.append("nodes")
    if plot_currents:
        panels.append("currents")
    if plot_temp:
        panels.append("temperature")
    if not panels:
        return

    fig, axes = plt.subplots(len(panels), 1, figsize=(11, 3.8 * len(panels)), squeeze=False)
    axes_flat = axes.ravel()
    panel_index = 0

    if plot_nodes:
        ax = axes_flat[panel_index]
        for node, values in result.node_voltages.items():
            ax.plot(result.time_s, values, label=node)
        ax.set_title("Node voltages")
        ax.set_xlabel("Time, s")
        ax.set_ylabel("V")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        panel_index += 1

    if plot_currents:
        ax = axes_flat[panel_index]
        for component_name, observables in result.component_observables.items():
            for key in _iter_current_keys(observables):
                ax.plot(result.time_s, observables[key], label=f"{_display_name(component_name)}:{key}")
        ax.set_title("Component currents")
        ax.set_xlabel("Time, s")
        ax.set_ylabel("A")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", ncols=2)
        panel_index += 1

    if plot_temp:
        ax = axes_flat[panel_index]
        for component_name, observables in result.component_observables.items():
            if "temperature_c" in observables:
                ax.plot(result.time_s, observables["temperature_c"], label=_display_name(component_name))
        ax.set_title("Component temperatures")
        ax.set_xlabel("Time, s")
        ax.set_ylabel("degC")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", ncols=2)

    fig.tight_layout()
    if save_plot:
        path = Path(save_plot)
        fig.savefig(path, dpi=160)
        print(f"Saved plot to {path}")
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run transient physical circuit simulations from Python examples or JSON projects.")
    parser.add_argument("example", help="Path to a Python example file, importable module, or JSON project.")
    parser.add_argument("--duration", type=float, help="Override simulation duration in seconds.")
    parser.add_argument("--dt", type=float, help="Override timestep in seconds.")
    parser.add_argument("--plot-currents", action="store_true", help="Plot component currents.")
    parser.add_argument("--plot-temp", action="store_true", help="Plot component temperatures.")
    parser.add_argument("--plot-nodes", action="store_true", help="Plot all node voltages.")
    parser.add_argument("--save-plot", help="Save plots to a file instead of opening a window.")
    parser.add_argument("--save-field", help="Save a quasi-static field map image to a file.")
    parser.add_argument("--save-fdtd", help="Save a simplified FDTD wave animation to a GIF file.")
    parser.add_argument("--save-maxwell", help="Save a 2D full-wave Maxwell animation to a GIF file.")
    parser.add_argument(
        "--field-layer",
        choices=("potential", "electric", "magnetic"),
        default="potential",
        help="Which field layer to save when --save-field is used.",
    )
    args = parser.parse_args()

    source, circuit = _load_circuit_source(args.example)
    result = circuit.simulate(_pick_duration(source, args.duration), _pick_dt(source, args.dt))
    _print_summary(result)
    _plot_result(result, args.plot_currents, args.plot_temp, args.plot_nodes, args.save_plot)
    if args.save_field:
        _save_field(circuit, result, args.field_layer, args.save_field)
    if args.save_fdtd:
        _save_fdtd(circuit, result, args.field_layer, args.save_fdtd)
    if args.save_maxwell:
        _save_maxwell(circuit, result, args.field_layer, args.save_maxwell)


if __name__ == "__main__":
    main()
