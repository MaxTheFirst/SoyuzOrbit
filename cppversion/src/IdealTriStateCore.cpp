#include "IdealTriStateCore.h"

IdealTriStateCore::IdealTriStateCore(Node* i, Node* en, Node* o)
    : in(i), enable(en), out(o) {
    n1 = in;
    n2 = out;
}

void IdealTriStateCore::step(double dt) {
    (void)dt;
    if (enable->voltage > 2.5) {
        out->voltage = in->voltage;
    }
}

void IdealTriStateCore::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    (void)A;
    (void)z;
    (void)nodes;
    (void)dt;
}
