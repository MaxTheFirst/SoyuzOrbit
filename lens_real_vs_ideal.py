import matplotlib.pyplot as plt
import numpy as np

from lens_wave_optics import (
    LensSpec,
    angular_spectrum_propagate,
    back_focal_length,
    bk7_refractive_index,
    effective_focal_length,
    focus_scan,
    ideal_lens_transmission,
    lens_thickness,
    make_grid,
    plane_wave,
    real_lens_transmission,
)


wavelength = 532e-9
refractive_index = bk7_refractive_index(wavelength)

lens = LensSpec(
    wavelength=wavelength,
    refractive_index=refractive_index,
    aperture_radius=2.2e-3,
    radius_front=22e-3,
    radius_back=22e-3,
    center_thickness=4.4e-3,
)

window_size = 10e-3
samples = 512
x, X, Y, dx = make_grid(window_size, samples)

f_eff = effective_focal_length(lens)
bfl = back_focal_length(lens)

field_in = plane_wave(X.shape)
field_real = field_in * real_lens_transmission(X, Y, lens)
field_ideal = field_in * ideal_lens_transmission(X, Y, wavelength, f_eff, lens.aperture_radius)

scan_distances = np.linspace(0.8 * bfl, 1.2 * bfl, 25)
scan_real = focus_scan(field_real, wavelength, dx, scan_distances, X, Y, roi_radius=0.3e-3)
scan_ideal = focus_scan(field_ideal, wavelength, dx, scan_distances, X, Y, roi_radius=0.3e-3)

screen_real = angular_spectrum_propagate(field_real, wavelength, dx, scan_real["best_rms_distance"])
screen_ideal = angular_spectrum_propagate(field_ideal, wavelength, dx, scan_ideal["best_rms_distance"])

phase_real = np.angle(real_lens_transmission(X, Y, lens))
phase_ideal = np.angle(ideal_lens_transmission(X, Y, wavelength, f_eff, lens.aperture_radius))
phase_error = np.angle(np.exp(1j * (phase_real - phase_ideal)))
phase_error[lens_thickness(X, Y, lens) <= 0.0] = np.nan

print("--- Реальная сферическая линза vs идеальная квадратичная фаза ---")
print(f"Эффективное фокусное расстояние: {f_eff * 1000:.2f} мм")
print(f"Реальная линза, лучший RMS-фокус: {scan_real['best_rms_distance'] * 1000:.2f} мм")
print(f"Идеальная линза, лучший RMS-фокус: {scan_ideal['best_rms_distance'] * 1000:.2f} мм")
print(
    f"Дополнительный фокус-сдвиг из-за сферического профиля: "
    f"{(scan_real['best_rms_distance'] - scan_ideal['best_rms_distance']) * 1e6:.1f} мкм"
)

plt.figure(figsize=(14, 8))

plt.subplot(2, 2, 1)
plt.title("Фазовая ошибка реальной линзы")
plt.imshow(
    phase_error,
    extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
    cmap="twilight",
)
plt.colorbar(label="рад")
plt.xlabel("x, мм")
plt.ylabel("y, мм")

plt.subplot(2, 2, 2)
plt.title("Фокус: реальная линза")
plt.imshow(
    np.abs(screen_real) ** 2,
    extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
    cmap="hot",
)
plt.xlabel("x, мм")
plt.ylabel("y, мм")
plt.xlim(-0.25, 0.25)
plt.ylim(-0.25, 0.25)

plt.subplot(2, 2, 3)
plt.title("Фокус: идеальная линза")
plt.imshow(
    np.abs(screen_ideal) ** 2,
    extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
    cmap="hot",
)
plt.xlabel("x, мм")
plt.ylabel("y, мм")
plt.xlim(-0.25, 0.25)
plt.ylim(-0.25, 0.25)

plt.subplot(2, 2, 4)
plt.title("RMS-радиус вдоль оси")
plt.plot(scan_distances * 1000, scan_real["rms_radius"] * 1e6, linewidth=3, label="Реальная линза")
plt.plot(scan_distances * 1000, scan_ideal["rms_radius"] * 1e6, linewidth=2, linestyle="--", label="Идеальная линза")
plt.xlabel("z от линзы, мм")
plt.ylabel("RMS-радиус, мкм")
plt.grid(alpha=0.3)
plt.legend()

plt.tight_layout()
plt.show()
