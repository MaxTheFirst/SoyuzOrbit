#include "IdealRamCore.h"

IdealRamCore::IdealRamCore(
    Node* a0,
    Node* a1,
    std::vector<Node*> d,
    std::vector<Node*> d_b,
    Node* we,
    std::array<int, 4> init_words
) : addr0(a0), addr1(a1), data_lines(d), data_lines_bar(d_b), write_enable(we), words(init_words) {
    n1 = d.empty() ? nullptr : d[0];
    n2 = d_b.empty() ? nullptr : d_b[0];
}

void IdealRamCore::step(double dt) {
    (void)dt;

    const int a0 = (addr0->voltage > 2.5) ? 1 : 0;
    const int a1 = (addr1->voltage > 2.5) ? 1 : 0;
    const int addr = (a1 << 1) | a0;

    if (write_enable->voltage > 2.5) {
        int value = 0;
        for (int i = 0; i < 4; ++i) {
            if (data_lines[i]->voltage > 2.5) {
                value |= (1 << i);
            }
        }
        words[addr] = value & 0xF;
    } else {
        const int value = words[addr] & 0xF;
        for (int i = 0; i < 4; ++i) {
            const bool bit = ((value >> i) & 1) != 0;
            data_lines[i]->voltage = bit ? 5.0 : 0.0;
            data_lines_bar[i]->voltage = bit ? 0.0 : 5.0;
        }
    }
}

void IdealRamCore::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    (void)A;
    (void)z;
    (void)nodes;
    (void)dt;
}
