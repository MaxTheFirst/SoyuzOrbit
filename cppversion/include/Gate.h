#ifndef GATE_H
#define GATE_H

#include "Circuit.h"
#include "Node.h"

// Базовый класс для всех логических элементов
class Gate {
public:
    virtual ~Gate() = default;
    // Метод для подключения элемента к схеме
    virtual void build(Circuit& circuit) = 0;
};

#endif // GATE_H
