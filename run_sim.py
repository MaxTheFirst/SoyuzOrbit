from __future__ import annotations

import argparse
from pathlib import Path

from core.field_solver import simulate_fdtd_wave, simulate_full_wave_maxwell_2d, solve_quasi_static_field
from core.result_plots import PLOT_PANEL_ORDER, available_plot_panel_ids, render_result_figure
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


def _save_maxwell(circuit, result, layer: str, target: str, mode: str) -> None:
    sequence = simulate_full_wave_maxwell_2d(circuit, result, mode=mode)
    frames = [sequence.to_image(layer=layer, frame_index=index, scale=3) for index in range(sequence.frame_count())]
    path = Path(target)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=70, loop=0)
    print(f"Saved Maxwell 2D animation to {path} ({layer}, {mode})")
    print(
        f"Maxwell stats: frames={sequence.frame_count()}, "
        f"E_max={float(sequence.electric_frames_v_m.max()):.5g}, "
        f"B_max={float(sequence.magnetic_frames_t.max()):.5g}"
    )


def _selected_plot_panels(
    result,
    *,
    plot_nodes: bool,
    plot_currents: bool,
    plot_temp: bool,
    plot_voltages: bool,
    plot_power_temperature: bool,
    plot_surface_temp: bool,
    plot_power: bool,
    plot_energy_storage: bool,
    plot_charge: bool,
    plot_iv_xy: bool,
    plot_state: bool,
    plot_all: bool,
) -> list[str]:
    selected: list[str] = []
    if plot_all:
        selected.extend(available_plot_panel_ids(result))
    if plot_nodes:
        selected.append("nodes")
    if plot_currents:
        selected.append("currents")
    if plot_voltages:
        selected.append("voltages")
    if plot_power_temperature:
        selected.append("power_temperature")
    if plot_temp:
        selected.append("temperature")
    if plot_surface_temp:
        selected.append("surface_temperature")
    if plot_power:
        selected.append("power")
    if plot_energy_storage:
        selected.append("energy_storage")
    if plot_charge:
        selected.append("charge")
    if plot_iv_xy:
        selected.append("iv_xy")
    if plot_state:
        selected.append("state")
    unique: list[str] = []
    for panel_id in selected:
        if panel_id not in PLOT_PANEL_ORDER:
            continue
        if panel_id not in unique:
            unique.append(panel_id)
    return unique


def _plot_result(result, panel_ids: list[str], save_plot: str | None) -> None:
    import matplotlib.pyplot as plt

    if not panel_ids:
        if save_plot:
            raise SystemExit(
                "No plot panels selected. Use --plot-all or at least one of "
                "--plot-nodes, --plot-currents, --plot-voltages, --plot-power-temperature, "
                "--plot-temp, --plot-surface-temp, --plot-power, --plot-energy-storage, "
                "--plot-charge, --plot-iv-xy, --plot-state."
            )
        return

    fig = plt.figure()
    rendered_panels = render_result_figure(fig, result, panel_ids)
    if not rendered_panels:
        raise SystemExit("Selected plot panels have no data for this simulation.")

    if save_plot:
        path = Path(save_plot)
        fig.savefig(path, dpi=160)
        print(f"Saved plot to {path}")
    else:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run transient physical circuit simulations from Python examples or JSON projects.")
    parser.add_argument("example", help="Path to a Python example file, importable module, or JSON project.")
    parser.add_argument("--duration", type=float, help="Override simulation duration in seconds.")
    parser.add_argument("--dt", type=float, help="Override timestep in seconds.")
    parser.add_argument("--plot-currents", action="store_true", help="Plot component currents.")
    parser.add_argument("--plot-voltages", action="store_true", help="Plot component voltages and source EMF.")
    parser.add_argument("--plot-power-temperature", action="store_true", help="Plot component power and temperature on a combined panel.")
    parser.add_argument("--plot-temp", action="store_true", help="Plot component temperatures.")
    parser.add_argument("--plot-surface-temp", action="store_true", help="Plot component surface temperatures.")
    parser.add_argument("--plot-power", action="store_true", help="Plot component power dissipation.")
    parser.add_argument("--plot-energy-storage", action="store_true", help="Plot charge and flux-linkage accumulation observables.")
    parser.add_argument("--plot-charge", action="store_true", help="Plot charge-related observables.")
    parser.add_argument("--plot-iv-xy", action="store_true", help="Plot nonlinear I(U) XY curves for components that expose voltage and current.")
    parser.add_argument("--plot-state", action="store_true", help="Plot unitless states such as brightness, SOC, overload flags.")
    parser.add_argument("--plot-nodes", action="store_true", help="Plot all node voltages.")
    parser.add_argument("--plot-all", action="store_true", help="Plot all available panels for the simulation result.")
    parser.add_argument("--save-plot", help="Save plots to a file instead of opening a window.")
    parser.add_argument("--save-field", help="Save a quasi-static field map image to a file.")
    parser.add_argument("--save-fdtd", help="Save a simplified FDTD wave animation to a GIF file.")
    parser.add_argument("--save-maxwell", help="Save a 2D full-wave Maxwell animation to a GIF file.")
    parser.add_argument("--maxwell-mode", choices=("tmz", "tez"), default="tmz", help="Maxwell solver mode.")
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
    plot_panels = _selected_plot_panels(
        result,
        plot_nodes=args.plot_nodes,
        plot_currents=args.plot_currents,
        plot_temp=args.plot_temp,
        plot_voltages=args.plot_voltages,
        plot_power_temperature=args.plot_power_temperature,
        plot_surface_temp=args.plot_surface_temp,
        plot_power=args.plot_power,
        plot_energy_storage=args.plot_energy_storage,
        plot_charge=args.plot_charge,
        plot_iv_xy=args.plot_iv_xy,
        plot_state=args.plot_state,
        plot_all=args.plot_all,
    )
    _plot_result(result, plot_panels, args.save_plot)
    if args.save_field:
        _save_field(circuit, result, args.field_layer, args.save_field)
    if args.save_fdtd:
        _save_fdtd(circuit, result, args.field_layer, args.save_fdtd)
    if args.save_maxwell:
        _save_maxwell(circuit, result, args.field_layer, args.save_maxwell, args.maxwell_mode)


if __name__ == "__main__":
    main()
