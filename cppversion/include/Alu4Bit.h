#ifndef ALU4BIT_H
#define ALU4BIT_H

#include "Gate.h"
#include "Adder4Bit.h"
#include "AndGate.h"
#include "Mux2to1.h"
#include <vector>

class Alu4Bit : public Gate {
public:
    std::vector<Node*> a; // Входы A0-A3
    std::vector<Node*> b; // Входы B0-B3
    Node* op_sel;         // Выбор операции (0: ADD, 1: AND)
    std::vector<Node*> out; // Выходы O0-O3
    Node* c_out;          // Перенос (только для ADD)
    Node* vdd;
    Node* gnd;

    Alu4Bit(std::vector<Node*> a, std::vector<Node*> b, Node* sel, std::vector<Node*> o, Node* co, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // ALU4BIT_H
