#ifndef CIRCUIT_H
#define CIRCUIT_H

#include <vector>
#include <memory>
#include <algorithm>
#include "Component.h"
#include "Node.h"
#include "Solver.h"

class Circuit {
public:
    std::vector<Node*> nodes;
    std::vector<Component*> components;
    std::unique_ptr<Solver> solver;

    Circuit();
    ~Circuit();

    void set_solver(std::unique_ptr<Solver> s);
    Node* create_node();
    void add_component(Component* comp);
    void remove_component(Component* comp);
    void simulate_step(double dt);
};

#endif // CIRCUIT_H
