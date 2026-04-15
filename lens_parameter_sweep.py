import matplotlib.pyplot as plt
import numpy as np

from lens_wave_optics import (
    LensSpec,
    airy_radius,
    angular_spectrum_propagate,
    back_focal_length,
    bk7_refractive_index,
    focus_scan,
    make_grid,
    plane_wave,
    real_lens_transmission,
    rms_spot_radius,
)


wavelength = 532e-9
refractive_index = bk7_refractive_index(wavelength)
window_size = 10e-3
samples = 512
x, X, Y, dx = make_grid(window_size, samples)

apertures = [1.0e-3, 1.6e-3, 2.4e-3]
spots = []
real_focuses = []
airy_radii = []
theory_focuses = []

plt.figure(figsize=(15, 5))

for index, aperture_radius in enumerate(apertures, start=1):
    lens = LensSpec(
        wavelength=wavelength,
        refractive_index=refractive_index,
        aperture_radius=aperture_radius,
        radius_front=25e-3,
        radius_back=25e-3,
        center_thickness=4.0e-3,
    )

    field_after_lens = plane_wave(X.shape) * real_lens_transmission(X, Y, lens)
    theory_focus = back_focal_length(lens)
    scan_distances = np.linspace(0.8 * theory_focus, 1.25 * theory_focus, 21)
    scan = focus_scan(field_after_lens, wavelength, dx, scan_distances, X, Y, roi_radius=0.3e-3)
    z_real = scan["best_rms_distance"]
    screen = angular_spectrum_propagate(field_after_lens, wavelength, dx, z_real)
    intensity = np.abs(screen) ** 2
    spot = rms_spot_radius(intensity, X, Y, roi_radius=0.3e-3)
    airy = airy_radius(wavelength, z_real, aperture_radius)

    spots.append(spot)
    real_focuses.append(z_real)
    airy_radii.append(airy)
    theory_focuses.append(theory_focus)

    print(
        f"Апертура {2 * aperture_radius * 1000:.1f} мм | "
        f"BFL = {theory_focus * 1000:.2f} мм | "
        f"реальный фокус = {z_real * 1000:.2f} мм | "
        f"RMS = {spot * 1e6:.1f} мкм | "
        f"Эйри = {airy * 1e6:.1f} мкм"
    )

    plt.subplot(1, 3, index)
    plt.title(f"D = {2 * aperture_radius * 1000:.1f} мм")
    plt.imshow(
        intensity**0.35,
        extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
        cmap="hot",
    )
    plt.xlabel("x, мм")
    plt.ylabel("y, мм")
    plt.xlim(-0.22, 0.22)
    plt.ylim(-0.22, 0.22)

plt.tight_layout()

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.title("Размер пятна vs апертура")
plt.plot(np.array(apertures) * 2000, np.array(spots) * 1e6, "o-", linewidth=3, label="RMS-пятно")
plt.plot(np.array(apertures) * 2000, np.array(airy_radii) * 1e6, "s--", linewidth=2, label="Предел Эйри")
plt.xlabel("Диаметр апертуры, мм")
plt.ylabel("Радиус, мкм")
plt.grid(alpha=0.3)
plt.legend()

plt.subplot(1, 2, 2)
plt.title("Смещение фокуса vs апертура")
plt.plot(
    np.array(apertures) * 2000,
    (np.array(real_focuses) - np.array(theory_focuses)) * 1e6,
    "o-",
    linewidth=3,
    color="darkred",
)
plt.xlabel("Диаметр апертуры, мм")
plt.ylabel("z_real - z_theory, мкм")
plt.grid(alpha=0.3)

plt.tight_layout()
plt.show()
