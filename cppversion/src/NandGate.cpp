#include "NandGate.h"

NandGate::NandGate(Node* a, Node* b, Node* o, Node* v, Node* g)
    : in_a(a), in_b(b), out(o), vdd(v), gnd(g) {}

void NandGate::build(Circuit& circuit) {
    // CMOS NAND:
    // PMOS: параллельно между VDD и OUT
    // NMOS: последовательно между OUT и GND

    // PMOS 1: Gate=A, Source=VDD, Drain=OUT
    circuit.add_component(new Pmos(out, vdd, in_a, -0.5, 0.01));

    // PMOS 2: Gate=B, Source=VDD, Drain=OUT
    circuit.add_component(new Pmos(out, vdd, in_b, -0.5, 0.01));

    // NMOS 1: Gate=A, Drain=OUT, Source=InternalNode
    Node* internal = circuit.create_node();
    circuit.add_component(new Nmos(out, internal, in_a, 0.5, 0.01));

    // NMOS 2: Gate=B, Drain=InternalNode, Source=GND
    circuit.add_component(new Nmos(internal, gnd, in_b, 0.5, 0.01));
}
