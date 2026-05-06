from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def trace_kepler_rays(
    input_angle: float,
    ray_heights: np.ndarray,
    objective_focal_length: float,
    eyepiece_focal_length: float,
    spacing: float,
    exit_distance: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    traces = []
    z_positions = np.array([0.0, spacing, spacing + exit_distance])

    for height in ray_heights:
        angle_after_objective = input_angle - height / objective_focal_length
        height_at_eyepiece = height + spacing * angle_after_objective
        angle_after_eyepiece = angle_after_objective - height_at_eyepiece / eyepiece_focal_length
        height_at_exit = height_at_eyepiece + exit_distance * angle_after_eyepiece
        heights = np.array([height, height_at_eyepiece, height_at_exit])
        traces.append((z_positions, heights))

    return traces


def output_angle(input_angle: float, objective_focal_length: float, eyepiece_focal_length: float) -> float:
    return -(objective_focal_length / eyepiece_focal_length) * input_angle


def main() -> None:
    wavelength = 532e-9
    objective_focal_length = 120e-3
    eyepiece_focal_length = 30e-3
    objective_diameter = 35e-3
    spacing = objective_focal_length + eyepiece_focal_length
    exit_distance = 70e-3

    magnification = -objective_focal_length / eyepiece_focal_length
    rayleigh_angle = 1.22 * wavelength / objective_diameter

    star_angles = np.deg2rad(np.array([-0.08, 0.0, 0.08]))
    ray_heights = np.linspace(-objective_diameter / 2.0, objective_diameter / 2.0, 7)

    print("--- Телескоп Кеплера ---")
    print(f"Фокус объектива: {objective_focal_length * 1e3:.1f} мм")
    print(f"Фокус окуляра: {eyepiece_focal_length * 1e3:.1f} мм")
    print(f"Расстояние между линзами: {spacing * 1e3:.1f} мм")
    print(f"Угловое увеличение: {magnification:.1f}x")
    print(f"Предел разрешения объектива: {rayleigh_angle * 206265:.2f} угл. секунд")
    print()
    for angle in star_angles:
        out = output_angle(angle, objective_focal_length, eyepiece_focal_length)
        intermediate_height = objective_focal_length * angle
        print(
            f"Входной угол {np.rad2deg(angle): .3f} град -> "
            f"промежуточное изображение y = {intermediate_height * 1e3: .3f} мм -> "
            f"выходной угол {np.rad2deg(out): .3f} град"
        )

    plt.figure(figsize=(12, 6))
    colors = ["tab:blue", "black", "tab:red"]
    for angle, color in zip(star_angles, colors):
        traces = trace_kepler_rays(
            angle,
            ray_heights,
            objective_focal_length,
            eyepiece_focal_length,
            spacing,
            exit_distance,
        )
        for z, height in traces:
            plt.plot(z * 1e3, height * 1e3, color=color, alpha=0.65, linewidth=1.4)

    plt.axvline(0.0, color="navy", linewidth=3, label="объектив")
    plt.axvline(spacing * 1e3, color="darkgreen", linewidth=3, label="окуляр")
    plt.axhline(0.0, color="gray", linewidth=1)
    plt.title("Ход лучей в телескопе Кеплера")
    plt.xlabel("z вдоль телескопа, мм")
    plt.ylabel("высота луча, мм")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    input_angles = np.deg2rad(np.linspace(-0.12, 0.12, 60))
    output_angles = output_angle(input_angles, objective_focal_length, eyepiece_focal_length)

    plt.figure(figsize=(7, 5))
    plt.plot(np.rad2deg(input_angles), np.rad2deg(output_angles), color="black", linewidth=2.5)
    plt.title("Угловое увеличение телескопа")
    plt.xlabel("угол объекта на небе, град")
    plt.ylabel("угол пучка после окуляра, град")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
