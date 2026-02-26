#include "HalfAdder.h"

HalfAdder::HalfAdder(Node* a, Node* b, Node* s, Node* c, Node* v, Node* g)
    : in_a(a), in_b(b), sum(s), carry(c), vdd(v), gnd(g) {}

void HalfAdder::build(Circuit& circuit) {
    // Sum = A XOR B
    XorGate xor_gate(in_a, in_b, sum, vdd, gnd);
    xor_gate.build(circuit);

    // Carry = A AND B
    AndGate and_gate(in_a, in_b, carry, vdd, gnd);
    and_gate.build(circuit);
}
