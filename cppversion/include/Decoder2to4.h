#ifndef DECODER2TO4_H
#define DECODER2TO4_H

#include "Gate.h"
#include <vector>

class Decoder2to4 : public Gate {
public:
    Node* a0;
    Node* a1;
    std::vector<Node*> out; // 4 output lines
    Node* vdd;
    Node* gnd;

    Decoder2to4(Node* a0, Node* a1, std::vector<Node*> out, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // DECODER2TO4_H
