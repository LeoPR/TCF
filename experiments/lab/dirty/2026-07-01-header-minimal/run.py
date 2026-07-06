# -*- coding: utf-8 -*-
"""Header-minimal — quanto o CABEÇALHO (shebang+meta) pode ser economizado num payload minúsculo?

FECHA o estudo (2026-07-05): conserta a contabilidade (o `medir.py` stub contava só o shebang) e a
lever `nature` (SPEC_CPF, não a string), mede o **piso** do header pelas levers reais + as **deduções**
(M/N implícitos, achado das peças hierárquicas P5/P6) + o **break-even** (header vs N registros).
READ-ONLY (não toca src/tcf). Levers hipotéticas (implícito/derivado) = engenhoca (o que um design
mínimo CUSTARIA), claramente rotuladas. `python run.py` regenera artifacts/.
"""
from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, SPEC_CPF        # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)


def nb(s): return len(s.encode("utf-8"))


def split_header(blob: str):
    """header = shebang + meta (as linhas antes do body). Detecta se o meta está FUNDIDO na 1ª linha
    (drop_names/#TCF.8M!...) ou numa 2ª linha (#TCF.7 M\\n<meta>). Line-based → robusto p/ nature/N>1."""
    lines = blob.split("\n")
    after_magic = lines[0][6:]                 # depois de "#TCF.N"
    fused = any(c in after_magic for c in "!@%=,0123456789")   # meta na 1ª linha?
    nhl = 1 if fused else 2
    header = "\n".join(lines[:nhl]) + "\n"
    hb = nb(header)
    return hb, nb(blob) - hb


def write(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
CPF, NOME = "111.444.777-35", "Joao Silva"
REC = {"cpf": [CPF], "nome": [NOME]}
raw_chars = len(CPF) + len(NOME)          # 24 — os dados "puros"


def secao_floor():
    L = ["# PISO do header — 1 registro (cpf + nome), dados puros = 24 chars", "",
         f"{'cenário':32} {'total':>5} {'header':>6} {'body':>5}   blob", "-" * 96]
    rows = {}

    def row(label, blob):
        h, d = split_header(blob)
        L.append(f"{label:32} {nb(blob):>5} {h:>6} {d:>5}   {blob!r}")
        rows[label] = (nb(blob), h)
        return nb(blob), h

    row("multi nomeado (default 0.7)", encode(REC))
    row("multi drop_names (anônimo)", encode(REC, drop_names=True))
    try:
        row("nature cpf (SPEC_CPF)", encode(REC, nature_per_col={"cpf": SPEC_CPF}))
    except Exception as e:
        L.append(f"{'nature cpf':32}   (erro: {e})")
    try:
        row("drop_names + nature cpf", encode(REC, drop_names=True, nature_per_col={"cpf": SPEC_CPF}))
    except Exception as e:
        L.append(f"{'drop_names+nature':32}   (erro: {e})")

    # levers HIPOTÉTICAS (deduções — não estão na API; engenhoca do que custaria)
    drop_blob = encode(REC, drop_names=True)
    drop_total, drop_h = nb(drop_blob), split_header(drop_blob)[0]
    body = drop_total - drop_h
    L += ["", "-- deduções (hipotético, não-API) --"]
    # implícito-M: >=2 colunas ⇒ multi (achado P5/P6) → dropar o byte 'M'
    L.append(f"{'implícito-M (deduz multi)':32} {drop_total-1:>5} {drop_h-1:>6} {body:>5}   (drop o flag M: >=2 cols ⇒ multi)")
    # derivado (O-FMT-14): schema pré-acordado ⇒ header vira só assinatura, ou nada
    L.append(f"{'derivado: só magic (#TCF.8)':32} {6+body:>5} {6:>6} {body:>5}   (schema pré-acordado; magic p/ roteamento)")
    L.append(f"{'derivado: body puro (0 header)':32} {body:>5} {0:>6} {body:>5}   (contrato total; header fora de banda)")

    L += ["", f"LEITURA: no registro mínimo, o header (shebang+meta) é ~metade do payload ({rows.get('multi nomeado (default 0.7)',(0,0))[1]}B "
              f"de {rows.get('multi nomeado (default 0.7)',(0,0))[0]}B). drop_names já corta os NOMES; as deduções (M implícito) e",
          "o header DERIVÁVEL (O-FMT-14, schema pré-acordado) são o piso — mas exigem contrato/decisão de formato (src)."]
    return "\n".join(L) + "\n", rows


def secao_breakeven():
    L = ["# BREAK-EVEN — o header só pesa em N pequeno (foco byte-level)", "",
         "N registros DISTINTOS (drop_names). header ~fixo; body cresce → header vira ruído.", "",
         f"{'N':>4} {'total':>7} {'header':>7} {'body':>7} {'header %':>9}", "-" * 40]
    # valores DISTINTOS e de alta entropia (pouco afixo comum → body cresce ~linear)
    for N in (1, 5, 20, 100):
        cpfs = [f"{i:03d}.{(i*13) % 1000:03d}.{(i*29) % 1000:03d}-{(i*7) % 100:02d}" for i in range(N)]
        nomes = [f"{(i*37) % 97}Nm{(i*53) % 89}x{(i*11) % 71}" for i in range(N)]
        blob = encode({"cpf": cpfs, "nome": nomes}, drop_names=True)
        h, d = split_header(blob)
        frac = 100.0 * h / nb(blob)
        L.append(f"{N:>4} {nb(blob):>7} {h:>7} {d:>7} {frac:>8.1f}%")
    L += ["", "LEITURA: N=1 → header ~1/3-1/2 do total; N=100 → ~poucos %. O ganho de encolher o header",
          "concentra-se em payloads MINÚSCULOS (1-poucos registros) — exatamente o foco byte-level."]
    return "\n".join(L) + "\n"


def main():
    s1, rows = secao_floor()
    s2 = secao_breakeven()
    write("01-piso-header.txt", s1)
    write("02-breakeven.txt", s2)
    write("00-resumo.txt", s1 + "\n" + "=" * 96 + "\n\n" + s2)
    print("Artefatos em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:22s} {p.stat().st_size:6d} B")
    print("\n" + s1 + "\n" + s2)


if __name__ == "__main__":
    main()
