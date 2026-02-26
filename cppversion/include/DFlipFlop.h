#ifndef DFLIPFLOP_H
#define DFLIPFLOP_H

#include "Gate.h"
#include "DLatch.h"
#include "Inverter.h"

class DFlipFlop : public Gate {
public:
    Node* d;
    Node* clk;
    Node* q;
    Node* q_bar;
    Node* vdd;
    Node* gnd;

    DFlipFlop(Node* d, Node* clk, Node* q, Node* qb, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // DFLIPFLOP_H
