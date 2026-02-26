#include "Resistor.h"

Resistor::Resistor(Node* node1, Node* node2, double r) : resistance(r) {
    n1 = node1;
    n2 = node2;
}

void Resistor::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    double g = 1.0 / resistance;
    int i1 = n1->index;
    int i2 = n2->index;

    if (i1 != -1) {
        A(i1, i1) += g;
    }
    if (i2 != -1) {
        A(i2, i2) += g;
    }
    if (i1 != -1 && i2 != -1) {
        A(i1, i2) -= g;
        A(i2, i1) -= g;
    }
}
