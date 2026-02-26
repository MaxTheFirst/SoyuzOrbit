#ifndef IDEALTRISTATECORE_H
#define IDEALTRISTATECORE_H

#include "Component.h"

class IdealTriStateCore : public Component {
public:
    Node* in;
    Node* enable;
    Node* out;

    IdealTriStateCore(Node* i, Node* en, Node* o);
    void step(double dt) override;
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // IDEALTRISTATECORE_H
