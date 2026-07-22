# -*- coding: utf-8 -*-
"""Overhead de header num REGISTRO MINIMO (1 linha). READ-ONLY.
Mostra header vs body pra o caso extremo 'chave-valor / 1 registro', e os levers atuais
(drop_names, nature). Pergunta do owner: quanto o header pode ser mais economizado?"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode

def split(blob):
    b = blob.encode("utf-8")
    nl = b.find(b"\n")
    if nl < 0 or not (blob.startswith("#TCF")):   # orfao (sem magic)
        return 0, len(b)
    return nl + 1, len(b) - (nl + 1)   # (header_bytes, body_bytes)

def show(label, blob):
    h, d = split(blob)
    print(f"{label:34} total={h+d:3}B  header={h:3}B  body={d:3}B   {blob!r}")

rec = {"cpf": ["111.444.777-35"], "nome": ["Joao Silva"]}
print("REGISTRO: 1 linha, 2 colunas (cpf + nome)\n")
show("multi nomeado", encode(rec))
try: show("multi + nature cpf", encode(rec, nature_per_col={"cpf": "cpf"}))
except Exception as e: print("  (nature:", e, ")")
try: show("multi drop_names (anonimo)", encode(rec, drop_names=True))
except Exception as e: print("  (drop_names:", e, ")")
try: show("drop_names + nature", encode(rec, drop_names=True, nature_per_col={"cpf": "cpf"}))
except Exception as e: print("  (dn+nat:", e, ")")
print()
show("single-col orfao (so cpf, 1 valor)", encode(["111.444.777-35"]))
show("single-col orfao (so nome)", encode(["Joao Silva"]))
