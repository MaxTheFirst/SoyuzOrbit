#include "Decoder2to4.h"
#include "Inverter.h"
#include "AndGate.h"

Decoder2to4::Decoder2to4(Node* a0, Node* a1, std::vector<Node*> out, Node* v, Node* g)
    : a0(a0), a1(a1), out(out), vdd(v), gnd(g) {}

void Decoder2to4::build(Circuit& circuit) {
    Node* not_a0 = circuit.create_node();
    Node* not_a1 = circuit.create_node();

    Inverter inv_a0(a0, not_a0, vdd, gnd);
    inv_a0.build(circuit);

    Inverter inv_a1(a1, not_a1, vdd, gnd);
    inv_a1.build(circuit);

    // out[0] = not_a1 AND not_a0
    AndGate and0(not_a1, not_a0, out[0], vdd, gnd);
    and0.build(circuit);

    // out[1] = not_a1 AND a0
    AndGate and1(not_a1, a0, out[1], vdd, gnd);
    and1.build(circuit);

    // out[2] = a1 AND not_a0
    AndGate and2(a1, not_a0, out[2], vdd, gnd);
    and2.build(circuit);

    // out[3] = a1 AND a0
    AndGate and3(a1, a0, out[3], vdd, gnd);
    and3.build(circuit);
}
