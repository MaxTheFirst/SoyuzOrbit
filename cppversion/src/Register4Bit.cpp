#include "Register4Bit.h"
#include "AndGate.h"
#include "Inverter.h"
#include "Nmos.h"
#include "Pmos.h"
#include "Resistor.h"

Register4Bit::Register4Bit(std::vector<Node*> d, std::vector<Node*> q, Node* clk, Node* we, Node* v, Node* g)
    : d(d), q(q), clk(clk), write_enable(we), vdd(v), gnd(g) {}

void Register4Bit::build(Circuit& circuit) {
    for (int i = 0; i < 4; ++i) {
        Node* q_bar = circuit.create_node();
        Node* m_q = circuit.create_node();
        Node* m_q_bar = circuit.create_node();

        circuit.add_component(new Resistor(m_q, gnd, 200000));
        circuit.add_component(new Resistor(m_q_bar, vdd, 200000));
        circuit.add_component(new Resistor(q[i], gnd, 200000));
        circuit.add_component(new Resistor(q_bar, vdd, 200000));

        Node* master_we = circuit.create_node();
        AndGate master_we_gate(clk, write_enable, master_we, vdd, gnd);
        master_we_gate.build(circuit);

        Node* master_we_bar = circuit.create_node();
        Inverter inv_master_we(master_we, master_we_bar, vdd, gnd);
        inv_master_we.build(circuit);

        Node* slave_we = master_we_bar;
        Node* slave_we_bar = master_we;

        Node* d_bar = circuit.create_node();
        Inverter inv_d(d[i], d_bar, vdd, gnd);
        inv_d.build(circuit);

        // Master latch.
        Inverter m_inv1(m_q, m_q_bar, vdd, gnd);
        m_inv1.build(circuit);
        Inverter m_inv2(m_q_bar, m_q, vdd, gnd);
        m_inv2.build(circuit);
        circuit.add_component(new Nmos(m_q, d[i], master_we, 0.5, 0.01));
        circuit.add_component(new Pmos(m_q, d[i], master_we_bar, -0.5, 0.01));
        circuit.add_component(new Nmos(m_q_bar, d_bar, master_we, 0.5, 0.01));
        circuit.add_component(new Pmos(m_q_bar, d_bar, master_we_bar, -0.5, 0.01));

        // Slave latch -> Q.
        Inverter s_inv1(q[i], q_bar, vdd, gnd);
        s_inv1.build(circuit);
        Inverter s_inv2(q_bar, q[i], vdd, gnd);
        s_inv2.build(circuit);
        circuit.add_component(new Nmos(q[i], m_q, slave_we, 0.5, 0.01));
        circuit.add_component(new Pmos(q[i], m_q, slave_we_bar, -0.5, 0.01));
        circuit.add_component(new Nmos(q_bar, m_q_bar, slave_we, 0.5, 0.01));
        circuit.add_component(new Pmos(q_bar, m_q_bar, slave_we_bar, -0.5, 0.01));
    }
}
