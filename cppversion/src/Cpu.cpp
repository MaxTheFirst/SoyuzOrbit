#include "Cpu.h"
#include "AndGate.h"
#include "Inverter.h"
#include "Nmos.h"
#include "OrGate.h"
#include "TriStateBuffer.h"
#include "XorGate.h"

Cpu::Cpu(Circuit& circuit, std::array<int, 4> boot_program) {
    // Узлы питания и тактирования
    vdd = circuit.create_node();
    gnd = circuit.create_node();
    clk = circuit.create_node();
    reset = circuit.create_node();

    vdd->is_forced = true;
    vdd->forced_voltage = 5.0;
    vdd->voltage = 5.0;

    gnd->is_forced = true;
    gnd->forced_voltage = 0.0;
    gnd->voltage = 0.0;
    gnd->is_ground = true;

    clk->is_forced = true;
    clk->forced_voltage = 0.0;
    clk->voltage = 0.0;

    reset->is_forced = true;
    reset->forced_voltage = 5.0;
    reset->voltage = 5.0;

    // Шины и внутренние группы сигналов
    bus.resize(4);
    bus_bar.resize(4);
    pc_out.resize(4);
    ir_out.resize(4);
    reg_a_out.resize(4);
    reg_b_out.resize(4);
    alu_out.resize(4);
    ram_data.resize(4);
    ram_data_bar.resize(4);
    micro_out.resize(4);

    std::vector<Node*> pc_next(4);
    std::vector<Node*> micro_next(4);
    std::vector<Node*> const_zero(4);
    micro_next_dbg.resize(4);

    for (int i = 0; i < 4; ++i) {
        bus[i] = circuit.create_node();
        bus_bar[i] = circuit.create_node();
        pc_out[i] = circuit.create_node();
        ir_out[i] = circuit.create_node();
        reg_a_out[i] = circuit.create_node();
        reg_b_out[i] = circuit.create_node();
        alu_out[i] = circuit.create_node();
        ram_data[i] = circuit.create_node();
        ram_data_bar[i] = circuit.create_node();
        micro_out[i] = circuit.create_node();
        pc_next[i] = circuit.create_node();
        micro_next[i] = circuit.create_node();
        micro_next_dbg[i] = micro_next[i];

        const_zero[i] = circuit.create_node();
        const_zero[i]->is_forced = true;
        const_zero[i]->forced_voltage = 0.0;
        const_zero[i]->voltage = 0.0;

        Inverter inv_bus(bus[i], bus_bar[i], vdd, gnd);
        inv_bus.build(circuit);

        // Аппаратный reset: при reset=1 принудительно тянем ключевые регистры к 0.
        circuit.add_component(new Nmos(pc_out[i], gnd, reset, 0.5, 0.01));
        circuit.add_component(new Nmos(ir_out[i], gnd, reset, 0.5, 0.01));
        circuit.add_component(new Nmos(reg_a_out[i], gnd, reset, 0.5, 0.01));
        circuit.add_component(new Nmos(reg_b_out[i], gnd, reset, 0.5, 0.01));
        circuit.add_component(new Nmos(micro_out[i], gnd, reset, 0.5, 0.01));
    }

    // Декодер микрофаз (T0/T1/T2)
    Node* not_m0 = circuit.create_node();
    Node* not_m1 = circuit.create_node();
    Inverter inv_m0(micro_out[0], not_m0, vdd, gnd);
    inv_m0.build(circuit);
    Inverter inv_m1(micro_out[1], not_m1, vdd, gnd);
    inv_m1.build(circuit);

    Node* phase0 = circuit.create_node();
    Node* phase1 = circuit.create_node();
    Node* phase2 = circuit.create_node();
    AndGate phase0_gate(not_m1, not_m0, phase0, vdd, gnd);
    phase0_gate.build(circuit);
    AndGate phase1_gate(not_m1, micro_out[0], phase1, vdd, gnd);
    phase1_gate.build(circuit);
    AndGate phase2_gate(micro_out[1], not_m0, phase2, vdd, gnd);
    phase2_gate.build(circuit);

    // Декодирование opcode в IR
    Node* not_i0 = circuit.create_node();
    Node* not_i1 = circuit.create_node();
    Node* not_i2 = circuit.create_node();
    Node* not_i3 = circuit.create_node();
    Inverter inv_i0(ir_out[0], not_i0, vdd, gnd);
    inv_i0.build(circuit);
    Inverter inv_i1(ir_out[1], not_i1, vdd, gnd);
    inv_i1.build(circuit);
    Inverter inv_i2(ir_out[2], not_i2, vdd, gnd);
    inv_i2.build(circuit);
    Inverter inv_i3(ir_out[3], not_i3, vdd, gnd);
    inv_i3.build(circuit);

    Node* load_left = circuit.create_node();
    Node* load_right = circuit.create_node();
    Node* is_load_a = circuit.create_node();
    AndGate load_left_gate(not_i3, not_i2, load_left, vdd, gnd);
    load_left_gate.build(circuit);
    AndGate load_right_gate(not_i1, ir_out[0], load_right, vdd, gnd);
    load_right_gate.build(circuit);
    AndGate load_gate(load_left, load_right, is_load_a, vdd, gnd);
    load_gate.build(circuit);

    Node* halt_left = circuit.create_node();
    Node* halt_right = circuit.create_node();
    Node* is_halt = circuit.create_node();
    AndGate halt_left_gate(ir_out[3], ir_out[2], halt_left, vdd, gnd);
    halt_left_gate.build(circuit);
    AndGate halt_right_gate(ir_out[1], ir_out[0], halt_right, vdd, gnd);
    halt_right_gate.build(circuit);
    AndGate halt_gate(halt_left, halt_right, is_halt, vdd, gnd);
    halt_gate.build(circuit);

    // Управляющая логика
    ir_write_enable = phase0;

    reg_a_write_enable = circuit.create_node();
    AndGate rega_we_gate(phase1, is_load_a, reg_a_write_enable, vdd, gnd);
    rega_we_gate.build(circuit);

    Node* pc_we_raw = circuit.create_node();
    OrGate pc_we_gate(phase0, reg_a_write_enable, pc_we_raw, vdd, gnd);
    pc_we_gate.build(circuit);
    pc_write_enable = circuit.create_node();
    OrGate pc_we_with_reset(pc_we_raw, reset, pc_write_enable, vdd, gnd);
    pc_we_with_reset.build(circuit);

    ram_out_enable = circuit.create_node();
    OrGate ram_oe_gate(phase0, reg_a_write_enable, ram_out_enable, vdd, gnd);
    ram_oe_gate.build(circuit);

    halted = circuit.create_node();
    AndGate halted_gate(phase2, is_halt, halted, vdd, gnd);
    halted_gate.build(circuit);

    // Невостребованные в текущем микрокоде сигналы
    reg_b_write_enable = gnd;
    ram_write_enable = gnd;
    alu_op_sel = gnd;
    pc_out_enable = gnd;
    alu_out_enable = gnd;

    // Постоянная запись в микросчетчик
    Node* micro_we = circuit.create_node();
    micro_we->is_forced = true;
    micro_we->forced_voltage = 5.0;
    micro_we->voltage = 5.0;

    // Инкрементер PC (PC + 1) через логические элементы.
    Inverter pc_inc0(pc_out[0], pc_next[0], vdd, gnd);
    pc_inc0.build(circuit);

    XorGate pc_inc1(pc_out[1], pc_out[0], pc_next[1], vdd, gnd);
    pc_inc1.build(circuit);

    Node* pc_c2 = circuit.create_node();
    AndGate pc_c2_gate(pc_out[1], pc_out[0], pc_c2, vdd, gnd);
    pc_c2_gate.build(circuit);
    XorGate pc_inc2(pc_out[2], pc_c2, pc_next[2], vdd, gnd);
    pc_inc2.build(circuit);

    Node* pc_c3 = circuit.create_node();
    AndGate pc_c3_gate(pc_out[2], pc_c2, pc_c3, vdd, gnd);
    pc_c3_gate.build(circuit);
    XorGate pc_inc3(pc_out[3], pc_c3, pc_next[3], vdd, gnd);
    pc_inc3.build(circuit);

    // Микросчетчик (mod-4): 00 -> 01 -> 10 -> 11 -> 00.
    Inverter micro_inc0(micro_out[0], micro_next[0], vdd, gnd);
    micro_inc0.build(circuit);
    XorGate micro_inc1(micro_out[1], micro_out[0], micro_next[1], vdd, gnd);
    micro_inc1.build(circuit);
    micro_next[2] = const_zero[2];
    micro_next[3] = const_zero[3];

    // Основные компоненты CPU
    pc = new Register4Bit(pc_next, pc_out, clk, pc_write_enable, vdd, gnd);
    ir = new Register4Bit(bus, ir_out, clk, ir_write_enable, vdd, gnd);
    reg_a = new Register4Bit(bus, reg_a_out, clk, reg_a_write_enable, vdd, gnd);
    reg_b = new Register4Bit(bus, reg_b_out, clk, reg_b_write_enable, vdd, gnd);
    micro_counter = new Register4Bit(micro_next, micro_out, clk, micro_we, vdd, gnd);

    Node* alu_c_out = circuit.create_node();
    alu = new Alu4Bit(reg_a_out, reg_b_out, alu_op_sel, alu_out, alu_c_out, vdd, gnd);

    ram = new Ram4x4(pc_out[0], pc_out[1], ram_data, ram_data_bar, ram_write_enable, vdd, gnd, boot_program);

    pc->build(circuit);
    ir->build(circuit);
    reg_a->build(circuit);
    reg_b->build(circuit);
    micro_counter->build(circuit);
    alu->build(circuit);
    ram->build(circuit);

    // Tri-state подключение источников на общую шину
    for (int i = 0; i < 4; ++i) {
        TriStateBuffer ram_to_bus(ram_data[i], ram_out_enable, bus[i], vdd, gnd);
        ram_to_bus.build(circuit);

        TriStateBuffer alu_to_bus(alu_out[i], alu_out_enable, bus[i], vdd, gnd);
        alu_to_bus.build(circuit);

        TriStateBuffer pc_to_bus(pc_out[i], pc_out_enable, bus[i], vdd, gnd);
        pc_to_bus.build(circuit);
    }
}
