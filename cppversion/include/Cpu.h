#ifndef CPU_H
#define CPU_H

#include "Register4Bit.h"
#include "Alu4Bit.h"
#include "Ram4x4.h"
#include "Circuit.h"
#include <array>

class Cpu {
public:
    // Компоненты
    Register4Bit* pc;
    Register4Bit* ir;
    Register4Bit* reg_a;
    Register4Bit* reg_b;
    Register4Bit* micro_counter;
    Alu4Bit* alu;
    Ram4x4* ram;

    // Узлы
    Node* vdd;
    Node* gnd;
    Node* clk;
    Node* reset;
    Node* halted;

    // Шины
    std::vector<Node*> bus;
    std::vector<Node*> bus_bar;
    std::vector<Node*> pc_out;
    std::vector<Node*> ir_out;
    std::vector<Node*> reg_a_out;
    std::vector<Node*> reg_b_out;
    std::vector<Node*> alu_out;
    std::vector<Node*> ram_data;
    std::vector<Node*> ram_data_bar;
    std::vector<Node*> micro_out;
    std::vector<Node*> micro_next_dbg;

    // Управляющие сигналы
    Node* pc_write_enable;
    Node* ir_write_enable;
    Node* reg_a_write_enable;
    Node* reg_b_write_enable;
    Node* ram_write_enable;
    Node* alu_op_sel;

    // Сигналы выбора выхода на шину (в реальности это tri-state buffers)
    Node* pc_out_enable;
    Node* ram_out_enable;
    Node* alu_out_enable;

    Cpu(Circuit& circuit, std::array<int, 4> boot_program = {1, 5, 15, 0});
};

#endif // CPU_H
