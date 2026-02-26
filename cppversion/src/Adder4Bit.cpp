#include "Adder4Bit.h"

Adder4Bit::Adder4Bit(std::vector<Node*> a, std::vector<Node*> b, Node* ci, std::vector<Node*> s, Node* co, Node* v, Node* g)
    : a(a), b(b), c_in(ci), sum(s), c_out(co), vdd(v), gnd(g) {}

void Adder4Bit::build(Circuit& circuit) {
    // Соединяем 4 полных сумматора последовательно
    // C_out[i] -> C_in[i+1]

    Node* c0 = c_in;
    Node* c1 = circuit.create_node();
    Node* c2 = circuit.create_node();
    Node* c3 = circuit.create_node();
    Node* c4 = c_out;

    FullAdder fa0(a[0], b[0], c0, sum[0], c1, vdd, gnd);
    fa0.build(circuit);

    FullAdder fa1(a[1], b[1], c1, sum[1], c2, vdd, gnd);
    fa1.build(circuit);

    FullAdder fa2(a[2], b[2], c2, sum[2], c3, vdd, gnd);
    fa2.build(circuit);

    FullAdder fa3(a[3], b[3], c3, sum[3], c4, vdd, gnd);
    fa3.build(circuit);
}
