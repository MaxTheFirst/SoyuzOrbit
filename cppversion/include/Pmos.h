#ifndef PMOS_H
#define PMOS_H

#include "Component.h"

class Pmos : public Component {
public:
    Node* gate;
    double threshold_voltage; // Обычно отрицательное для PMOS
    double transconductance;

    // Drain, Source, Gate
    Pmos(Node* drain, Node* source, Node* gate, double vt, double gm);

    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // PMOS_H
