"""Simple calculator terminal powered by transistor-level adder blocks."""

from __future__ import annotations

import re
import time
from typing import List

from simulation.physical_cpu import RippleCarryAdder8
from simulation.full_physical_cpu import FullPhysicalCPU, Instruction
from simulation.assembler import assemble


class SpiceCalculatorTerminal:
    PROMPT_CALC = "phys-calc> "
    PROMPT_CPU = "phys-cpu> "
    PROMPT_INPUT = "input?> "

    def __init__(self) -> None:
        self._boot_lines = [
            "PHYSICAL TRANSISTOR ENGINE ONLINE.",
            "Система работает на эмуляции полевых транзисторов (SPICE-lite).",
            "Доступные режимы:",
            "  calc - Калькулятор (A+B)",
            "  cpu  - Программируемый процессор (ASM)",
            "Введите 'cpu' для перехода в режим процессора.",
        ]
        self.adder_low = RippleCarryAdder8()
        self.adder_high = RippleCarryAdder8()
        
        self.cpu = FullPhysicalCPU()
        self.mode = "calc"
        self.cpu_program_buffer: List[str] = []
        self.cpu_output_buffer: List[str] = []
        
        # Register I/O Ports
        # Port 1: Console Output
        self.cpu.register_io_port(1, self._port_out_handler)

    def _port_out_handler(self, value: int, mode: str):
        if mode == 'write':
            self.cpu_output_buffer.append(f"OUTPUT [Port 1]: {value} (0x{value:02X})")

    @property
    def boot_lines(self) -> list[str]:
        return list(self._boot_lines)

    @property
    def prompt(self) -> str:
        if self.cpu.is_waiting_for_input:
            return self.PROMPT_INPUT
        return self.PROMPT_CPU if self.mode == "cpu" else self.PROMPT_CALC

    def reset_session(self) -> None:
        self.mode = "calc"
        self.cpu_program_buffer = []
        self.cpu.reset()

    def handle_line(self, line: str) -> list[str]:
        text = line.strip()
        
        # Special handling for Input Wait state
        if self.cpu.is_waiting_for_input:
            try:
                val = int(text)
                self.cpu.provide_input(val)
                return self._resume_cpu_execution()
            except ValueError:
                return ["Ошибка: Введите число."]

        if not text:
            return []

        low = text.lower()
        
        if low == "calc":
            self.mode = "calc"
            return ["Режим: Калькулятор."]
        if low == "cpu":
            self.mode = "cpu"
            self.cpu_program_buffer = []
            return [
                "Режим: Процессор.",
                "Введите программу на ассемблере.",
                "Команды: run, list, clear, calc",
                "Новые инструкции: OUT <port>, IN <port>",
                "Пример I/O:",
                "  IN 2    ; Читать из порта 2 в A",
                "  ADD     ; A = A + B (B=0)",
                "  OUT 1   ; Вывести A в порт 1",
                "  HALT"
            ]

        if self.mode == "cpu":
            return self._handle_cpu_command(text)
        else:
            return self._handle_calc_command(text)

    def _handle_calc_command(self, text: str) -> list[str]:
        low = text.lower()
        if low in {"help", "?"}:
            return ["Формат: A+B", "Команды: cpu"]

        match = re.fullmatch(r"(\d+)\s*\+\s*(\d+)", text)
        if match is None:
            return ["Ошибка: поддерживается только сложение в формате A+B."]

        left = int(match.group(1))
        right = int(match.group(2))
        
        if left > 65535 or right > 65535:
             return ["Ошибка: числа слишком большие."]

        start_t = time.time()
        result = self._add_16bit_physical(left, right)
        dt = time.time() - start_t
        
        return [f"Результат: {left} + {right} = {result}", f"[Физика: {dt*1000:.1f} ms]"]

    def _handle_cpu_command(self, text: str) -> list[str]:
        low = text.lower()
        
        if low == "run":
            if not self.cpu_program_buffer:
                return ["Ошибка: Программа пуста."]
            
            code = "\n".join(self.cpu_program_buffer)
            program, errors = assemble(code)
            
            if errors:
                return ["Ошибки сборки:"] + errors
            
            self.cpu.load_program(program)
            return self._resume_cpu_execution()

        elif low == "list":
            return [f"{i+1}: {line}" for i, line in enumerate(self.cpu_program_buffer)]

        elif low == "clear":
            self.cpu_program_buffer = []
            return ["Программа очищена."]
            
        else:
            self.cpu_program_buffer.append(text)
            return [f"{len(self.cpu_program_buffer)}: {text}"]

    def _resume_cpu_execution(self) -> list[str]:
        output = ["--- CPU RUNNING ---"]
        self.cpu_output_buffer = [] # Clear previous output
        
        cycles = 0
        max_cycles = 50 # Increased limit
        
        while not self.cpu.halted and not self.cpu.is_waiting_for_input and cycles < max_cycles:
            self.cpu.tick()
            cycles += 1
            # Optional: Add trace to output if needed, but it might be too verbose
            # output.append(f"T{cycles}: {self.cpu.get_state_str()}")
        
        # Append any I/O output generated during execution
        output.extend(self.cpu_output_buffer)
        
        if self.cpu.is_waiting_for_input:
            output.append(f"CPU PAUSED: Waiting for input on Port {self.cpu.input_port}...")
            return output
            
        if self.cpu.halted:
            output.append("CPU HALTED.")
        else:
            output.append("CPU STOPPED (Max cycles reached).")
            
        output.append(f"Final State: {self.cpu.get_state_str()}")
        return output

    def _add_16bit_physical(self, left: int, right: int) -> int:
        left_low = left & 0xFF; left_high = (left >> 8) & 0xFF
        right_low = right & 0xFF; right_high = (right >> 8) & 0xFF
        sum_low, carry_low = self.adder_low.add(left_low, right_low, c_in=0)
        sum_high, carry_high = self.adder_high.add(left_high, right_high, c_in=carry_low)
        return (sum_high << 8) | sum_low
