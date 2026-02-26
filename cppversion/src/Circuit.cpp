#include "Circuit.h"
#include "Resistor.h"
#include "Transistor.h"
#include <iostream>

Circuit::Circuit() : solver(std::make_unique<IterativeSolver>()) {}

Circuit::~Circuit() {
    for (auto c : components) delete c;
    for (auto n : nodes) delete n;
}

void Circuit::set_solver(std::unique_ptr<Solver> s) {
    solver = std::move(s);
}

Node* Circuit::create_node() {
    Node* n = new Node();
    nodes.push_back(n);
    return n;
}

void Circuit::add_component(Component* comp) {
    components.push_back(comp);
}

void Circuit::remove_component(Component* comp) {
    auto it = std::find(components.begin(), components.end(), comp);
    if (it != components.end()) {
        components.erase(it);
        delete comp;
    }
}

void Circuit::simulate_step(double dt) {
    for (Node* n : nodes) {
        if (n->is_forced) {
            n->voltage = n->forced_voltage;
        }
    }

    if (solver) {
        solver->solve(*this, dt);
    }

    for (Node* n : nodes) {
        if (n->is_forced) {
            n->voltage = n->forced_voltage;
        }
    }

    // Обновляем состояние компонентов
    for (Component* comp : components) {
        comp->step(dt);
    }
}
