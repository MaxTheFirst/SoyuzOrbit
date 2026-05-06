import pygame
import numpy as np

# --- ПАРАМЕТРЫ ---
WIDTH, HEIGHT = 512, 512
λ = 550e-9  # длина волны (м)
k = 2 * np.pi / λ
dx = 1e-6   # шаг сетки
z_focus = 1e-3  # начальный фокус

NA_values = [0.1, 0.25, 0.5, 0.75]
NA_index = 1

# --- FFT ---
def fft2c(u):
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(u)))

def ifft2c(U):
    return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(U)))

# --- Френель ---
def fresnel_propagation(U, z):
    fx = np.fft.fftfreq(WIDTH, d=dx)
    fy = np.fft.fftfreq(HEIGHT, d=dx)
    FX, FY = np.meshgrid(fx, fy)

    H = np.exp(-1j * np.pi * λ * z * (FX**2 + FY**2))
    return ifft2c(fft2c(U) * H)

# --- Объект ---
def create_object():
    x = np.linspace(-1, 1, WIDTH)
    y = np.linspace(-1, 1, HEIGHT)
    X, Y = np.meshgrid(x, y)

    # пример: круг + текстура
    obj = np.exp(-((X**2 + Y**2) * 20))
    obj += 0.3 * np.sin(20 * X) * np.sin(20 * Y)

    return obj

# --- Объектив ---
def lens(U, NA):
    fx = np.fft.fftfreq(WIDTH, d=dx)
    fy = np.fft.fftfreq(HEIGHT, d=dx)
    FX, FY = np.meshgrid(fx, fy)

    cutoff = NA / λ
    aperture = (FX**2 + FY**2) < cutoff**2

    U_f = fft2c(U)
    U_f *= aperture

    return ifft2c(U_f)

# --- Интенсивность ---
def intensity(U):
    return np.abs(U)**2

# --- PYGAME ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

obj = create_object()
U = obj.astype(np.complex128)

running = True

while running:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                z_focus += 0.0002
            if event.key == pygame.K_DOWN:
                z_focus -= 0.0002
            if event.key == pygame.K_RIGHT:
                NA_index = (NA_index + 1) % len(NA_values)
            if event.key == pygame.K_LEFT:
                NA_index = (NA_index - 1) % len(NA_values)

    NA = NA_values[NA_index]

    # --- модель микроскопа ---
    U1 = fresnel_propagation(U, z_focus)
    U2 = lens(U1, NA)
    U3 = fresnel_propagation(U2, -z_focus)

    I = intensity(U3)

    # нормализация
    I /= I.max()
    img = (I * 255).astype(np.uint8)

    # в pygame
    surface = pygame.surfarray.make_surface(np.stack([img]*3, axis=-1))
    screen.blit(surface, (0, 0))

    pygame.display.set_caption(f"NA={NA:.2f}  focus={z_focus:.5f}")
    pygame.display.flip()
    clock.tick(30)

pygame.quit()
