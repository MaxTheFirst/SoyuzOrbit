#ifndef COMPONENT_H
#define COMPONENT_H

#include "Node.h"
#include "Matrix.h"
#include <vector>

class Component {
public:
    virtual ~Component() = default;

    // Метод для обновления состояния компонента (для динамических элементов)
    virtual void step(double dt) {}

    // Метод для "штамповки" вклада компонента в MNA-матрицу
    virtual void stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) = 0;

    Node *n1, *n2;
};

#endif // COMPONENT_H
