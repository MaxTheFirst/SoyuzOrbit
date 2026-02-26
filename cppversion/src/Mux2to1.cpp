#include "Mux2to1.h"

Mux2to1::Mux2to1(Node* a, Node* b, Node* s, Node* o, Node* v, Node* g)
    : in_a(a), in_b(b), sel(s), out(o), vdd(v), gnd(g) {}

void Mux2to1::build(Circuit& circuit) {
    // MUX 2:1
    // Out = (A AND NOT Sel) OR (B AND Sel)
    // Если Sel=0, Out=A
    // Если Sel=1, Out=B

    Node* not_sel = circuit.create_node();
    Node* and1_out = circuit.create_node();
    Node* and2_out = circuit.create_node();

    Inverter inv(sel, not_sel, vdd, gnd);
    inv.build(circuit);

    AndGate and1(in_a, not_sel, and1_out, vdd, gnd);
    and1.build(circuit);

    AndGate and2(in_b, sel, and2_out, vdd, gnd);
    and2.build(circuit);

    OrGate or_gate(and1_out, and2_out, out, vdd, gnd);
    or_gate.build(circuit);
}
