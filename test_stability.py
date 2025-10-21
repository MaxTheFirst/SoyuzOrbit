# test_stability.py
import numpy as np
import config

def test_parameters():
    """Проверяет параметры на стабильность."""
    print("Stability analysis...")
    
    # Критерий Куранта для численной стабильности
    k = config.DEFAULT_SPRING_CONSTANT
    m = config.DEFAULT_MASS
    dt = config.TIME_STEP
    
    # Собственная частота системы
    omega = np.sqrt(k / m)
    
    # Критерий стабильности
    stability_criterion = dt * omega
    
    print(f"Spring constant: {k}")
    print(f"Mass: {m}")
    print(f"Time step: {dt}")
    print(f"Natural frequency: {omega:.4f} rad/s")
    print(f"Stability criterion (dt * omega): {stability_criterion:.4f}")
    
    if stability_criterion < 2:
        print("✓ Parameters are numerically stable")
    else:
        print("✗ Parameters may be unstable! Consider smaller time step or spring constant")
    
    # Проверка смещения
    print(f"\nInitial displacement: ({config.INITIAL_DISPLACEMENT_X}, {config.INITIAL_DISPLACEMENT_Y})")
    if max(config.INITIAL_DISPLACEMENT_X, config.INITIAL_DISPLACEMENT_Y) < 0.5:
        print("✓ Initial displacement is reasonable")
    else:
        print("✗ Initial displacement may be too large")

if __name__ == "__main__":
    test_parameters()