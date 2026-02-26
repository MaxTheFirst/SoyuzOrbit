"""Full MNA-based SPICE-like solver for transistor circuits.

Implemented devices:
- R: resistor
- I: independent current source
- V: independent voltage source
- C: capacitor (transient via backward Euler companion model)
- M: MOSFET Level-1-like (Shichman-Hodges square-law, 4-terminal API)

The solver builds a full MNA matrix and solves nonlinear systems with
Newton-Raphson at each operating-point or transient step.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np


GND_NAMES = {"0", "gnd", "GND"}


@dataclass
class Resistor:
    a: str
    b: str
    r_ohm: float


@dataclass
class CurrentSource:
    p: str
    n: str
    i_amp: float


@dataclass
class VoltageSource:
    p: str
    n: str
    v_volt: float
    name: str


@dataclass
class Capacitor:
    a: str
    b: str
    c_f: float
    v_prev: float = 0.0


@dataclass
class MosfetLevel1:
    d: str
    g: str
    s: str
    b: str
    mtype: str  # "n" or "p"
    beta: float
    vth: float
    lamb: float = 0.02


@dataclass
class SolveResult:
    converged: bool
    iterations: int
    residual_norm: float
    voltages: dict[str, float]
    source_currents: dict[str, float]


class SpiceMNA:
    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self.resistors: list[Resistor] = []
        self.current_sources: list[CurrentSource] = []
        self.voltage_sources: list[VoltageSource] = []
        self.capacitors: list[Capacitor] = []
        self.mosfets: list[MosfetLevel1] = []

        self.gmin = 1e-12
        self.newton_max_iter = 80
        self.newton_tol = 1e-7
        self.voltage_limit = 20.0

    def _norm_node(self, n: str) -> str:
        return "0" if n in GND_NAMES else n

    def _touch_nodes(self, *nodes: str) -> None:
        for n in nodes:
            nn = self._norm_node(n)
            if nn != "0":
                self._nodes.add(nn)

    def add_resistor(self, a: str, b: str, r_ohm: float) -> None:
        if r_ohm <= 0:
            raise ValueError("resistor must be > 0")
        a, b = self._norm_node(a), self._norm_node(b)
        self.resistors.append(Resistor(a, b, float(r_ohm)))
        self._touch_nodes(a, b)

    def add_current_source(self, p: str, n: str, i_amp: float) -> None:
        p, n = self._norm_node(p), self._norm_node(n)
        self.current_sources.append(CurrentSource(p, n, float(i_amp)))
        self._touch_nodes(p, n)

    def add_voltage_source(self, name: str, p: str, n: str, v_volt: float) -> None:
        p, n = self._norm_node(p), self._norm_node(n)
        self.voltage_sources.append(VoltageSource(p, n, float(v_volt), name))
        self._touch_nodes(p, n)

    def set_voltage_source(self, name: str, v_volt: float) -> None:
        for vs in self.voltage_sources:
            if vs.name == name:
                vs.v_volt = float(v_volt)
                return
        raise KeyError(f"unknown voltage source: {name}")

    def add_capacitor(self, a: str, b: str, c_f: float, ic_volt: float = 0.0) -> None:
        if c_f <= 0:
            raise ValueError("capacitance must be > 0")
        a, b = self._norm_node(a), self._norm_node(b)
        self.capacitors.append(Capacitor(a, b, float(c_f), float(ic_volt)))
        self._touch_nodes(a, b)

    def add_mosfet(self, d: str, g: str, s: str, b: str, mtype: str, beta: float, vth: float, lamb: float = 0.02) -> None:
        mt = mtype.lower()
        if mt not in {"n", "p"}:
            raise ValueError("mtype must be 'n' or 'p'")
        if beta <= 0:
            raise ValueError("beta must be > 0")
        d, g, s, b = self._norm_node(d), self._norm_node(g), self._norm_node(s), self._norm_node(b)
        self.mosfets.append(MosfetLevel1(d, g, s, b, mt, float(beta), float(vth), float(lamb)))
        self._touch_nodes(d, g, s, b)

    @property
    def transistor_count(self) -> int:
        return len(self.mosfets)

    def _build_maps(self) -> tuple[dict[str, int], dict[str, int]]:
        node_list = sorted(self._nodes)
        node_map = {name: i for i, name in enumerate(node_list)}
        vs_map = {vs.name: i for i, vs in enumerate(self.voltage_sources)}
        return node_map, vs_map

    @staticmethod
    def _idx(node: str, node_map: dict[str, int]) -> int | None:
        if node == "0":
            return None
        return node_map[node]

    @staticmethod
    def _xv(x: np.ndarray, node: str, node_map: dict[str, int]) -> float:
        if node == "0":
            return 0.0
        return float(x[node_map[node]])

    @staticmethod
    def _mos_n_id_gm_gds(vgs: float, vds: float, beta: float, vth: float, lamb: float) -> tuple[float, float, float]:
        # Voltage limiting to keep Newton linearization numerically stable.
        vgs = max(min(vgs, 20.0), -20.0)
        vds = max(min(vds, 20.0), -20.0)

        # Off region with small conductance for numerical robustness.
        if vgs <= vth:
            return (0.0, 0.0, 1e-12)

        vov = vgs - vth
        if vds < vov:
            # Triode
            i0 = beta * ((vov * vds) - 0.5 * vds * vds)
            idrain = i0 * (1.0 + lamb * vds)
            gm = beta * vds * (1.0 + lamb * vds)
            gds = beta * ((vov - vds) * (1.0 + lamb * vds) + ((vov * vds) - 0.5 * vds * vds) * lamb)
            return (idrain, gm, max(gds, 1e-12))

        # Saturation
        i0 = 0.5 * beta * vov * vov
        idrain = i0 * (1.0 + lamb * vds)
        gm = beta * vov * (1.0 + lamb * vds)
        gds = i0 * lamb
        return (idrain, gm, max(gds, 1e-12))

    def _mos_eval(self, m: MosfetLevel1, vd: float, vg: float, vs: float) -> tuple[float, float, float, float, float, float]:
        # Returns Id(d->s), and derivatives wrt (vd, vg, vs).
        if m.mtype == "n":
            idrain, gm, gds = self._mos_n_id_gm_gds(vg - vs, vd - vs, m.beta, m.vth, m.lamb)
            did_d = gds
            did_g = gm
            did_s = -(gds + gm)
            return idrain, did_d, did_g, did_s, gm, gds

        # PMOS mapped through source-referenced NMOS equations.
        i_sd, gm_p, gds_p = self._mos_n_id_gm_gds(vs - vg, vs - vd, m.beta, abs(m.vth), m.lamb)
        idrain = -i_sd
        did_d = gds_p
        did_g = gm_p
        did_s = -(gds_p + gm_p)
        return idrain, did_d, did_g, did_s, gm_p, gds_p

    def _add_node_term(self, f: np.ndarray, j: np.ndarray, node: str, val: float, derivs: Iterable[tuple[str, float]], node_map: dict[str, int]) -> None:
        i = self._idx(node, node_map)
        if i is None:
            return
        f[i] += val
        for n, d in derivs:
            k = self._idx(n, node_map)
            if k is not None:
                j[i, k] += d

    def _build_system(self, x: np.ndarray, dt_sec: float | None) -> tuple[np.ndarray, np.ndarray, dict[str, int], dict[str, int]]:
        node_map, vs_map = self._build_maps()
        n = len(node_map)
        m = len(vs_map)
        dim = n + m
        f = np.zeros(dim, dtype=float)
        j = np.zeros((dim, dim), dtype=float)

        # Resistors
        for r in self.resistors:
            va = self._xv(x, r.a, node_map)
            vb = self._xv(x, r.b, node_map)
            g = 1.0 / r.r_ohm
            self._add_node_term(f, j, r.a, g * (va - vb), ((r.a, g), (r.b, -g)), node_map)
            self._add_node_term(f, j, r.b, g * (vb - va), ((r.b, g), (r.a, -g)), node_map)

        # Current sources (defined from p -> n)
        for cs in self.current_sources:
            self._add_node_term(f, j, cs.p, cs.i_amp, (), node_map)
            self._add_node_term(f, j, cs.n, -cs.i_amp, (), node_map)

        # Capacitors (transient only): backward-Euler companion
        if dt_sec is not None and dt_sec > 0.0:
            for c in self.capacitors:
                g = c.c_f / dt_sec
                va = self._xv(x, c.a, node_map)
                vb = self._xv(x, c.b, node_map)
                i_hist = g * c.v_prev
                self._add_node_term(f, j, c.a, g * (va - vb) - i_hist, ((c.a, g), (c.b, -g)), node_map)
                self._add_node_term(f, j, c.b, g * (vb - va) + i_hist, ((c.b, g), (c.a, -g)), node_map)

        # MOSFETs
        for mos in self.mosfets:
            vd = self._xv(x, mos.d, node_map)
            vg = self._xv(x, mos.g, node_map)
            vs = self._xv(x, mos.s, node_map)
            idrain, did_d, did_g, did_s, _gm, _gds = self._mos_eval(mos, vd, vg, vs)

            self._add_node_term(
                f,
                j,
                mos.d,
                idrain,
                ((mos.d, did_d), (mos.g, did_g), (mos.s, did_s)),
                node_map,
            )
            self._add_node_term(
                f,
                j,
                mos.s,
                -idrain,
                ((mos.d, -did_d), (mos.g, -did_g), (mos.s, -did_s)),
                node_map,
            )

        # Voltage sources (MNA augmentation)
        for vs in self.voltage_sources:
            k = n + vs_map[vs.name]
            vp = self._idx(vs.p, node_map)
            vn = self._idx(vs.n, node_map)

            if vp is not None:
                f[vp] += x[k]
                j[vp, k] += 1.0
            if vn is not None:
                f[vn] -= x[k]
                j[vn, k] -= 1.0

            f[k] += self._xv(x, vs.p, node_map) - self._xv(x, vs.n, node_map) - vs.v_volt
            if vp is not None:
                j[k, vp] += 1.0
            if vn is not None:
                j[k, vn] -= 1.0

        # Global gmin stabilization
        for i in range(n):
            j[i, i] += self.gmin

        return f, j, node_map, vs_map

    def _newton(self, x0: np.ndarray, dt_sec: float | None) -> tuple[np.ndarray, bool, int, float, dict[str, int], dict[str, int]]:
        x = x0.copy()
        node_map: dict[str, int] = {}
        vs_map: dict[str, int] = {}
        residual = float("inf")

        for it in range(1, self.newton_max_iter + 1):
            f, j, node_map, vs_map = self._build_system(x, dt_sec)
            residual = float(np.linalg.norm(f, ord=np.inf))

            if residual < self.newton_tol:
                return x, True, it, residual, node_map, vs_map

            try:
                dx = np.linalg.solve(j, -f)
            except np.linalg.LinAlgError:
                return x, False, it, residual, node_map, vs_map

            if not np.isfinite(dx).all():
                return x, False, it, residual, node_map, vs_map

            step = 1.0
            accepted = False
            n_nodes = len(node_map)
            for _ in range(10):
                cand = x + step * dx
                # Limit only node voltages; source currents can stay unconstrained.
                cand[:n_nodes] = np.clip(cand[:n_nodes], -self.voltage_limit, self.voltage_limit)
                f_c, _, _, _ = self._build_system(cand, dt_sec)
                r_c = float(np.linalg.norm(f_c, ord=np.inf))
                if math.isfinite(r_c) and r_c <= residual:
                    x = cand
                    accepted = True
                    break
                step *= 0.5

            if not accepted:
                x = x + 0.1 * dx
                x[:n_nodes] = np.clip(x[:n_nodes], -self.voltage_limit, self.voltage_limit)

            if float(np.linalg.norm(dx, ord=np.inf)) < self.newton_tol:
                f2, _, node_map, vs_map = self._build_system(x, dt_sec)
                residual = float(np.linalg.norm(f2, ord=np.inf))
                return x, residual < (self.newton_tol * 10.0), it, residual, node_map, vs_map

        return x, False, self.newton_max_iter, residual, node_map, vs_map

    def _format_result(self, x: np.ndarray, ok: bool, it: int, residual: float, node_map: dict[str, int], vs_map: dict[str, int]) -> SolveResult:
        n = len(node_map)
        volts = {name: float(x[idx]) for name, idx in node_map.items()}
        src_i = {name: float(x[n + idx]) for name, idx in vs_map.items()}
        return SolveResult(ok, it, residual, volts, src_i)

    def solve_operating_point(self, initial_guess: dict[str, float] | None = None) -> SolveResult:
        node_map, vs_map = self._build_maps()
        dim = len(node_map) + len(vs_map)
        x0 = np.zeros(dim, dtype=float)

        if initial_guess:
            for node, val in initial_guess.items():
                nn = self._norm_node(node)
                if nn != "0" and nn in node_map:
                    x0[node_map[nn]] = float(val)

        x, ok, it, residual, node_map, vs_map = self._newton(x0, None)
        return self._format_result(x, ok, it, residual, node_map, vs_map)

    def solve_transient(self, tstop_sec: float, dt_sec: float, initial_guess: dict[str, float] | None = None) -> list[SolveResult]:
        if dt_sec <= 0.0:
            raise ValueError("dt_sec must be > 0")
        if tstop_sec <= 0.0:
            raise ValueError("tstop_sec must be > 0")

        node_map, vs_map = self._build_maps()
        dim = len(node_map) + len(vs_map)
        x = np.zeros(dim, dtype=float)

        if initial_guess:
            for node, val in initial_guess.items():
                nn = self._norm_node(node)
                if nn != "0" and nn in node_map:
                    x[node_map[nn]] = float(val)

        out: list[SolveResult] = []
        steps = int(math.ceil(tstop_sec / dt_sec))
        for _ in range(steps):
            x, ok, it, residual, node_map, vs_map = self._newton(x, dt_sec)
            result = self._format_result(x, ok, it, residual, node_map, vs_map)
            out.append(result)

            # Update capacitor history after accepted step.
            if ok:
                for c in self.capacitors:
                    va = 0.0 if c.a == "0" else result.voltages[c.a]
                    vb = 0.0 if c.b == "0" else result.voltages[c.b]
                    c.v_prev = va - vb

        return out


def build_cmos_inverter_chain_1000(vdd_volt: float = 5.0, beta_n: float = 2e-4, beta_p: float = 1.2e-4) -> SpiceMNA:
    """Return a circuit with exactly 1000 MOSFETs (500 CMOS inverters)."""
    c = SpiceMNA()
    c.add_voltage_source("VDD", "vdd", "0", vdd_volt)
    c.add_voltage_source("VIN", "in0", "0", vdd_volt)

    stages = 500
    prev = "in0"
    for i in range(stages):
        out = f"n{i}"
        c.add_mosfet(d=out, g=prev, s="0", b="0", mtype="n", beta=beta_n, vth=0.7, lamb=0.02)
        c.add_mosfet(d=out, g=prev, s="vdd", b="vdd", mtype="p", beta=beta_p, vth=-0.7, lamb=0.02)
        c.add_resistor(out, "0", 1e9)
        c.add_capacitor(out, "0", 2e-14)
        prev = out

    return c
