"""Pipeline — executes strategies in fixed order to produce a ShapeResult.

The pipeline reads the full dataset via DatasetReader, then applies
each registered strategy in sequence. Each strategy transforms the
tables dict and appends to the trace.

Order:
    1. schema_filter
    2. join_resolver
    3. compressibility (future)
    4. stratify (future)
    5. volume_sampler
    6. orderer

Strategies are optional — if a request doesn't use a dimension,
the corresponding strategy is a no-op.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dataset_reader import DatasetReader  # noqa: E402

from .request import ShapeRequest
from .result import ShapeResult


# Type alias for strategy functions
StrategyFn = Callable[
    [DatasetReader, dict[str, list[dict]], ShapeRequest, list[str]],
    dict[str, list[dict]],
]

# Registry of strategies in execution order.
# Each entry: (name, module_path, function_name)
# Strategies are imported lazily to keep startup fast.
_STRATEGY_REGISTRY: list[tuple[str, str | None, StrategyFn | None]] = []


def register_strategy(name: str, fn: StrategyFn) -> None:
    """Register a strategy function. Called by each strategy module."""
    _STRATEGY_REGISTRY.append((name, None, fn))


def _load_builtin_strategies() -> None:
    """Import and register all built-in strategies.

    Called once on first pipeline run. Each strategy module calls
    register_strategy() at import time.
    """
    if _STRATEGY_REGISTRY:
        return  # already loaded

    # Import in pipeline order — each module registers itself
    # Import in pipeline order — each module registers itself via register_strategy()
    # Order: schema → join → compressibility → stratify → volume → ordering
    for _mod in ("schema", "join", "compressibility", "stratify", "volume", "ordering"):
        try:
            __import__(f"shaper.strategies.{_mod}", fromlist=[_mod])
        except ImportError:
            pass  # strategy not yet implemented — skip


class Shaper:
    """Applies a ShapeRequest to a dataset, producing a ShapeResult."""

    def apply(self, request: ShapeRequest) -> ShapeResult:
        """Execute the shaping pipeline.

        Args:
            request: validated ShapeRequest

        Returns:
            ShapeResult with shaped tables, metadata, trace, stats.

        Raises:
            ValueError: if request is invalid
            FileNotFoundError: if dataset SQLite not found
        """
        request.assert_valid()
        _load_builtin_strategies()

        trace: list[str] = []
        trace.append(f"request: {request.summary()}")

        # Open dataset
        reader = DatasetReader(request.dataset)
        trace.append(f"opened: {request.dataset} ({len(reader.tables)} tables)")

        # Load all tables (initial state)
        tables: dict[str, list[dict]] = {}
        for table_name in reader.tables:
            tables[table_name] = reader.rows(table_name)
            trace.append(f"loaded: {table_name} ({len(tables[table_name]):,} rows)")

        # Snapshot before
        rows_before = sum(len(rows) for rows in tables.values())

        # Apply strategies in order
        for name, _, fn in _STRATEGY_REGISTRY:
            if fn is not None:
                tables = fn(reader, tables, request, trace)

        # Snapshot after
        rows_after = sum(len(rows) for rows in tables.values())

        # Build result
        metadata = copy.deepcopy(reader.metadata)
        metadata["_shaped"] = True
        metadata["_request_summary"] = request.summary()

        stats = {
            "rows_before": rows_before,
            "rows_after": rows_after,
            "tables_before": len(reader.tables),
            "tables_after": len(tables),
            "reduction_pct": round(100 * (1 - rows_after / max(1, rows_before)), 1),
        }

        reader.close()

        return ShapeResult(
            tables=tables,
            metadata=metadata,
            request=request,
            trace=trace,
            stats=stats,
        )
