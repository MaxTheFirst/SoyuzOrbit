from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from lens_wave_optics import (
    LensSpec,
    airy_radius,
    angular_spectrum_propagate,
    back_focal_length,
    bk7_refractive_index,
    circular_aperture,
    effective_focal_length,
    make_grid,
    plane_wave,
    real_lens_transmission,
)


def estimate_fwhm(x: np.ndarray, profile: np.ndarray) -> float:
    peak_index = int(np.argmax(profile))
    peak_value = float(profile[peak_index])
    if peak_value <= 0.0:
        return float("nan")
    half_max = peak_value / 2.0
    left = peak_index
    while left > 0 and profile[left] >= half_max:
        left -= 1
    right = peak_index
    while right < profile.size - 1 and profile[right] >= half_max:
        right += 1

    if left == 0 or right == profile.size - 1:
        return float("nan")

    def interpolate_crossing(x0: float, y0: float, x1: float, y1: float, level: float) -> float:
        if y1 == y0:
            return float(0.5 * (x0 + x1))
        return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))

    left_x = interpolate_crossing(x[left], profile[left], x[left + 1], profile[left + 1], half_max)
    right_x = interpolate_crossing(x[right - 1], profile[right - 1], x[right], profile[right], half_max)
    return float(right_x - left_x)


def normalize_profile(profile: np.ndarray) -> np.ndarray:
    peak = float(np.max(profile))
    if peak <= 0.0:
        return np.zeros_like(profile)
    return profile / peak


def oversampled_focal_plane_profiles(
    X: np.ndarray,
    Y: np.ndarray,
    field_after_lens: np.ndarray,
    wavelength: float,
    dx: float,
    focal_length: float,
    aperture_radius: float,
    pad_factor: int = 2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    k = 2.0 * np.pi / wavelength
    samples = field_after_lens.shape[0]
    padded_samples = pad_factor * samples
    pad_before = (padded_samples - samples) // 2
    pad_after = padded_samples - samples - pad_before

    reference_quadratic = np.exp(1j * k * (X**2 + Y**2) / (2.0 * focal_length))
    pupil_real = field_after_lens * reference_quadratic
    pupil_ideal = circular_aperture(X, Y, aperture_radius).astype(np.complex128)

    def focal_profile(pupil: np.ndarray) -> np.ndarray:
        padded = np.pad(pupil, ((pad_before, pad_after), (pad_before, pad_after)))
        spectrum = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded)))
        return np.abs(spectrum[padded_samples // 2, :]) ** 2

    fx = np.fft.fftshift(np.fft.fftfreq(padded_samples, d=dx))
    focal_x = wavelength * focal_length * fx
    return focal_x, focal_profile(pupil_ideal), focal_profile(pupil_real)


def strongest_peaks(x: np.ndarray, profile: np.ndarray, count: int = 5) -> list[tuple[float, float]]:
    top_indices = np.argsort(profile)[-count:][::-1]
    return [(float(x[index]), float(profile[index])) for index in top_indices]


def scan_focus(
    field_after_lens: np.ndarray,
    wavelength: float,
    dx: float,
    distances: np.ndarray,
) -> tuple[np.ndarray, float]:
    center = field_after_lens.shape[0] // 2
    on_axis = np.empty_like(distances, dtype=float)
    for index, distance in enumerate(distances):
        propagated = angular_spectrum_propagate(field_after_lens, wavelength, dx, float(distance))
        intensity = np.abs(propagated) ** 2
        on_axis[index] = float(intensity[center, center])
    best_index = int(np.argmax(on_axis))
    return on_axis, float(distances[best_index])


def refine_focus_distance(
    field_after_lens: np.ndarray,
    wavelength: float,
    dx: float,
    bfl: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    coarse_distances = np.linspace(0.85 * bfl, 1.15 * bfl, 21)
    coarse_on_axis, coarse_best = scan_focus(field_after_lens, wavelength, dx, coarse_distances)

    coarse_step = float(coarse_distances[1] - coarse_distances[0])
    fine_distances = np.linspace(coarse_best - coarse_step, coarse_best + coarse_step, 21)
    fine_on_axis, fine_best = scan_focus(field_after_lens, wavelength, dx, fine_distances)
    return fine_distances, fine_on_axis, fine_best


def make_debug_report(
    x: np.ndarray,
    dx: float,
    lens: LensSpec,
    f_eff: float,
    bfl: float,
    scan_distances: np.ndarray,
    on_axis: np.ndarray,
    z_real: float,
    profile_theory: np.ndarray,
    profile_real: np.ndarray,
    focal_x: np.ndarray,
    focal_profile_ideal: np.ndarray,
    focal_profile_real: np.ndarray,
) -> str:
    airy = airy_radius(lens.wavelength, f_eff, lens.aperture_radius)
    pixels_per_airy = airy / dx
    peak_theory = strongest_peaks(x, profile_theory)
    peak_real = strongest_peaks(x, profile_real)
    fwhm_theory = estimate_fwhm(x, profile_theory)
    fwhm_real = estimate_fwhm(x, profile_real)
    focal_profile_ideal_norm = normalize_profile(focal_profile_ideal)
    focal_profile_real_norm = normalize_profile(focal_profile_real)
    airy_index = int(np.argmin(np.abs(focal_x - airy)))

    lines = [
        "--- Отладка lens_focus_basic.py ---",
        f"lambda = {lens.wavelength * 1e9:.0f} нм",
        f"n(BK7) = {lens.refractive_index:.6f}",
        f"aperture radius = {lens.aperture_radius * 1e3:.3f} мм",
        f"grid window = {(x[-1] - x[0] + dx) * 1e3:.3f} мм",
        f"samples = {x.size}",
        f"dx = {dx * 1e6:.3f} мкм",
        f"effective focal length = {f_eff * 1e3:.3f} мм",
        f"back focal length = {bfl * 1e3:.3f} мм",
        f"best on-axis z = {z_real * 1e3:.3f} мм",
        f"shift from BFL = {(z_real - bfl) * 1e6:.1f} мкм",
        f"shift from EFL = {(z_real - f_eff) * 1e6:.1f} мкм",
        f"Airy radius estimate = {airy * 1e6:.3f} мкм",
        f"Airy radius / dx = {pixels_per_airy:.3f} пикс",
        "warning = поперечное пятно недоразрешено сеткой" if pixels_per_airy < 3.0 else "warning = разрешение приемлемое",
        "note = в точном фокусе ожидаются кольца Эйри; на исходной ASM-сетке они почти скрыты дискретизацией",
        "note = BFL для толстой линзы некорректно сравнивать с этой моделью, потому что линза задана как один фазовый экран",
        f"oversampled focal profile at Airy radius: ideal = {focal_profile_ideal_norm[airy_index]:.4f}, real = {focal_profile_real_norm[airy_index]:.4f}",
        "",
        "On-axis intensity scan:",
    ]

    for distance, axis_value in zip(scan_distances, on_axis):
        lines.append(f"  z = {distance * 1e3:8.4f} мм | I(0,0) = {axis_value:11.6f}")

    lines.extend(
        [
            "",
            "Strongest transverse peaks at EFL plane:",
            *[
                f"  x = {peak_x * 1e6:8.3f} мкм | I = {peak_value:11.6f}"
                for peak_x, peak_value in peak_theory
            ],
            f"  FWHM estimate = {fwhm_theory * 1e6:.3f} мкм",
            "",
            "Strongest transverse peaks at best on-axis plane:",
            *[
                f"  x = {peak_x * 1e6:8.3f} мкм | I = {peak_value:11.6f}"
                for peak_x, peak_value in peak_real
            ],
            f"  FWHM estimate = {fwhm_real * 1e6:.3f} мкм",
        ]
    )
    return "\n".join(lines)


wavelength = 532e-9
refractive_index = bk7_refractive_index(wavelength)

# Use a slightly smaller clear aperture and a denser grid so the Airy-scale
# spot is resolved by several pixels in the raw ASM plots.
lens = LensSpec(
    wavelength=wavelength,
    refractive_index=refractive_index,
    aperture_radius=1.4e-3,
    radius_front=25e-3,
    radius_back=25e-3,
    center_thickness=4.0e-3,
)

window_size = 3.4e-3
samples = 2048
x, X, Y, dx = make_grid(window_size, samples)

field_before_lens = plane_wave(X.shape)
field_after_lens = field_before_lens * real_lens_transmission(X, Y, lens)

f_eff = effective_focal_length(lens)
bfl = back_focal_length(lens)
scan_distances, on_axis, z_real = refine_focus_distance(field_after_lens, wavelength, dx, bfl)

center_index = samples // 2
profile_zoom_radius = 30e-6
profile_zoom_mask = np.abs(x) <= profile_zoom_radius

caustic_half_width = 40e-6
caustic_mask = np.abs(x) <= caustic_half_width
axial_map = []
for distance in scan_distances:
    propagated = angular_spectrum_propagate(field_after_lens, wavelength, dx, float(distance))
    axial_map.append(np.abs(propagated[center_index, caustic_mask]) ** 2)
axial_map = np.array(axial_map)

screen_efl = angular_spectrum_propagate(field_after_lens, wavelength, dx, f_eff)
screen_real = angular_spectrum_propagate(field_after_lens, wavelength, dx, z_real)
intensity_theory = np.abs(screen_efl) ** 2
intensity_real = np.abs(screen_real) ** 2
profile_theory = intensity_theory[center_index, :]
profile_real = intensity_real[center_index, :]
focal_x, focal_profile_ideal, focal_profile_real = oversampled_focal_plane_profiles(
    X=X,
    Y=Y,
    field_after_lens=field_after_lens,
    wavelength=wavelength,
    dx=dx,
    focal_length=f_eff,
    aperture_radius=lens.aperture_radius,
)

debug_report = make_debug_report(
    x=x,
    dx=dx,
    lens=lens,
    f_eff=f_eff,
    bfl=bfl,
    scan_distances=scan_distances,
    on_axis=on_axis,
    z_real=z_real,
    profile_theory=profile_theory,
    profile_real=profile_real,
    focal_x=focal_x,
    focal_profile_ideal=focal_profile_ideal,
    focal_profile_real=focal_profile_real,
)
print(debug_report)
Path("lens_focus_basic_debug.txt").write_text(debug_report + "\n", encoding="utf-8")

profile_theory_norm = np.clip(normalize_profile(profile_theory), 1e-12, None)
profile_real_norm = np.clip(normalize_profile(profile_real), 1e-12, None)
focal_profile_ideal_norm = np.clip(normalize_profile(focal_profile_ideal), 1e-12, None)
focal_profile_real_norm = np.clip(normalize_profile(focal_profile_real), 1e-12, None)
focal_zoom_radius = 20e-6
focal_zoom_mask = np.abs(focal_x) <= focal_zoom_radius

plt.figure(figsize=(13.5, 8.2))

plt.subplot(2, 2, 1)
plt.title("Каустика около оси")
plt.imshow(
    axial_map**0.35,
    extent=(
        x[caustic_mask][0] * 1e6,
        x[caustic_mask][-1] * 1e6,
        scan_distances[-1] * 1e3,
        scan_distances[0] * 1e3,
    ),
    aspect="auto",
    cmap="hot",
)
plt.axhline(f_eff * 1e3, color="deepskyblue", linestyle="--", label=f"EFL = {f_eff * 1e3:.2f} мм")
plt.axhline(bfl * 1e3, color="cyan", linestyle=":", label=f"BFL = {bfl * 1e3:.2f} мм")
plt.axhline(z_real * 1e3, color="lime", linestyle=":", label=f"Факт = {z_real * 1e3:.2f} мм")
plt.xlabel("x, мкм")
plt.ylabel("z от линзы, мм")
plt.legend(fontsize=8)

plt.subplot(2, 2, 2)
plt.title("Интенсивность на оси")
plt.plot(scan_distances * 1e3, on_axis, linewidth=2.5, color="crimson")
plt.axvline(f_eff * 1e3, color="deepskyblue", linestyle="--", label=f"EFL = {f_eff * 1e3:.2f} мм")
plt.axvline(bfl * 1e3, color="cyan", linestyle=":", label=f"BFL = {bfl * 1e3:.2f} мм")
plt.axvline(z_real * 1e3, color="lime", linestyle="-.", label=f"Факт = {z_real * 1e3:.2f} мм")
plt.xlabel("z, мм")
plt.ylabel("I(0, 0, z)")
plt.grid(alpha=0.3)
plt.legend(fontsize=8)

plt.subplot(2, 2, 3)
plt.title("ASM-профили: EFL vs фактический фокус")
plt.semilogy(
    x[profile_zoom_mask] * 1e6,
    profile_theory_norm[profile_zoom_mask],
    linewidth=2.5,
    color="deepskyblue",
    label=f"EFL = {f_eff * 1e3:.2f} мм",
)
plt.semilogy(
    x[profile_zoom_mask] * 1e6,
    profile_real_norm[profile_zoom_mask],
    linewidth=2.5,
    color="orange",
    linestyle="--",
    label=f"Факт = {z_real * 1e3:.2f} мм",
)
plt.axvline(-airy_radius(wavelength, f_eff, lens.aperture_radius) * 1e6, color="gray", linestyle=":", linewidth=1.3)
plt.axvline(airy_radius(wavelength, f_eff, lens.aperture_radius) * 1e6, color="gray", linestyle=":", linewidth=1.3)
plt.xlabel("x, мкм")
plt.ylabel("I / Imax")
plt.grid(alpha=0.3)
plt.legend(fontsize=8)

plt.subplot(2, 2, 4)
plt.title("Oversampled: идеал vs реальная линза в EFL")
plt.semilogy(
    focal_x[focal_zoom_mask] * 1e6,
    focal_profile_ideal_norm[focal_zoom_mask],
    linewidth=2.3,
    color="black",
    label="Идеальный круглый зрачок",
)
plt.semilogy(
    focal_x[focal_zoom_mask] * 1e6,
    focal_profile_real_norm[focal_zoom_mask],
    linewidth=2.3,
    color="limegreen",
    linestyle="--",
    label="Реальная линза",
)
plt.axvline(-airy_radius(wavelength, f_eff, lens.aperture_radius) * 1e6, color="gray", linestyle=":", linewidth=1.3)
plt.axvline(airy_radius(wavelength, f_eff, lens.aperture_radius) * 1e6, color="gray", linestyle=":", linewidth=1.3)
plt.xlabel("x в фокальной плоскости, мкм")
plt.ylabel("I / Imax")
plt.grid(alpha=0.3)
plt.legend(fontsize=8)

plt.tight_layout()
plt.show()
