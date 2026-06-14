"""
uma.core.projection -- map psi(x,y) <-> z (leading Fourier modes).

The projection takes the 2D complex field and extracts its (2n+1)^2 - 1
leading Fourier modes (DC excluded), packed as a real vector of length
2 * ((2n+1)^2 - 1). The lift inverts this exactly: the operator is a
partial isometry between psi and the band-limited subspace.

This is the geometric piece that lets the Kalman filter and constraint
projections run on a low-dimensional state z without losing the band-
limited spectral content of the field.
"""
from __future__ import annotations
import numpy as np


class FieldProjection:
    """Project psi(x,y) onto leading Fourier modes."""

    def __init__(self, N: int = 32, n_modes: int = 4):
        self.N = N
        self.n_modes = n_modes
        # FFT-frequency masks
        kx = np.fft.fftfreq(N, d=1.0 / N).astype(int)  # integer k indices
        ky = np.fft.fftfreq(N, d=1.0 / N).astype(int)
        KX, KY = np.meshgrid(kx, ky, indexing="ij")
        mask = (np.abs(KX) <= n_modes) & (np.abs(KY) <= n_modes)
        # exclude DC
        mask[0, 0] = False
        self._mask = mask
        self._idx = np.argwhere(mask)  # list of (i, j) grid indices
        self._n_complex = self._idx.shape[0]

    @property
    def real_dim(self) -> int:
        """Dimension of the real-valued projected state z."""
        return 2 * self._n_complex

    @property
    def complex_dim(self) -> int:
        return self._n_complex

    def project(self, psi: np.ndarray) -> np.ndarray:
        """Project psi(N,N) -> real-valued z of length 2 * n_complex."""
        psi = np.asarray(psi)
        F = np.fft.fft2(psi) / (self.N * self.N)
        coeffs = F[self._mask]
        return np.concatenate([coeffs.real, coeffs.imag])

    def lift(self, z: np.ndarray) -> np.ndarray:
        """Lift z back to a band-limited psi(N,N) via inverse FFT."""
        z = np.asarray(z, dtype=float).ravel()
        n = self._n_complex
        re = z[:n]
        im = z[n:2 * n]
        coeffs = re + 1j * im
        F = np.zeros((self.N, self.N), dtype=complex)
        F[self._mask] = coeffs
        # enforce Hermitian symmetry only if input was real -- here psi is complex,
        # so we keep the asymmetric spectrum.
        psi = np.fft.ifft2(F) * (self.N * self.N)
        return psi
