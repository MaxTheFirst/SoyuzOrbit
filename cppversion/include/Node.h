#ifndef NODE_H
#define NODE_H

#include <vector>

class Component;

class Node {
public:
    double voltage;
    int index; // Индекс узла в MNA-матрице
    bool is_ground;
    bool is_forced;
    double forced_voltage;

    Node();
};

#endif // NODE_H
