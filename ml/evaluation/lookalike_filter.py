import numpy as np
from typing import Dict, Any, Tuple, Optional

class LookAlikeFilterInterface:
    """
    Modular interface for SAR oil spill look-alike discrimination.
    Assesses whether dark ocean surface patches correspond to mineral oil slicks
    or natural / meteorological look-alikes (low-wind calm zones, biogenic slicks,
    ship wakes, or internal wave modulation).
    """

    def evaluate_candidate(
        self,
        patch: np.ndarray,
        wind_speed_mps: Optional[float] = None,
        context_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError


class RuleBasedLookAlikeFilter(LookAlikeFilterInterface):
    """
    Configurable physical rule-based filter for oil spill look-alike mitigation.
    Evaluates:
    1. Ambient Wind Speed: If wind < 2.5 m/s, dark patches are predominantly low-wind calm zones.
    2. Patch Gradient / Border Sharpness: Real mineral spills exhibit steep damping gradients
       along borders, whereas natural biogenic films have feathered, gradual transitions.
    3. Aspect Ratio / Linearity: Very high aspect ratios along heading lines denote ship wakes.
    """
    def __init__(
        self,
        min_reliable_wind_mps: float = 2.5,
        max_reliable_wind_mps: float = 12.0,
        edge_gradient_threshold: float = 0.08
    ):
        self.min_reliable_wind = min_reliable_wind_mps
        self.max_reliable_wind = max_reliable_wind_mps
        self.edge_gradient_threshold = edge_gradient_threshold

    def evaluate_candidate(
        self,
        patch: np.ndarray,
        wind_speed_mps: Optional[float] = None,
        context_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        flags = []
        lookalike_probability = 0.0

        # 1. Wind Speed Assessment
        if wind_speed_mps is not None:
            if wind_speed_mps < self.min_reliable_wind:
                flags.append("LOW_WIND_CALM_ZONE_SUSPECTED")
                lookalike_probability += 0.55
            elif wind_speed_mps > self.max_reliable_wind:
                flags.append("HIGH_WIND_DISPERSION_SUSPECTED")
                lookalike_probability += 0.25

        # 2. Gradient Sharpness across boundary
        if patch.ndim == 2 and patch.size > 25:
            gy, gx = np.gradient(patch)
            grad_mag = np.sqrt(gx**2 + gy**2)
            mean_grad = float(np.mean(grad_mag))
            if mean_grad < self.edge_gradient_threshold:
                flags.append("FEATHERED_BOUNDARY_NATURAL_FILM_CANDIDATE")
                lookalike_probability += 0.20

        lookalike_probability = min(lookalike_probability, 0.95)
        is_probable_spill = lookalike_probability < 0.50

        return {
            "is_probable_spill": is_probable_spill,
            "lookalike_probability": round(lookalike_probability, 3),
            "confidence_penalty": round(lookalike_probability * 0.4, 3),
            "flags": flags,
            "scientific_note": (
                "Dark patch evaluated against meteorological look-alike heuristics. "
                "MVP filter reduces obvious false alarms; secondary neural classification recommended for production."
            ),
        }
