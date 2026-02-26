#ifndef ANDGATE_H
#define ANDGATE_H

#include "Gate.h"
#include "NandGate.h"
#include "Inverter.h"

class AndGate : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* out;
    Node* vdd;
    Node* gnd;

    AndGate(Node* a, Node* b, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // ANDGATE_H
