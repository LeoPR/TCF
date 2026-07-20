"""ShapeRequest — declarative specification for dataset subsetting.

A ShapeRequest describes WHAT subset of a canonical dataset you want,
along WHICH dimensions, WITHOUT specifying HOW to get it. The pipeline
(pipeline.py) interprets the request and applies strategies in order.

All fields have sensible defaults so that `ShapeRequest(dataset="adult-census")`
returns the full dataset unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Valid named schema levels (per-dataset mapping lives in schema strategy)
SCHEMA_LEVELS = ("minimal", "core", "chain", "full")

# Valid join levels
JOIN_LEVELS = ("normalized", "flat")

# Valid order prefixes
ORDER_PREFIXES = ("natural", "random", "sorted:", "reverse:")


@dataclass
class ShapeRequest:
    """Declarative request for a shaped dataset subset.

    Attributes:
        dataset:    canonical dataset name (e.g. "adult-census", "tpch-sf001")
        volume:     how many rows to return
                      int   → exact N rows
                      float → fraction 0.0-1.0 (e.g. 0.1 = 10%)
                      None  → all rows (default)
        seed:       random seed for reproducibility (default 42)
        schema:     which tables/columns to include
                      str   → named level ("minimal", "core", "chain", "full")
                      list  → explicit table names (e.g. ["customer", "orders"])
        join_level: how to present multi-table data
                      "normalized" → separate tables with FK references
                      "flat"       → single denormalized supertable
        order:      row ordering in the output
                      "natural"      → insertion order from SQLite
                      "random"       → shuffled using seed
                      "sorted:col"   → ascending by column
                      "reverse:col"  → descending by column
        stratify_by: column name for stratified sampling (None = no stratification)
        compressibility_range: tuple (lo, hi) with 0.0=easiest, 1.0=hardest
                               None = no filtering by compressibility
    """

    dataset: str
    volume: int | float | None = None
    seed: int = 42
    schema: str | list[str] = "full"
    join_level: str = "normalized"
    order: str = "natural"
    stratify_by: str | None = None
    compressibility_range: tuple[float, float] | None = None
    fk_preserving: bool = False
    fact_table: str | None = None

    def validate(self) -> list[str]:
        """Return list of validation errors. Empty list = valid."""
        errors: list[str] = []

        # dataset
        if not self.dataset or not isinstance(self.dataset, str):
            errors.append("dataset must be a non-empty string")

        # volume
        if self.volume is not None:
            if isinstance(self.volume, float):
                if not (0.0 <= self.volume <= 1.0):
                    errors.append(f"volume as float must be 0.0-1.0, got {self.volume}")
            elif isinstance(self.volume, int):
                if self.volume < 0:
                    errors.append(f"volume as int must be >= 0, got {self.volume}")
            else:
                errors.append(f"volume must be int, float, or None; got {type(self.volume).__name__}")

        # seed
        if not isinstance(self.seed, int):
            errors.append(f"seed must be int, got {type(self.seed).__name__}")

        # schema
        if isinstance(self.schema, str):
            if self.schema not in SCHEMA_LEVELS:
                errors.append(f"schema must be one of {SCHEMA_LEVELS} or a list; got {self.schema!r}")
        elif isinstance(self.schema, list):
            if not all(isinstance(t, str) for t in self.schema):
                errors.append("schema list must contain only strings")
            if len(self.schema) == 0:
                errors.append("schema list must not be empty")
        else:
            errors.append(f"schema must be str or list[str]; got {type(self.schema).__name__}")

        # join_level
        if self.join_level not in JOIN_LEVELS:
            errors.append(f"join_level must be one of {JOIN_LEVELS}; got {self.join_level!r}")

        # order
        if not isinstance(self.order, str):
            errors.append(f"order must be str; got {type(self.order).__name__}")
        elif not any(self.order == p.rstrip(":") or self.order.startswith(p)
                     for p in ORDER_PREFIXES):
            errors.append(
                f"order must start with one of {ORDER_PREFIXES}; got {self.order!r}"
            )

        # stratify_by
        if self.stratify_by is not None and not isinstance(self.stratify_by, str):
            errors.append(f"stratify_by must be str or None; got {type(self.stratify_by).__name__}")

        # compressibility_range
        cr = self.compressibility_range
        if cr is not None:
            if not (isinstance(cr, tuple) and len(cr) == 2):
                errors.append("compressibility_range must be a 2-tuple or None")
            else:
                lo, hi = cr
                if not (0.0 <= lo <= hi <= 1.0):
                    errors.append(
                        f"compressibility_range must satisfy 0<=lo<=hi<=1; got ({lo}, {hi})"
                    )

        return errors

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def assert_valid(self) -> None:
        """Raise ValueError if request is invalid."""
        errors = self.validate()
        if errors:
            raise ValueError(
                f"Invalid ShapeRequest:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    def summary(self) -> str:
        """One-line human-readable summary."""
        parts = [f"dataset={self.dataset}"]
        if self.volume is not None:
            parts.append(f"volume={self.volume}")
        if self.schema != "full":
            parts.append(f"schema={self.schema}")
        if self.join_level != "normalized":
            parts.append(f"join={self.join_level}")
        if self.order != "natural":
            parts.append(f"order={self.order}")
        if self.stratify_by:
            parts.append(f"stratify={self.stratify_by}")
        if self.compressibility_range:
            parts.append(f"compress={self.compressibility_range}")
        if self.fk_preserving:
            parts.append(f"fk_preserving=True")
            if self.fact_table:
                parts.append(f"fact={self.fact_table}")
        parts.append(f"seed={self.seed}")
        return "ShapeRequest(" + ", ".join(parts) + ")"
