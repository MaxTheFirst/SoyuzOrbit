#ifndef SOLVER_H
#define SOLVER_H

class Circuit;

class Solver {
public:
    virtual ~Solver() = default;
    virtual void solve(Circuit& circuit, double dt) = 0;
};

class IterativeSolver : public Solver {
public:
    void solve(Circuit& circuit, double dt) override;
};

#endif // SOLVER_H
