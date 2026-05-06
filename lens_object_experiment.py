import matplotlib.pyplot as plt
import numpy as np

from lens_wave_optics import (
    LensSpec,
    angular_spectrum_propagate,
    bk7_refractive_index,
    make_grid,
    paraxial_image_distance,
    real_lens_transmission,
)


def demo_object(X: np.ndarray, Y: np.ndarray, scale: float) -> np.ndarray:
    transmission = np.zeros_like(X, dtype=float)

    y_top = 0.52 * scale
    y_bottom = -0.52 * scale
    left_top = np.array([-0.34 * scale, y_top])
    apex = np.array([0.0, y_bottom])
    right_top = np.array([0.34 * scale, y_top])
    leg_half_width = 0.08 * scale
    bar_half_height = 0.07 * scale
    bar_half_width = 0.18 * scale
    bar_y = -0.02 * scale

    def segment_distance(x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
        vx = x2 - x1
        vy = y2 - y1
        wx = X - x1
        wy = Y - y1
        denom = vx * vx + vy * vy
        projection = np.clip((wx * vx + wy * vy) / denom, 0.0, 1.0)
        closest_x = x1 + projection * vx
        closest_y = y1 + projection * vy
        return np.sqrt((X - closest_x) ** 2 + (Y - closest_y) ** 2)

    left_leg = segment_distance(left_top[0], left_top[1], apex[0], apex[1]) <= leg_half_width
    right_leg = segment_distance(right_top[0], right_top[1], apex[0], apex[1]) <= leg_half_width
    crossbar = (
        (np.abs(Y - bar_y) <= bar_half_height)
        & (X >= -bar_half_width)
        & (X <= bar_half_width)
    )

    transmission[left_leg | right_leg | crossbar] = 1.0
    return transmission


def normalize(image: np.ndarray) -> np.ndarray:
    peak = float(np.max(image))
    if peak <= 0.0:
        return np.zeros_like(image)
    return image / peak


def quantile_normalize(image: np.ndarray, upper_quantile: float = 0.995, gamma: float = 0.6) -> np.ndarray:
    clipped = np.clip(image, 0.0, float(np.quantile(image, upper_quantile)))
    peak = float(np.max(clipped))
    if peak <= 0.0:
        return np.zeros_like(image)
    return (clipped / peak) ** gamma


def expected_image_template(
    X: np.ndarray,
    Y: np.ndarray,
    object_scale: float,
    magnification: float,
) -> np.ndarray:
    if np.isclose(magnification, 0.0):
        return np.zeros_like(X, dtype=float)
    return demo_object(X / magnification, Y / magnification, object_scale)


def template_match_score(image: np.ndarray, template: np.ndarray) -> float:
    support = template > 0.05
    if not np.any(support):
        return float("-inf")

    ys, xs = np.where(support)
    pad = 24
    y0 = max(int(ys.min()) - pad, 0)
    y1 = min(int(ys.max()) + pad + 1, template.shape[0])
    x0 = max(int(xs.min()) - pad, 0)
    x1 = min(int(xs.max()) + pad + 1, template.shape[1])

    image_roi = image[y0:y1, x0:x1]
    template_roi = template[y0:y1, x0:x1]
    image_zero_mean = (image_roi - float(np.mean(image_roi))).ravel()
    template_zero_mean = (template_roi - float(np.mean(template_roi))).ravel()
    denom = np.linalg.norm(image_zero_mean) * np.linalg.norm(template_zero_mean)
    if denom <= 0.0:
        return float("-inf")
    return float(np.dot(image_zero_mean, template_zero_mean) / denom)


def main() -> None:
    wavelength = 532e-9
    refractive_index = bk7_refractive_index(wavelength)

    lens = LensSpec(
        wavelength=wavelength,
        refractive_index=refractive_index,
        aperture_radius=1.6e-3,
        radius_front=24e-3,
        radius_back=24e-3,
        center_thickness=4.0e-3,
    )

    object_distance = 120e-3
    window_size = 6.0e-3
    samples = 1024
    x, X, Y, dx = make_grid(window_size, samples)

    object_scale = 0.85e-3
    object_transmission = demo_object(X, Y, object_scale).astype(np.complex128)
    field_at_lens = angular_spectrum_propagate(object_transmission, wavelength, dx, object_distance)
    field_after_lens = field_at_lens * real_lens_transmission(X, Y, lens)

    image_distance_theory = paraxial_image_distance(lens, object_distance)
    scan_distances = np.linspace(image_distance_theory - 6e-3, image_distance_theory + 6e-3, 31)
    magnification_theory = -image_distance_theory / object_distance
    template_theory = expected_image_template(X, Y, object_scale, magnification_theory)

    similarity = np.empty_like(scan_distances)
    image_stack: list[np.ndarray] = []
    for index, distance in enumerate(scan_distances):
        propagated = angular_spectrum_propagate(field_after_lens, wavelength, dx, float(distance))
        intensity = np.abs(propagated) ** 2
        image_stack.append(intensity)
        similarity[index] = template_match_score(normalize(intensity), template_theory)

    best_index = int(np.argmax(similarity))
    best_distance = float(scan_distances[best_index])
    intensity_theory = normalize(image_stack[int(np.argmin(np.abs(scan_distances - image_distance_theory)))])
    intensity_best = normalize(image_stack[best_index])

    magnification = -best_distance / object_distance
    enlargement_theory = abs(magnification_theory)
    enlargement_best = abs(magnification)
    image_half_size = 0.75 * abs(magnification_theory) * object_scale

    print("Волновой эксперимент: предмет -> линза -> экран")
    print(f"lambda = {wavelength * 1e9:.0f} нм")
    print(f"n(BK7) = {refractive_index:.6f}")
    print(f"Расстояние предмет-линза = {object_distance * 1e3:.2f} мм")
    print(f"Параксиальное расстояние изображения = {image_distance_theory * 1e3:.2f} мм")
    print(f"Лучшее расстояние по похожести на A = {best_distance * 1e3:.2f} мм")
    print(f"Поперечное увеличение ~= {magnification:.3f}")
    print(f"Увеличение по модулю (теория) = {enlargement_theory:.3f}x")
    print(f"Увеличение по модулю (численно) = {enlargement_best:.3f}x")
    print(f"Корреляция с шаблоном A в теории = {template_match_score(intensity_theory, template_theory):.4f}")
    print(f"Корреляция с шаблоном A в лучшей плоскости = {template_match_score(intensity_best, template_theory):.4f}")

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9))

    ax = axes[0, 0]
    ax.set_title("Предмет")
    ax.imshow(
        object_transmission.real,
        extent=(-window_size / 2 * 1e3, window_size / 2 * 1e3, -window_size / 2 * 1e3, window_size / 2 * 1e3),
        cmap="gray",
        origin="lower",
    )
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_xlabel("x, мм")
    ax.set_ylabel("y, мм")

    ax = axes[0, 1]
    ax.set_title("Интенсивность у линзы")
    ax.imshow(
        quantile_normalize(np.abs(field_at_lens) ** 2, upper_quantile=0.995, gamma=0.55),
        extent=(-window_size / 2 * 1e3, window_size / 2 * 1e3, -window_size / 2 * 1e3, window_size / 2 * 1e3),
        cmap="magma",
        origin="lower",
    )
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-2.0, 2.0)
    ax.set_xlabel("x, мм")
    ax.set_ylabel("y, мм")

    ax = axes[1, 0]
    ax.set_title("Экран в параксиальной плоскости")
    ax.imshow(
        quantile_normalize(intensity_theory, upper_quantile=0.999, gamma=0.5),
        extent=(-window_size / 2 * 1e3, window_size / 2 * 1e3, -window_size / 2 * 1e3, window_size / 2 * 1e3),
        cmap="hot",
        origin="lower",
    )
    ax.set_xlim(-image_half_size * 1e3, image_half_size * 1e3)
    ax.set_ylim(-image_half_size * 1e3, image_half_size * 1e3)
    ax.set_xlabel("x, мм")
    ax.set_ylabel("y, мм")

    ax = axes[1, 1]
    ax.set_title("Экран в плоскости лучшего совпадения с A")
    ax.imshow(
        quantile_normalize(intensity_best, upper_quantile=0.999, gamma=0.5),
        extent=(-window_size / 2 * 1e3, window_size / 2 * 1e3, -window_size / 2 * 1e3, window_size / 2 * 1e3),
        cmap="hot",
        origin="lower",
    )
    ax.set_xlim(-image_half_size * 1e3, image_half_size * 1e3)
    ax.set_ylim(-image_half_size * 1e3, image_half_size * 1e3)
    ax.set_xlabel("x, мм")
    ax.set_ylabel("y, мм")

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
