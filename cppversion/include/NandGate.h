#ifndef NANDGATE_H
#define NANDGATE_H

#include "Gate.h"
#include "Nmos.h"
#include "Pmos.h"

class NandGate : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* out;
    Node* vdd;
    Node* gnd;

    NandGate(Node* a, Node* b, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // NANDGATE_H
