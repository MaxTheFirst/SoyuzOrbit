#ifndef CAPACITOR_H
#define CAPACITOR_H

#include "Component.h"

class Capacitor : public Component {
public:
    double capacitance;
    double voltage_prev; // Напряжение на предыдущем шаге

    Capacitor(Node* node1, Node* node2, double c);
    void step(double dt) override;
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // CAPACITOR_H
