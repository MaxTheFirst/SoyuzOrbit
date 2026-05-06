from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


def make_test_target(samples: int = 320) -> np.ndarray:
    target = np.zeros((samples, samples), dtype=float)

    target[30:290, 35:45] = 1.0
    target[30:290, 275:285] = 1.0
    target[30:40, 35:285] = 1.0
    target[280:290, 35:285] = 1.0

    groups = [
        (70, 70, 9, 8),
        (70, 150, 5, 8),
        (70, 220, 3, 8),
        (180, 70, 9, 8),
        (180, 150, 5, 8),
        (180, 220, 3, 8),
    ]
    for y0, x0, bar_width, bars in groups:
        for index in range(bars):
            x_start = x0 + index * 2 * bar_width
            target[y0 : y0 + 65, x_start : x_start + bar_width] = 1.0
            y_start = y0 + index * 2 * bar_width
            target[y_start : y_start + bar_width, x0 + 95 : x0 + 160] = 1.0

    diagonal = np.eye(samples, dtype=float)
    target = np.maximum(target, np.roll(diagonal, 35, axis=1) * 0.9)
    target = np.maximum(target, np.roll(np.fliplr(diagonal), -35, axis=1) * 0.9)
    return target


def circular_frequency_mask(samples: int, cutoff_fraction: float) -> np.ndarray:
    coords = np.linspace(-1.0, 1.0, samples, endpoint=False)
    FX, FY = np.meshgrid(coords, coords)
    return (FX**2 + FY**2 <= cutoff_fraction**2).astype(float)


def image_through_pupil(target: np.ndarray, cutoff_fraction: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    spectrum = np.fft.fftshift(np.fft.fft2(target))
    pupil = circular_frequency_mask(target.shape[0], cutoff_fraction)
    filtered_spectrum = spectrum * pupil
    field = np.fft.ifft2(np.fft.ifftshift(filtered_spectrum))
    image = np.abs(field) ** 2
    image /= np.max(image)
    return image, spectrum, pupil


def main() -> None:
    target = make_test_target()
    cutoffs = [0.08, 0.15, 0.28]

    print("--- Фурье-оптика изображения ---")
    print("Картинка раскладывается на пространственные частоты.")
    print("Большие детали живут в низких частотах, мелкие штрихи - в высоких.")
    print("Апертура линзы работает как фильтр: если она мала, часть высоких частот не попадает в изображение.")
    print()
    for cutoff in cutoffs:
        print(f"Относительный радиус частотной апертуры: {cutoff:.2f}")

    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    first_image, spectrum, first_pupil = image_through_pupil(target, cutoffs[0])
    del first_image

    axes[0, 0].imshow(target, cmap="gray", vmin=0, vmax=1)
    axes[0, 0].set_title("объект")
    axes[0, 0].axis("off")

    axes[0, 1].imshow(np.log1p(np.abs(spectrum)), cmap="magma")
    axes[0, 1].set_title("Фурье-спектр")
    axes[0, 1].axis("off")

    axes[0, 2].imshow(first_pupil, cmap="gray")
    axes[0, 2].set_title("круглая апертура в спектре")
    axes[0, 2].axis("off")

    for index, cutoff in enumerate(cutoffs):
        image, _, _ = image_through_pupil(target, cutoff)
        axes[1, index].imshow(image, cmap="gray", vmin=0, vmax=1)
        axes[1, index].set_title(f"апертура {cutoff:.2f}")
        axes[1, index].axis("off")

    fig.suptitle("Чем меньше апертура, тем хуже проходят мелкие детали")
    fig.tight_layout()

    plt.figure(figsize=(8, 5))
    row = target.shape[0] // 2
    plt.plot(target[row], color="black", linewidth=2.0, label="исходный объект")
    for cutoff in cutoffs:
        image, _, _ = image_through_pupil(target, cutoff)
        plt.plot(image[row], linewidth=1.8, label=f"апертура {cutoff:.2f}")
    plt.title("Срез через изображение")
    plt.xlabel("пиксель")
    plt.ylabel("яркость")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
