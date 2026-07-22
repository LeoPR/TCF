"""run.py — Ciclo 1c: a FRONTEIRA do link posicional + fix da família nullable/presença (máscara).

(1) Mostra as 4 formas que o retângulo homogêneo não fecha (crash/corrupção concreta).
(2) PROVA o fix de B1 (chave-ausente) e B2 (null-em-coluna) com máscara 3-estados (RT exato).
(3) CARACTERIZA B3 (array-em-array → repetition level) e B4 (N:N → flat OK, normalização precisa de ponte),
    deferidos ao welding. Prior-art: Dremel rep/def levels; H-CARD-06.

`python run.py` regenera artifacts/. Ponteiro: EXP-015 report.md (peça 10) + teoria-cardinalidade.md.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "2026-07-06-2238-tcf8h-escala-formas-e-tipos"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import mask_codec as MK                                # noqa: E402
import tipos_codec as TP                               # noqa: E402  (o codec tabular do 1b)

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


BOUNDARIES = {
    "B1-chave-ausente": {"linhas": [{"a": 1, "b": 2}, {"a": 3}]},
    "B2-null-em-coluna": {"linhas": [{"x": 1}, {"x": None}]},
    "B3-array-em-array": {"grupos": [{"g": "A", "itens": [{"n": 1}, {"n": 2}]}, {"g": "B", "itens": [{"n": 3}]}]},
    "B4-N-para-N": {"pares": [{"aluno": "ana", "curso": "mat"}, {"aluno": "ana", "curso": "fis"},
                             {"aluno": "bob", "curso": "mat"}]},
}


def thread_boundaries():
    L = ["# THREAD 1 — as 4 fronteiras no codec TABULAR (C-híbrida do 1b): o que quebra o retângulo", ""]
    diag = []
    for tag, src in BOUNDARIES.items():
        L.append(f"## {tag}\n  {json.dumps(src, ensure_ascii=False)}")
        try:
            blob, _ = TP.encode_C(src)
            back = TP.decode_C(blob)
            ok = back == src
            if ok:
                L.append(f"  TABULAR: RT-OK {len(blob.encode())}B — o retângulo FECHA (não é fronteira de RT)")
                diag.append((tag, "RT-OK (flat)"))
            else:
                L.append(f"  TABULAR: RT-MISMATCH (corrompe)\n    out: {back}")
                diag.append((tag, "CORROMPE"))
        except Exception as e:
            L.append(f"  TABULAR: FRONTEIRA {type(e).__name__}: {e}")
            diag.append((tag, f"CRASH ({type(e).__name__})"))
        L.append("")
    w("01-fronteiras-no-tabular.txt", "\n".join(L) + "\n")
    return diag


def thread_mask_fix():
    """Prova o fix de B1+B2: máscara 3-estados sobre o array de objetos."""
    L = ["# THREAD 2 — FIX da família nullable/presença: máscara 3-estados ('.'=valor '0'=null '-'=ausente)",
         "", "RT exato reconstruindo o array heterogêneo (chave ausente omitida; null = None).", ""]
    ok_all = True
    for tag in ("B1-chave-ausente", "B2-null-em-coluna"):
        rows = BOUNDARIES[tag]["linhas"]
        masked, order = MK.array_to_masked(rows)
        back = MK.masked_to_array(masked, order, len(rows))
        ok = back == rows
        ok_all &= ok
        L.append(f"## {tag}  RT={'OK' if ok else 'MISMATCH'}")
        L.append(f"  in : {rows}")
        for k, (dense, mask) in masked.items():
            L.append(f"  col({k}): dense={dense}  máscara={mask!r}")
        L.append(f"  out: {back}\n")
    L += ["LEITURA: a máscara é o CANAL DE PRESENÇA que faltava — dense body (só valores) + string de",
          "estados. Custo = |máscara| bytes por coluna esparsa (1 char/linha; comprimível por RLE se",
          "denso/regular). Fecha B1 (ausente) e B2 (null) SEM materializar buracos. É o mesmo mecanismo",
          "do definition level do Dremel (níveis de nulo/presença), aqui em forma textual inspecionável."]
    w("02-fix-mascara-presenca.txt", "\n".join(L) + "\n")
    return ok_all


def main():
    diag = thread_boundaries()
    ok_mask = thread_mask_fix()

    R = ["# Ciclo 1c — fronteira do link posicional + fix nullable/presença [resumo]", "",
         "## As 4 fronteiras no codec tabular (thread 1)"]
    for tag, s in diag:
        R.append(f"  {tag:20s} {s}")
    R += ["", f"## Fix da família nullable/presença (thread 2): máscara 3-estados — RT {'OK' if ok_mask else 'FALHA'}",
          "  B1 (chave-ausente) e B2 (null-em-coluna) FECHAM com máscara '.'/'0'/'-'. = definition level (Dremel).",
          "", "## Caracterização (o que fica pro welding)",
          "- **B1 presença** + **B2 nullable**: MESMO mecanismo (máscara/def-level) — provado tratável aqui.",
          "- **B3 array-em-array**: precisa de **repetition level** (onde o array aninhado reinicia) — o caso",
          "  da peça 10 (EXP-015). Não é máscara simples; é o rep-level do Dremel. Deferido.",
          "- **B4 N:N**: o array PLANO fecha RT (é uma tabela). A fronteira é de NORMALIZAÇÃO (fatorar aluno×curso",
          "  pede tabela-ponte) — escolha de compressão/estrutura, não gap de RT. Deferido (liga com @dict/H-CARD).",
          "", "## Fecha o Ciclo 1 (funcionalidade)",
          "- 1a tipos (RT) · 1b A/B/C decidido (C default) + formas · 1c fronteiras caracterizadas + nullable/presença",
          "  provado tratável. RT-alvo comum (aninhamento, tipos, esparsidade) COBERTO; rep-level (B3) + N:N (B4)",
          "  são o próximo salto de estrutura (welding). → Ciclo 2 (fluxo)."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:28s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()
