import numpy as fallback_np

try:
    import cupy as np
    print("✅ Успешно импортирован CuPy. Симуляция будет на GPU.")
except ImportError:
    np = fallback_np
    print("⚠️ CuPy не найден. Симуляция будет на CPU (NumPy).")

# Определяем, нужно ли вызывать .get() для копирования с GPU
USING_GPU = (np != fallback_np)

def to_cpu(arr):
    """Конвертирует массив в NumPy, если он был на GPU."""
    if USING_GPU:
        return arr.get()
    return arr