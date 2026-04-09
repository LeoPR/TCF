"""Schema: parse metadata.json → table/column structure."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class TableMeta:
    name: str
    file: Path
    pk: str | None                 # primary-key column name
    fks: dict[str, str] = field(default_factory=dict)  # col_name → ref_table_name


def load_schema(meta_path: Path, data_dir: Path) -> dict[str, TableMeta]:
    """Parse metadata.json and return an ordered dict of TableMeta.

    metadata.json format:
        {
          "pessoas": "pessoas.csv#id",
          "vendas":  "vendas.csv#pessoas=id_pessoa,produtos=id_produto"
        }

    PK spec:  "#col_name"            (no '=' sign)
    FK spec:  "#ref1=col1,ref2=col2" (each item has '=')
    """
    raw: dict[str, str] = json.loads(meta_path.read_text(encoding="utf-8"))
    tables: dict[str, TableMeta] = {}

    for table_name, spec in raw.items():
        file_part, _, rel_part = spec.partition("#")
        file = data_dir / file_part
        pk: str | None = None
        fks: dict[str, str] = {}

        if rel_part:
            if "=" not in rel_part:
                pk = rel_part
            else:
                for item in rel_part.split(","):
                    ref_table, _, col_name = item.partition("=")
                    fks[col_name.strip()] = ref_table.strip()

        tables[table_name] = TableMeta(
            name=table_name,
            file=file,
            pk=pk,
            fks=fks,
        )

    return tables
