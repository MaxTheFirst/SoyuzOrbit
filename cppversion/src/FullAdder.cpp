#include "FullAdder.h"

FullAdder::FullAdder(Node* a, Node* b, Node* ci, Node* s, Node* co, Node* v, Node* g)
    : in_a(a), in_b(b), c_in(ci), sum(s), c_out(co), vdd(v), gnd(g) {}

void FullAdder::build(Circuit& circuit) {
    // Full Adder из двух Half Adders и одного OR
    // HA1(A, B) -> S1, C1
    // HA2(S1, Cin) -> Sum, C2
    // Cout = C1 OR C2

    Node* s1 = circuit.create_node();
    Node* c1 = circuit.create_node();
    Node* c2 = circuit.create_node();

    HalfAdder ha1(in_a, in_b, s1, c1, vdd, gnd);
    ha1.build(circuit);

    HalfAdder ha2(s1, c_in, sum, c2, vdd, gnd);
    ha2.build(circuit);

    OrGate or_gate(c1, c2, c_out, vdd, gnd);
    or_gate.build(circuit);
}
