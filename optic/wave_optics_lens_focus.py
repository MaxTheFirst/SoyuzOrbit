diff --git a//Users/maksimversinin/Python/SoyuzOrbit-1/optic/wave_optics_lens_focus.py b//Users/maksimversinin/Python/SoyuzOrbit-1/optic/wave_optics_lens_focus.py
new file mode 100644
--- /dev/null
+++ b//Users/maksimversinin/Python/SoyuzOrbit-1/optic/wave_optics_lens_focus.py
@@ -0,0 +1,245 @@
+from __future__ import annotations
+
+from dataclasses import dataclass
+
+import matplotlib.pyplot as plt
+import numpy as np
+
+
+@dataclass(frozen=True)
+class Setup:
+    wavelength: float = 532e-9
+    focal_length: float = 50e-3
+    aperture_radius: float = 1.5e-3
+    source_distance: float = 180e-3
+    window_size: float = 12e-3
+    samples: int = 1024
+    scan_half_width: float = 8e-3
+    scan_steps: int = 121
+
+
+def make_grid(window_size: float, samples: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
+    dx = window_size / samples
+    x = (np.arange(samples) - samples // 2) * dx
+    X, Y = np.meshgrid(x, x)
+    return x, X, Y, dx
+
+
+def point_source_field(X: np.ndarray, Y: np.ndarray, wavelength: float, distance: float) -> np.ndarray:
+    k = 2.0 * np.pi / wavelength
+    r = np.sqrt(X**2 + Y**2 + distance**2)
+    field = np.exp(1j * k * r) / r
+    return field / np.sqrt(np.max(np.abs(field) ** 2))
+
+
+def circular_aperture(X: np.ndarray, Y: np.ndarray, radius: float) -> np.ndarray:
+    return (X**2 + Y**2 <= radius**2).astype(np.float64)
+
+
+def thin_lens_transmission(
+    X: np.ndarray,
+    Y: np.ndarray,
+    wavelength: float,
+    focal_length: float,
+    aperture_radius: float,
+) -> np.ndarray:
+    k = 2.0 * np.pi / wavelength
+    phase = np.exp(-1j * k * (X**2 + Y**2) / (2.0 * focal_length))
+    return circular_aperture(X, Y, aperture_radius) * phase
+
+
+def angular_spectrum_propagate(field: np.ndarray, wavelength: float, dx: float, distance: float) -> np.ndarray:
+    samples_y, samples_x = field.shape
+    k = 2.0 * np.pi / wavelength
+    kx = 2.0 * np.pi * np.fft.fftfreq(samples_x, d=dx)
+    ky = 2.0 * np.pi * np.fft.fftfreq(samples_y, d=dx)
+    KX, KY = np.meshgrid(kx, ky)
+    kt2 = KX**2 + KY**2
+
+    kz = np.empty_like(KX, dtype=np.complex128)
+    propagating = kt2 <= k**2
+    kz[propagating] = np.sqrt(k**2 - kt2[propagating])
+    kz[~propagating] = 1j * np.sqrt(kt2[~propagating] - k**2)
+
+    transfer = np.exp(1j * kz * distance)
+    return np.fft.ifft2(np.fft.fft2(field) * transfer)
+
+
+def gaussian_image_distance(source_distance: float, focal_length: float) -> float:
+    return 1.0 / (1.0 / focal_length - 1.0 / source_distance)
+
+
+def airy_radius(wavelength: float, focal_length: float, aperture_radius: float) -> float:
+    diameter = 2.0 * aperture_radius
+    return 1.22 * wavelength * focal_length / diameter
+
+
+def radial_profile(intensity: np.ndarray, x: np.ndarray, bins: int = 300) -> tuple[np.ndarray, np.ndarray]:
+    X, Y = np.meshgrid(x, x)
+    radius = np.sqrt(X**2 + Y**2)
+    r_flat = radius.ravel()
+    i_flat = intensity.ravel()
+
+    edges = np.linspace(0.0, np.max(r_flat), bins + 1)
+    which = np.digitize(r_flat, edges) - 1
+    profile = np.zeros(bins, dtype=np.float64)
+    counts = np.zeros(bins, dtype=np.int64)
+
+    valid = (which >= 0) & (which < bins)
+    np.add.at(profile, which[valid], i_flat[valid])
+    np.add.at(counts, which[valid], 1)
+
+    nonzero = counts > 0
+    profile[nonzero] /= counts[nonzero]
+    centers = 0.5 * (edges[:-1] + edges[1:])
+    return centers, profile
+
+
+def rms_radius(intensity: np.ndarray, X: np.ndarray, Y: np.ndarray, roi_radius: float) -> float:
+    mask = (X**2 + Y**2) <= roi_radius**2
+    weights = intensity * mask
+    total = np.sum(weights)
+    if total <= 0.0:
+        return float("nan")
+    return float(np.sqrt(np.sum(weights * (X**2 + Y**2)) / total))
+
+
+def j1_series(x: np.ndarray, terms: int = 60) -> np.ndarray:
+    result = np.zeros_like(x, dtype=np.float64)
+    half = 0.5 * x
+    half_sq = half**2
+    term = half.copy()
+    result += term
+    for m in range(1, terms):
+        term *= -half_sq / (m * (m + 1.0))
+        result += term
+    return result
+
+
+def airy_profile(radius: np.ndarray, wavelength: float, image_distance: float, aperture_radius: float) -> np.ndarray:
+    numerical_aperture_argument = 2.0 * np.pi * aperture_radius * radius / (wavelength * image_distance)
+    profile = np.ones_like(radius, dtype=np.float64)
+    nonzero = numerical_aperture_argument > 1e-12
+    j1 = j1_series(numerical_aperture_argument[nonzero])
+    profile[nonzero] = (2.0 * j1 / numerical_aperture_argument[nonzero]) ** 2
+    return profile
+
+
+def main() -> None:
+    setup = Setup()
+    x, X, Y, dx = make_grid(setup.window_size, setup.samples)
+
+    field_before_lens = point_source_field(X, Y, setup.wavelength, setup.source_distance)
+    lens = thin_lens_transmission(X, Y, setup.wavelength, setup.focal_length, setup.aperture_radius)
+    field_after_lens = field_before_lens * lens
+
+    image_distance_theory = gaussian_image_distance(setup.source_distance, setup.focal_length)
+    scan_distances = np.linspace(
+        image_distance_theory - setup.scan_half_width,
+        image_distance_theory + setup.scan_half_width,
+        setup.scan_steps,
+    )
+
+    on_axis = np.empty_like(scan_distances)
+    rms_spot = np.empty_like(scan_distances)
+    center = setup.samples // 2
+    roi_radius = 0.35e-3
+    axial_map = []
+    caustic_mask = np.abs(x) <= 60e-6
+
+    for index, distance in enumerate(scan_distances):
+        screen_field = angular_spectrum_propagate(field_after_lens, setup.wavelength, dx, float(distance))
+        intensity = np.abs(screen_field) ** 2
+        on_axis[index] = intensity[center, center]
+        rms_spot[index] = rms_radius(intensity, X, Y, roi_radius=roi_radius)
+        axial_map.append(intensity[center, caustic_mask])
+
+    axial_map = np.array(axial_map)
+    focus_on_axis = float(scan_distances[int(np.argmax(on_axis))])
+    focus_rms = float(scan_distances[int(np.argmin(rms_spot))])
+
+    field_focus = angular_spectrum_propagate(field_after_lens, setup.wavelength, dx, focus_on_axis)
+    intensity_focus = np.abs(field_focus) ** 2
+    intensity_focus /= np.max(intensity_focus)
+
+    radius, profile_sim = radial_profile(intensity_focus, x, bins=280)
+    profile_theory = airy_profile(radius, setup.wavelength, image_distance_theory, setup.aperture_radius)
+
+    airy_first_zero = airy_radius(setup.wavelength, image_distance_theory, setup.aperture_radius)
+
+    print("Волновая модель: источник -> линза -> экран")
+    print(f"lambda = {setup.wavelength * 1e9:.0f} нм")
+    print(f"Фокус линзы (заданный) = {setup.focal_length * 1e3:.3f} мм")
+    print(f"Радиус апертуры = {setup.aperture_radius * 1e3:.3f} мм")
+    print(f"Расстояние источник-линза = {setup.source_distance * 1e3:.3f} мм")
+    print(f"Расчетное расстояние изображения = {image_distance_theory * 1e3:.3f} мм")
+    print(f"Фокус по максимуму I(0,0,z) = {focus_on_axis * 1e3:.3f} мм")
+    print(f"Фокус по минимуму RMS = {focus_rms * 1e3:.3f} мм")
+    print(f"Отклонение от теории = {(focus_on_axis - image_distance_theory) * 1e6:.1f} мкм")
+    print(f"Радиус первого нуля Эйри = {airy_first_zero * 1e6:.2f} мкм")
+    print("Важно: в фокальной плоскости здесь возникают кольца Эйри, а не кольца Ньютона.")
+
+    zoom_mm = 0.08
+    zoom_um = 25.0
+
+    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
+
+    ax = axes[0, 0]
+    ax.set_title("Каустика около фокуса")
+    ax.imshow(
+        axial_map**0.4,
+        extent=(
+            x[caustic_mask][0] * 1e6,
+            x[caustic_mask][-1] * 1e6,
+            scan_distances[-1] * 1e3,
+            scan_distances[0] * 1e3,
+        ),
+        aspect="auto",
+        cmap="magma",
+    )
+    ax.axhline(image_distance_theory * 1e3, color="cyan", linestyle="--", label="Теория")
+    ax.axhline(focus_on_axis * 1e3, color="lime", linestyle="-.", label="Численный фокус")
+    ax.set_xlabel("x, мкм")
+    ax.set_ylabel("z от линзы, мм")
+    ax.legend(fontsize=9)
+
+    ax = axes[0, 1]
+    ax.set_title("Интенсивность на оси и размер пятна")
+    ax.plot(scan_distances * 1e3, on_axis / np.max(on_axis), color="crimson", linewidth=2.2, label="I(0,0,z)")
+    ax.plot(scan_distances * 1e3, np.min(rms_spot) / rms_spot, color="navy", linewidth=2.0, label="1 / RMS")
+    ax.axvline(image_distance_theory * 1e3, color="cyan", linestyle="--", label="Теория")
+    ax.axvline(focus_on_axis * 1e3, color="lime", linestyle="-.", label="Численный фокус")
+    ax.set_xlabel("z от линзы, мм")
+    ax.set_ylabel("Нормированная величина")
+    ax.grid(alpha=0.3)
+    ax.legend(fontsize=9)
+
+    ax = axes[1, 0]
+    ax.set_title("Карта интенсивности в фокусе")
+    ax.imshow(
+        intensity_focus**0.35,
+        extent=(-setup.window_size / 2 * 1e3, setup.window_size / 2 * 1e3, -setup.window_size / 2 * 1e3, setup.window_size / 2 * 1e3),
+        cmap="hot",
+    )
+    ax.set_xlim(-zoom_mm, zoom_mm)
+    ax.set_ylim(-zoom_mm, zoom_mm)
+    ax.set_xlabel("x, мм")
+    ax.set_ylabel("y, мм")
+
+    ax = axes[1, 1]
+    ax.set_title("Радиальный профиль в фокальной плоскости")
+    ax.semilogy(radius * 1e6, np.clip(profile_sim / np.max(profile_sim), 1e-12, None), color="black", linewidth=2.2, label="Симуляция")
+    ax.semilogy(radius * 1e6, np.clip(profile_theory, 1e-12, None), color="deepskyblue", linestyle="--", linewidth=2.0, label="Профиль Эйри")
+    ax.axvline(airy_first_zero * 1e6, color="gray", linestyle=":", label="1-й нуль Эйри")
+    ax.set_xlim(0.0, zoom_um)
+    ax.set_xlabel("r, мкм")
+    ax.set_ylabel("I / Imax")
+    ax.grid(alpha=0.3)
+    ax.legend(fontsize=9)
+
+    fig.tight_layout()
+    plt.show()
+
+
+if __name__ == "__main__":
+    main()
