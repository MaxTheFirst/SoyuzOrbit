#include "Capacitor.h"

Capacitor::Capacitor(Node* node1, Node* node2, double c) : capacitance(c), voltage_prev(0.0) {
    n1 = node1;
    n2 = node2;
}

// Метод step теперь используется для сохранения состояния
void Capacitor::step(double dt) {
    voltage_prev = n1->voltage - n2->voltage;
}

void Capacitor::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    if (dt <= 0) return; // Нельзя делить на ноль или отрицательное время

    double g = capacitance / dt;
    double i_source = g * voltage_prev;

    int i1 = n1->index;
    int i2 = n2->index;

    if (i1 != -1) {
        A(i1, i1) += g;
        z[i1] -= i_source;
    }
    if (i2 != -1) {
        A(i2, i2) += g;
        z[i2] += i_source;
    }
    if (i1 != -1 && i2 != -1) {
        A(i1, i2) -= g;
        A(i2, i1) -= g;
    }
}
