#ifndef IDEALDFFCELL_H
#define IDEALDFFCELL_H

#include "Component.h"

class IdealDffCell : public Component {
public:
    Node* d;
    Node* clk;
    Node* write_enable;
    Node* q;
    Node* q_bar;
    double prev_clk;

    IdealDffCell(Node* d, Node* clk, Node* we, Node* q, Node* qb);
    void step(double dt) override;
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // IDEALDFFCELL_H
