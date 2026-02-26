#ifndef REGISTER4BIT_H
#define REGISTER4BIT_H

#include "Gate.h"
#include "DFlipFlop.h"
#include <vector>

class Register4Bit : public Gate {
public:
    std::vector<Node*> d; // Входы D0-D3
    std::vector<Node*> q; // Выходы Q0-Q3
    Node* clk;
    Node* write_enable; // Сигнал разрешения записи
    Node* vdd;
    Node* gnd;

    Register4Bit(std::vector<Node*> d, std::vector<Node*> q, Node* clk, Node* we, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // REGISTER4BIT_H
