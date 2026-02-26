#ifndef ORGATE_H
#define ORGATE_H

#include "Gate.h"
#include "NandGate.h"
#include "Inverter.h"

class OrGate : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* out;
    Node* vdd;
    Node* gnd;

    OrGate(Node* a, Node* b, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // ORGATE_H
