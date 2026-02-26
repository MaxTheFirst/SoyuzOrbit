#include "Inverter.h"

Inverter::Inverter(Node* i, Node* o, Node* v, Node* g)
    : in(i), out(o), vdd(v), gnd(g) {}

void Inverter::build(Circuit& circuit) {
    // Инвертор из NAND: оба входа соединены вместе
    NandGate nand(in, in, out, vdd, gnd);
    nand.build(circuit);
}
