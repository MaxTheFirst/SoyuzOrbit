#include "TriStateBuffer.h"
#include "Inverter.h"
#include "Nmos.h"
#include "Pmos.h"

TriStateBuffer::TriStateBuffer(Node* i, Node* en, Node* o, Node* v, Node* g)
    : in(i), enable(en), out(o), vdd(v), gnd(g) {}

void TriStateBuffer::build(Circuit& circuit) {
    Node* en_bar = circuit.create_node();
    Inverter inv(enable, en_bar, vdd, gnd);
    inv.build(circuit);

    // Transmission gate: enable=1 -> OUT follows IN, enable=0 -> high-Z.
    circuit.add_component(new Nmos(out, in, enable, 0.5, 0.01));
    circuit.add_component(new Pmos(out, in, en_bar, -0.5, 0.01));
}
