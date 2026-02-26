#ifndef IDEALCONTROLCORE_H
#define IDEALCONTROLCORE_H

#include "Component.h"
#include <vector>

class IdealControlCore : public Component {
public:
    std::vector<Node*> micro_out;
    std::vector<Node*> ir_out;
    Node* ir_write_enable;
    Node* reg_a_write_enable;
    Node* pc_write_enable;
    Node* ram_out_enable;
    Node* halted;
    Node* phase0;
    Node* phase1;
    Node* phase2;

    IdealControlCore(
        std::vector<Node*> micro,
        std::vector<Node*> ir,
        Node* ir_we,
        Node* a_we,
        Node* pc_we,
        Node* ram_oe,
        Node* halted,
        Node* p0,
        Node* p1,
        Node* p2
    );

    void step(double dt) override;
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // IDEALCONTROLCORE_H
