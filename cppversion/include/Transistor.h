#ifndef TRANSISTOR_H
#define TRANSISTOR_H

#include "Component.h"

class Transistor : public Component {
public:
    Node* gate;
    double threshold_voltage;
    double transconductance; // Коэффициент усиления (beta)

    Transistor(Node* drain, Node* source, Node* gate, double vt, double gm);

    // Метод для линеаризации и "штамповки"
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // TRANSISTOR_H
