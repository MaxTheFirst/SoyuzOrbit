import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. ФИЗИЧЕСКИЕ ПАРАМЕТРЫ И РАСЧЕТЫ
# ==========================================
wavelength = 0.5e-6    # Длина волны: 500 нм (зеленый свет)
k = 2 * np.pi / wavelength
z = 0.1                # Расстояние до экрана: 10 см

# Геометрия преграды (Опыт Юнга - 2 щели)
d = 0.00004            # Ширина одной щели: 40 мкм
D = 0.0002             # Расстояние между центрами щелей: 200 мкм
slit_height = 0.001    # Высота щелей: 1 мм

# --- ТЕОРЕТИЧЕСКИЕ РАСЧЕТЫ ---
S_diff = (wavelength * z) / d  # Граница дифракционной огибающей (первый ноль)
S_int = (wavelength * z) / D   # Шаг интерференционной "зебры" (между максимумами)

print(f"--- Теоретические расчеты ---")
print(f"Ширина щели (d): {d*1000} мм | Расстояние между щелями (D): {D*1000} мм")
print(f"Шаг зебры (S_int): {S_int*1000} мм")
print(f"Первый ноль огибающей (S_diff): {S_diff*1000} мм")
print(f"Количество ярких полос в центральном пятне: ~ {int(2 * S_diff / S_int)}")
print(f"-----------------------------")

# Параметры сетки
L = 0.004              # Физический размер моделируемой области: 4 мм
N = 1000               # Разрешение сетки
dx = L / N             # Физический размер одного пикселя
print(f"Запуск симуляции (Сетка {N}x{N})...")

# ==========================================
# 2. ПОДГОТОВКА ПРОСТРАНСТВА И ПРЕГРАДЫ
# ==========================================
# Используем arange для идеального нуля в центре
x = np.arange(-N//2, N//2) * dx
y = np.arange(-N//2, N//2) * dx
X, Y = np.meshgrid(x, y)

# Матрица преграды (2 щели)
E_out = np.zeros((N, N))
E_out[(np.abs(Y) < slit_height/2) & (np.abs(X - D/2) < d/2)] = 1.0  # Правая щель
E_out[(np.abs(Y) < slit_height/2) & (np.abs(X + D/2) < d/2)] = 1.0  # Левая щель

# ==========================================
# 3. ЗАЩИТА ОТ АРТЕФАКТОВ (Zero-Padding)
# ==========================================
E_padded = np.pad(E_out, pad_width=N//2, mode='constant', constant_values=0)

x_pad = np.arange(-N, N) * dx
y_pad = np.arange(-N, N) * dx
X_pad, Y_pad = np.meshgrid(x_pad, y_pad)

# ==========================================
# 4. ИМПУЛЬСНЫЙ ОТКЛИК И ФУРЬЕ-СВЕРТКА
# ==========================================
r = np.sqrt(X_pad**2 + Y_pad**2 + z**2)
h = np.exp(-1j * k * r) / r
h_shifted = np.fft.ifftshift(h)

H_freq = np.fft.fft2(h_shifted)
E_freq = np.fft.fft2(E_padded)

E_screen_padded = np.fft.ifft2(E_freq * H_freq)

# ==========================================
# 5. ВОЗВРАТ К РЕАЛЬНОСТИ И ОТРИСОВКА
# ==========================================
E_screen = E_screen_padded[N//2 : N//2 + N, N//2 : N//2 + N]
I = np.abs(E_screen)**2

# --- Подготовка 1D Графика ---
# Срез симуляции
I_sim_1d = I[N//2, :]
I_sim_1d = I_sim_1d / np.max(I_sim_1d) # Нормируем

# Теоретическая дифракционная огибающая (sinc^2)
# np.sinc(x) вычисляет sin(pi*x)/(pi*x), поэтому pi внутри не пишем
I_diff_envelope = np.sinc((d * x) / (wavelength * z))**2

# Теоретическая интерференция (cos^2)
I_interference = np.cos((np.pi * D * x) / (wavelength * z))**2

# Полная теория = Огибающая * Интерференция
I_theory_1d = I_diff_envelope * I_interference

# --- Визуализация ---
plt.figure(figsize=(16, 6))

# 1. Преграда
plt.subplot(1, 3, 1)
plt.title("Преграда (2 щели)")
plt.imshow(E_out, extent=(-L/2*1000, L/2*1000, -L/2*1000, L/2*1000), cmap='gray')
plt.xlabel("мм")
plt.ylabel("мм")

# 2. Экран 2D
plt.subplot(1, 3, 2)
plt.title(f"Экран на расстоянии z = {z*100} см")
# Используем гамма-коррекцию 0.5 для лучшей видимости слабых пиков
plt.imshow(I**0.5, extent=(-L/2*1000, L/2*1000, -L/2*1000, L/2*1000), cmap='hot')
plt.xlabel("мм")

# 3. График 1D
plt.subplot(1, 3, 3)
plt.title("1D Срез: Дифракция + Интерференция")
plt.plot(x * 1000, I_sim_1d, label='Симуляция', color='blue', linewidth=4, alpha=0.5)
plt.plot(x * 1000, I_theory_1d, label='Теория', color='red', linestyle='--', linewidth=2)
plt.plot(x * 1000, I_diff_envelope, label='Огибающая (sinc²)', color='orange', linestyle=':', linewidth=2)

# Линии для проверки S_int (Шаг зебры)
# Отметим первые два боковых максимума
plt.axvline(x=S_int*1000, color='green', linestyle='-', alpha=0.5, label=f'Шаг S_int ({S_int*1000} мм)')
plt.axvline(x=-S_int*1000, color='green', linestyle='-', alpha=0.5)
plt.axvline(x=2*S_int*1000, color='green', linestyle=':', alpha=0.5)
plt.axvline(x=-2*S_int*1000, color='green', linestyle=':', alpha=0.5)

# Линии для проверки S_diff (Ноль огибающей)
plt.axvline(x=S_diff*1000, color='purple', linestyle='-', alpha=0.8, label=f'Ноль S_diff ({S_diff*1000} мм)')
plt.axvline(x=-S_diff*1000, color='purple', linestyle='-', alpha=0.8)

plt.xlabel("Координата X (мм)")
plt.ylabel("Интенсивность (норм.)")
plt.legend(loc='upper right', fontsize=8)
plt.grid(True, alpha=0.3)
plt.xlim(-2, 2)

plt.tight_layout()
plt.show()