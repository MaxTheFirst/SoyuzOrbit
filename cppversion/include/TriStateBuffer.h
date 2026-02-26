#ifndef TRISTATEBUFFER_H
#define TRISTATEBUFFER_H

#include "Gate.h"

class TriStateBuffer : public Gate {
public:
    Node* in;
    Node* enable;
    Node* out;
    Node* vdd;
    Node* gnd;

    TriStateBuffer(Node* i, Node* en, Node* o, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // TRISTATEBUFFER_H
