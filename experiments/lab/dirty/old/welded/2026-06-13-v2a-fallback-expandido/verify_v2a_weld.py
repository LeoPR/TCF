"""Smoke test do weld de V2-A (opt-in fallback) na API publica. Z-free."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

# coluna baixa-card curta (padrao beijing 'hour') infla em TCF -> raw vence
hour = [str(i % 24) for i in range(300)]
nome = [f"item_{i:04d}_descricao_longa_unica" for i in range(300)]  # TCF vence
table = {"hour": hour, "nome": nome}


def show(label, **kw):
    side = SideOutputs()
    text = encode(table, side_outputs=side, **kw)
    rt = decode(text) == table
    print(f"{label}: {len(text.encode('utf-8'))}B  magic={text.split(chr(10),1)[0]!r}  "
          f"RT={'OK' if rt else 'FAIL'}  fallback_cols={side.multi_info.get('fallback_cols')}")
    return text


print("== tabela com coluna baixa-card (hour) + coluna texto-unico ==")
v1 = show("fallback=False (default)")
v2 = show("fallback=True ", fallback=True)
print(f"ganho fallback: {(1 - len(v2.encode('utf-8'))/len(v1.encode('utf-8')))*100:.2f}%")

print("\n== invariante: fallback=False byte-identico ao comportamento atual ==")
print("v1 default == encode sem kwarg?", encode(table) == v1)

print("\n== tabela onde NADA beneficia (fallback=True deve dar #TCF.6) ==")
t2 = {"a": ["abc", "abcd", "abcde"], "b": ["xyz", "xyzw", "xyzwv"]}
txt = encode(t2, fallback=True)
print(f"magic={txt.split(chr(10),1)[0]!r}  (esperado #TCF.6 M)  RT={decode(txt)==t2}")

print("\n== raw col com valores vazios + RT ==")
t3 = {"x": ["", "1", "2", "", "3"], "y": ["a", "b", "c", "d", "e"]}
txt3 = encode(t3, fallback=True)
print(f"magic={txt3.split(chr(10),1)[0]!r}  RT={decode(txt3)==t3}")

print("\n== decode v2 sem flag (self-describing) ==")
print("decode(v2) == table?", decode(v2) == table)
