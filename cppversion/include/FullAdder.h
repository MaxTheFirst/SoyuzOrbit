#ifndef FULLADDER_H
#define FULLADDER_H

#include "Gate.h"
#include "HalfAdder.h"
#include "OrGate.h"

class FullAdder : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* c_in;
    Node* sum;
    Node* c_out;
    Node* vdd;
    Node* gnd;

    FullAdder(Node* a, Node* b, Node* ci, Node* s, Node* co, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // FULLADDER_H
