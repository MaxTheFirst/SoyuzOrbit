#include "AndGate.h"

AndGate::AndGate(Node* a, Node* b, Node* o, Node* v, Node* g)
    : in_a(a), in_b(b), out(o), vdd(v), gnd(g) {}

void AndGate::build(Circuit& circuit) {
    // AND = NAND + Inverter
    Node* nand_out = circuit.create_node();

    NandGate nand(in_a, in_b, nand_out, vdd, gnd);
    nand.build(circuit);

    Inverter inv(nand_out, out, vdd, gnd);
    inv.build(circuit);
}
