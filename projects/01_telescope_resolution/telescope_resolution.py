from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def make_pupil_grid(window_size: float, samples: int) -> tuple[np.ndarray, np.ndarray, float]:
    dx = window_size / samples
    x = (np.arange(samples) - samples // 2) * dx
    X, Y = np.meshgrid(x, x)
    return X, Y, dx


def circular_pupil(X: np.ndarray, Y: np.ndarray, aperture_diameter: float) -> np.ndarray:
    radius = aperture_diameter / 2.0
    return (X**2 + Y**2 <= radius**2).astype(np.complex128)


def focal_plane_from_angle(
    X: np.ndarray,
    Y: np.ndarray,
    dx: float,
    wavelength: float,
    focal_length: float,
    aperture_diameter: float,
    source_angle: float,
    pad_factor: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    k = 2.0 * np.pi / wavelength
    pupil = circular_pupil(X, Y, aperture_diameter)
    tilted_wave = np.exp(-1j * k * source_angle * X)
    field_at_pupil = pupil * tilted_wave

    samples = field_at_pupil.shape[0]
    padded_samples = samples * pad_factor
    pad_before = (padded_samples - samples) // 2
    pad_after = padded_samples - samples - pad_before
    padded = np.pad(field_at_pupil, ((pad_before, pad_after), (pad_before, pad_after)))

    spectrum = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
    intensity = np.abs(spectrum) ** 2
    intensity /= np.max(intensity)

    spatial_frequency = np.fft.fftshift(np.fft.fftfreq(padded_samples, d=dx))
    image_x = wavelength * focal_length * spatial_frequency
    return image_x, intensity


def two_star_image(
    X: np.ndarray,
    Y: np.ndarray,
    dx: float,
    wavelength: float,
    focal_length: float,
    aperture_diameter: float,
    angular_separation: float,
) -> tuple[np.ndarray, np.ndarray]:
    image_x, left = focal_plane_from_angle(
        X,
        Y,
        dx,
        wavelength,
        focal_length,
        aperture_diameter,
        -angular_separation / 2.0,
    )
    _, right = focal_plane_from_angle(
        X,
        Y,
        dx,
        wavelength,
        focal_length,
        aperture_diameter,
        angular_separation / 2.0,
    )
    intensity = left + right
    intensity /= np.max(intensity)
    return image_x, intensity


def main() -> None:
    wavelength = 532e-9
    focal_length = 600e-3
    aperture_diameter = 70e-3
    samples = 512
    pupil_window = 1.2 * aperture_diameter

    X, Y, dx = make_pupil_grid(pupil_window, samples)

    rayleigh_angle = 1.22 * wavelength / aperture_diameter
    rayleigh_image_separation = focal_length * rayleigh_angle
    separations = [0.55 * rayleigh_angle, rayleigh_angle, 1.6 * rayleigh_angle]
    labels = ["меньше предела", "предел Рэлея", "легко различимо"]

    print("--- Разрешение телескопа ---")
    print(f"Длина волны: {wavelength * 1e9:.0f} нм")
    print(f"Диаметр объектива: {aperture_diameter * 1e3:.1f} мм")
    print(f"Фокусное расстояние: {focal_length * 1e3:.1f} мм")
    print(f"Угловой предел Рэлея: {rayleigh_angle * 206265:.2f} угл. секунд")
    print(f"Расстояние между пятнами в фокальной плоскости на пределе: {rayleigh_image_separation * 1e6:.2f} мкм")

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    crop_radius = 25e-6

    for index, (separation, label) in enumerate(zip(separations, labels)):
        image_x, intensity = two_star_image(
            X,
            Y,
            dx,
            wavelength,
            focal_length,
            aperture_diameter,
            separation,
        )
        crop = np.abs(image_x) <= crop_radius
        cropped = intensity[np.ix_(crop, crop)]
        cropped_x = image_x[crop]
        center_line = cropped[cropped.shape[0] // 2, :]

        axes[0, index].imshow(
            cropped**0.45,
            extent=(cropped_x[0] * 1e6, cropped_x[-1] * 1e6, cropped_x[0] * 1e6, cropped_x[-1] * 1e6),
            cmap="hot",
        )
        axes[0, index].set_title(label)
        axes[0, index].set_xlabel("x, мкм")
        axes[0, index].set_ylabel("y, мкм")

        axes[1, index].plot(cropped_x * 1e6, center_line, color="black", linewidth=2.2)
        axes[1, index].axvline(-focal_length * separation * 0.5 * 1e6, color="tab:blue", linestyle=":")
        axes[1, index].axvline(focal_length * separation * 0.5 * 1e6, color="tab:blue", linestyle=":")
        axes[1, index].set_title(f"{separation / rayleigh_angle:.2f} от предела")
        axes[1, index].set_xlabel("x, мкм")
        axes[1, index].set_ylabel("интенсивность")
        axes[1, index].grid(alpha=0.3)

    fig.suptitle("Две близкие звезды: когда телескоп видит их отдельно")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
