#ifndef IDEALINCREMENTERCORE_H
#define IDEALINCREMENTERCORE_H

#include "Component.h"
#include <vector>

class IdealIncrementerCore : public Component {
public:
    std::vector<Node*> in;
    std::vector<Node*> out;

    IdealIncrementerCore(std::vector<Node*> in, std::vector<Node*> out);
    void step(double dt) override;
    void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) override;
};

#endif // IDEALINCREMENTERCORE_H
