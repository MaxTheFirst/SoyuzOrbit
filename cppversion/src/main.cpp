#include <iostream>
#include <vector>
#include <array>
#include "Circuit.h"
#include "Cpu.h"

// --- Глобальные переменные ---
Circuit g_circuit;
Cpu* g_cpu;

// --- Вспомогательные функции ---
void tick() {
    g_cpu->clk->forced_voltage = 5.0;
    g_cpu->clk->voltage = 5.0;
    g_circuit.simulate_step(0.001);
    g_cpu->clk->forced_voltage = 0.0;
    g_cpu->clk->voltage = 0.0;
    g_circuit.simulate_step(0.001);
}

int read_nibble(const std::vector<Node*>& lines) {
    int value = 0;
    for (int i = 0; i < 4; ++i) {
        if (lines[i]->voltage > 2.5) {
            value |= (1 << i);
        }
    }
    return value;
}

// --- Основной цикл ---
int main() {
    g_circuit.set_solver(std::make_unique<IterativeSolver>());
    const std::array<int, 4> boot_program = {1, 5, 15, 0}; // LOAD_A 5; HALT
    g_cpu = new Cpu(g_circuit, boot_program);

    // Power-on reset: несколько тактов держим reset=1, затем отпускаем.
    tick();
    tick();
    g_cpu->reset->forced_voltage = 0.0;
    g_cpu->reset->voltage = 0.0;
    g_circuit.simulate_step(0.001);
    std::cout << "INIT: PC bits = "
              << g_cpu->pc_out[3]->voltage << ","
              << g_cpu->pc_out[2]->voltage << ","
              << g_cpu->pc_out[1]->voltage << ","
              << g_cpu->pc_out[0]->voltage
              << " | MICRO bits = "
              << g_cpu->micro_out[3]->voltage << ","
              << g_cpu->micro_out[2]->voltage << ","
              << g_cpu->micro_out[1]->voltage << ","
              << g_cpu->micro_out[0]->voltage
              << std::endl;

    std::cout << "--- Hardware-Controlled CPU Simulation ---" << std::endl;
    std::cout << "Program: RAM[0]=LOAD_A, RAM[1]=5, RAM[2]=HALT" << std::endl;

    const int max_cycles = 12;
    bool seen_halt = false;

    for (int cycle = 0; cycle < max_cycles; ++cycle) {
        tick();

        int phase = ((g_cpu->micro_out[1]->voltage > 2.5) ? 2 : 0) |
                    ((g_cpu->micro_out[0]->voltage > 2.5) ? 1 : 0);
        int pc = read_nibble(g_cpu->pc_out);
        int ir = read_nibble(g_cpu->ir_out);
        int reg_a = read_nibble(g_cpu->reg_a_out);
        int micro_next = read_nibble(g_cpu->micro_next_dbg);

        std::cout << "[CYCLE " << cycle << "]"
                  << " PHASE=" << phase
                  << " MICRO_NEXT=" << micro_next
                  << " PC=" << pc
                  << " IR=" << ir
                  << " A=" << reg_a
                  << std::endl;

        if (g_cpu->halted->voltage > 2.5) {
            seen_halt = true;
            std::cout << "[HALT] Hardware halt signal asserted." << std::endl;
            break;
        }
    }

    if (!seen_halt) {
        std::cout << "[WARN] HALT was not observed within " << max_cycles << " cycles." << std::endl;
    }

    std::cout << "CPU simulation finished." << std::endl;
    delete g_cpu;
    return 0;
}
