from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lens_wave_optics import (
    LensSpec,
    airy_radius,
    bk7_refractive_index,
    circular_aperture,
    effective_focal_length,
    lens_thickness,
    make_grid,
    real_lens_transmission,
)


def focal_plane_intensity(
    X: np.ndarray,
    Y: np.ndarray,
    dx: float,
    field_after_lens: np.ndarray,
    wavelength: float,
    focal_length: float,
    pad_factor: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    k = 2.0 * np.pi / wavelength
    samples = field_after_lens.shape[0]
    padded_samples = samples * pad_factor
    pad_before = (padded_samples - samples) // 2
    pad_after = padded_samples - samples - pad_before

    reference = np.exp(1j * k * (X**2 + Y**2) / (2.0 * focal_length))
    pupil = field_after_lens * reference
    padded = np.pad(pupil, ((pad_before, pad_after), (pad_before, pad_after)))
    spectrum = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
    intensity = np.abs(spectrum) ** 2

    spatial_frequency = np.fft.fftshift(np.fft.fftfreq(padded_samples, d=dx))
    focal_x = wavelength * focal_length * spatial_frequency
    return focal_x, intensity


def rms_radius(coords: np.ndarray, intensity: np.ndarray, roi_radius: float) -> float:
    X, Y = np.meshgrid(coords, coords)
    mask = X**2 + Y**2 <= roi_radius**2
    weights = intensity * mask
    total = float(np.sum(weights))
    if total <= 0.0:
        return float("nan")
    return float(np.sqrt(np.sum(weights * (X**2 + Y**2)) / total))


def strehl_ratio(real_intensity: np.ndarray, ideal_intensity: np.ndarray) -> float:
    real_normalized = real_intensity / np.sum(real_intensity)
    ideal_normalized = ideal_intensity / np.sum(ideal_intensity)
    return float(np.max(real_normalized) / np.max(ideal_normalized))


def phase_error_rms(X: np.ndarray, Y: np.ndarray, lens: LensSpec, focal_length: float) -> float:
    k = 2.0 * np.pi / lens.wavelength
    aperture = circular_aperture(X, Y, lens.aperture_radius).astype(bool)
    real_phase = k * (lens.refractive_index - 1.0) * lens_thickness(X, Y, lens)
    ideal_phase = -k * (X**2 + Y**2) / (2.0 * focal_length)
    error = np.angle(np.exp(1j * (real_phase - ideal_phase)))
    values = error[aperture]
    values = values - np.mean(values)
    return float(np.sqrt(np.mean(values**2)))


def main() -> None:
    wavelength = 532e-9
    refractive_index = bk7_refractive_index(wavelength)
    radius_front = 22e-3
    radius_back = 22e-3
    center_thickness = 4.4e-3
    diameters = np.array([1.0, 1.4, 1.8, 2.2, 2.6, 3.0, 3.4, 3.8, 4.2]) * 1e-3

    rms_values = []
    airy_values = []
    strehl_values = []
    phase_rms_values = []
    spot_examples: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    print("--- Поиск разумной апертуры ---")
    print("Маленькая апертура усиливает дифракцию, большая апертура сильнее проявляет сферическую аберрацию.")
    print("Ниже ищем компромисс по RMS-радиусу пятна.")
    print()
    print("D, мм | Airy, мкм | RMS пятна, мкм | Strehl | RMS фазовой ошибки, рад")

    for diameter in diameters:
        aperture_radius = diameter / 2.0
        lens = LensSpec(
            wavelength=wavelength,
            refractive_index=refractive_index,
            aperture_radius=aperture_radius,
            radius_front=radius_front,
            radius_back=radius_back,
            center_thickness=center_thickness,
        )
        focal_length = effective_focal_length(lens)
        window_size = max(1.35 * diameter, diameter + 0.7e-3)
        samples = 512
        _, X, Y, dx = make_grid(window_size, samples)

        real_field = real_lens_transmission(X, Y, lens)
        ideal_field = circular_aperture(X, Y, aperture_radius) * np.exp(
            -1j * 2.0 * np.pi / wavelength * (X**2 + Y**2) / (2.0 * focal_length)
        )

        coords, real_intensity = focal_plane_intensity(X, Y, dx, real_field, wavelength, focal_length)
        _, ideal_intensity = focal_plane_intensity(X, Y, dx, ideal_field, wavelength, focal_length)

        real_intensity /= np.max(real_intensity)
        ideal_intensity /= np.max(ideal_intensity)

        rms = rms_radius(coords, real_intensity, roi_radius=120e-6)
        airy = airy_radius(wavelength, focal_length, aperture_radius)
        strehl = strehl_ratio(real_intensity, ideal_intensity)
        phase_rms = phase_error_rms(X, Y, lens, focal_length)

        rms_values.append(rms)
        airy_values.append(airy)
        strehl_values.append(strehl)
        phase_rms_values.append(phase_rms)

        print(f"{diameter * 1e3:4.1f} | {airy * 1e6:10.2f} | {rms * 1e6:14.2f} | {strehl:6.3f} | {phase_rms:9.3f}")

        if diameter in (diameters[0], diameters[len(diameters) // 2], diameters[-1]):
            spot_examples[f"D = {diameter * 1e3:.1f} мм"] = (coords, real_intensity.copy())

    rms_values_array = np.array(rms_values)
    best_index = int(np.argmin(rms_values_array))
    best_diameter = diameters[best_index]
    print()
    print(f"Лучший компромисс в этом наборе: D = {best_diameter * 1e3:.1f} мм")

    plt.figure(figsize=(13, 5))
    plt.subplot(1, 2, 1)
    plt.plot(diameters * 1e3, np.array(rms_values) * 1e6, "o-", linewidth=2.5, label="RMS пятна")
    plt.plot(diameters * 1e3, np.array(airy_values) * 1e6, "s--", linewidth=2.0, label="только дифракция")
    plt.axvline(best_diameter * 1e3, color="black", linestyle=":", label="лучший компромисс")
    plt.title("Размер пятна против диаметра апертуры")
    plt.xlabel("диаметр апертуры, мм")
    plt.ylabel("радиус, мкм")
    plt.grid(alpha=0.3)
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(diameters * 1e3, strehl_values, "o-", linewidth=2.5, color="darkgreen", label="Strehl")
    plt.plot(diameters * 1e3, phase_rms_values, "s--", linewidth=2.0, color="darkred", label="RMS фазы")
    plt.title("Качество волнового фронта")
    plt.xlabel("диаметр апертуры, мм")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.figure(figsize=(12, 4))
    for index, (title, (coords, intensity)) in enumerate(spot_examples.items(), start=1):
        crop = np.abs(coords) <= 70e-6
        cropped = intensity[np.ix_(crop, crop)]
        cropped_coords = coords[crop]
        plt.subplot(1, 3, index)
        plt.imshow(
            cropped**0.35,
            extent=(
                cropped_coords[0] * 1e6,
                cropped_coords[-1] * 1e6,
                cropped_coords[0] * 1e6,
                cropped_coords[-1] * 1e6,
            ),
            cmap="hot",
        )
        plt.title(title)
        plt.xlabel("x, мкм")
        plt.ylabel("y, мкм")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
