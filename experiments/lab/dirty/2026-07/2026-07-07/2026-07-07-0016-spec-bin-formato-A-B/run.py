"""run.py — Formato A vs B do corpo spec_bin + o stream de refs nativo do HCC (owner 2026-07-07).

(1) mostra que o HCC JÁ produz literais+refs com índices naturais (^1=bit0, ^2=bit1) — o pack é pós-HCC.
(2) Formato A (literais na 1ª ocorrência, 2º declarado no 1º byte-escape) vs B (2 literais no topo) — RT, layout, bytes.
(3) caso do "2º valor aparece tarde" (male×4, female) — como A/B lidam.
(4) decisão: HCC-nativo-RLE (ordenado, textual) vs pack A/B (espalhado, V2-L); A casa com o layout do HCC.

`python run.py` regenera artifacts/. Não toca src/tcf.
"""
from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import formatos as F                                   # noqa: E402
from tcf import encode                                 # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


CASES = {
    "grupos (3m,2f,2m,3f)": ["male"] * 3 + ["female"] * 2 + ["male"] * 2 + ["female"] * 3,
    "alternado": ["male", "female"] * 4,
    "2º tarde (4m,1f)": ["male"] * 4 + ["female"],
    "espalhado": ["male" if (i * 7) % 3 else "female" for i in range(16)],
}


def thread_hcc_native():
    L = ["# HCC NATIVO — o binário já vira literais + REFERÊNCIAS com índices naturais (^1=bit0, ^2=bit1)", ""]
    for name, col in CASES.items():
        blob = encode(col)
        L.append(f"## {name}\n  col: {col}\n  HCC: {blob!r}")
        L.append("  → male=^1=bit0, female(=fe1)=^2=bit1; a corrente *N|^k É o bit-stream em RLE.\n")
    L += ["Os 'nós já têm nomes e índices naturais' (owner): o HCC coloca o literal na 1ª ocorrência e",
          "referencia (^k) depois. Pra ordenado, ISSO já é a resposta (textual/explicável). O pack (A/B) é",
          "o passo pós-HCC (V2-L) que troca a RLE por bytes quando o dado é espalhado (muitos runs curtos)."]
    w("01-hcc-native-refs.txt", "\n".join(L) + "\n")


def thread_formatos():
    L = ["# FORMATO A vs B — mesmo conteúdo (2 literais + bits empacotados), layouts diferentes", ""]
    for name, col in CASES.items():
        encA, encB = F.encode_A(col), F.encode_B(col)
        okA, okB = F.decode(encA) == col, F.decode(encB) == col
        L.append(f"## {name}  (N={len(col)}, domínio={encA['dom']}, 2º aparece na posição {encA['second_first_seen']})")
        L.append(f"  RT: A={'OK' if okA else 'FAIL'}  B={'OK' if okB else 'FAIL'}  · corpo(bytes)=A/B={F.body_bytes(encA)}B (igual)")
        L.append("  --- Formato B (2 literais no topo, ordem predeterminada 0/1) ---")
        L.append("  " + F.serialize(encB, "sexo").replace("\n", "\n  ").rstrip())
        L.append("  --- Formato A (literal na 1ª ocorrência; 2º declarado no 1º byte-escape) ---")
        L.append("  " + F.serialize(encA, "sexo").replace("\n", "\n  ").rstrip())
        L.append("")
    L += ["OBSERVAÇÃO: A e B têm os MESMOS bytes (2 literais + ceil(N/8)); diferem no LAYOUT.",
          "- **B**: precisa dos 2 valores ANTES de empacotar (2 passadas, ou buffer) — simples, predeterminado.",
          "- **A**: declara o 2º no 1º byte-escape (mesmo sem ter ocorrido) → STREAMING single-pass, e casa com",
          "  o layout NATIVO do HCC (literal na 1ª ocorrência + refs). Por isso o owner prefere A: reusa o que o",
          "  HCC já produz — 'associar depois no HCC (ou após) pra virar bytes'.",
          "- caso '2º tarde' (female só na posição 4): em A o byte-escape declara female antes; em B ele já está no topo."]
    w("02-formato-A-B.txt", "\n".join(L) + "\n")


def main():
    thread_hcc_native()
    thread_formatos()
    # decisão sem import extra (texto direto)
    L = ["# DECISÃO — pack A/B (V2-L, bytes) vs HCC-nativo-RLE (textual) por ordenação", "",
         "(medido no motor 2026-07-06-2354: ordenado/skew → RLE nativo vence e é EXPLICÁVEL; espalhado →",
         " packed vence, binário. adult.sex real: packed 6KB vs RLE 86KB → 16×.)", "",
         "spec_bin NÃO substitui o HCC — é CAMADA pós-HCC:",
         "- ordenado/agrupado → deixa o HCC-nativo (RLE de ^refs, textual, mantém a quebra);",
         "- espalhado → pack A das refs em bytes (V2-L); header textual `sexo:spec_bin` roteia.",
         "- Formato A = natural: reusa literais+refs que o HCC já pôs na 1ª ocorrência; só empacota os bits."]
    w("03-decisao-pos-hcc.txt", "\n".join(L) + "\n")

    R = ["# Formato A vs B + reuso do HCC [resumo]", "",
         "## Descoberta (grounding)",
         "O HCC já vira o binário em literais+REFERÊNCIAS com índices naturais: male=^1=bit0, female(fe1)=^2=bit1;",
         "a corrente `*N|^k` É o bit-stream em RLE (01). 'Os nós já têm nomes e índices naturais' — confirmado.",
         "",
         "## Formato A vs B (02) — mesmos bytes, layout diferente",
         "- **B**: 2 literais no topo (ordem predeterminada 0/1) + bytes. Precisa dos 2 antes (2 passadas). Simples.",
         "- **A**: literal na 1ª ocorrência; o 2º declarado no 1º byte-escape (mesmo sem ter ocorrido). STREAMING",
         "  single-pass + casa com o layout NATIVO do HCC → **owner prefere A** (reusa o que o HCC já produz).",
         "- Ambos RT-OK; corpo = 2 literais (afixo: male→fe1) + ceil(N/8) bytes.",
         "",
         "## Decisão (03)",
         "- spec_bin = CAMADA pós-HCC (V2-L), não substituto. Ordenado → HCC-nativo RLE (textual, mantém quebra);",
         "  espalhado → pack A das refs (binário, 16× em adult.sex). O header textual roteia.",
         "",
         "## Próximo",
         "- protótipo do pack pós-HCC lendo o stream de ^refs de verdade (parse `*N|^k`); enum-k; welding V2-L."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:26s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
