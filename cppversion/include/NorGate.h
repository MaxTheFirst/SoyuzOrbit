#ifndef NORGATE_H
#define NORGATE_H

#include "Gate.h"
#include "Nmos.h"
#include "Pmos.h"

class NorGate : public Gate {
public:
    Node* in_a;
    Node* in_b;
    Node* out;
    Node* vdd;
    Node* gnd;

    NorGate(Node* a, Node* b, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // NORGATE_H
