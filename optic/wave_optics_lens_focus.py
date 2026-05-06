from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lens_wave_optics import (
    LensSpec,
    angular_spectrum_propagate,
    bk7_refractive_index,
    make_grid,
    paraxial_image_distance,
    point_source,
    real_lens_transmission,
)


def radial_profile(intensity: np.ndarray, x: np.ndarray, bins: int = 320) -> tuple[np.ndarray, np.ndarray]:
    X, Y = np.meshgrid(x, x)
    radius = np.sqrt(X**2 + Y**2)
    radius_flat = radius.ravel()
    intensity_flat = intensity.ravel()

    edges = np.linspace(0.0, float(np.max(radius_flat)), bins + 1)
    indices = np.digitize(radius_flat, edges) - 1
    profile = np.zeros(bins, dtype=float)
    counts = np.zeros(bins, dtype=int)

    valid = (indices >= 0) & (indices < bins)
    np.add.at(profile, indices[valid], intensity_flat[valid])
    np.add.at(counts, indices[valid], 1)

    nonzero = counts > 0
    profile[nonzero] /= counts[nonzero]
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers, profile


def j1_series(x: np.ndarray, terms: int = 80) -> np.ndarray:
    result = np.zeros_like(x, dtype=float)
    half = 0.5 * x
    term = half.copy()
    result += term
    half_sq = half**2
    for order in range(1, terms):
        term *= -half_sq / (order * (order + 1.0))
        result += term
    return result


def airy_profile(radius: np.ndarray, wavelength: float, image_distance: float, aperture_radius: float) -> np.ndarray:
    argument = 2.0 * np.pi * aperture_radius * radius / (wavelength * image_distance)
    profile = np.ones_like(radius, dtype=float)
    nonzero = argument > 1e-12
    j1 = j1_series(argument[nonzero])
    profile[nonzero] = (2.0 * j1 / argument[nonzero]) ** 2
    return profile


def airy_first_zero_radius(wavelength: float, image_distance: float, aperture_radius: float) -> float:
    return 1.22 * wavelength * image_distance / (2.0 * aperture_radius)


def main() -> None:
    wavelength = 532e-9
    refractive_index = bk7_refractive_index(wavelength)

    lens = LensSpec(
        wavelength=wavelength,
        refractive_index=refractive_index,
        aperture_radius=0.8e-3,
        radius_front=40e-3,
        radius_back=40e-3,
        center_thickness=4.0e-3,
    )

    source_distance = 160e-3
    window_size = 2.5e-3
    samples = 1024
    x, X, Y, dx = make_grid(window_size, samples)

    field_at_lens = point_source(X, Y, wavelength, source_distance)
    field_after_lens = field_at_lens * real_lens_transmission(X, Y, lens)

    image_distance_theory = paraxial_image_distance(lens, source_distance)
    scan_half_width = 5.0e-3
    scan_distances = np.linspace(
        image_distance_theory - scan_half_width,
        image_distance_theory + scan_half_width,
        61,
    )

    center = samples // 2
    caustic_mask = np.abs(x) <= 80e-6
    roi = (X**2 + Y**2) <= (120e-6) ** 2
    axial_map = []
    on_axis = np.empty_like(scan_distances)
    rms_radius = np.empty_like(scan_distances)
    focus_index = 0
    for index, distance in enumerate(scan_distances):
        propagated = angular_spectrum_propagate(field_after_lens, wavelength, dx, float(distance))
        intensity = np.abs(propagated) ** 2
        axial_map.append(intensity[center, caustic_mask])
        on_axis[index] = float(intensity[center, center])

        weights = intensity * roi
        total = float(np.sum(weights))
        rms_radius[index] = float(np.sqrt(np.sum(weights * (X**2 + Y**2)) / total))

        if on_axis[index] >= on_axis[focus_index]:
            focus_index = index

    axial_map = np.array(axial_map, dtype=float)
    axial_map /= float(np.max(axial_map))
    best_focus = float(scan_distances[focus_index])
    field_focus = angular_spectrum_propagate(field_after_lens, wavelength, dx, best_focus)
    intensity_focus = np.abs(field_focus) ** 2
    intensity_focus /= float(np.max(intensity_focus))

    radius, profile_sim = radial_profile(intensity_focus, x)
    profile_sim /= float(np.max(profile_sim))
    profile_theory = airy_profile(radius, wavelength, image_distance_theory, lens.aperture_radius)
    airy_zero = airy_first_zero_radius(wavelength, image_distance_theory, lens.aperture_radius)

    print("Волновая оптика: источник -> линза -> экран")
    print(f"lambda = {wavelength * 1e9:.0f} нм")
    print(f"n(BK7) = {refractive_index:.6f}")
    print(f"Расстояние источник-линза = {source_distance * 1e3:.3f} мм")
    print(f"Диаметр апертуры линзы = {2.0 * lens.aperture_radius * 1e3:.3f} мм")
    print(f"Параксиальное расстояние изображения = {image_distance_theory * 1e3:.3f} мм")
    print(f"Численный фокус по максимуму I(0, 0, z) = {best_focus * 1e3:.3f} мм")
    print(f"Сдвиг фокуса = {(best_focus - image_distance_theory) * 1e6:.1f} мкм")
    print(f"Радиус первого темного кольца Эйри = {airy_zero * 1e6:.2f} мкм")
    print("В этой постановке в фокальной плоскости возникают кольца Эйри.")
    print("Кольца Ньютона требуют интерференции в тонкой воздушной прослойке, а не одиночной линзы в фокусе.")

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9))

    ax = axes[0, 0]
    ax.set_title("Каустика около фокуса")
    ax.imshow(
        axial_map**0.45,
        extent=(
            x[caustic_mask][0] * 1e6,
            x[caustic_mask][-1] * 1e6,
            scan_distances[-1] * 1e3,
            scan_distances[0] * 1e3,
        ),
        aspect="auto",
        cmap="magma",
    )
    ax.axhline(image_distance_theory * 1e3, color="cyan", linestyle="--", label="Параксиальная теория")
    ax.axhline(best_focus * 1e3, color="lime", linestyle="-.", label="Численный фокус")
    ax.set_xlabel("x, мкм")
    ax.set_ylabel("z от линзы, мм")
    ax.legend(fontsize=9)

    ax = axes[0, 1]
    ax.set_title("Фокусировка вдоль оси")
    ax.plot(scan_distances * 1e3, on_axis / np.max(on_axis), color="crimson", linewidth=2.4, label="I(0, 0, z)")
    ax.plot(
        scan_distances * 1e3,
        np.min(rms_radius) / rms_radius,
        color="navy",
        linewidth=2.0,
        linestyle="--",
        label="1 / RMS",
    )
    ax.axvline(image_distance_theory * 1e3, color="cyan", linestyle=":", label="Параксиальная теория")
    ax.axvline(best_focus * 1e3, color="lime", linestyle="-.", label="Численный фокус")
    ax.set_xlabel("z от линзы, мм")
    ax.set_ylabel("Нормированная величина")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)

    ax = axes[1, 0]
    ax.set_title("Карта интенсивности в фокусе")
    ax.imshow(
        intensity_focus**0.35,
        extent=(-window_size / 2 * 1e3, window_size / 2 * 1e3, -window_size / 2 * 1e3, window_size / 2 * 1e3),
        cmap="hot",
    )
    ax.set_xlim(-0.08, 0.08)
    ax.set_ylim(-0.08, 0.08)
    ax.set_xlabel("x, мм")
    ax.set_ylabel("y, мм")

    ax = axes[1, 1]
    ax.set_title("Радиальный профиль в фокальной плоскости")
    ax.semilogy(radius * 1e6, np.clip(profile_sim, 1e-12, None), color="black", linewidth=2.2, label="Симуляция")
    ax.semilogy(
        radius * 1e6,
        np.clip(profile_theory / np.max(profile_theory), 1e-12, None),
        color="deepskyblue",
        linewidth=2.0,
        linestyle="--",
        label="Теория Эйри",
    )
    ax.axvline(airy_zero * 1e6, color="gray", linestyle=":", label="1-й нуль Эйри")
    ax.set_xlim(0.0, 100.0)
    ax.set_xlabel("r, мкм")
    ax.set_ylabel("I / Imax")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
