#ifndef MATRIX_H
#define MATRIX_H

#include <vector>
#include <stdexcept>

class Matrix {
public:
    Matrix(int rows, int cols) : m_rows(rows), m_cols(cols), m_data(rows * cols, 0.0) {}

    double& operator()(int row, int col) {
        if (row >= m_rows || col >= m_cols) {
            throw std::out_of_range("Matrix access out of range");
        }
        return m_data[row * m_cols + col];
    }

    const double& operator()(int row, int col) const {
        if (row >= m_rows || col >= m_cols) {
            throw std::out_of_range("Matrix access out of range");
        }
        return m_data[row * m_cols + col];
    }

    int rows() const { return m_rows; }
    int cols() const { return m_cols; }

private:
    int m_rows;
    int m_cols;
    std::vector<double> m_data;
};

// Функция для решения системы линейных уравнений Ax = b с помощью LU-разложения
std::vector<double> solve_linear_system(Matrix& A, std::vector<double>& b);

#endif // MATRIX_H
