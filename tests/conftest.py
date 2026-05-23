"""Pytest configuration — markers + global fixtures.

Marker `requires_data`: tests dependem de SQLite hubs em
Z:/tcf-data/interim/ (configurado via scripts/_paths.py). Em ambientes
sem esses datasets (CI Linux, novo clone), tests sao SKIPADOS
automaticamente (via _needs_db helper em test_shaper).

CI roda: `pytest -m "not requires_data"` pra rodar so' tests sem deps
externos.

Local roda: `pytest` pra rodar tudo (incluindo integration tests).
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-marca tests que dependem de SQLite hubs externos."""
    requires_data_marker = pytest.mark.requires_data
    for item in items:
        # Convencao: tests em test_shaper precisam SQLite
        # (test_shaper ja' tem _needs_db helper interno que skipa, mas
        # marker permite filter via -m "not requires_data" em CI)
        if "test_shaper" in item.nodeid:
            item.add_marker(requires_data_marker)
