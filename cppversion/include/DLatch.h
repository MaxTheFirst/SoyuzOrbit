#ifndef DLATCH_H
#define DLATCH_H

#include "Gate.h"
#include "NandGate.h"
#include "Inverter.h"

class DLatch : public Gate {
public:
    Node* d;
    Node* clk;
    Node* q;
    Node* q_bar;
    Node* vdd;
    Node* gnd;

    DLatch(Node* d, Node* clk, Node* q, Node* qb, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // DLATCH_H
