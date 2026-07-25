"""Revisão de grafia (owner 2026-07-24) — `0` (dígito nu) vs `^0` (referência de linha).

Objeção do owner: *"o `0` causa uma sobrecarga de interpretação; se é pra apontar pra uma
referência, ele seria uma referência interna ao null. Esse `0` sem indicar referência fica
ambíguo."* — e propôs que TODOS os nulls sejam `^0`, não só o primeiro.

O formato tem DOIS espaços de referência:

  dígito nu   -> FRAGMENTO: pedaços de string para COMPOR (`pedido-*\\1` / `1\\2`)
  `^N`        -> LINHA:     o VALOR INTEIRO daquela linha

null é um **valor inteiro**, não um pedaço de string.

Variantes medidas:
  A  `0`   dígito nu; o 1º null DECLARA um nó, os demais viram `^k`  (forma da 1ª rodada)
  B  `^0`  endereço reservado ESTÁVEL; NÃO declara nó; todo null é `^0`  (proposta do owner)
"""
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
sys.path.insert(0, str(RAIZ.parents[5] / "src"))

from tcf import encode, decode  # noqa: E402

MARCA, CAB = "0", "#TCF.8\n"


def _split(ln):
    """`*N|resto` -> ('*N|', resto); senão ('', ln)."""
    if ln.startswith("*") and "|" in ln:
        bar = ln.find("|")
        return ln[:bar + 1], ln[bar + 1:]
    return "", ln


# ------------------------------------------------------------------ A: dígito nu
def enc_A(col):
    corpo = encode([MARCA if v is None else v for v in col], stamp=False)
    out = []
    for ln in corpo.split("\n"):
        pre, r = _split(ln)
        out.append(pre + "0" if r == "\\0" else ln)
    return CAB + "\n".join(out)


def dec_A(wire):
    out = []
    for ln in wire[len(CAB):].split("\n"):
        pre, r = _split(ln)
        out.append(pre + "\\0" if r == "0" else ln)
    return [None if v == MARCA else v for v in decode("\n".join(out))]


# ------------------------------------------------------------------ B: `^0` reservado
def enc_B(col):
    """`^0` é endereço RESERVADO: não declara nó. Logo os nós reais renumeram para baixo."""
    corpo = encode([MARCA if v is None else v for v in col], stamp=False)
    linhas = corpo.split("\n")
    z, no = None, 0                                   # z = nó (A) ocupado pela declaração do null
    for ln in linhas:
        pre, r = _split(ln)
        if r.startswith("^"):
            continue
        if ln == "":                                  # linha final vazia do split
            continue
        no += 1
        if r == "\\0":
            z = no
    out = []
    for ln in linhas:
        pre, r = _split(ln)
        if r == "\\0":
            out.append(pre + "^0")                    # declaração -> endereço reservado
        elif r.startswith("^"):
            k = int(r[1:])
            out.append(pre + ("^0" if k == z else f"^{k - 1 if z and k > z else k}"))
        else:
            out.append(ln)
    return CAB + "\n".join(out)


def dec_B(wire):
    """Pré-avaliador: B -> A (o 1º `^0` vira a declaração) -> core REAL -> materializa None."""
    linhas = wire[len(CAB):].split("\n")
    m = 0                                             # nós declarados ANTES do 1º `^0`
    for ln in linhas:
        _pre, r = _split(ln)
        if r == "^0":
            break
        if r.startswith("^") or ln == "":
            continue
        m += 1
    z, visto, out = m + 1, False, []
    for ln in linhas:
        pre, r = _split(ln)
        if r == "^0":
            if not visto:
                visto = True
                out.append(pre + "\\0")               # 1º `^0` = a declaração, em A
            else:
                out.append(pre + f"^{z}")
        elif r.startswith("^"):
            k = int(r[1:])
            out.append(pre + f"^{k + 1 if k >= z else k}")
        else:
            out.append(ln)
    return [None if v == MARCA else v for v in decode("\n".join(out))]


# ------------------------------------------------------------------ execução
def main():
    src = (RAIZ / "run.py").read_text(encoding="utf-8").replace('if __name__ == "__main__":', "if False:")
    ns = {"__file__": str((RAIZ / "run.py").resolve())}
    exec(compile(src, "run.py", "exec"), ns)
    FONTES = ns["FONTES"]

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas = [], 0
    for eid, (col, _n) in FONTES.items():
        wa, wb = enc_A(col), enc_B(col)
        ok_a, ok_b = dec_A(wa) == col, dec_B(wb) == col
        falhas += (not ok_a) + (not ok_b)
        a, b = len(wa.encode()), len(wb.encode())
        linhas.append((eid, sum(v is None for v in col), a, b, b - a,
                       "OK" if (ok_a and ok_b) else ("A" if ok_b else "B") + " FALHOU"))

    out = ["# Revisão de grafia — `0` (dígito nu) vs `^0` (referência de linha)", "",
           "| id | nulls | A `0` (B) | B `^0` (B) | Δ | RT |", "|---|---:|---:|---:|---:|---|"]
    out += [f"| {e} | {k} | {a} | {b} | {d:+} | {s} |" for e, k, a, b, d, s in linhas]
    tot = sum(d for *_, d, _s in linhas)
    out += ["", f"RT: **{len(linhas) * 2 - falhas}/{len(linhas) * 2}** (A e B).",
            f"Δ total de B sobre A: **{tot:+} B** em {len(linhas)} casos.", ""]

    col = FONTES["A-exemplo-owner"][0]
    out += ["## Exemplo do owner", "", "```",
            f"coluna : {col}",
            f"A `0`  : {enc_A(col)!r}",
            f"B `^0` : {enc_B(col)!r}", "```", "",
            "```", "# B, legível:", enc_B(col).replace("\\", "\\\\"), "```"]
    (RAIZ / "result-revisao-grafia.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
