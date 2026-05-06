from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def make_grid(window_size: float, samples: int) -> tuple[np.ndarray, np.ndarray, float]:
    dx = window_size / samples
    x = (np.arange(samples) - samples // 2) * dx
    X, Y = np.meshgrid(x, x)
    return X, Y, dx


def pupil_mask(X: np.ndarray, Y: np.ndarray, pupil_diameter: float) -> np.ndarray:
    radius = pupil_diameter / 2.0
    return (X**2 + Y**2 <= radius**2).astype(np.complex128)


def retinal_image(
    X: np.ndarray,
    Y: np.ndarray,
    dx: float,
    wavelength: float,
    retina_distance: float,
    lens_focal_length: float,
    pupil_diameter: float,
    pad_factor: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    k = 2.0 * np.pi / wavelength
    r2 = X**2 + Y**2

    # Fresnel propagation to the retina turns an ideal in-focus lens into a flat
    # pupil phase. If f != retina_distance, the remaining quadratic phase is defocus.
    defocus_phase = np.exp(0.5j * k * r2 * (1.0 / retina_distance - 1.0 / lens_focal_length))
    pupil = pupil_mask(X, Y, pupil_diameter) * defocus_phase

    samples = pupil.shape[0]
    padded_samples = samples * pad_factor
    pad_before = (padded_samples - samples) // 2
    pad_after = padded_samples - samples - pad_before
    padded = np.pad(pupil, ((pad_before, pad_after), (pad_before, pad_after)))

    spectrum = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
    intensity = np.abs(spectrum) ** 2
    intensity /= np.max(intensity)

    spatial_frequency = np.fft.fftshift(np.fft.fftfreq(padded_samples, d=dx))
    retina_x = wavelength * retina_distance * spatial_frequency
    return retina_x, intensity


def rms_radius(coords: np.ndarray, intensity: np.ndarray, roi_radius: float) -> float:
    X, Y = np.meshgrid(coords, coords)
    mask = X**2 + Y**2 <= roi_radius**2
    weights = intensity * mask
    total = float(np.sum(weights))
    if total <= 0.0:
        return float("nan")
    return float(np.sqrt(np.sum(weights * (X**2 + Y**2)) / total))


def main() -> None:
    wavelength = 550e-9
    retina_distance = 17e-3
    pupil_diameter = 4e-3
    samples = 512
    pupil_window = 7e-3
    X, Y, dx = make_grid(pupil_window, samples)

    focus_cases = [
        ("нормальный глаз", 17.0e-3),
        ("фокус перед сетчаткой", 16.2e-3),
        ("фокус за сетчаткой", 17.9e-3),
    ]
    pupil_cases = [2e-3, 4e-3, 6e-3]

    print("--- Простая модель глаза ---")
    print(f"Длина волны: {wavelength * 1e9:.0f} нм")
    print(f"Расстояние от линзы глаза до сетчатки: {retina_distance * 1e3:.1f} мм")
    print(f"Базовый диаметр зрачка: {pupil_diameter * 1e3:.1f} мм")
    print()

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    crop_radius = 45e-6

    for index, (label, focal_length) in enumerate(focus_cases):
        coords, intensity = retinal_image(
            X,
            Y,
            dx,
            wavelength,
            retina_distance,
            focal_length,
            pupil_diameter,
        )
        crop = np.abs(coords) <= crop_radius
        cropped = intensity[np.ix_(crop, crop)]
        cropped_coords = coords[crop]
        spot_rms = rms_radius(coords, intensity, roi_radius=80e-6)
        focus_error = focal_length - retina_distance

        print(f"{label}:")
        print(f"  фокус линзы = {focal_length * 1e3:.2f} мм")
        print(f"  ошибка относительно сетчатки = {focus_error * 1e6:.0f} мкм")
        print(f"  RMS-радиус пятна на сетчатке = {spot_rms * 1e6:.2f} мкм")

        axes[0, index].imshow(
            cropped**0.35,
            extent=(
                cropped_coords[0] * 1e6,
                cropped_coords[-1] * 1e6,
                cropped_coords[0] * 1e6,
                cropped_coords[-1] * 1e6,
            ),
            cmap="hot",
        )
        axes[0, index].set_title(label)
        axes[0, index].set_xlabel("x, мкм")
        axes[0, index].set_ylabel("y, мкм")

        line = intensity[intensity.shape[0] // 2, crop]
        axes[1, index].plot(cropped_coords * 1e6, line, color="black", linewidth=2.0)
        axes[1, index].set_xlabel("x, мкм")
        axes[1, index].set_ylabel("интенсивность")
        axes[1, index].grid(alpha=0.3)

    fig.suptitle("Резкость на сетчатке: фокус попал или промахнулся")
    fig.tight_layout()

    plt.figure(figsize=(8, 5))
    for pupil in pupil_cases:
        coords, intensity = retinal_image(
            X,
            Y,
            dx,
            wavelength,
            retina_distance,
            retina_distance,
            pupil,
        )
        crop = np.abs(coords) <= 25e-6
        profile = intensity[intensity.shape[0] // 2, crop]
        airy_radius = 1.22 * wavelength * retina_distance / pupil
        plt.plot(coords[crop] * 1e6, profile, linewidth=2.0, label=f"зрачок {pupil * 1e3:.0f} мм")
        plt.axvline(airy_radius * 1e6, color="gray", linestyle=":", linewidth=0.9)
        plt.axvline(-airy_radius * 1e6, color="gray", linestyle=":", linewidth=0.9)
        print(f"Предел Эйри для зрачка {pupil * 1e3:.0f} мм: {airy_radius * 1e6:.2f} мкм")

    plt.title("Как размер зрачка меняет дифракционное пятно")
    plt.xlabel("x на сетчатке, мкм")
    plt.ylabel("интенсивность")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
