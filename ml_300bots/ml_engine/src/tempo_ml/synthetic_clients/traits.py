"""Client trait vectors and benchmark archetypes.

Owner: docs/topics/synthetic-clients/record.md, sections 3.1 and 4.

theta = <baseline_ms, mu, sigma, beta, alpha, F, C>, where F is derived from C
so that R(t = S, S) = 0.9.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Mapping

import numpy as np

# Trait bounds from record section 3.1.
BASELINE_MS_RANGE = (150.0, 500.0)
ALPHA_RANGE = (0.1, 0.5)


@dataclass(frozen=True)
class ClientTraits:
    """Cognitive traits of one synthetic client.

    Attributes:
        baseline_ms: Physical motor / board-scan / UI latency floor (ms).
        mu: Log-space mean of the raw hesitation log-normal (seconds).
        sigma: Log-space dispersion of the raw hesitation log-normal.
        beta: Effort; scales cognitive strain when retrievability is low.
        alpha: Practice automaticity rate.
        C: Forgetting-curve decay power.
    """

    baseline_ms: float
    mu: float
    sigma: float
    beta: float
    alpha: float
    C: float

    def __post_init__(self) -> None:
        lo, hi = BASELINE_MS_RANGE
        if not lo <= self.baseline_ms <= hi:
            raise ValueError(f"baseline_ms must be in [{lo}, {hi}], got {self.baseline_ms}")
        if self.sigma <= 0.0:
            raise ValueError(f"sigma must be > 0, got {self.sigma}")
        if self.beta < 0.0:
            raise ValueError(f"beta must be >= 0, got {self.beta}")
        lo, hi = ALPHA_RANGE
        if not lo <= self.alpha <= hi:
            raise ValueError(f"alpha must be in [{lo}, {hi}], got {self.alpha}")
        if self.C <= 0.0:
            raise ValueError(f"C must be > 0, got {self.C}")

    @property
    def F(self) -> float:
        """Forgetting-curve scaling factor F = 0.9^(-1/C) - 1."""
        return 0.9 ** (-1.0 / self.C) - 1.0

    def as_dict(self) -> dict[str, float]:
        out = asdict(self)
        out["F"] = self.F
        return out


# Stage 1 benchmark archetypes (record section 4).
ARCHETYPES: Mapping[str, ClientTraits] = {
    "blitzer": ClientTraits(baseline_ms=220.0, mu=-0.6, sigma=0.45, beta=0.4, alpha=0.35, C=0.65),
    "balanced": ClientTraits(baseline_ms=300.0, mu=-0.2, sigma=0.40, beta=1.0, alpha=0.25, C=0.50),
    "diligent": ClientTraits(baseline_ms=380.0, mu=0.3, sigma=0.35, beta=2.2, alpha=0.20, C=0.35),
}

_TRAIT_NAMES = ("baseline_ms", "mu", "sigma", "beta", "alpha", "C")


def clamp_traits(values: Mapping[str, float]) -> ClientTraits:
    """Build ClientTraits, clamping each value into its permitted range."""
    v = dict(values)
    v["baseline_ms"] = float(np.clip(v["baseline_ms"], *BASELINE_MS_RANGE))
    v["alpha"] = float(np.clip(v["alpha"], *ALPHA_RANGE))
    v["sigma"] = max(float(v["sigma"]), 1e-3)
    v["beta"] = max(float(v["beta"]), 0.0)
    v["C"] = max(float(v["C"]), 1e-3)
    v["mu"] = float(v["mu"])
    return ClientTraits(**{k: v[k] for k in _TRAIT_NAMES})


@dataclass(frozen=True)
class TraitDistribution:
    """Multivariate normal over the trait vector, theta ~ N(mean, cov).

    This is the hook for Stage 2 calibration (review-dataset record, 4.2):
    a calibrated cohort supplies ``mean`` and ``cov``. Samples are clamped
    into the permitted trait ranges.

    Args:
        mean: Cohort mean traits.
        cov: 6x6 covariance in the order baseline_ms, mu, sigma, beta, alpha, C.
    """

    mean: ClientTraits
    cov: np.ndarray

    def __post_init__(self) -> None:
        cov = np.asarray(self.cov, dtype=float)
        if cov.shape != (len(_TRAIT_NAMES), len(_TRAIT_NAMES)):
            raise ValueError(f"cov must be {len(_TRAIT_NAMES)}x{len(_TRAIT_NAMES)}")
        object.__setattr__(self, "cov", cov)

    @classmethod
    def diagonal(cls, mean: ClientTraits, std: Mapping[str, float]) -> "TraitDistribution":
        """Independent traits with the given standard deviations (missing = 0)."""
        stds = np.array([float(std.get(name, 0.0)) for name in _TRAIT_NAMES])
        return cls(mean=mean, cov=np.diag(stds**2))

    def sample(self, rng: np.random.Generator) -> ClientTraits:
        mean_vec = np.array([getattr(self.mean, name) for name in _TRAIT_NAMES])
        draw = rng.multivariate_normal(mean_vec, self.cov)
        return clamp_traits(dict(zip(_TRAIT_NAMES, draw)))


def with_overrides(traits: ClientTraits, **overrides: float) -> ClientTraits:
    """Return a copy of ``traits`` with some fields replaced (validated)."""
    return replace(traits, **overrides)
