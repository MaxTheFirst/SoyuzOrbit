#include "Alu4Bit.h"
#include "Adder4Bit.h"
#include "AndGate.h"
#include "Mux2to1.h"

Alu4Bit::Alu4Bit(std::vector<Node*> a, std::vector<Node*> b, Node* sel, std::vector<Node*> o, Node* co, Node* v, Node* g)
    : a(a), b(b), op_sel(sel), out(o), c_out(co), vdd(v), gnd(g) {}

void Alu4Bit::build(Circuit& circuit) {
    // 1. Сложение (ADD)
    std::vector<Node*> sum(4);
    for (int i = 0; i < 4; ++i) sum[i] = circuit.create_node();
    Node* c_in = circuit.create_node();
    c_in->voltage = 0.0; // Начальный перенос = 0

    // Adder4Bit(a, b, c_in, sum, c_out, vdd, gnd)
    Adder4Bit adder(a, b, c_in, sum, c_out, vdd, gnd);
    adder.build(circuit);

    // 2. Логическое И (AND)
    std::vector<Node*> and_res(4);
    for (int i = 0; i < 4; ++i) {
        and_res[i] = circuit.create_node();
        AndGate and_gate(a[i], b[i], and_res[i], vdd, gnd);
        and_gate.build(circuit);
    }

    // 3. Мультиплексор для выбора результата
    // Если sel=0 -> ADD (sum)
    // Если sel=1 -> AND (and_res)
    for (int i = 0; i < 4; ++i) {
        // Mux2to1(in_a, in_b, sel, out, vdd, gnd)
        // in_a = sum[i], in_b = and_res[i]
        Mux2to1 mux(sum[i], and_res[i], op_sel, out[i], vdd, gnd);
        mux.build(circuit);
    }
}
