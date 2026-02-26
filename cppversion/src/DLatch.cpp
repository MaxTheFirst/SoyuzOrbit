#include "DLatch.h"
#include "SrLatch.h"

DLatch::DLatch(Node* d, Node* clk, Node* q, Node* qb, Node* v, Node* g)
    : d(d), clk(clk), q(q), q_bar(qb), vdd(v), gnd(g) {}

void DLatch::build(Circuit& circuit) {
    // D-Latch на NAND-элементах:
    // 1. Инвертируем D -> D_bar
    // 2. NAND1(D, CLK) -> S_bar
    // 3. NAND2(D_bar, CLK) -> R_bar
    // 4. SR-Latch(S_bar, R_bar) -> Q, Q_bar

    Node* d_bar = circuit.create_node();
    Node* s_bar = circuit.create_node();
    Node* r_bar = circuit.create_node();

    // Инвертор D
    Inverter inv(d, d_bar, vdd, gnd);
    inv.build(circuit);

    // NAND1 (S_bar)
    NandGate nand1(d, clk, s_bar, vdd, gnd);
    nand1.build(circuit);

    // NAND2 (R_bar)
    NandGate nand2(d_bar, clk, r_bar, vdd, gnd);
    nand2.build(circuit);

    // SR-Latch (активный низкий уровень)
    SrLatch sr(s_bar, r_bar, q, q_bar, vdd, gnd);
    sr.build(circuit);
}
