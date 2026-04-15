import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. ФИЗИЧЕСКИЕ ПАРАМЕТРЫ
# ==========================================
wavelength = 0.5e-6    # 500 нм
k = 2 * np.pi / wavelength

# ГЕОМЕТРИЯ: Теперь у нас две важные дистанции
z_src = 0.05           # От источника до преграды (5 см)
z_scr = 0.05           # От преграды до экрана (5 см)

# РАСЧЕТНАЯ ПРОВЕРКА (Новая формула зон Френеля)
# Для сферической волны: R_m = sqrt(m * lambda * (z_src * z_scr) / (z_src + z_scr))
m = 4  # Проверяем 2-ю зону (в центре должна быть черная точка)
R_ideal = np.sqrt(m * wavelength * (z_src * z_scr) / (z_src + z_scr))
R = R_ideal

print(f"--- Параметры системы ---")
print(f"z_источник: {z_src*100} см | z_экран: {z_scr*100} см")
print(f"Эффективное z_eff: {(z_src * z_scr / (z_src + z_scr))*100:.2f} см")
print(f"Установленный радиус отверстия: {R*1000:.4f} мм")

# Параметры сетки
L = 0.002              # 2 мм
N = 1000
dx = L / N

# ==========================================
# 2. ПАДАЮЩЕЕ ПОЛЕ (СФЕРИЧЕСКАЯ ВОЛНА)
# ==========================================
x = np.arange(-N//2, N//2) * dx
y = np.arange(-N//2, N//2) * dx
X, Y = np.meshgrid(x, y)

# Точное расстояние от источника до каждой точки отверстия
r_src = np.sqrt(X**2 + Y**2 + z_src**2)

# Поле непосредственно ПЕРЕД преградой (уже не константа 1.0!)
# Амплитуда падает как 1/r, фаза крутится как exp(-ikr)
E_inc = (1.0 / r_src) * np.exp(-1j * k * r_src)

# Маска отверстия
Mask = np.zeros((N, N))
Mask[X**2 + Y**2 <= R**2] = 1.0

# Поле на выходе из преграды
E_out = E_inc * Mask

# ==========================================
# 3. ПРОПАГАТОР (БПФ-СВЕРТКА)
# ==========================================
E_padded = np.pad(E_out, pad_width=N//2, mode='constant')

x_pad = np.arange(-N, N) * dx
y_pad = np.arange(-N, N) * dx
X_p, Y_p = np.meshgrid(x_pad, y_pad)

r_scr = np.sqrt(X_p**2 + Y_p**2 + z_scr**2)
h = np.exp(-1j * k * r_scr) / r_scr
H_freq = np.fft.fft2(np.fft.ifftshift(h))

E_freq = np.fft.fft2(E_padded)
E_screen_full = np.fft.ifft2(E_freq * H_freq)

E_screen = E_screen_full[N//2 : N//2 + N, N//2 : N//2 + N]
I = np.abs(E_screen)**2

# ==========================================
# 4. ВИЗУАЛИЗАЦИЯ
# ==========================================
plt.figure(figsize=(12, 5))

# Левый график: Фаза. Если бы волна была плоской, здесь был бы один цвет.
# Но мы видим кольца — это и есть кривизна "пузыря" света от близкого источника.
plt.subplot(1, 2, 1)
plt.title("Фаза падающей волны в отверстии")
phase = np.angle(E_out)
phase[Mask == 0] = np.nan
plt.imshow(phase, extent=(-L/2*1000, L/2*1000, -L/2*1000, L/2*1000), cmap='twilight')
plt.colorbar(label='Радианы')
plt.xlabel("мм")

# Правый график: Результат. Благодаря новой формуле R_m,
# мы точно попали во 2-ю зону: центр экрана темный.
plt.subplot(1, 2, 2)
plt.title(f"Интенсивность на экране (m={m})")
plt.imshow(I**0.5, extent=(-L/2*1000, L/2*1000, -L/2*1000, L/2*1000), cmap='hot')
plt.xlabel("мм")

plt.tight_layout()
plt.show()