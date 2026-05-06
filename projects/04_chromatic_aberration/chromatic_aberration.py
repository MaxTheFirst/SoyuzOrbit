from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lens_wave_optics import LensSpec, back_focal_length, bk7_refractive_index, effective_focal_length


def main() -> None:
    wavelengths = np.array([450e-9, 486e-9, 532e-9, 589e-9, 650e-9])
    display_wavelengths = np.linspace(430e-9, 680e-9, 160)

    radius_front = 25e-3
    radius_back = 25e-3
    center_thickness = 4.0e-3
    aperture_radius = 1.8e-3

    print("--- Хроматическая аберрация простой BK7-линзы ---")
    print("Одна и та же линза имеет разный показатель преломления для разных цветов.")
    print("Из-за этого фокус для синего, зеленого и красного света находится в разных местах.")
    print()
    print("цвет/длина волны | n(BK7) | EFL, мм | BFL, мм")

    table = []
    for wavelength in wavelengths:
        n = bk7_refractive_index(float(wavelength))
        lens = LensSpec(
            wavelength=float(wavelength),
            refractive_index=n,
            aperture_radius=aperture_radius,
            radius_front=radius_front,
            radius_back=radius_back,
            center_thickness=center_thickness,
        )
        efl = effective_focal_length(lens)
        bfl = back_focal_length(lens)
        table.append((wavelength, n, efl, bfl))
        print(f"{wavelength * 1e9:7.0f} нм      | {n:.6f} | {efl * 1e3:7.3f} | {bfl * 1e3:7.3f}")

    bfl_curve = []
    efl_curve = []
    for wavelength in display_wavelengths:
        n = bk7_refractive_index(float(wavelength))
        lens = LensSpec(
            wavelength=float(wavelength),
            refractive_index=n,
            aperture_radius=aperture_radius,
            radius_front=radius_front,
            radius_back=radius_back,
            center_thickness=center_thickness,
        )
        efl_curve.append(effective_focal_length(lens))
        bfl_curve.append(back_focal_length(lens))

    green_bfl = table[2][3]
    print()
    for wavelength, _, _, bfl in table:
        print(f"Смещение фокуса {wavelength * 1e9:.0f} нм относительно 532 нм: {(bfl - green_bfl) * 1e6:+.1f} мкм")

    colors = ["royalblue", "deepskyblue", "limegreen", "gold", "red"]

    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(display_wavelengths * 1e9, np.array(efl_curve) * 1e3, label="EFL", linewidth=2.3)
    plt.plot(display_wavelengths * 1e9, np.array(bfl_curve) * 1e3, label="BFL", linewidth=2.3)
    plt.title("Фокусное расстояние зависит от цвета")
    plt.xlabel("длина волны, нм")
    plt.ylabel("расстояние, мм")
    plt.grid(alpha=0.3)
    plt.legend()

    plt.subplot(1, 2, 2)
    for (wavelength, _, _, bfl), color in zip(table, colors):
        plt.axvline(bfl * 1e3, color=color, linewidth=3, label=f"{wavelength * 1e9:.0f} нм")
    plt.axvline(green_bfl * 1e3, color="black", linestyle="--", linewidth=1.3, label="экран в зеленом фокусе")
    plt.title("Где собираются разные цвета")
    plt.xlabel("z от линзы, мм")
    plt.yticks([])
    plt.grid(axis="x", alpha=0.3)
    plt.legend(fontsize=8)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
