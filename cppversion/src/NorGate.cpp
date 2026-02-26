#include "NorGate.h"

NorGate::NorGate(Node* a, Node* b, Node* o, Node* v, Node* g)
    : in_a(a), in_b(b), out(o), vdd(v), gnd(g) {}

void NorGate::build(Circuit& circuit) {
    // CMOS NOR:
    // PMOS: последовательно между VDD и OUT
    // NMOS: параллельно между OUT и GND

    // PMOS 1: Gate=A, Source=VDD, Drain=InternalNode
    Node* internal = circuit.create_node();
    circuit.add_component(new Pmos(internal, vdd, in_a, -0.5, 0.01));

    // PMOS 2: Gate=B, Source=InternalNode, Drain=OUT
    circuit.add_component(new Pmos(out, internal, in_b, -0.5, 0.01));

    // NMOS 1: Gate=A, Drain=OUT, Source=GND
    circuit.add_component(new Nmos(out, gnd, in_a, 0.5, 0.01));

    // NMOS 2: Gate=B, Drain=OUT, Source=GND
    circuit.add_component(new Nmos(out, gnd, in_b, 0.5, 0.01));
}
