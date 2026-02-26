"""Single-window app: electrical schematic + attached terminal screen."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import tkinter as tk
from tkinter import ttk

from simulation.calculator_system import SpiceCalculatorTerminal
from simulation.electrical import ElectricalSystem
from simulation.logic_cpu import SimpleLogicCPU


@dataclass
class WirePath:
    name: str
    points: list[tuple[float, float]]
    state_key: str
    line_id: int = 0

    @property
    def length(self) -> float:
        total = 0.0
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            total += math.hypot(x2 - x1, y2 - y1)
        return total

    def point_at(self, t: float) -> tuple[float, float]:
        if len(self.points) == 1:
            return self.points[0]
        t = t % 1.0
        target = self.length * t
        walked = 0.0
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            seg = math.hypot(x2 - x1, y2 - y1)
            if walked + seg >= target:
                local = (target - walked) / seg if seg > 0 else 0.0
                return (x1 + (x2 - x1) * local, y1 + (y2 - y1) * local)
            walked += seg
        return self.points[-1]


@dataclass
class Electron:
    wire_index: int
    t: float
    speed: float
    item_id: int = 0


@dataclass
class DetailWire:
    points: list[tuple[float, float]]
    state_key: str
    line_id: int = 0

    @property
    def length(self) -> float:
        total = 0.0
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            total += math.hypot(x2 - x1, y2 - y1)
        return total

    def point_at(self, t: float) -> tuple[float, float]:
        if len(self.points) == 1:
            return self.points[0]
        t = t % 1.0
        target = self.length * t
        walked = 0.0
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            seg = math.hypot(x2 - x1, y2 - y1)
            if walked + seg >= target:
                local = (target - walked) / seg if seg > 0 else 0.0
                return (x1 + (x2 - x1) * local, y1 + (y2 - y1) * local)
            walked += seg
        return self.points[-1]


@dataclass
class BlockInspector:
    key: str
    window: tk.Toplevel
    canvas: tk.Canvas
    status_label: tk.Label
    wires: list[DetailWire]
    particles: list[Electron]


class AttachedScreenApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("SoyuzOrbit: 100% Physical Transistor Model")
        self.root.geometry("1360x800")
        self.root.minsize(1200, 720)

        self.cpu = SimpleLogicCPU()
        self.electrical = ElectricalSystem(self.cpu)
        self.calculator = SpiceCalculatorTerminal()

        self.canvas = tk.Canvas(self.root, width=1360, height=800, bg="#0E1116", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.blocks: dict[str, int] = {}
        self.block_titles: dict[str, str] = {}
        self.block_subtitles: dict[str, str] = {}
        self.labels: dict[str, int] = {}
        self.wires: list[WirePath] = []
        self.electrons: list[Electron] = []
        self.inspectors: dict[str, BlockInspector] = {}

        self.current_var = tk.DoubleVar(value=self.electrical.power.available_current_a)
        self.electron_density_var = tk.DoubleVar(value=8.0)
        self.power_btn = ttk.Button(self.root, text="Power ON", command=self._toggle_power)
        self.current_scale = ttk.Scale(
            self.root,
            from_=0.0,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=self.current_var,
            command=self._on_current_change,
        )
        self.current_value_label = ttk.Label(self.root, text="")
        self.electron_scale = ttk.Scale(
            self.root,
            from_=1.0,
            to=20.0,
            orient=tk.HORIZONTAL,
            variable=self.electron_density_var,
            command=self._on_electron_density_change,
        )
        self.electron_value_label = ttk.Label(self.root, text="")

        self.monitor_frame = tk.Frame(self.root, bg="#05080C", bd=0, highlightthickness=2, highlightbackground="#3F8E5A")
        self.monitor_text = tk.Text(
            self.monitor_frame,
            bg="#05080C",
            fg="#91F39C",
            insertbackground="#91F39C",
            bd=0,
            wrap=tk.WORD,
            font=("Courier New", 11),
            state=tk.DISABLED,
        )
        self.input_frame = tk.Frame(self.monitor_frame, bg="#05080C")
        self.prompt_label = tk.Label(
            self.input_frame,
            text="",
            bg="#05080C",
            fg="#91F39C",
            font=("Courier New", 11),
            anchor="w",
        )
        self.input_entry = tk.Entry(
            self.input_frame,
            bg="#0A1118",
            fg="#91F39C",
            insertbackground="#91F39C",
            bd=0,
            font=("Courier New", 11),
            relief=tk.FLAT,
        )
        self.input_entry.bind("<Return>", self._on_submit_line)

        self.mem_frame = tk.Frame(self.root, bg="#0A1017", bd=0, highlightthickness=2, highlightbackground="#4D86C6")
        self.mem_text = tk.Text(
            self.mem_frame,
            bg="#0A1017",
            fg="#9FCAFF",
            insertbackground="#9FCAFF",
            bd=0,
            wrap=tk.NONE,
            font=("Courier New", 10),
            state=tk.DISABLED,
        )
        self.mem_scroll_y = ttk.Scrollbar(self.mem_frame, orient=tk.VERTICAL, command=self.mem_text.yview)
        self.mem_scroll_x = ttk.Scrollbar(self.mem_frame, orient=tk.HORIZONTAL, command=self.mem_text.xview)
        self.mem_text.configure(yscrollcommand=self.mem_scroll_y.set, xscrollcommand=self.mem_scroll_x.set)

        self._last_boot_state = False
        self._screen_online = False
        self._last_update_ms = 0

        self._build_scene()
        self._boot_screen_off_message()

    def _build_scene(self) -> None:
        self._draw_background()
        self._draw_wires()
        self._draw_blocks()
        self.canvas.tag_bind("block", "<Button-1>", self._on_block_click)
        self._spawn_electrons()
        self._place_controls()
        self._place_terminal_monitor()
        self._place_memory_monitor()
        self._update_prompt()

    def _draw_background(self) -> None:
        self.canvas.create_rectangle(0, 0, 1360, 800, fill="#0E1116", outline="")
        self.canvas.create_text(
            20,
            18,
            text="Физическая модель ПК (Transistor Level)",
            fill="#E7EDF5",
            anchor="w",
            font=("Arial", 15, "bold"),
        )
        self.labels["status"] = self.canvas.create_text(
            20, 44, text="", fill="#A9B4C0", anchor="w", font=("Arial", 11)
        )
        self.labels["cpu"] = self.canvas.create_text(
            20, 64, text="", fill="#A9B4C0", anchor="w", font=("Arial", 11)
        )
        self.canvas.create_text(
            20,
            84,
            text="Клик по блоку открывает внутреннюю схему с анимацией тока.",
            fill="#8FA5BF",
            anchor="w",
            font=("Arial", 10),
        )

    def _block(self, key: str, x1: int, y1: int, x2: int, y2: int, title: str, subtitle: str) -> None:
        block_tag = f"block:{key}"
        rid = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill="#1B2330",
            outline="#6D7D90",
            width=2,
            tags=("block", block_tag),
        )
        self.canvas.create_text(
            (x1 + x2) // 2,
            y1 + 18,
            text=title,
            fill="#E5ECF5",
            font=("Arial", 11, "bold"),
            tags=("block", block_tag),
        )
        self.canvas.create_text(
            (x1 + x2) // 2,
            y1 + 40,
            text=subtitle,
            fill="#A4B3C4",
            font=("Arial", 9),
            tags=("block", block_tag),
        )
        self.blocks[key] = rid
        self.block_titles[key] = title
        self.block_subtitles[key] = subtitle

    def _draw_blocks(self) -> None:
        self._block("psu", 40, 130, 190, 220, "PSU", "5V / ток")
        self._block("clock", 240, 95, 390, 165, "CLOCK", "тактовый генератор")
        self._block("ctrl", 240, 205, 390, 295, "CONTROL", "декодер команд")
        self._block("regs", 430, 95, 580, 175, "REGISTERS", "PC / ACC / IR")
        self._block("alu", 430, 205, 580, 295, "ALU", "сложение на логике")
        self._block("ram", 620, 205, 780, 295, "RAM", "оперативная память")
        self._block("hdd", 620, 325, 780, 405, "HDD", "долговременное хранилище")
        self._block("mmio", 620, 95, 780, 175, "MMIO UART", "терминалный интерфейс")

        self.canvas.create_text(
            830, 26, text="Подключенный экран", fill="#D4E8D8", anchor="w", font=("Arial", 11, "bold")
        )
        self.canvas.create_rectangle(820, 40, 1320, 740, outline="#3F8E5A", width=3, fill="#101A14")

        self.canvas.create_rectangle(20, 430, 800, 790, outline="#4D86C6", width=3, fill="#101722")

    def _draw_wires(self) -> None:
        self.wires = [
            WirePath(
                "Power bus",
                [(190, 175), (220, 175), (220, 420), (800, 420), (800, 110), (820, 110)],
                "power_bus",
            ),
            WirePath("Clock line", [(390, 130), (410, 130), (410, 250), (240, 250)], "clock_line"),
            WirePath("Control line", [(390, 250), (430, 250), (430, 250)], "control_line"),
            WirePath("ALU bus", [(580, 250), (620, 250), (620, 130), (620, 130)], "alu_bus"),
            WirePath("Memory bus", [(780, 250), (810, 250), (810, 235), (390, 235)], "memory_bus"),
            WirePath("RAM line", [(580, 250), (620, 250), (620, 250)], "ram_line"),
            WirePath("HDD line", [(700, 295), (700, 325), (700, 325)], "hdd_line"),
            WirePath("Video line", [(780, 130), (820, 130), (820, 390)], "video_line"),
            WirePath("RAM screen line", [(700, 295), (700, 430), (410, 430), (410, 440)], "ram_screen_line"),
        ]

        for wire in self.wires:
            wire.line_id = self.canvas.create_line(
                *self._flatten(wire.points),
                fill="#3F4B59",
                width=4,
                smooth=False,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

    @staticmethod
    def _flatten(points: list[tuple[float, float]]) -> list[float]:
        out: list[float] = []
        for x, y in points:
            out.extend([x, y])
        return out

    def _spawn_electrons(self) -> None:
        random.seed(42)
        for particle in self.electrons:
            self.canvas.delete(particle.item_id)
        self.electrons.clear()
        per_wire = max(1, min(20, int(round(self.electron_density_var.get()))))
        for wire_idx, _wire in enumerate(self.wires):
            for _ in range(per_wire):
                t = random.random()
                speed = random.uniform(0.08, 0.26)
                particle = Electron(wire_index=wire_idx, t=t, speed=speed)
                x, y = self.wires[wire_idx].point_at(t)
                particle.item_id = self.canvas.create_oval(
                    x - 2.2, y - 2.2, x + 2.2, y + 2.2, outline="", fill="#9DD7FF"
                )
                self.electrons.append(particle)

    def _place_controls(self) -> None:
        self.canvas.create_window(430, 26, window=self.power_btn, anchor="w")
        self.canvas.create_text(522, 26, text="Ток (A):", fill="#CED9E5", anchor="w", font=("Arial", 10))
        self.canvas.create_window(580, 26, window=self.current_scale, anchor="w", width=210)
        self.canvas.create_window(804, 26, window=self.current_value_label, anchor="w")
        self.canvas.create_text(930, 26, text="Эл/провод:", fill="#CED9E5", anchor="w", font=("Arial", 10))
        self.canvas.create_window(1010, 26, window=self.electron_scale, anchor="w", width=150)
        self.canvas.create_window(1170, 26, window=self.electron_value_label, anchor="w")
        self.current_value_label.configure(
            text=f"{self.current_var.get():.2f} A / нужно >= {self.electrical.power.required_current_a:.2f} A"
        )
        self.electron_value_label.configure(text=f"{int(round(self.electron_density_var.get()))} шт/провод")

    def _place_terminal_monitor(self) -> None:
        self.monitor_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 4))
        self.input_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.prompt_label.pack(side=tk.LEFT)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self.canvas.create_window(830, 60, window=self.monitor_frame, anchor="nw", width=480, height=660)

    def _place_memory_monitor(self) -> None:
        self.mem_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)
        self.mem_scroll_x.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))
        self.mem_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(8, 0))
        self.canvas.create_window(30, 440, window=self.mem_frame, anchor="nw", width=760, height=340)

    def _toggle_power(self) -> None:
        self.electrical.toggle_power()
        self.power_btn.configure(text="Power OFF" if self.electrical.power_switch_on else "Power ON")

    def _on_current_change(self, _value: str) -> None:
        value = self.current_var.get()
        self.electrical.set_available_current(value)
        self.current_value_label.configure(
            text=f"{value:.2f} A / нужно >= {self.electrical.power.required_current_a:.2f} A"
        )

    def _on_electron_density_change(self, _value: str) -> None:
        self.electron_value_label.configure(text=f"{int(round(self.electron_density_var.get()))} шт/провод")
        self._spawn_electrons()

    def _set_entry_enabled(self, enabled: bool) -> None:
        if enabled:
            self.input_entry.configure(state=tk.NORMAL)
            self.input_entry.focus_set()
        else:
            self.input_entry.configure(state=tk.DISABLED)
        self.input_entry.configure(show="")

    def _append_line(self, text: str) -> None:
        self.monitor_text.configure(state=tk.NORMAL)
        self.monitor_text.insert(tk.END, text + "\n")
        self.monitor_text.configure(state=tk.DISABLED)
        self.monitor_text.see(tk.END)

    def _clear_screen(self) -> None:
        self.monitor_text.configure(state=tk.NORMAL)
        self.monitor_text.delete("1.0", tk.END)
        self.monitor_text.configure(state=tk.DISABLED)

    def _render_memory_screen(self) -> None:
        lines = self.electrical.memory_screen_lines()
        self.mem_text.configure(state=tk.NORMAL)
        self.mem_text.delete("1.0", tk.END)
        self.mem_text.insert("1.0", "\n".join(lines) + "\n")
        self.mem_text.configure(state=tk.DISABLED)

    def _update_prompt(self) -> None:
        self.prompt_label.configure(text=self.calculator.prompt)
        self.input_entry.configure(show="")

    def _boot_screen_off_message(self) -> None:
        self._clear_screen()
        self._append_line("Экран подключен к MMIO-UART.")
        self._append_line("Режим: SPICE-PC калькулятор.")
        self._append_line("Ожидание питания и достаточного тока...")
        self._set_entry_enabled(False)
        self._render_memory_screen()

    def _boot_calculator_online(self) -> None:
        self._clear_screen()
        self.calculator.reset_session()
        for line in self.calculator.boot_lines:
            self._append_line(line)
        self._update_prompt()
        self._set_entry_enabled(True)
        self._screen_online = True

    def _shutdown_calculator(self) -> None:
        if self._screen_online:
            self._append_line("[Сигнал потерян: питание/ток недостаточны]")
        self._set_entry_enabled(False)
        self._screen_online = False
        self._render_memory_screen()

    def _on_submit_line(self, _event: tk.Event[tk.Misc]) -> str:
        if not self.electrical.boot_ready:
            return "break"

        raw = self.input_entry.get()
        self.input_entry.delete(0, tk.END)

        self._append_line(f"{self.calculator.prompt}{raw}")
        # Force UI update before calculation to show the prompt
        self.root.update_idletasks()

        for line in self.calculator.handle_line(raw):
            self._append_line(line)

        self._update_prompt()
        self._set_entry_enabled(True)
        return "break"

    def _update_visuals(self, dt: float) -> None:
        for wire in self.wires:
            active = self.electrical.wire_states.get(wire.state_key, False)
            color = "#4A5564"
            if active:
                color = "#56D882" if wire.state_key != "clock_line" else "#FFD166"
            self.canvas.itemconfigure(wire.line_id, fill=color)

        for particle in self.electrons:
            wire = self.wires[particle.wire_index]
            active = self.electrical.wire_states.get(wire.state_key, False)
            if active:
                particle.t = (particle.t + particle.speed * dt) % 1.0
                x, y = wire.point_at(particle.t)
                self.canvas.coords(particle.item_id, x - 2.2, y - 2.2, x + 2.2, y + 2.2)
                self.canvas.itemconfigure(particle.item_id, state=tk.NORMAL)
            else:
                self.canvas.itemconfigure(particle.item_id, state=tk.HIDDEN)

        self._update_status_labels()
        self._highlight_active_blocks()
        self._render_memory_screen()

    def _update_status_labels(self) -> None:
        status = (
            f"V={self.electrical.power.voltage_v:.2f}V  "
            f"I={self.electrical.power.available_current_a:.2f}A  "
            f"boot={'YES' if self.electrical.boot_ready else 'NO'}  "
            f"| {self.electrical.power_message}"
        )
        self.canvas.itemconfigure(self.labels["status"], text=status)

        cpu_txt = (
            f"CPU: phase={self.cpu.phase}  PC={self.cpu.pc.value:02X}  "
            f"ACC={self.cpu.acc.value:02X}  IR={self.cpu.ir.value:02X}  "
            f"cycles={self.cpu.cycle_count}"
        )
        self.canvas.itemconfigure(self.labels["cpu"], text=cpu_txt)

    def _detail_active(self, state_key: str) -> bool:
        return self.electrical.wire_states.get(state_key, False) and self.electrical.boot_ready

    def _block_spec(self, key: str) -> tuple[str, list[tuple[str, int, int, int, int]], list[DetailWire]]:
        title = self.block_titles.get(key, key.upper())
        if key == "psu":
            comps = [("Fuse", 30, 80, 140, 130), ("Regulator", 200, 80, 340, 130), ("Filter C", 400, 80, 510, 130)]
            wires = [DetailWire([(10, 170), (540, 170)], "power_bus")]
            return title, comps, wires
        if key == "clock":
            comps = [("RC node", 40, 70, 150, 120), ("Schmitt inv", 200, 70, 320, 120), ("Divider", 380, 70, 510, 120)]
            wires = [DetailWire([(20, 170), (540, 170)], "clock_line")]
            return title, comps, wires
        if key == "ctrl":
            comps = [("Instr decode", 40, 70, 170, 130), ("Mux", 220, 70, 320, 130), ("Control ROM", 370, 70, 520, 130)]
            wires = [DetailWire([(20, 170), (540, 170)], "control_line")]
            return title, comps, wires
        if key == "alu":
            comps = [("XOR", 40, 70, 140, 130), ("Full adder", 200, 70, 330, 130), ("Flags", 390, 70, 510, 130)]
            wires = [DetailWire([(20, 170), (540, 170)], "alu_bus")]
            return title, comps, wires
        if key == "regs":
            comps = [("PC reg", 40, 70, 150, 130), ("ACC reg", 200, 70, 320, 130), ("IR reg", 370, 70, 500, 130)]
            wires = [DetailWire([(20, 170), (540, 170)], "memory_bus")]
            return title, comps, wires
        if key == "ram":
            comps = [("Addr latch", 40, 60, 170, 120), ("Cell array", 220, 45, 360, 145), ("Sense amp", 410, 60, 520, 120)]
            wires = [DetailWire([(20, 170), (540, 170)], "ram_line")]
            return title, comps, wires
        if key == "hdd":
            comps = [("Controller", 40, 70, 170, 130), ("Sector cache", 220, 70, 360, 130), ("Platter model", 410, 55, 520, 145)]
            wires = [DetailWire([(20, 170), (540, 170)], "hdd_line")]
            return title, comps, wires
        comps = [("UART RX/TX", 40, 70, 190, 130), ("MMIO regs", 240, 70, 390, 130), ("IRQ line", 430, 70, 520, 130)]
        wires = [DetailWire([(20, 170), (540, 170)], "video_line")]
        return title, comps, wires

    def _on_block_click(self, event: tk.Event[tk.Misc]) -> None:
        item_id = self.canvas.find_withtag("current")
        if not item_id:
            return
        tags = self.canvas.gettags(item_id[0])
        block_key = ""
        for tag in tags:
            if tag.startswith("block:"):
                block_key = tag.split(":", 1)[1]
                break
        if block_key:
            self._open_block_inspector(block_key, event.x_root + 10, event.y_root + 10)

    def _open_block_inspector(self, key: str, x: int, y: int) -> None:
        existing = self.inspectors.get(key)
        if existing is not None and existing.window.winfo_exists():
            existing.window.lift()
            existing.window.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title(f"{self.block_titles.get(key, key)}: internal view")
        win.geometry(f"580x300+{x}+{y}")
        win.configure(bg="#11161E")

        title, components, wires = self._block_spec(key)
        canvas = tk.Canvas(win, width=560, height=220, bg="#0F141B", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        status = tk.Label(win, text="", bg="#11161E", fg="#B7C4D4", anchor="w")
        status.pack(fill=tk.X, padx=10, pady=(0, 8))

        canvas.create_text(10, 12, text=title, anchor="w", fill="#E7EDF5", font=("Arial", 12, "bold"))
        canvas.create_text(
            10,
            30,
            text=self.block_subtitles.get(key, ""),
            anchor="w",
            fill="#95A6BA",
            font=("Arial", 9),
        )

        detail_particles: list[Electron] = []
        for w in wires:
            w.line_id = canvas.create_line(
                *self._flatten(w.points),
                fill="#4A5564",
                width=4,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
            for _ in range(6):
                t = random.random()
                p = Electron(wire_index=len(detail_particles), t=t, speed=random.uniform(0.08, 0.2))
                x0, y0 = w.point_at(t)
                p.item_id = canvas.create_oval(x0 - 2.0, y0 - 2.0, x0 + 2.0, y0 + 2.0, outline="", fill="#A1D9FF")
                detail_particles.append(p)

        for name, x1, y1, x2, y2 in components:
            canvas.create_rectangle(x1, y1, x2, y2, fill="#1D2631", outline="#6B7C90", width=2)
            canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=name, fill="#DCE7F3", font=("Arial", 9))

        inspector = BlockInspector(
            key=key,
            window=win,
            canvas=canvas,
            status_label=status,
            wires=wires,
            particles=detail_particles,
        )

        def _on_close() -> None:
            if key in self.inspectors:
                del self.inspectors[key]
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_close)
        self.inspectors[key] = inspector

    def _update_inspectors(self, dt: float) -> None:
        dead: list[str] = []
        for key, inspector in self.inspectors.items():
            if not inspector.window.winfo_exists():
                dead.append(key)
                continue

            active_count = 0
            particle_idx = 0
            for wire in inspector.wires:
                active = self._detail_active(wire.state_key)
                if active:
                    active_count += 1
                inspector.canvas.itemconfigure(wire.line_id, fill="#57D583" if active else "#4A5564")

                for _ in range(6):
                    particle = inspector.particles[particle_idx]
                    if active:
                        particle.t = (particle.t + particle.speed * dt) % 1.0
                        x0, y0 = wire.point_at(particle.t)
                        inspector.canvas.coords(particle.item_id, x0 - 2.0, y0 - 2.0, x0 + 2.0, y0 + 2.0)
                        inspector.canvas.itemconfigure(particle.item_id, state=tk.NORMAL)
                    else:
                        inspector.canvas.itemconfigure(particle.item_id, state=tk.HIDDEN)
                    particle_idx += 1

            inspector.status_label.configure(
                text=(
                    f"Power={self.electrical.power_switch_on}  "
                    f"Boot={self.electrical.boot_ready}  "
                    f"Active wires={active_count}/{len(inspector.wires)}"
                )
            )

        for key in dead:
            del self.inspectors[key]

    def _highlight_active_blocks(self) -> None:
        base = "#1B2330"
        active = "#2E3E54"
        offline = "#242931"

        for block in self.blocks.values():
            self.canvas.itemconfigure(block, fill=base)

        if not self.electrical.power_switch_on:
            for block in self.blocks.values():
                self.canvas.itemconfigure(block, fill=offline)
            return

        self.canvas.itemconfigure(self.blocks["psu"], fill=active)

        if not self.electrical.boot_ready:
            return

        self.canvas.itemconfigure(self.blocks["clock"], fill=active)
        phase = self.cpu.phase
        if phase in {"FETCH", "DECODE"}:
            self.canvas.itemconfigure(self.blocks["ctrl"], fill=active)
            self.canvas.itemconfigure(self.blocks["ram"], fill=active)
        elif phase == "EXECUTE":
            self.canvas.itemconfigure(self.blocks["alu"], fill=active)
            self.canvas.itemconfigure(self.blocks["regs"], fill=active)
        elif phase == "WRITEBACK":
            self.canvas.itemconfigure(self.blocks["regs"], fill=active)
            self.canvas.itemconfigure(self.blocks["ram"], fill=active)

        if self.electrical.wire_states.get("ram_line"):
            self.canvas.itemconfigure(self.blocks["ram"], fill=active)
        if self.electrical.wire_states.get("hdd_line"):
            self.canvas.itemconfigure(self.blocks["hdd"], fill=active)

        self.canvas.itemconfigure(self.blocks["mmio"], fill=active)

    def _tick(self) -> None:
        now_ms = int(self.root.tk.call("clock", "milliseconds"))
        if self._last_update_ms == 0:
            dt = 0.03
        else:
            dt = max(0.005, min(0.08, (now_ms - self._last_update_ms) / 1000.0))
        self._last_update_ms = now_ms

        self.electrical.update(dt)
        boot = self.electrical.boot_ready

        if boot and not self._last_boot_state:
            self._boot_calculator_online()
        elif not boot and self._last_boot_state:
            self._shutdown_calculator()

        if not self.electrical.power_switch_on and not self._screen_online:
            self._boot_screen_off_message()

        self._last_boot_state = boot

        if not boot:
            self.input_entry.configure(state=tk.DISABLED)

        self._update_visuals(dt)
        self._update_inspectors(dt)
        self.root.after(33, self._tick)

    def run(self) -> None:
        self._tick()
        self.root.mainloop()
