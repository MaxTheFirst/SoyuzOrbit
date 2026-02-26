#include "IdealDffCell.h"

IdealDffCell::IdealDffCell(Node* d, Node* clk, Node* we, Node* q, Node* qb)
    : d(d), clk(clk), write_enable(we), q(q), q_bar(qb), prev_clk(0.0) {
    n1 = q;
    n2 = q_bar;

    q->is_forced = true;
    q_bar->is_forced = true;
    q->forced_voltage = 0.0;
    q_bar->forced_voltage = 5.0;
    q->voltage = 0.0;
    q_bar->voltage = 5.0;
}

void IdealDffCell::step(double dt) {
    const bool rising = (prev_clk <= 2.5) && (clk->voltage > 2.5);
    if (rising && write_enable->voltage > 2.5) {
        const bool bit = d->voltage > 2.5;
        q->forced_voltage = bit ? 5.0 : 0.0;
        q_bar->forced_voltage = bit ? 0.0 : 5.0;
    }

    q->voltage = q->forced_voltage;
    q_bar->voltage = q_bar->forced_voltage;
    prev_clk = clk->voltage;
}

void IdealDffCell::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    (void)A;
    (void)z;
    (void)nodes;
    (void)dt;
}
