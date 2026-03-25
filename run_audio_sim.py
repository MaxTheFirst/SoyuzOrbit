from __future__ import annotations

import argparse
import inspect
from pathlib import Path
from typing import Callable

from core import (
    AudioFileSource,
    AudioSink,
    Circuit,
    RealCapacitor,
    RealResistor,
    SchockleyDiode,
    audio_buffer_from_simulation_result,
    is_supported_audio_export_path,
    load_project,
    probe_audio_file,
    save_audio_file,
)
from core.engine import load_example_module


def build_passthrough(input_path: str, *, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    circuit = Circuit("Audio passthrough")
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            file_path=input_path,
            peak_voltage_v=peak_voltage_v,
            target_sample_rate_hz=sample_rate_hz,
            internal_resistance_ohm=0.2,
        )
    )
    circuit.add(
        AudioSink(
            "OUT",
            "vin",
            "0",
            input_resistance_ohm=1.0e9,
            output_gain=1.0 / max(abs(peak_voltage_v), 1.0e-9),
        )
    )
    return circuit


def build_hard_mute(input_path: str, *, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    circuit = Circuit("Audio hard mute")
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            file_path=input_path,
            peak_voltage_v=peak_voltage_v,
            target_sample_rate_hz=sample_rate_hz,
            internal_resistance_ohm=0.2,
        )
    )
    circuit.add(RealResistor("R_TOP", "vin", "vout", resistance_ohm=1.0e9))
    circuit.add(RealResistor("R_SHUNT", "vout", "0", resistance_ohm=1.0))
    circuit.add(AudioSink("OUT", "vout", "0", input_resistance_ohm=1.0e9, output_gain=1.0))
    return circuit


def build_divider(input_path: str, *, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    circuit = Circuit("Audio divider")
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            file_path=input_path,
            peak_voltage_v=peak_voltage_v,
            target_sample_rate_hz=sample_rate_hz,
            internal_resistance_ohm=0.2,
        )
    )
    circuit.add(RealResistor("R_TOP", "vin", "vout", resistance_ohm=3300.0))
    circuit.add(RealResistor("R_BOTTOM", "vout", "0", resistance_ohm=1000.0))
    circuit.add(
        AudioSink(
            "OUT",
            "vout",
            "0",
            input_resistance_ohm=1.0e9,
            output_gain=1.0 / max(abs(peak_voltage_v), 1.0e-9),
        )
    )
    return circuit


def build_rc_smoother(input_path: str, *, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    circuit = Circuit("Audio RC smoother")
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            file_path=input_path,
            peak_voltage_v=peak_voltage_v,
            target_sample_rate_hz=sample_rate_hz,
            internal_resistance_ohm=0.2,
        )
    )
    circuit.add(RealResistor("R1", "vin", "vout", resistance_ohm=1800.0))
    circuit.add(RealCapacitor("C1", "vout", "0", capacitance_f=2.2e-5, max_voltage_v=max(abs(peak_voltage_v) * 4.0, 5.0)))
    circuit.add(
        AudioSink(
            "OUT",
            "vout",
            "0",
            input_resistance_ohm=1.0e9,
            output_gain=1.0 / max(abs(peak_voltage_v), 1.0e-9),
        )
    )
    return circuit


def build_peak_spreader(input_path: str, *, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    circuit = Circuit("Audio peak spreader")
    circuit.add(
        AudioFileSource(
            "SRC",
            "vin",
            "0",
            file_path=input_path,
            peak_voltage_v=peak_voltage_v,
            target_sample_rate_hz=sample_rate_hz,
            internal_resistance_ohm=0.2,
        )
    )
    circuit.add(SchockleyDiode("D1", "vin", "vpeak", forward_drop_v=0.32, shunt_resistance_ohm=2.0e8))
    circuit.add(RealCapacitor("C1", "vpeak", "0", capacitance_f=6.8e-5, esr_ohm=0.08, max_voltage_v=max(abs(peak_voltage_v) * 4.0, 5.0)))
    circuit.add(RealResistor("R1", "vpeak", "0", resistance_ohm=1200.0))
    circuit.add(
        AudioSink(
            "OUT",
            "vpeak",
            "0",
            input_resistance_ohm=1.0e9,
            output_gain=1.0 / max(abs(peak_voltage_v), 1.0e-9),
        )
    )
    return circuit


BUILTIN_SCHEMES: dict[str, tuple[str, Callable[..., Circuit]]] = {
    "passthrough": ("Прямой проход без обработки.", build_passthrough),
    "hard_mute": ("Почти полное подавление сигнала через жесткий шунт на землю.", build_hard_mute),
    "divider": ("Ослабление амплитуды простым резистивным делителем.", build_divider),
    "rc_smoother": ("RC-сглаживание: быстрые колебания приглушаются, волна становится мягче.", build_rc_smoother),
    "peak_spreader": ("Диод + RC-цепь: короткие пики превращаются в широкую огибающую.", build_peak_spreader),
}


def _list_schemes() -> str:
    lines = ["Built-in schemes:"]
    for name, (description, _) in BUILTIN_SCHEMES.items():
        lines.append(f"  {name:14s} {description}")
    return "\n".join(lines)


def _pick_named_component(components: list[object], requested_name: str | None, label: str):
    if not components:
        raise SystemExit(f"The selected circuit does not contain any {label} components.")
    if requested_name:
        for component in components:
            if getattr(component, "name", None) == requested_name:
                return component
        names = ", ".join(getattr(component, "name", "?") for component in components)
        raise SystemExit(f"{label} '{requested_name}' was not found. Available: {names}")
    if len(components) == 1:
        return components[0]
    names = ", ".join(getattr(component, "name", "?") for component in components)
    raise SystemExit(f"The circuit contains multiple {label} components. Select one with the matching flag. Available: {names}")


def _call_build_function(build_fn, *, input_path: str, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    known_kwargs = {
        "input_path": input_path,
        "audio_path": input_path,
        "input_audio_path": input_path,
        "file_path": input_path,
        "sample_rate_hz": sample_rate_hz,
        "target_sample_rate_hz": sample_rate_hz,
        "peak_voltage_v": peak_voltage_v,
    }
    signature = inspect.signature(build_fn)
    kwargs: dict[str, object] = {}
    accepts_var_kwargs = False
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            accepts_var_kwargs = True
            continue
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            continue
        if parameter.name in known_kwargs:
            kwargs[parameter.name] = known_kwargs[parameter.name]
            continue
        if parameter.default is inspect.Signature.empty:
            raise SystemExit(
                f"{build_fn.__name__}() requires unsupported parameter '{parameter.name}'. "
                "Use a function without mandatory custom arguments or build the circuit in JSON."
            )
    if accepts_var_kwargs:
        for name, value in known_kwargs.items():
            kwargs.setdefault(name, value)
    circuit = build_fn(**kwargs)
    if not isinstance(circuit, Circuit):
        raise SystemExit(f"{build_fn.__name__}() must return a Circuit instance.")
    return circuit


def _load_external_circuit(source: str, *, input_path: str, sample_rate_hz: int, peak_voltage_v: float) -> Circuit:
    path = Path(source)
    if path.suffix.lower() == ".json" and path.exists():
        return load_project(path).to_circuit()
    module = load_example_module(source)
    for function_name in ("build_audio_circuit", "build_circuit"):
        build_fn = getattr(module, function_name, None)
        if build_fn is None:
            continue
        return _call_build_function(
            build_fn,
            input_path=input_path,
            sample_rate_hz=sample_rate_hz,
            peak_voltage_v=peak_voltage_v,
        )
    raise SystemExit(f"{source} does not export build_audio_circuit() or build_circuit().")


def _configure_external_audio_io(
    circuit: Circuit,
    *,
    input_path: str,
    sample_rate_hz: int,
    peak_voltage_v: float,
    source_name: str | None,
    sink_name: str | None,
) -> str:
    sources = [component for component in circuit.components if isinstance(component, AudioFileSource)]
    sinks = [component for component in circuit.components if isinstance(component, AudioSink)]
    selected_source = _pick_named_component(sources, source_name, "AudioFileSource")
    selected_sink = _pick_named_component(sinks, sink_name, "AudioSink")
    selected_source.peak_voltage_v = float(peak_voltage_v)
    selected_source.target_sample_rate_hz = int(sample_rate_hz)
    selected_source.reload_source(str(Path(input_path).expanduser()))
    return str(selected_sink.name)


def _build_circuit(
    scheme: str,
    *,
    input_path: str,
    sample_rate_hz: int,
    peak_voltage_v: float,
    source_name: str | None,
    sink_name: str | None,
) -> tuple[Circuit, str]:
    if scheme in BUILTIN_SCHEMES:
        _, builder = BUILTIN_SCHEMES[scheme]
        circuit = builder(input_path, sample_rate_hz=sample_rate_hz, peak_voltage_v=peak_voltage_v)
        return circuit, "OUT"
    circuit = _load_external_circuit(
        scheme,
        input_path=input_path,
        sample_rate_hz=sample_rate_hz,
        peak_voltage_v=peak_voltage_v,
    )
    selected_sink_name = _configure_external_audio_io(
        circuit,
        input_path=input_path,
        sample_rate_hz=sample_rate_hz,
        peak_voltage_v=peak_voltage_v,
        source_name=source_name,
        sink_name=sink_name,
    )
    return circuit, selected_sink_name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an audio file through a built-in or custom circuit and save the captured AudioSink output.",
        epilog=_list_schemes(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_path", nargs="?", help="Input audio file path.")
    parser.add_argument("scheme", nargs="?", help="Built-in scheme name or path to a Python/JSON circuit.")
    parser.add_argument("output_path", nargs="?", help="Output audio file path.")
    parser.add_argument("--sample-rate", type=int, default=11025, help="Simulation sample rate in Hz.")
    parser.add_argument("--peak-voltage", type=float, default=1.0, help="Peak voltage produced by AudioFileSource.")
    parser.add_argument("--duration", type=float, help="Optional simulation duration override in seconds.")
    parser.add_argument("--normalize-output", action="store_true", help="Normalize the exported audio buffer before saving.")
    parser.add_argument("--source", help="AudioFileSource name to use when a custom circuit contains multiple sources.")
    parser.add_argument("--sink", help="AudioSink name to export when a custom circuit contains multiple sinks.")
    parser.add_argument("--list-schemes", action="store_true", help="Print built-in scheme names and exit.")
    args = parser.parse_args()

    if args.list_schemes:
        print(_list_schemes())
        return

    if not args.input_path or not args.scheme or not args.output_path:
        parser.error("input_path, scheme, and output_path are required unless --list-schemes is used.")

    if args.sample_rate <= 0:
        raise SystemExit("--sample-rate must be positive.")
    if not is_supported_audio_export_path(args.output_path):
        raise SystemExit(f"Unsupported output format: {Path(args.output_path).suffix or '(no extension)'}")

    input_info = probe_audio_file(args.input_path)
    duration_s = float(args.duration) if args.duration is not None else float(input_info.duration_s)
    if duration_s <= 0.0:
        raise SystemExit("Simulation duration must be positive.")

    circuit, sink_name = _build_circuit(
        args.scheme,
        input_path=args.input_path,
        sample_rate_hz=args.sample_rate,
        peak_voltage_v=args.peak_voltage,
        source_name=args.source,
        sink_name=args.sink,
    )
    dt_s = 1.0 / args.sample_rate
    result = circuit.simulate(duration_s, dt_s)
    output_buffer = audio_buffer_from_simulation_result(
        result,
        sink_name,
        observable_key="captured_v",
        normalize=args.normalize_output,
    )
    output_path = save_audio_file(args.output_path, output_buffer, normalize=False)
    print(f"Saved processed audio to {output_path}")
    print(f"Scheme: {args.scheme} | sink: {sink_name} | duration: {duration_s:.3f} s | sample_rate: {output_buffer.sample_rate_hz} Hz")


if __name__ == "__main__":
    main()
