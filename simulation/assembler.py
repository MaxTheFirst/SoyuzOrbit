"""
A simple assembler for the FullPhysicalCPU's instruction set.
Supports: MOV, ADD, HALT, OUT, IN.
"""

from typing import List, Tuple
from simulation.full_physical_cpu import Instruction

# Opcodes mapping
OPCODES = {
    "MOV": {"A": 1, "B": 2},
    "ADD": 3,
    "OUT": 4, # New: Output Reg A to Port
    "IN":  5, # New: Input from Port to Reg A
    "HALT": 0,
}

def assemble(code: str) -> Tuple[List[Instruction], List[str]]:
    """
    Assembles a string of assembly code into a list of Instructions.
    Returns the program and a list of any errors.
    """
    program: List[Instruction] = []
    errors: List[str] = []
    lines = code.strip().split('\n')

    for i, line in enumerate(lines):
        line_num = i + 1
        line = line.strip().upper()
        if not line or line.startswith(';'):
            continue

        parts = line.replace(',', ' ').split()
        mnemonic = parts[0]

        if mnemonic == "MOV":
            if len(parts) != 3:
                errors.append(f"L{line_num}: MOV expects 2 arguments (e.g., MOV A, 5)")
                continue
            reg = parts[1]
            try:
                val = int(parts[2])
                if reg in OPCODES["MOV"]:
                    program.append(Instruction(OPCODES["MOV"][reg], val))
                else:
                    errors.append(f"L{line_num}: Invalid register for MOV: {reg}")
            except ValueError:
                errors.append(f"L{line_num}: Invalid value for MOV: {parts[2]}")

        elif mnemonic == "ADD":
            if len(parts) != 1:
                errors.append(f"L{line_num}: ADD expects 0 arguments")
                continue
            program.append(Instruction(OPCODES["ADD"], 0))

        elif mnemonic == "OUT":
            if len(parts) != 2:
                errors.append(f"L{line_num}: OUT expects 1 argument (Port #)")
                continue
            try:
                port = int(parts[1])
                program.append(Instruction(OPCODES["OUT"], port))
            except ValueError:
                errors.append(f"L{line_num}: Invalid port number: {parts[1]}")

        elif mnemonic == "IN":
            if len(parts) != 2:
                errors.append(f"L{line_num}: IN expects 1 argument (Port #)")
                continue
            try:
                port = int(parts[1])
                program.append(Instruction(OPCODES["IN"], port))
            except ValueError:
                errors.append(f"L{line_num}: Invalid port number: {parts[1]}")

        elif mnemonic == "HALT":
            if len(parts) != 1:
                errors.append(f"L{line_num}: HALT expects 0 arguments")
                continue
            program.append(Instruction(OPCODES["HALT"], 0))
            
        else:
            errors.append(f"L{line_num}: Unknown instruction '{mnemonic}'")

    return program, errors
