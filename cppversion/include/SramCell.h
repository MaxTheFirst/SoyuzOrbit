#ifndef SRAMCELL_H
#define SRAMCELL_H

#include "Gate.h"
#include "Inverter.h"
#include "Nmos.h"

class SramCell : public Gate {
public:
    Node* wl;    // Word Line (вход)
    Node* bl;    // Bit Line (вход/выход)
    Node* bl_b;  // Bit Line Bar (вход/выход)
    Node* vdd;
    Node* gnd;
    bool initial_one;

    SramCell(Node* wl, Node* bl, Node* bl_b, Node* v, Node* g, bool init_one = false);
    void build(Circuit& circuit) override;
};

#endif // SRAMCELL_H
