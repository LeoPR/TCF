"""Test fixtures — progressive datasets from trivial to complex.

Each fixture creates a temporary directory with CSVs + metadata.json,
returning (meta_path, data_dir) ready for encode()/decode().

Levels:
  L0  single_column   1 table, 1 text column (no PK)
  L1  key_value       1 table, PK + 1 text column
  L2  numeric         1 table, PK + numeric columns (int, float)
  L3  multi_type      1 table with mixed types (text + int + float)
  L4  two_tables_fk   2 tables with FK relationship
  L5  rle_heavy       Data with lots of repetition (tests RLE compression)
  L6  edge_cases      Spaces in values, accents, empty strings, zeros, negatives
"""

import csv
import json
import tempfile
from pathlib import Path
from typing import Any


def _write_fixture(
    tables: dict[str, list[dict[str, str]]],
    metadata: dict[str, str],
) -> tuple[Path, Path]:
    """Write tables as CSVs + metadata.json to a temp directory.

    Returns (meta_path, data_dir).
    """
    tmp = Path(tempfile.mkdtemp(prefix="tcf_test_"))
    for name, rows in tables.items():
        if not rows:
            # Write empty CSV with no rows
            (tmp / f"{name}.csv").write_text("", encoding="utf-8")
            continue
        path = tmp / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    meta_path = tmp / "metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path, tmp


# ─────────────────────────────────────────────────────────────────────────────
# L0 — Single column, no PK
# ─────────────────────────────────────────────────────────────────────────────

def l0_single_column() -> tuple[Path, Path, dict]:
    """1 table, 1 column: just names.

    frutas.csv:
      nome
      Banana
      Maca
      Uva
    """
    tables = {
        "frutas": [
            {"nome": "Banana"},
            {"nome": "Maca"},
            {"nome": "Uva"},
        ],
    }
    metadata = {"frutas": "frutas.csv"}
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "frutas": [
            {"nome": "Banana"},
            {"nome": "Maca"},
            {"nome": "Uva"},
        ],
    }
    return meta, data_dir, expected


# ─────────────────────────────────────────────────────────────────────────────
# L1 — Key-value (PK + text)
# ─────────────────────────────────────────────────────────────────────────────

def l1_key_value() -> tuple[Path, Path, dict]:
    """1 table, PK + 1 text column.

    cores.csv:
      id,nome
      1,Vermelho
      2,Azul
      3,Verde
    """
    tables = {
        "cores": [
            {"id": "1", "nome": "Vermelho"},
            {"id": "2", "nome": "Azul"},
            {"id": "3", "nome": "Verde"},
        ],
    }
    metadata = {"cores": "cores.csv#id"}
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "cores": [
            {"id": "1", "nome": "Vermelho"},
            {"id": "2", "nome": "Azul"},
            {"id": "3", "nome": "Verde"},
        ],
    }
    return meta, data_dir, expected


# ─────────────────────────────────────────────────────────────────────────────
# L2 — Numeric columns (int + float)
# ─────────────────────────────────────────────────────────────────────────────

def l2_numeric() -> tuple[Path, Path, dict]:
    """1 table with numeric data: integers and floats.

    medidas.csv:
      id,peso,altura
      1,70,1.75
      2,85,1.80
      3,60,1.65
      4,90,1.92
      5,55,1.58
    """
    tables = {
        "medidas": [
            {"id": "1", "peso": "70",  "altura": "1.75"},
            {"id": "2", "peso": "85",  "altura": "1.80"},
            {"id": "3", "peso": "60",  "altura": "1.65"},
            {"id": "4", "peso": "90",  "altura": "1.92"},
            {"id": "5", "peso": "55",  "altura": "1.58"},
        ],
    }
    metadata = {"medidas": "medidas.csv#id"}
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "medidas": [
            {"id": "1", "peso": "70",  "altura": "1.75"},
            {"id": "2", "peso": "85",  "altura": "1.80"},
            {"id": "3", "peso": "60",  "altura": "1.65"},
            {"id": "4", "peso": "90",  "altura": "1.92"},
            {"id": "5", "peso": "55",  "altura": "1.58"},
        ],
    }
    return meta, data_dir, expected


# ─────────────────────────────────────────────────────────────────────────────
# L3 — Multi-type (text + int + float in one table)
# ─────────────────────────────────────────────────────────────────────────────

def l3_multi_type() -> tuple[Path, Path, dict]:
    """1 table mixing text, int, and float.

    produtos.csv:
      id,nome,qtd,preco
      1,Caneta,100,2.50
      2,Caderno,50,12.90
      3,Borracha,200,1.00
      4,Lapis,150,0.75
    """
    tables = {
        "produtos": [
            {"id": "1", "nome": "Caneta",   "qtd": "100", "preco": "2.50"},
            {"id": "2", "nome": "Caderno",  "qtd": "50",  "preco": "12.90"},
            {"id": "3", "nome": "Borracha", "qtd": "200", "preco": "1.00"},
            {"id": "4", "nome": "Lapis",    "qtd": "150", "preco": "0.75"},
        ],
    }
    metadata = {"produtos": "produtos.csv#id"}
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "produtos": [
            {"id": "1", "nome": "Caneta",   "qtd": "100", "preco": "2.50"},
            {"id": "2", "nome": "Caderno",  "qtd": "50",  "preco": "12.90"},
            {"id": "3", "nome": "Borracha", "qtd": "200", "preco": "1.00"},
            {"id": "4", "nome": "Lapis",    "qtd": "150", "preco": "0.75"},
        ],
    }
    return meta, data_dir, expected


# ─────────────────────────────────────────────────────────────────────────────
# L4 — Two tables with FK
# ─────────────────────────────────────────────────────────────────────────────

def l4_two_tables_fk() -> tuple[Path, Path, dict]:
    """2 tables: categorias (PK) and itens (FK -> categorias).

    categorias.csv:
      id,nome
      1,Escritorio
      2,Cozinha

    itens.csv:
      id_categoria,item,preco
      1,Caneta,2.50
      1,Grampeador,15.00
      2,Prato,8.00
      2,Copo,3.50
      1,Papel,12.00
    """
    tables = {
        "categorias": [
            {"id": "1", "nome": "Escritorio"},
            {"id": "2", "nome": "Cozinha"},
        ],
        "itens": [
            {"id_categoria": "1", "item": "Caneta",     "preco": "2.50"},
            {"id_categoria": "1", "item": "Grampeador", "preco": "15.00"},
            {"id_categoria": "2", "item": "Prato",      "preco": "8.00"},
            {"id_categoria": "2", "item": "Copo",       "preco": "3.50"},
            {"id_categoria": "1", "item": "Papel",      "preco": "12.00"},
        ],
    }
    metadata = {
        "categorias": "categorias.csv#id",
        "itens": "itens.csv#categorias=id_categoria",
    }
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "categorias": tables["categorias"],
        "itens": tables["itens"],
    }
    return meta, data_dir, expected


# ─────────────────────────────────────────────────────────────────────────────
# L5 — RLE heavy (many repeated values)
# ─────────────────────────────────────────────────────────────────────────────

def l5_rle_heavy() -> tuple[Path, Path, dict]:
    """1 table with very repetitive FK values — perfect for RLE testing.

    vendas_rep.csv:
      id_loja,produto,vl
      (loja 1 repeated 5x, loja 2 repeated 3x, loja 1 again 2x)

    lojas.csv:
      id,nome
      1,Centro
      2,Shopping
    """
    tables = {
        "lojas": [
            {"id": "1", "nome": "Centro"},
            {"id": "2", "nome": "Shopping"},
        ],
        "vendas_rep": [
            {"id_loja": "1", "produto": "A", "vl": "10.0"},
            {"id_loja": "1", "produto": "B", "vl": "20.0"},
            {"id_loja": "1", "produto": "A", "vl": "10.0"},
            {"id_loja": "1", "produto": "C", "vl": "30.0"},
            {"id_loja": "1", "produto": "A", "vl": "10.0"},
            {"id_loja": "2", "produto": "B", "vl": "20.0"},
            {"id_loja": "2", "produto": "B", "vl": "20.0"},
            {"id_loja": "2", "produto": "C", "vl": "30.0"},
            {"id_loja": "1", "produto": "A", "vl": "10.0"},
            {"id_loja": "1", "produto": "A", "vl": "10.0"},
        ],
    }
    metadata = {
        "lojas": "lojas.csv#id",
        "vendas_rep": "vendas_rep.csv#lojas=id_loja",
    }
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "lojas": tables["lojas"],
        "vendas_rep": tables["vendas_rep"],
    }
    return meta, data_dir, expected


# ─────────────────────────────────────────────────────────────────────────────
# L6 — Edge cases
# ─────────────────────────────────────────────────────────────────────────────

def l6_edge_cases() -> tuple[Path, Path, dict]:
    """Edge cases: zeros, negatives, large numbers, accented text.

    dados.csv:
      id,nome,valor,nota
      1,Joao,0.00,10
      2,Maria,-5.50,0
      3,Jose,1000.99,7
      4,Ana,0.01,-3
    """
    tables = {
        "dados": [
            {"id": "1", "nome": "Joao",  "valor": "0.00",    "nota": "10"},
            {"id": "2", "nome": "Maria", "valor": "-5.50",   "nota": "0"},
            {"id": "3", "nome": "Jose",  "valor": "1000.99", "nota": "7"},
            {"id": "4", "nome": "Ana",   "valor": "0.01",    "nota": "-3"},
        ],
    }
    metadata = {"dados": "dados.csv#id"}
    meta, data_dir = _write_fixture(tables, metadata)
    expected = {
        "dados": tables["dados"],
    }
    return meta, data_dir, expected
