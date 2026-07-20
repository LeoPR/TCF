"""Dataset Shaper — multidimensional sampler for canonical datasets.

Extracts controlled subsets from the SQLite hub according to
volume, schema complexity, join level, ordering, stratification,
and compressibility.

**This is a support tool, NOT part of TCF core.**

Usage:
    from shaper import Shaper, ShapeRequest

    req = ShapeRequest(
        dataset="adult-census",
        volume=100,
        order="random",
        seed=42,
    )
    result = Shaper().apply(req)

    for name, rows in result.tables.items():
        print(f"{name}: {len(rows)} rows")
"""

from .request import ShapeRequest
from .result import ShapeResult
from .pipeline import Shaper

__all__ = ["ShapeRequest", "ShapeResult", "Shaper"]
