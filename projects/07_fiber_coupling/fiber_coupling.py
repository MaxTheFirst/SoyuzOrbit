from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def gaussian_field(X: np.ndarray, Y: np.ndarray, waist: float, x_offset: float = 0.0) -> np.ndarray:
    return np.exp(-((X - x_offset) ** 2 + Y**2) / waist**2).astype(np.complex128)


def overlap_efficiency(field_a: np.ndarray, field_b: np.ndarray, dx: float) -> float:
    numerator = abs(np.sum(field_a * np.conj(field_b)) * dx * dx) ** 2
    power_a = float(np.sum(np.abs(field_a) ** 2) * dx * dx)
    power_b = float(np.sum(np.abs(field_b) ** 2) * dx * dx)
    if power_a <= 0.0 or power_b <= 0.0:
        return float("nan")
    return float(numerator / (power_a * power_b))


def fiber_v_number(wavelength: float, core_radius: float, n_core: float, n_clad: float) -> tuple[float, float]:
    numerical_aperture = np.sqrt(n_core**2 - n_clad**2)
    v_number = 2.0 * np.pi * core_radius * numerical_aperture / wavelength
    return float(numerical_aperture), float(v_number)


def marcuse_mode_radius(core_radius: float, v_number: float) -> float:
    return float(core_radius * (0.65 + 1.619 / v_number**1.5 + 2.879 / v_number**6))


def main() -> None:
    wavelength = 1550e-9
    core_radius = 4.1e-6
    n_core = 1.450
    n_clad = 1.444

    numerical_aperture, v_number = fiber_v_number(wavelength, core_radius, n_core, n_clad)
    mode_radius = marcuse_mode_radius(core_radius, v_number)

    window_size = 28e-6
    samples = 501
    dx = window_size / samples
    x = (np.arange(samples) - samples // 2) * dx
    X, Y = np.meshgrid(x, x)

    fiber_mode = gaussian_field(X, Y, mode_radius)
    focused_ideal = gaussian_field(X, Y, mode_radius)
    focused_too_small = gaussian_field(X, Y, 0.55 * mode_radius)
    focused_too_large = gaussian_field(X, Y, 1.8 * mode_radius)

    offsets = np.linspace(0.0, 8e-6, 80)
    offset_coupling = [
        overlap_efficiency(gaussian_field(X, Y, mode_radius, x_offset=offset), fiber_mode, dx) for offset in offsets
    ]

    waist_ratios = np.linspace(0.35, 2.4, 120)
    waist_coupling = [
        overlap_efficiency(gaussian_field(X, Y, mode_radius * ratio), fiber_mode, dx) for ratio in waist_ratios
    ]

    print("--- Ввод света в одномодовое оптоволокно ---")
    print(f"Длина волны: {wavelength * 1e9:.0f} нм")
    print(f"Радиус сердцевины: {core_radius * 1e6:.2f} мкм")
    print(f"n сердцевины: {n_core:.4f}")
    print(f"n оболочки: {n_clad:.4f}")
    print(f"NA = {numerical_aperture:.3f}")
    print(f"V-number = {v_number:.3f}")
    print("Волокно одномодовое по простому критерию V < 2.405." if v_number < 2.405 else "Волокно многомодовое по критерию V >= 2.405.")
    print(f"Оценка радиуса основной моды: {mode_radius * 1e6:.2f} мкм")
    print(f"Идеальное совпадение пятна и моды: {overlap_efficiency(focused_ideal, fiber_mode, dx) * 100:.1f}%")
    print(f"Слишком маленькое пятно: {overlap_efficiency(focused_too_small, fiber_mode, dx) * 100:.1f}%")
    print(f"Слишком большое пятно: {overlap_efficiency(focused_too_large, fiber_mode, dx) * 100:.1f}%")

    plt.figure(figsize=(13, 8))
    images = [
        ("мода волокна", fiber_mode),
        ("фокус совпал", focused_ideal),
        ("фокус меньше моды", focused_too_small),
        ("фокус больше моды", focused_too_large),
    ]
    for index, (title, field) in enumerate(images, start=1):
        plt.subplot(2, 4, index)
        intensity = np.abs(field) ** 2
        intensity /= np.max(intensity)
        plt.imshow(
            intensity,
            extent=(x[0] * 1e6, x[-1] * 1e6, x[0] * 1e6, x[-1] * 1e6),
            cmap="hot",
            vmin=0,
            vmax=1,
        )
        plt.title(title)
        plt.xlabel("x, мкм")
        plt.ylabel("y, мкм")

    plt.subplot(2, 4, 5)
    plt.plot(offsets * 1e6, np.array(offset_coupling) * 100, color="black", linewidth=2.3)
    plt.title("Потери от смещения")
    plt.xlabel("смещение фокуса, мкм")
    plt.ylabel("ввод в волокно, %")
    plt.grid(alpha=0.3)

    plt.subplot(2, 4, 6)
    plt.plot(waist_ratios, np.array(waist_coupling) * 100, color="darkgreen", linewidth=2.3)
    plt.axvline(1.0, color="black", linestyle=":")
    plt.title("Потери от неправильного размера")
    plt.xlabel("радиус пятна / радиус моды")
    plt.ylabel("ввод в волокно, %")
    plt.grid(alpha=0.3)

    plt.subplot(2, 4, 7)
    plt.axis("off")
    plt.text(
        0.0,
        0.95,
        f"NA = {numerical_aperture:.3f}\n"
        f"V = {v_number:.3f}\n"
        f"радиус моды = {mode_radius * 1e6:.2f} мкм\n\n"
        "Хороший ввод получается,\n"
        "когда фокус похож на моду\n"
        "по размеру и положению.",
        va="top",
        fontsize=12,
    )

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
