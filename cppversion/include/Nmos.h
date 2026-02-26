#ifndef NMOS_H
#define NMOS_H

#include "Component.h"

class Nmos : public Component {
public:
    Node* gate;
    double threshold_voltage;
    double transconductance;

    // Drain, Source, Gate
    Nmos(Node* drain, Node* source, Node* gate, double vt, double gm);

    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // NMOS_H
