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


def grid_for_aperture(aperture_radius: float) -> tuple[float, int]:
    diameter = 2.0 * aperture_radius
    window_size = max(1.12 * diameter, diameter + 0.4e-3)
    dx_target = 1.6e-6
    samples = int(np.ceil(window_size / dx_target / 256.0) * 256)
    samples = max(samples, 1536)
    return window_size, samples


def refine_focus_scan(
    field_after_lens: np.ndarray,
    wavelength: float,
    dx: float,
    X: np.ndarray,
    Y: np.ndarray,
    theory_focus: float,
    roi_radius: float,
) -> dict[str, np.ndarray | float]:
    coarse_distances = np.linspace(0.85 * theory_focus, 1.20 * theory_focus, 31)
    coarse_scan = focus_scan(field_after_lens, wavelength, dx, coarse_distances, X, Y, roi_radius=roi_radius)

    coarse_step = float(coarse_distances[1] - coarse_distances[0])
    coarse_best = float(coarse_scan["best_rms_distance"])
    fine_distances = np.linspace(coarse_best - coarse_step, coarse_best + coarse_step, 31)
    fine_scan = focus_scan(field_after_lens, wavelength, dx, fine_distances, X, Y, roi_radius=roi_radius)
    fine_scan["scan_distances"] = fine_distances
    return fine_scan


wavelength = 532e-9
refractive_index = bk7_refractive_index(wavelength)

apertures = [1.0e-3, 1.6e-3, 2.4e-3]
spots = []
real_focuses = []
airy_radii = []
theory_focuses = []

plt.figure(figsize=(15, 5))

for index, aperture_radius in enumerate(apertures, start=1):
    window_size, samples = grid_for_aperture(aperture_radius)
    x, X, Y, dx = make_grid(window_size, samples)
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
    roi_radius = 0.08e-3
    scan = refine_focus_scan(field_after_lens, wavelength, dx, X, Y, theory_focus, roi_radius=roi_radius)
    z_real = scan["best_rms_distance"]
    screen = angular_spectrum_propagate(field_after_lens, wavelength, dx, z_real)
    intensity = np.abs(screen) ** 2
    spot = rms_spot_radius(intensity, X, Y, roi_radius=roi_radius)
    airy = airy_radius(wavelength, z_real, aperture_radius)
    pixels_per_airy = airy / dx

    spots.append(spot)
    real_focuses.append(z_real)
    airy_radii.append(airy)
    theory_focuses.append(theory_focus)

    print(
        f"Апертура {2 * aperture_radius * 1000:.1f} мм | "
        f"BFL = {theory_focus * 1000:.2f} мм | "
        f"реальный фокус = {z_real * 1000:.2f} мм | "
        f"RMS = {spot * 1e6:.1f} мкм | "
        f"Эйри = {airy * 1e6:.1f} мкм | "
        f"Airy/dx = {pixels_per_airy:.2f} пикс"
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
    plt.xlim(-0.08, 0.08)
    plt.ylim(-0.08, 0.08)

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
