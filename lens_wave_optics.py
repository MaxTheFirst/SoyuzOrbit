from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LensSpec:
    wavelength: float
    refractive_index: float
    aperture_radius: float
    radius_front: float
    radius_back: float
    center_thickness: float
    transmission_loss: bool = True


def bk7_refractive_index(wavelength: float) -> float:
    wavelength_um = wavelength * 1e6
    lam2 = wavelength_um**2
    b1, b2, b3 = 1.03961212, 0.231792344, 1.01046945
    c1, c2, c3 = 0.00600069867, 0.0200179144, 103.560653
    n2 = 1.0 + (b1 * lam2) / (lam2 - c1) + (b2 * lam2) / (lam2 - c2) + (b3 * lam2) / (lam2 - c3)
    return float(np.sqrt(n2))


def make_grid(window_size: float, samples: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    dx = window_size / samples
    x = (np.arange(samples) - samples // 2) * dx
    X, Y = np.meshgrid(x, x)
    return x, X, Y, dx


def plane_wave(shape: tuple[int, int]) -> np.ndarray:
    return np.ones(shape, dtype=np.complex128)


def gaussian_source(X: np.ndarray, Y: np.ndarray, waist: float) -> np.ndarray:
    return np.exp(-(X**2 + Y**2) / waist**2).astype(np.complex128)


def point_source(X: np.ndarray, Y: np.ndarray, wavelength: float, distance: float) -> np.ndarray:
    k = 2 * np.pi / wavelength
    r = np.sqrt(X**2 + Y**2 + distance**2)
    field = np.exp(1j * k * r) / r
    return field / np.max(np.abs(field))


def circular_aperture(X: np.ndarray, Y: np.ndarray, radius: float) -> np.ndarray:
    return (X**2 + Y**2 <= radius**2).astype(float)


def _surface_sag(r2: np.ndarray, radius: float) -> np.ndarray:
    if np.isinf(radius):
        return np.zeros_like(r2)
    radius_abs = abs(radius)
    inside = np.clip(radius_abs**2 - r2, 0.0, None)
    return radius_abs - np.sqrt(inside)


def lens_thickness(X: np.ndarray, Y: np.ndarray, spec: LensSpec) -> np.ndarray:
    r2 = X**2 + Y**2
    sag_front = _surface_sag(r2, spec.radius_front)
    sag_back = _surface_sag(r2, spec.radius_back)
    thickness = spec.center_thickness - sag_front - sag_back
    thickness[r2 > spec.aperture_radius**2] = 0.0
    return np.clip(thickness, 0.0, None)


def fresnel_amplitude_factor(spec: LensSpec) -> float:
    if not spec.transmission_loss:
        return 1.0
    n = spec.refractive_index
    reflectance = ((n - 1.0) / (n + 1.0)) ** 2
    transmission_intensity = (1.0 - reflectance) ** 2
    return float(np.sqrt(transmission_intensity))


def real_lens_transmission(X: np.ndarray, Y: np.ndarray, spec: LensSpec) -> np.ndarray:
    k = 2 * np.pi / spec.wavelength
    thickness = lens_thickness(X, Y, spec)
    aperture = circular_aperture(X, Y, spec.aperture_radius)
    phase = np.exp(1j * k * (spec.refractive_index - 1.0) * thickness)
    return fresnel_amplitude_factor(spec) * aperture * phase


def ideal_lens_transmission(
    X: np.ndarray,
    Y: np.ndarray,
    wavelength: float,
    focal_length: float,
    aperture_radius: float,
) -> np.ndarray:
    k = 2 * np.pi / wavelength
    aperture = circular_aperture(X, Y, aperture_radius)
    phase = np.exp(-1j * k * (X**2 + Y**2) / (2.0 * focal_length))
    return aperture * phase


def angular_spectrum_propagate(field: np.ndarray, wavelength: float, dx: float, distance: float) -> np.ndarray:
    samples_y, samples_x = field.shape
    k = 2 * np.pi / wavelength
    kx = 2 * np.pi * np.fft.fftfreq(samples_x, d=dx)
    ky = 2 * np.pi * np.fft.fftfreq(samples_y, d=dx)
    KX, KY = np.meshgrid(kx, ky)
    kt2 = KX**2 + KY**2

    propagating = kt2 <= k**2
    kz = np.empty_like(KX, dtype=np.complex128)
    kz[propagating] = np.sqrt(k**2 - kt2[propagating])
    kz[~propagating] = 1j * np.sqrt(kt2[~propagating] - k**2)

    transfer = np.exp(1j * distance * kz)
    return np.fft.ifft2(np.fft.fft2(field) * transfer)


def effective_focal_length(spec: LensSpec) -> float:
    n = spec.refractive_index
    r1 = np.inf if np.isinf(spec.radius_front) else spec.radius_front
    r2 = -np.inf if np.isinf(spec.radius_back) else -spec.radius_back

    curvature_term = 0.0
    if np.isfinite(r1):
        curvature_term += 1.0 / r1
    if np.isfinite(r2):
        curvature_term -= 1.0 / r2

    thickness_term = 0.0
    if np.isfinite(r1) and np.isfinite(r2):
        thickness_term = ((n - 1.0) * spec.center_thickness) / (n * r1 * r2)

    power = (n - 1.0) * (curvature_term + thickness_term)
    return 1.0 / power


def back_focal_length(spec: LensSpec) -> float:
    f_eff = effective_focal_length(spec)
    if np.isinf(spec.radius_front):
        return f_eff
    n = spec.refractive_index
    return f_eff * (1.0 - ((n - 1.0) * spec.center_thickness) / (n * spec.radius_front))


def gaussian_image_distance(object_distance: float, focal_length: float) -> float:
    return 1.0 / (1.0 / focal_length - 1.0 / object_distance)


def airy_radius(wavelength: float, focal_length: float, aperture_radius: float) -> float:
    diameter = 2.0 * aperture_radius
    return 1.22 * wavelength * focal_length / diameter


def rms_spot_radius(
    intensity: np.ndarray,
    X: np.ndarray,
    Y: np.ndarray,
    roi_radius: float | None = None,
) -> float:
    if roi_radius is None:
        weights = intensity
        radius2 = X**2 + Y**2
    else:
        mask = X**2 + Y**2 <= roi_radius**2
        weights = intensity * mask
        radius2 = (X**2 + Y**2) * mask

    total = np.sum(weights)
    if total <= 0.0:
        return float("nan")
    return float(np.sqrt(np.sum(weights * radius2) / total))


def focus_scan(
    field_after_lens: np.ndarray,
    wavelength: float,
    dx: float,
    distances: np.ndarray,
    X: np.ndarray,
    Y: np.ndarray,
    roi_radius: float | None = None,
) -> dict[str, np.ndarray | float]:
    center = field_after_lens.shape[0] // 2
    on_axis = np.empty_like(distances, dtype=float)
    rms_radius = np.empty_like(distances, dtype=float)

    for index, distance in enumerate(distances):
        propagated = angular_spectrum_propagate(field_after_lens, wavelength, dx, float(distance))
        intensity = np.abs(propagated) ** 2
        on_axis[index] = float(intensity[center, center])
        rms_radius[index] = rms_spot_radius(intensity, X, Y, roi_radius=roi_radius)

    best_axis_index = int(np.argmax(on_axis))
    best_rms_index = int(np.argmin(rms_radius))
    return {
        "on_axis": on_axis,
        "rms_radius": rms_radius,
        "best_axis_distance": float(distances[best_axis_index]),
        "best_rms_distance": float(distances[best_rms_index]),
    }
