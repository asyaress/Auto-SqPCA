"""F3-v1 A1-A4 abstention rule."""
from __future__ import annotations


def reasons(selected: str | None, stability: float, observed_fraction: float,
            relative_width: float, theta_s: float, theta_d: float, theta_w: float) -> list[str]:
    out = []
    if selected is None: out.append("A1")
    if stability < theta_s: out.append("A2")
    if observed_fraction < theta_d: out.append("A3")
    if relative_width > theta_w: out.append("A4")
    return out
