#ifndef HALFADDER_H
#define HALFADDER_H

#include "Gate.h"
#include "XorGate.h"
#include "AndGate.h"

class HalfAdder : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* sum;
    Node* carry;
    Node* vdd;
    Node* gnd;

    HalfAdder(Node* a, Node* b, Node* s, Node* c, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // HALFADDER_H
