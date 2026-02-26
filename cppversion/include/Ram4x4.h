#ifndef RAM4X4_H
#define RAM4X4_H

#include "Gate.h"
#include "SramCell.h"
#include "Decoder2to4.h"
#include <array>
#include <vector>

class Ram4x4 : public Gate {
public:
    // --- Интерфейс ---
    // Адрес (2 бита)
    Node* addr0;
    Node* addr1;
    // Шина данных (4 бита)
    std::vector<Node*> data_lines;
    std::vector<Node*> data_lines_bar; // Инверсные линии
    // Управление
    Node* write_enable; // 1 = Запись, 0 = Чтение
    Node* vdd;
    Node* gnd;
    std::array<int, 4> init_words;

    Ram4x4(
        Node* a0,
        Node* a1,
        std::vector<Node*> d,
        std::vector<Node*> d_b,
        Node* we,
        Node* v,
        Node* g,
        std::array<int, 4> init = {0, 0, 0, 0}
    );
    void build(Circuit& circuit) override;
};

#endif // RAM4X4_H
