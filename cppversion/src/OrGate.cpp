#include "OrGate.h"

OrGate::OrGate(Node* a, Node* b, Node* o, Node* v, Node* g)
    : in_a(a), in_b(b), out(o), vdd(v), gnd(g) {}

void OrGate::build(Circuit& circuit) {
    // OR = NAND(NOT(A), NOT(B))
    Node* not_a = circuit.create_node();
    Node* not_b = circuit.create_node();

    Inverter inv_a(in_a, not_a, vdd, gnd);
    inv_a.build(circuit);

    Inverter inv_b(in_b, not_b, vdd, gnd);
    inv_b.build(circuit);

    NandGate nand(not_a, not_b, out, vdd, gnd);
    nand.build(circuit);
}
