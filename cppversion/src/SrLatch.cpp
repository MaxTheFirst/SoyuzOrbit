#include "SrLatch.h"
#include "Resistor.h"

SrLatch::SrLatch(Node* s, Node* r, Node* q, Node* qb, Node* v, Node* g)
    : set(s), reset(r), q(q), q_bar(qb), vdd(v), gnd(g) {}

void SrLatch::build(Circuit& circuit) {
    // SR-триггер на NAND-элементах (активный низкий уровень)
    // Q = NAND(S, Q_bar)
    // Q_bar = NAND(R, Q)

    NandGate nand1(set, q_bar, q, vdd, gnd);
    nand1.build(circuit);

    NandGate nand2(reset, q, q_bar, vdd, gnd);
    nand2.build(circuit);

    // Слабый bias для детерминированного старта.
    circuit.add_component(new Resistor(q, gnd, 100000));
    circuit.add_component(new Resistor(q_bar, vdd, 100000));
}
