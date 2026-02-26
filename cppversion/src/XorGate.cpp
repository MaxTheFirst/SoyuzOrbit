#include "XorGate.h"

XorGate::XorGate(Node* a, Node* b, Node* o, Node* v, Node* g)
    : in_a(a), in_b(b), out(o), vdd(v), gnd(g) {}

void XorGate::build(Circuit& circuit) {
    // XOR = (A AND NOT B) OR (NOT A AND B)
    // Оптимизированная схема на NAND:
    // 1. NAND(A, B) -> N1
    // 2. NAND(A, N1) -> N2
    // 3. NAND(B, N1) -> N3
    // 4. NAND(N2, N3) -> OUT

    Node* n1 = circuit.create_node();
    Node* n2 = circuit.create_node();
    Node* n3 = circuit.create_node();

    NandGate nand1(in_a, in_b, n1, vdd, gnd);
    nand1.build(circuit);

    NandGate nand2(in_a, n1, n2, vdd, gnd);
    nand2.build(circuit);

    NandGate nand3(in_b, n1, n3, vdd, gnd);
    nand3.build(circuit);

    NandGate nand4(n2, n3, out, vdd, gnd);
    nand4.build(circuit);
}
