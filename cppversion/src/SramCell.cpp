#include "SramCell.h"
#include "Nmos.h"
#include "Inverter.h"

SramCell::SramCell(Node* wl, Node* bl, Node* bl_b, Node* v, Node* g, bool init_one)
    : wl(wl), bl(bl), bl_b(bl_b), vdd(v), gnd(g), initial_one(init_one) {}

void SramCell::build(Circuit& circuit) {
    // 6T SRAM Cell
    // 1. Два перекрестно-соединенных инвертора (хранение)
    Node* q = circuit.create_node();
    Node* q_bar = circuit.create_node();
    q->voltage = initial_one ? 5.0 : 0.0;
    q_bar->voltage = initial_one ? 0.0 : 5.0;

    // Инвертор 1: Q -> Q_bar
    Inverter inv1(q, q_bar, vdd, gnd);
    inv1.build(circuit);

    // Инвертор 2: Q_bar -> Q
    Inverter inv2(q_bar, q, vdd, gnd);
    inv2.build(circuit);

    // 2. Два транзистора доступа (чтение/запись)
    // NMOS 1: Подключает Q к BL, управляется WL
    // Внимание: NMOS(Drain, Source, Gate, ...)
    // Подключаем BL к Q через транзистор
    circuit.add_component(new Nmos(bl, q, wl, 0.5, 0.01));

    // NMOS 2: Подключает Q_bar к BL_bar, управляется WL
    circuit.add_component(new Nmos(bl_b, q_bar, wl, 0.5, 0.01));
}
