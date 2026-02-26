#include "Matrix.h"
#include <cmath>
#include <stdexcept>

// Решает Ax = b, где A - квадратная матрица
std::vector<double> solve_linear_system(Matrix& A, std::vector<double>& b) {
    int n = A.rows();
    if (n != A.cols() || n != b.size()) {
        throw std::invalid_argument("Matrix must be square and dimensions must match");
    }

    // LU-разложение (Doolittle's method)
    Matrix LU(n, n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            LU(i, j) = A(i, j);
        }
    }

    std::vector<int> pi(n);
    for (int i = 0; i < n; i++) pi[i] = i;

    for (int k = 0; k < n; k++) {
        double max_val = 0;
        int p = -1;
        for (int i = k; i < n; i++) {
            const double candidate = std::abs(LU(i, k));
            if (candidate > max_val && !std::isnan(candidate)) {
                max_val = candidate;
                p = i;
            }
        }
        if (p == -1 || max_val < 1e-18) {
            // Gmin fallback для плохо обусловленных или частично плавающих схем.
            LU(k, k) = 1e-12;
            continue;
        }

        std::swap(pi[k], pi[p]);
        for (int i = 0; i < n; i++) {
            std::swap(LU(k, i), LU(p, i));
        }

        for (int i = k + 1; i < n; i++) {
            if (std::abs(LU(k, k)) < 1e-18) {
                LU(k, k) = (LU(k, k) >= 0.0) ? 1e-12 : -1e-12;
            }
            LU(i, k) /= LU(k, k);
            for (int j = k + 1; j < n; j++) {
                LU(i, j) -= LU(i, k) * LU(k, j);
            }
        }
    }

    // Решение Ly = Pb
    std::vector<double> y(n);
    for (int i = 0; i < n; i++) {
        double sum = 0;
        for (int j = 0; j < i; j++) {
            sum += LU(i, j) * y[j];
        }
        y[i] = b[pi[i]] - sum;
    }

    // Решение Ux = y
    std::vector<double> x(n);
    for (int i = n - 1; i >= 0; i--) {
        double sum = 0;
        for (int j = i + 1; j < n; j++) {
            sum += LU(i, j) * x[j];
        }
        if (std::abs(LU(i, i)) < 1e-18) {
            LU(i, i) = (LU(i, i) >= 0.0) ? 1e-12 : -1e-12;
        }
        x[i] = (y[i] - sum) / LU(i, i);
    }

    return x;
}
