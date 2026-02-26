#include "IdealControlCore.h"

IdealControlCore::IdealControlCore(
    std::vector<Node*> micro,
    std::vector<Node*> ir,
    Node* ir_we,
    Node* a_we,
    Node* pc_we,
    Node* ram_oe,
    Node* halted_node,
    Node* p0,
    Node* p1,
    Node* p2
) : micro_out(std::move(micro)),
    ir_out(std::move(ir)),
    ir_write_enable(ir_we),
    reg_a_write_enable(a_we),
    pc_write_enable(pc_we),
    ram_out_enable(ram_oe),
    halted(halted_node),
    phase0(p0),
    phase1(p1),
    phase2(p2) {
    n1 = this->micro_out.empty() ? nullptr : this->micro_out[0];
    n2 = this->ir_out.empty() ? nullptr : this->ir_out[0];

    ir_write_enable->is_forced = true;
    reg_a_write_enable->is_forced = true;
    pc_write_enable->is_forced = true;
    ram_out_enable->is_forced = true;
    halted->is_forced = true;
    phase0->is_forced = true;
    phase1->is_forced = true;
    phase2->is_forced = true;
}

void IdealControlCore::step(double dt) {
    (void)dt;

    const int phase = ((micro_out[1]->voltage > 2.5) ? 2 : 0) |
                      ((micro_out[0]->voltage > 2.5) ? 1 : 0);
    const bool p0 = (phase == 0);
    const bool p1 = (phase == 1);
    const bool p2 = (phase == 2);

    int ir = 0;
    for (int i = 0; i < 4; ++i) {
        if (ir_out[i]->voltage > 2.5) {
            ir |= (1 << i);
        }
    }

    const bool is_load_a = (ir == 1);
    const bool is_halt = (ir == 15);

    ir_write_enable->forced_voltage = p0 ? 5.0 : 0.0;
    reg_a_write_enable->forced_voltage = (p1 && is_load_a) ? 5.0 : 0.0;
    pc_write_enable->forced_voltage = (p0 || (p1 && is_load_a)) ? 5.0 : 0.0;
    ram_out_enable->forced_voltage = (p0 || (p1 && is_load_a)) ? 5.0 : 0.0;
    halted->forced_voltage = (p2 && is_halt) ? 5.0 : 0.0;
    phase0->forced_voltage = p0 ? 5.0 : 0.0;
    phase1->forced_voltage = p1 ? 5.0 : 0.0;
    phase2->forced_voltage = p2 ? 5.0 : 0.0;

    ir_write_enable->voltage = ir_write_enable->forced_voltage;
    reg_a_write_enable->voltage = reg_a_write_enable->forced_voltage;
    pc_write_enable->voltage = pc_write_enable->forced_voltage;
    ram_out_enable->voltage = ram_out_enable->forced_voltage;
    halted->voltage = halted->forced_voltage;
    phase0->voltage = phase0->forced_voltage;
    phase1->voltage = phase1->forced_voltage;
    phase2->voltage = phase2->forced_voltage;
}

void IdealControlCore::stamp(Matrix& A, std::vector<double>& z, const std::vector<Node*>& nodes, double dt) {
    (void)A;
    (void)z;
    (void)nodes;
    (void)dt;
}
