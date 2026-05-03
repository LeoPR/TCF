"""Encoder adapters — interface unificada para varios formatos.

Cada encoder implementa:
- name: str
- encode(rows: list[dict]) -> str  (or bytes for binary formats)
- decode(data: str) -> list[dict]

Para uso no pipeline. Encoders sao stateless (config por instancia).
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
import csv
import io
import json


@runtime_checkable
class Encoder(Protocol):
    name: str
    def encode(self, rows: list[dict]) -> str: ...
    def decode(self, data: str) -> list[dict]: ...


# ---------------------------------------------------------------------------
# CSV — baseline. Stdlib only.
# ---------------------------------------------------------------------------

class CSVEncoder:
    name = "csv"

    def __init__(self, infer_types: bool = True):
        self.infer_types = infer_types

    def encode(self, rows: list[dict]) -> str:
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    def decode(self, data: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
        if self.infer_types and rows:
            return [self._infer_types(r) for r in rows]
        return rows

    @staticmethod
    def _infer_types(row: dict) -> dict:
        """Tenta converter strings para int/float/bool quando possivel."""
        out = {}
        for k, v in row.items():
            if v == "":
                out[k] = None
            elif v in ("True", "true"):
                out[k] = True
            elif v in ("False", "false"):
                out[k] = False
            else:
                # Tenta int, depois float, fallback para str
                try:
                    out[k] = int(v)
                except (ValueError, TypeError):
                    try:
                        out[k] = float(v)
                    except (ValueError, TypeError):
                        out[k] = v
        return out


# ---------------------------------------------------------------------------
# JSON — formato hierarquico standard
# ---------------------------------------------------------------------------

class JSONEncoder:
    name = "json"

    def __init__(self, compact: bool = True):
        self.compact = compact

    def encode(self, rows: list[dict]) -> str:
        if self.compact:
            return json.dumps(rows, separators=(",", ":"))
        return json.dumps(rows)

    def decode(self, data: str) -> list[dict]:
        return json.loads(data)


# ---------------------------------------------------------------------------
# JSONL — JSON line-delimited (1 row per linha)
# ---------------------------------------------------------------------------

class JSONLEncoder:
    name = "jsonl"

    def encode(self, rows: list[dict]) -> str:
        return "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)

    def decode(self, data: str) -> list[dict]:
        return [json.loads(line) for line in data.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# TCF — adapter para o nosso encoder atual (v0.2)
# ---------------------------------------------------------------------------

class TCFEncoder:
    name = "tcf"

    def __init__(self, level: int = 2, include_stats: bool = True,
                 precision: int | None = None,
                 sort_by: str | None = None):
        # NOTA: TCF v0.2 atual nao tem sort_by. Mantemos parametro para
        # compatibilidade futura (v0.4); por agora, sort_by e ignorado
        # silenciosamente. EXP-003 vai testar isso quando v0.4 chegar.
        self.level = level
        self.include_stats = include_stats
        self.precision = precision
        self.sort_by = sort_by

    def encode(self, rows: list[dict]) -> str:
        from tcf import encode_rows, EncodeConfig
        # v0.2 EncodeConfig aceita: level, include_stats, precision
        if self.sort_by is not None:
            # Se sort_by foi pedido, aplicamos manualmente (v0.2 hack)
            rows = sorted(rows, key=lambda r: r.get(self.sort_by, ""))
        cfg = EncodeConfig(level=self.level, include_stats=self.include_stats,
                           precision=self.precision)
        return encode_rows("data", rows, config=cfg)

    def decode(self, data: str) -> list[dict]:
        """Decode TCF text -> list[dict] (single-table only).

        NOTA: TCF v0.2 tem bug em que decoder interpreta colunas com
        nomes parecendo FK (active, id_*, etc.) como tabelas separadas.
        Aqui extraimos apenas a tabela 'data' (nome usado em encode).
        Reportar como achado: TCF v0.4 deve corrigir essa heuristica.
        """
        from tcf import decode
        result = decode(data)
        if isinstance(result, dict):
            # Tabela principal e a que tem o nome usado em encode_rows("data", ...)
            if "data" in result:
                return result["data"]
            # Fallback: maior tabela (mais linhas)
            return max(result.values(), key=len)
        return result


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ENCODERS: dict[str, type] = {
    "csv": CSVEncoder,
    "json": JSONEncoder,
    "jsonl": JSONLEncoder,
    "tcf": TCFEncoder,
    # toon: adicionar quando biblioteca disponivel
}


def get_encoder(name: str, **kwargs) -> Encoder:
    """Instancia um encoder pelo nome com kwargs."""
    if name not in ENCODERS:
        raise ValueError(f"Unknown encoder {name!r}. Available: {sorted(ENCODERS)}")
    return ENCODERS[name](**kwargs)


def list_encoders() -> list[str]:
    return sorted(ENCODERS)
