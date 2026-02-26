#include "Ram4x4.h"
#include "Inverter.h"
#include "Resistor.h"
#include "TriStateBuffer.h"

Ram4x4::Ram4x4(
    Node* a0,
    Node* a1,
    std::vector<Node*> d,
    std::vector<Node*> d_b,
    Node* we,
    Node* v,
    Node* g,
    std::array<int, 4> init
)
    : addr0(a0), addr1(a1), data_lines(d), data_lines_bar(d_b), write_enable(we), vdd(v), gnd(g), init_words(init) {}

void Ram4x4::build(Circuit& circuit) {
    // 1. Декодер адреса
    std::vector<Node*> word_lines(4);
    for (int i = 0; i < 4; ++i) {
        word_lines[i] = circuit.create_node();
    }

    Decoder2to4 decoder(addr0, addr1, word_lines, vdd, gnd);
    decoder.build(circuit);

    // 2. Внутренние битовые линии матрицы памяти
    std::vector<Node*> bit_lines(4);
    std::vector<Node*> bit_lines_bar(4);
    for (int i = 0; i < 4; ++i) {
        bit_lines[i] = circuit.create_node();
        bit_lines_bar[i] = circuit.create_node();
    }

    // 3. Матрица 4x4 из SRAM-ячеек
    for (int row = 0; row < 4; ++row) {
        for (int col = 0; col < 4; ++col) {
            const bool init_one = ((init_words[row] >> col) & 1) != 0;
            SramCell cell(word_lines[row], bit_lines[col], bit_lines_bar[col], vdd, gnd, init_one);
            cell.build(circuit);
        }
    }

    // 4. Precharge bitline в режиме чтения
    for (int i = 0; i < 4; ++i) {
        circuit.add_component(new Resistor(vdd, bit_lines[i], 10000));
        circuit.add_component(new Resistor(vdd, bit_lines_bar[i], 10000));
    }

    // 5. Режим чтение/запись
    Node* read_enable = circuit.create_node();
    Inverter inv_we(write_enable, read_enable, vdd, gnd);
    inv_we.build(circuit);

    // 6. Write drivers: внешняя шина -> внутренние bitline
    for (int i = 0; i < 4; ++i) {
        TriStateBuffer wr_bl(data_lines[i], write_enable, bit_lines[i], vdd, gnd);
        wr_bl.build(circuit);

        TriStateBuffer wr_bl_bar(data_lines_bar[i], write_enable, bit_lines_bar[i], vdd, gnd);
        wr_bl_bar.build(circuit);
    }

    // 7. Read path: внутренние bitline -> внешняя шина
    for (int i = 0; i < 4; ++i) {
        TriStateBuffer rd_bl(bit_lines[i], read_enable, data_lines[i], vdd, gnd);
        rd_bl.build(circuit);

        TriStateBuffer rd_bl_bar(bit_lines_bar[i], read_enable, data_lines_bar[i], vdd, gnd);
        rd_bl_bar.build(circuit);
    }
}
