#ifndef XORGATE_H
#define XORGATE_H

#include "Gate.h"
#include "NandGate.h"
#include "OrGate.h"
#include "AndGate.h"
#include "Inverter.h"

class XorGate : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* out;
    Node* vdd;
    Node* gnd;

    XorGate(Node* a, Node* b, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // XORGATE_H
