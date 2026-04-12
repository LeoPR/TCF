"""Strategy modules for the dataset shaper pipeline.

Each strategy transforms `tables: dict[str, list[dict]]` according
to one dimension of a ShapeRequest. Strategies are applied in a
fixed order defined in pipeline.py.

Protocol:
    def apply(reader, tables, request, trace) -> tables
"""
