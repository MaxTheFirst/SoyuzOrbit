#include "Nmos.h"
#include <algorithm>
#include <cmath>

Nmos::Nmos(Node* drain, Node* source, Node* gate, double vt, double gm)
    : gate(gate), threshold_voltage(vt), transconductance(gm) {
    n1 = drain;
    n2 = source;
}

void Nmos::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    double gate_v = std::isfinite(gate->voltage) ? gate->voltage : 0.0;
    double d_v = std::isfinite(n1->voltage) ? n1->voltage : 0.0;
    double s_v = std::isfinite(n2->voltage) ? n2->voltage : 0.0;
    gate_v = std::clamp(gate_v, -0.5, 5.5);
    d_v = std::clamp(d_v, -0.5, 5.5);
    s_v = std::clamp(s_v, -0.5, 5.5);

    (void)d_v;
    (void)s_v;
    const bool is_on = gate_v > 2.5;
    const double r_on = 10.0;
    const double r_off = 1e12;
    const double g_ds = 1.0 / (is_on ? r_on : r_off);

    int d = n1->index;
    int s = n2->index;

    if (d != -1) {
        A(d, d) += g_ds;
    }
    if (s != -1) {
        A(s, s) += g_ds;
    }
    if (d != -1 && s != -1) {
        A(d, s) -= g_ds;
        A(s, d) -= g_ds;
    }
}
