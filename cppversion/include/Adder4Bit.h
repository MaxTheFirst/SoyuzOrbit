#ifndef ADDER4BIT_H
#define ADDER4BIT_H

#include "Gate.h"
#include "FullAdder.h"
#include <vector>

class Adder4Bit : public Gate {
public:
    std::vector<Node*> a; // Входы A0-A3
    std::vector<Node*> b; // Входы B0-B3
    Node* c_in;           // Входящий перенос
    std::vector<Node*> sum; // Выходы S0-S3
    Node* c_out;          // Выходящий перенос
    Node* vdd;
    Node* gnd;

    Adder4Bit(std::vector<Node*> a, std::vector<Node*> b, Node* ci, std::vector<Node*> s, Node* co, Node* v, Node* g);
    void build(Circuit& circuit) override;
};

#endif // ADDER4BIT_H
