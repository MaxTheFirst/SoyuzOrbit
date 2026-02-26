#include "IdealIncrementerCore.h"

IdealIncrementerCore::IdealIncrementerCore(std::vector<Node*> in, std::vector<Node*> out)
    : in(std::move(in)), out(std::move(out)) {
    n1 = this->in.empty() ? nullptr : this->in[0];
    n2 = this->out.empty() ? nullptr : this->out[0];
}

void IdealIncrementerCore::step(double dt) {
    (void)dt;
    int value = 0;
    for (int i = 0; i < 4; ++i) {
        if (in[i]->voltage > 2.5) {
            value |= (1 << i);
        }
    }

    const int inc = (value + 1) & 0xF;
    for (int i = 0; i < 4; ++i) {
        out[i]->voltage = ((inc >> i) & 1) ? 5.0 : 0.0;
    }
}

void IdealIncrementerCore::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    (void)A;
    (void)z;
    (void)nodes;
    (void)dt;
}
