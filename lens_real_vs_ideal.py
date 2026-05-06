import matplotlib.pyplot as plt
import numpy as np

from lens_wave_optics import (
    LensSpec,
    airy_radius,
    back_focal_length,
    bk7_refractive_index,
    effective_focal_length,
    focus_scan,
    ideal_lens_transmission,
    lens_thickness,
    make_grid,
    plane_wave,
    real_lens_transmission,
)


def refine_focus_scans(
    field_real: np.ndarray,
    field_ideal: np.ndarray,
    wavelength: float,
    dx: float,
    X: np.ndarray,
    Y: np.ndarray,
    bfl: float,
    roi_radius: float,
) -> tuple[np.ndarray, dict[str, np.ndarray | float], dict[str, np.ndarray | float]]:
    coarse_distances = np.linspace(0.85 * bfl, 1.15 * bfl, 21)
    coarse_real = focus_scan(field_real, wavelength, dx, coarse_distances, X, Y, roi_radius=roi_radius)
    coarse_ideal = focus_scan(field_ideal, wavelength, dx, coarse_distances, X, Y, roi_radius=roi_radius)

    coarse_step = float(coarse_distances[1] - coarse_distances[0])
    coarse_best_real = float(coarse_real["best_rms_distance"])
    coarse_best_ideal = float(coarse_ideal["best_rms_distance"])
    fine_center = 0.5 * (coarse_best_real + coarse_best_ideal)
    fine_half_width = max(abs(coarse_best_real - fine_center), abs(coarse_best_ideal - fine_center)) + coarse_step
    fine_distances = np.linspace(fine_center - fine_half_width, fine_center + fine_half_width, 31)
    fine_real = focus_scan(field_real, wavelength, dx, fine_distances, X, Y, roi_radius=roi_radius)
    fine_ideal = focus_scan(field_ideal, wavelength, dx, fine_distances, X, Y, roi_radius=roi_radius)
    return fine_distances, fine_real, fine_ideal


def oversampled_screen_crop(
    X: np.ndarray,
    Y: np.ndarray,
    field_after_lens: np.ndarray,
    wavelength: float,
    dx: float,
    distance: float,
    crop_radius: float,
    pad_factor: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    k = 2.0 * np.pi / wavelength
    samples = field_after_lens.shape[0]
    padded_samples = pad_factor * samples
    pad_before = (padded_samples - samples) // 2
    pad_after = padded_samples - samples - pad_before

    reference_quadratic = np.exp(1j * k * (X**2 + Y**2) / (2.0 * distance))
    pupil = field_after_lens * reference_quadratic
    padded = np.pad(pupil, ((pad_before, pad_after), (pad_before, pad_after)))
    spectrum = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))

    fx = np.fft.fftshift(np.fft.fftfreq(padded_samples, d=dx))
    coords = wavelength * distance * fx
    crop_mask = np.abs(coords) <= crop_radius
    cropped_spectrum = spectrum[np.ix_(crop_mask, crop_mask)]
    intensity = np.abs(cropped_spectrum) ** 2
    return coords[crop_mask], intensity


wavelength = 532e-9
refractive_index = bk7_refractive_index(wavelength)

lens = LensSpec(
    wavelength=wavelength,
    refractive_index=refractive_index,
    aperture_radius=2.2e-3,
    radius_front=22e-3,
    radius_back=22e-3,
    center_thickness=4.4e-3,
)

# Reduce the transverse window and increase sampling so the focal spot is not
# represented by a single coarse pixel in the comparison plots.
window_size = 4.8e-3
samples = 2048
x, X, Y, dx = make_grid(window_size, samples)

f_eff = effective_focal_length(lens)
bfl = back_focal_length(lens)

field_in = plane_wave(X.shape)
field_real = field_in * real_lens_transmission(X, Y, lens)
field_ideal = field_in * ideal_lens_transmission(X, Y, wavelength, f_eff, lens.aperture_radius)

roi_radius = 0.08e-3
scan_distances, scan_real, scan_ideal = refine_focus_scans(
    field_real=field_real,
    field_ideal=field_ideal,
    wavelength=wavelength,
    dx=dx,
    X=X,
    Y=Y,
    bfl=bfl,
    roi_radius=roi_radius,
)

focus_crop_radius = 0.08e-3
focus_x_real, intensity_real = oversampled_screen_crop(
    X=X,
    Y=Y,
    field_after_lens=field_real,
    wavelength=wavelength,
    dx=dx,
    distance=float(scan_real["best_rms_distance"]),
    crop_radius=focus_crop_radius,
)
focus_x_ideal, intensity_ideal = oversampled_screen_crop(
    X=X,
    Y=Y,
    field_after_lens=field_ideal,
    wavelength=wavelength,
    dx=dx,
    distance=float(scan_ideal["best_rms_distance"]),
    crop_radius=focus_crop_radius,
)
intensity_real_plot = np.clip(intensity_real / np.max(intensity_real), 1e-12, None) ** 0.35
intensity_ideal_plot = np.clip(intensity_ideal / np.max(intensity_ideal), 1e-12, None) ** 0.35

phase_real = np.angle(real_lens_transmission(X, Y, lens))
phase_ideal = np.angle(ideal_lens_transmission(X, Y, wavelength, f_eff, lens.aperture_radius))
phase_error = np.angle(np.exp(1j * (phase_real - phase_ideal)))
phase_error[lens_thickness(X, Y, lens) <= 0.0] = np.nan
airy = airy_radius(wavelength, float(scan_ideal["best_rms_distance"]), lens.aperture_radius)
pixels_per_airy = airy / dx

print("--- Реальная сферическая линза vs идеальная квадратичная фаза ---")
print(f"Эффективное фокусное расстояние: {f_eff * 1000:.2f} мм")
print(f"Реальная линза, лучший RMS-фокус: {scan_real['best_rms_distance'] * 1000:.2f} мм")
print(f"Идеальная линза, лучший RMS-фокус: {scan_ideal['best_rms_distance'] * 1000:.2f} мм")
print(f"Дифракционный радиус Эйри: {airy * 1e6:.2f} мкм")
print(f"Радиус Эйри в пикселях сетки ASM: {pixels_per_airy:.2f}")
print(
    f"Дополнительный фокус-сдвиг из-за сферического профиля: "
    f"{(scan_real['best_rms_distance'] - scan_ideal['best_rms_distance']) * 1e6:.1f} мкм"
)

plt.figure(figsize=(14, 8))

plt.subplot(2, 2, 1)
plt.title("Фазовая ошибка реальной линзы")
plt.imshow(
    phase_error,
    extent=(-window_size / 2 * 1000, window_size / 2 * 1000, -window_size / 2 * 1000, window_size / 2 * 1000),
    cmap="twilight",
)
plt.colorbar(label="рад")
plt.xlabel("x, мм")
plt.ylabel("y, мм")

plt.subplot(2, 2, 2)
plt.title("Фокус: реальная линза")
plt.imshow(
    intensity_real_plot,
    extent=(focus_x_real[0] * 1000, focus_x_real[-1] * 1000, focus_x_real[0] * 1000, focus_x_real[-1] * 1000),
    cmap="hot",
)
plt.xlabel("x, мм")
plt.ylabel("y, мм")
plt.xlim(-focus_crop_radius * 1000, focus_crop_radius * 1000)
plt.ylim(-focus_crop_radius * 1000, focus_crop_radius * 1000)

plt.subplot(2, 2, 3)
plt.title("Фокус: идеальная линза")
plt.imshow(
    intensity_ideal_plot,
    extent=(focus_x_ideal[0] * 1000, focus_x_ideal[-1] * 1000, focus_x_ideal[0] * 1000, focus_x_ideal[-1] * 1000),
    cmap="hot",
)
plt.xlabel("x, мм")
plt.ylabel("y, мм")
plt.xlim(-focus_crop_radius * 1000, focus_crop_radius * 1000)
plt.ylim(-focus_crop_radius * 1000, focus_crop_radius * 1000)

plt.subplot(2, 2, 4)
plt.title("RMS-радиус вдоль оси")
plt.plot(scan_distances * 1000, scan_real["rms_radius"] * 1e6, linewidth=3, label="Реальная линза")
plt.plot(scan_distances * 1000, scan_ideal["rms_radius"] * 1e6, linewidth=2, linestyle="--", label="Идеальная линза")
plt.xlabel("z от линзы, мм")
plt.ylabel("RMS-радиус, мкм")
plt.grid(alpha=0.3)
plt.legend()

plt.tight_layout()
plt.show()
