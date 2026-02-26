#ifndef INVERTER_H
#define INVERTER_H

#include "Gate.h"
#include "NandGate.h"

class Inverter : public Gate {
public:
    Node* in;
    Node* out;
    Node* vdd;
    Node* gnd;

    Inverter(Node* i, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // INVERTER_H
