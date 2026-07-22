"""PROBES da auditoria adversarial (workflow 2026-07-15) — REPRO PINADO dos achados.

A auditoria (4 lentes + síntese) criticou que o estudo fazia CENSO (contar ocorrências na
população) em vez de PROBE (construir o valor-quebrador e passar pelo RT). Estes probes são
independentes de população. Cada caso roda em SUBPROCESSO com timeout (há um caso de HANG).

RESULTADO VERIFICADO (2026-07-15, weld a20ddf7):
  BUGS R0-class (entrada aceita pelo encoder quebra RT — regra de preempção do T-REL-08):
    nome com ','  -> CORRUPÇÃO SILENCIOSA (decode devolve dado errado sem erro)
    nome com '{'  -> CORRUPÇÃO SILENCIOSA
    nome com '['  -> HANG (>20s, loop no parse do meta — classe BUG-12)
    nome com ':'  -> fail-loud TARDIO (HierarchicalError no decode; deveria rejeitar no encode)
    nome com '#'  -> fail-loud TARDIO (idem)
  ROBUSTOS (medos da auditoria NÃO confirmados):
    espaço em nome · backslash em nome · \\t em valor · \\x00 em valor · string vazia ·
    coluna toda-vazia + array vazio (sem dessincronização de cursor) · todas-folhas-vazias
  JÁ FAIL-LOUD CLARO (herdado do core, contrato \\n pendente em T-API-BOUNDARY-CONTRACTS):
    \\n em valor -> ValueError com mensagem explícita

Causa: `_build_meta` emite NOMES crus; `_parse_meta` corta nome em `,[]{}:#`. O header plano
`.8M` já ESCAPA nomes com `\\` (T-FMT-NAME-ESCAPING) — o `.8H` nasceu sem portar isso.
Fix proposto (aguarda aprovação do owner p/ mexer em src/tcf): portar o escaping de nome do
`.8M` pro meta do `.8H` (encode escapa, parse des-escapa) + rejeitar no encode o que sobrar.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = str(HERE.parents[3] / "src")

CASES = [
    # (nome, python-literal dos docs, resultado esperado APÓS o fix)
    ("nome com :", "[{'a:b': '1'}]", "RT-OK"),
    ("nome com ,", "[{'c,d': '2'}]", "RT-OK"),
    ("nome com #", "[{'ef#': '3'}]", "RT-OK"),
    ("nome com [", "[{'g[h': '4'}]", "RT-OK"),
    ("nome com {", "[{'i{j': '5'}]", "RT-OK"),
    ("nome com espaco", "[{'Order Date': '2026-01'}]", "RT-OK"),
    ("nome com backslash", "[{'k\\\\l': '6'}]", "RT-OK"),
    ("valor com \\n", "[{'x': 'a\\nb'}]", "FAILLOUD"),  # contrato \n pendente (boundary)
    ("valor com \\t", "[{'x': 'c\\td'}]", "RT-OK"),
    ("valor com \\x00", "[{'x': 'e\\x00f'}]", "RT-OK"),
    ("valor string vazia", "[{'x': ''}]", "RT-OK"),
    ("coluna toda-vazia + arr vazio", "[{'x': '', 'ys': ['', '']}, {'x': 'a', 'ys': []}]", "RT-OK"),
    ("todas as folhas vazias", "[{'x': '', 'y': ''}]", "RT-OK"),
]

TMPL = """
import sys; sys.path.insert(0, {src!r})
from tcf import decode, encode_hierarchical
docs = {docs}
blob = encode_hierarchical(docs)
back = decode(blob)
print('RT-OK' if back == docs else 'CORROMPE-SILENCIOSO obtido=' + repr(back)[:100])
"""


def run():
    out = ["PROBES da auditoria — matriz verificada (cada caso em subprocesso, timeout 20s)", ""]
    for name, docs, esperado_pos_fix in CASES:
        try:
            r = subprocess.run(
                [sys.executable, "-X", "utf8", "-c", TMPL.format(src=SRC, docs=docs)],
                capture_output=True, text=True, timeout=20, encoding="utf-8")
            if r.returncode == 0:
                got = r.stdout.strip()
            else:
                lines = (r.stderr or "").strip().splitlines()
                got = f"FAILLOUD: {lines[-1][:90] if lines else '?'}"
        except subprocess.TimeoutExpired:
            got = "***HANG >20s***"
        out.append(f"  {name:<32} -> {got}   (esperado pós-fix: {esperado_pos_fix})")
    text = "\n".join(out) + "\n"
    (HERE / "outputs").mkdir(exist_ok=True)
    (HERE / "outputs" / "02-probes-auditoria.txt").write_bytes(text.encode("utf-8"))
    print(text)


if __name__ == "__main__":
    run()
