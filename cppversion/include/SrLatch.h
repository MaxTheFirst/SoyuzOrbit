#ifndef SRLATCH_H
#define SRLATCH_H

#include "Gate.h"
#include "NandGate.h"

class SrLatch : public Gate {
public:
    Node* set;
    Node* reset;
    Node* q;
    Node* q_bar;
    Node* vdd;
    Node* gnd;

    SrLatch(Node* s, Node* r, Node* q, Node* qb, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // SRLATCH_H
