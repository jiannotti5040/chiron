"""
uma.core.filter -- Linear-Gaussian Kalman filter on z.
"""
from __future__ import annotations
import numpy as np
from uma.core.state import FieldPosterior


class KalmanFilter:
    """
    Linear-Gaussian Kalman filter operating on the projected state z.

    predict(F, Q):
        m_pred = F m
        P_pred = F P F^T + Q

    update(y, H, R):
        S = H P H^T + R
        K = P H^T S^{-1}
        m_new = m + K (y - H m)
        P_new = (I - K H) P (I - K H)^T + K R K^T   (Joseph form)
    """

    def __init__(self, posterior: FieldPosterior, process_noise: float = 0.05):
        self.posterior = posterior
        self.q = float(process_noise)

    def predict(self, F: np.ndarray | None = None, Q: np.ndarray | None = None) -> FieldPosterior:
        d = self.posterior.dim
        if F is None:
            F = np.eye(d)
        if Q is None:
            Q = self.q * np.eye(d)
        m = self.posterior.mean
        P = self.posterior.cov
        m_new = F @ m
        P_new = F @ P @ F.T + Q
        # symmetrize
        P_new = 0.5 * (P_new + P_new.T)
        self.posterior = FieldPosterior(mean=m_new, cov=P_new)
        return self.posterior

    def update(self, y: np.ndarray, H: np.ndarray, R: np.ndarray) -> FieldPosterior:
        m = self.posterior.mean
        P = self.posterior.cov
        innov = y - H @ m
        S = H @ P @ H.T + R
        # solve K S = P H^T  ->  K = P H^T S^{-1}
        K = np.linalg.solve(S.T, (H @ P.T)).T
        m_new = m + K @ innov
        I_KH = np.eye(P.shape[0]) - K @ H
        P_new = I_KH @ P @ I_KH.T + K @ R @ K.T
        # symmetrize
        P_new = 0.5 * (P_new + P_new.T)
        self.posterior = FieldPosterior(mean=m_new, cov=P_new)
        return self.posterior
