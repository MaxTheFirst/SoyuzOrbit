#include "DFlipFlop.h"

DFlipFlop::DFlipFlop(Node* d, Node* clk, Node* q, Node* qb, Node* v, Node* g)
    : d(d), clk(clk), q(q), q_bar(qb), vdd(v), gnd(g) {}

void DFlipFlop::build(Circuit& circuit) {
    // Master-Slave D-Flip-Flop:
    // 1. Master Latch (активен при CLK=1)
    // 2. Slave Latch (активен при CLK=0)

    Node* clk_bar = circuit.create_node();
    Node* q_master = circuit.create_node();
    Node* q_master_bar = circuit.create_node();

    // Инвертор CLK
    Inverter inv(clk, clk_bar, vdd, gnd);
    inv.build(circuit);

    // Master Latch (D, CLK) -> Q_master
    DLatch master(d, clk, q_master, q_master_bar, vdd, gnd);
    master.build(circuit);

    // Slave Latch (Q_master, CLK_bar) -> Q
    DLatch slave(q_master, clk_bar, q, q_bar, vdd, gnd);
    slave.build(circuit);
}
