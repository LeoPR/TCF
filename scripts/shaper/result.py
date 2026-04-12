"""ShapeResult — output of the shaper pipeline.

Contains the shaped data, metadata, the original request, an execution
trace (for auditability), and summary statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ShapeResult:
    """Result of applying a ShapeRequest to a dataset.

    Attributes:
        tables:   row-oriented data — {table_name: [row_dict, ...]}
        metadata: copy of dataset metadata, adjusted for the subset
        request:  the original ShapeRequest that produced this result
        trace:    ordered list of pipeline steps executed
        stats:    summary numbers (rows_before, rows_after, tables, etc)
    """

    tables: dict[str, list[dict[str, Any]]]
    metadata: dict[str, Any]
    request: Any  # ShapeRequest (avoid circular import)
    trace: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def table_names(self) -> list[str]:
        return list(self.tables.keys())

    @property
    def total_rows(self) -> int:
        return sum(len(rows) for rows in self.tables.values())

    def table_row_counts(self) -> dict[str, int]:
        return {name: len(rows) for name, rows in self.tables.items()}

    def summary(self) -> str:
        """Human-readable summary of the result."""
        lines = [
            f"ShapeResult: {len(self.tables)} table(s), {self.total_rows:,} total rows",
        ]
        for name, rows in self.tables.items():
            cols = list(rows[0].keys()) if rows else []
            lines.append(f"  {name}: {len(rows):,} rows x {len(cols)} cols")
        if self.trace:
            lines.append(f"  trace: {len(self.trace)} steps")
        return "\n".join(lines)
