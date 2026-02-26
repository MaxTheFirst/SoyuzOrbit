#ifndef MNASOLVER_H
#define MNASOLVER_H

#include "Solver.h"

class MnaSolver : public Solver {
public:
    void solve(Circuit& circuit, double dt) override;
};

#endif // MNASOLVER_H
