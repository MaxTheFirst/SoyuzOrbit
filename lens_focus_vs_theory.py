import matplotlib.pyplot as plt
import numpy as np

from lens_wave_optics import (
    LensSpec,
    airy_radius,
    angular_spectrum_propagate,
    bk7_refractive_index,
    effective_focal_length,
    focus_scan,
    gaussian_image_distance,
    make_grid,
    point_source,
    real_lens_transmission,
    rms_spot_radius,
)


wavelength = 532e-9
refractive_index = bk7_refractive_index(wavelength)

lens = LensSpec(
    wavelength=wavelength,
    refractive_index=refractive_index,
    aperture_radius=1.8e-3,
    radius_front=24e-3,
    radius_back=24e-3,
    center_thickness=4.2e-3,
)

source_distance = 120e-3
window_size = 9e-3
samples = 512
x, X, Y, dx = make_grid(window_size, samples)

field_at_lens = point_source(X, Y, wavelength, source_distance)
field_after_lens = field_at_lens * real_lens_transmission(X, Y, lens)

f_eff = effective_focal_length(lens)
image_distance_theory = gaussian_image_distance(source_distance, f_eff)

scan_distances = np.linspace(0.7 * image_distance_theory, 1.3 * image_distance_theory, 31)
scan = focus_scan(field_after_lens, wavelength, dx, scan_distances, X, Y, roi_radius=0.3e-3)
z_axis = scan["best_axis_distance"]
z_rms = scan["best_rms_distance"]

screen_axis = angular_spectrum_propagate(field_after_lens, wavelength, dx, z_axis)
screen_rms = angular_spectrum_propagate(field_after_lens, wavelength, dx, z_rms)

intensity_axis = np.abs(screen_axis) ** 2
intensity_rms = np.abs(screen_rms) ** 2
spot_radius = rms_spot_radius(intensity_rms, X, Y, roi_radius=0.3e-3)
airy = airy_radius(wavelength, z_rms, lens.aperture_radius)

print("--- Теоретический и фактический фокус ---")
print(f"Расстояние от источника до линзы: {source_distance * 1000:.1f} мм")
print(f"Эффективное фокусное расстояние линзы: {f_eff * 1000:.2f} мм")
print(f"Тонколинзовый расчет изображения: {image_distance_theory * 1000:.2f} мм")
print(f"Максимум интенсивности на оси: {z_axis * 1000:.2f} мм")
print(f"Минимум RMS-пятна: {z_rms * 1000:.2f} мм")
print(f"Разница теория - минимум RMS: {(z_rms - image_distance_theory) * 1e6:.1f} мкм")
print(f"RMS-радиус пятна: {spot_radius * 1e6:.1f} мкм")
print(f"Дифракционный радиус Эйри: {airy * 1e6:.1f} мкм")

plt.figure(figsize=(15, 5))

plt.subplot(1, 3, 1)
plt.title("Интенсивность на оси vs z")
plt.plot(scan_distances * 1000, scan["on_axis"], linewidth=3, color="navy")
plt.axvline(image_distance_theory * 1000, color="red", linestyle="--", label="Теория тонкой линзы")
plt.axvline(z_axis * 1000, color="green", linestyle=":", label="Пик на оси")
plt.axvline(z_rms * 1000, color="purple", linestyle="-.", label="Мин. RMS")
plt.xlabel("z от линзы, мм")
plt.ylabel("I(0, 0)")
plt.grid(alpha=0.3)
plt.legend(fontsize=8)

plt.subplot(1, 3, 2)
plt.title("Экран в плоскости пика на оси")
plt.imshow(
    intensity_axis**0.35,
    extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
    cmap="hot",
)
plt.xlabel("x, мм")
plt.ylabel("y, мм")
plt.xlim(-0.25, 0.25)
plt.ylim(-0.25, 0.25)

plt.subplot(1, 3, 3)
plt.title("Экран в плоскости минимума RMS")
plt.imshow(
    intensity_rms**0.35,
    extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
    cmap="hot",
)
plt.xlabel("x, мм")
plt.ylabel("y, мм")
plt.xlim(-0.25, 0.25)
plt.ylim(-0.25, 0.25)

plt.tight_layout()
plt.show()
