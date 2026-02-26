#include "Solver.h"
#include "Circuit.h"
#include "Nmos.h"
#include "Pmos.h"
#include "Resistor.h"
#include "Transistor.h"

static double transistor_conductance_nm(double gate_v, double source_v, double vt) {
    (void)source_v;
    (void)vt;
    const bool on = gate_v > 2.5;
    const double r_on = 10.0;
    const double r_off = 1e12;
    return 1.0 / (on ? r_on : r_off);
}

static double transistor_conductance_pm(double gate_v, double source_v, double vt) {
    (void)source_v;
    (void)vt;
    const bool on = gate_v < 2.5;
    const double r_on = 10.0;
    const double r_off = 1e12;
    return 1.0 / (on ? r_on : r_off);
}

void IterativeSolver::solve(Circuit& circuit, double dt) {
    const int iterations = 220;
    const double g_leak = 1.0 / 1e6;
    for (int i = 0; i < iterations; ++i) {
        for (size_t j = 0; j < circuit.nodes.size(); ++j) {
            Node* n = circuit.nodes[j];
            if (n->is_ground || n->is_forced) continue;
            double total_current = 0.0;
            double total_conductance = g_leak; // Слабая утечка к земле для анти-флоата.

            for (Component* comp : circuit.components) {
                if (comp->n1 == n || comp->n2 == n) {
                    Node* other_node = (comp->n1 == n) ? comp->n2 : comp->n1;
                    double conductance = 0.0;

                    if (auto r = dynamic_cast<Resistor*>(comp)) {
                        conductance = 1.0 / r->resistance;
                    } else if (auto nm = dynamic_cast<Nmos*>(comp)) {
                        conductance = transistor_conductance_nm(
                            nm->gate->voltage,
                            nm->n2->voltage,
                            nm->threshold_voltage
                        );
                    } else if (auto pm = dynamic_cast<Pmos*>(comp)) {
                        conductance = transistor_conductance_pm(
                            pm->gate->voltage,
                            pm->n2->voltage,
                            pm->threshold_voltage
                        );
                    } else if (auto t = dynamic_cast<Transistor*>(comp)) {
                        conductance = transistor_conductance_nm(
                            t->gate->voltage,
                            t->n2->voltage,
                            t->threshold_voltage
                        );
                    }

                    if (conductance > 0.0) {
                        total_current += other_node->voltage * conductance;
                        total_conductance += conductance;
                    }
                }
            }

            if (total_conductance > 0) {
                n->voltage = total_current / total_conductance;
            }
        }
    }
}
