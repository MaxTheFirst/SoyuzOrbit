#ifndef IDEALRAMCORE_H
#define IDEALRAMCORE_H

#include "Component.h"
#include <array>
#include <vector>

class IdealRamCore : public Component {
public:
    Node* addr0;
    Node* addr1;
    std::vector<Node*> data_lines;
    std::vector<Node*> data_lines_bar;
    Node* write_enable;
    std::array<int, 4> words;

    IdealRamCore(
        Node* a0,
        Node* a1,
        std::vector<Node*> d,
        std::vector<Node*> d_b,
        Node* we,
        std::array<int, 4> init_words
    );

    void step(double dt) override;
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // IDEALRAMCORE_H
