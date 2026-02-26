#ifndef MUX2TO1_H
#define MUX2TO1_H

#include "Gate.h"
#include "AndGate.h"
#include "OrGate.h"
#include "Inverter.h"

class Mux2to1 : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* sel;
    Node* out;
    Node* vdd;
    Node* gnd;

    Mux2to1(Node* a, Node* b, Node* s, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // MUX2TO1_H
