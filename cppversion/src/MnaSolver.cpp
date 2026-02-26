#include "MnaSolver.h"
#include "Circuit.h"
#include "Matrix.h"
#include <iostream>
#include <cmath>
#include <algorithm>

void MnaSolver::solve(Circuit& circuit, double dt) {
    int num_nodes = 0;
    // Индексация MNA-матрицы 0-based.
    for (Node* n : circuit.nodes) {
        n->index = n->is_ground ? -1 : num_nodes++;
    }
    if (num_nodes == 0) return;

    const int max_iter = 4;
    const double tolerance = 1e-2;
    const double gfix = 1e6;

    for (int iter = 0; iter < max_iter; ++iter) {
        for (Node* n : circuit.nodes) {
            if (n->is_forced) {
                n->voltage = n->forced_voltage;
            } else if (!std::isfinite(n->voltage)) {
                n->voltage = 0.0;
            }
        }

        Matrix A(num_nodes, num_nodes);
        std::vector<double> z(num_nodes, 0.0);
        const double gmin = 1e-12;
        for (int i = 0; i < num_nodes; ++i) {
            A(i, i) += gmin;
        }

        // Заполняем матрицу и вектор
        for (Component* comp : circuit.components) {
            comp->stamp(A, z, circuit.nodes, dt);
        }

        for (Node* n : circuit.nodes) {
            if (n->index >= 0 && n->is_forced) {
                A(n->index, n->index) += gfix;
                z[n->index] += gfix * n->forced_voltage;
            }
        }

        // Решаем систему A * V = z для текущей линеаризации
        std::vector<double> solved_v;
        try {
            solved_v = solve_linear_system(A, z);
        } catch (const std::exception& e) {
            std::cerr << "Solver error: " << e.what() << std::endl;
            return;
        }

        // Обновляем напряжения
        double max_change = 0;
        for (Node* n : circuit.nodes) {
            if (n->index >= 0) {
                if (n->is_forced) {
                    n->voltage = n->forced_voltage;
                    continue;
                }
                double new_voltage = solved_v[n->index];
                if (!std::isfinite(new_voltage)) {
                    new_voltage = n->voltage;
                }
                new_voltage = std::clamp(new_voltage, -0.5, 5.5);
                new_voltage = 0.7 * n->voltage + 0.3 * new_voltage;
                double change = new_voltage - n->voltage;
                n->voltage = new_voltage;
                if (std::abs(change) > max_change) {
                    max_change = std::abs(change);
                }
            }
        }

        // Проверка сходимости
        if (max_change < tolerance) {
            // std::cout << "Converged after " << iter + 1 << " iterations." << std::endl;
            goto end_loop;
        }
    }
    // std::cout << "Warning: Solver did not converge." << std::endl;

end_loop:
    // Обновляем состояние динамических компонентов (например, конденсаторов)
    for (Component* comp : circuit.components) {
        comp->step(dt);
    }
}
