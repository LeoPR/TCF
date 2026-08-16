# -*- coding: utf-8 -*-
"""RT QUEBRADO CALADO: a polaridade come o fim do nome da coluna no `.8M` e no `.8H`.

    python run.py     # sai 0 se REPRODUZIR o defeito (é um lab de defeito, não de ganho)

## O defeito

`decode({"obs.": [...]})` devolve a chave `"obs"`. Com pontuação DOBRADA (`"obs.."`), além da
chave, **os valores também corrompem**. Nenhum warning, nenhuma exceção — perda 100% silenciosa.

## O mecanismo, verificado

A polaridade é **camada de borda, a PRIMEIRA coisa do decode** (`decoder.py:154-161`):

    _tag, _sufixo = _separa_sufixo_polaridade(line1[6:])

Ela roda sobre `line1[6:]` — que no `.8M` é `M<meta>`, e no fim do meta está o **nome da última
coluna** (forma `min_header`, `multi/core.py:413-414`, que omite o size da última). A polaridade
não sabe disso: vê `Mobs.`, separa `('Mobs', '.')`, e entrega ao parser um meta onde a coluna se
chama `obs`.

## Por que passou despercebido: depende de `n`

O gatilho é o **modo** que vence no `min()` por coluna, e o modo põe (ou não) um prefixo:

    n=3   -> header `#TCF.8M!obs.`  (modo raw, prefixo `!`)  -> RT ok
    n>=10 -> header `#TCF.8Mobs.`   (modo tcf, prefixo VAZIO) -> RT QUEBRA

Com poucos valores o `!` protege. Um teste de RT com coluna pequena não vê nada.

## GATE

`src/tcf` INTOCADO. Este lab só REPRODUZE e delimita — não conserta.
"""
from __future__ import annotations

import json
import pathlib
import string
import sys
import warnings

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode                              # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _js(p, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, **JSON_KW), encoding="utf-8", newline="")


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            import shutil
            shutil.rmtree(p)
        p.mkdir(parents=True)
    reg = {}
    VALS = [f"v{i}" for i in range(26)]

    # ── BLOCO 1 — o caso concreto, e a dependência de n ─────────────────────
    print("BLOCO 1 — o mesmo nome, variando só o NÚMERO DE VALORES\n")
    print(f"  {'nome':<8} {'n':>5}  {'header':<24} {'RT':<6} chave de volta")
    b1 = []
    for nome in ("obs.", "qtd.", "ab."):
        for n in (3, 5, 10, 26, 100):
            d = {nome: VALS[:n] if n <= 26 else [f"v{i}" for i in range(n)]}
            w = encode(d)
            volta = decode(w)
            ok = volta == d
            b1.append({"nome": nome, "n": n, "header": w.split("\n", 1)[0],
                       "rt": ok, "chave_volta": list(volta)[0] if volta else None})
            _k = repr(list(volta)[0]) if volta else "?"
            print(f"  {nome:<8} {n:>5}  {w.split(chr(10),1)[0]:<24} "
                  f"{'ok' if ok else 'QUEBRA':<6} {_k}")
    reg["bloco1_dependencia_de_n"] = b1
    virada = [x for x in b1 if x["nome"] == "obs."]
    print(f"\n  a virada é o MODO: com prefixo `!` (raw) o RT fecha; sem prefixo, quebra.")

    # ── BLOCO 2 — o sweep: quanto da pontuação quebra, nas duas rotas ───────
    print("\nBLOCO 2 — sweep de toda a pontuação ASCII, .8M e .8H (n=26)")
    so_chave, chave_e_vals, ok_M = [], [], []
    falhas_H = ok_H = 0
    with warnings.catch_warnings(record=True) as capt:
        warnings.simplefilter("always")
        for p in string.punctuation:
            for nome in (f"ab{p}", f"ab{p}{p}"):
                d = {nome: list(VALS)}
                try:
                    volta = decode(encode(d))
                    if volta == d:
                        ok_M.append(nome)
                    elif list(volta.values())[0] == VALS:
                        so_chave.append(nome)
                    else:
                        chave_e_vals.append(nome)
                except Exception:
                    pass
                r = [{nome: v} for v in VALS]
                try:
                    if decode(encode(r)) == r:
                        ok_H += 1
                    else:
                        falhas_H += 1
                except Exception:
                    pass
    n_tot = len(string.punctuation) * 2
    n_falha_M = len(so_chave) + len(chave_e_vals)
    print(f"  .8M: {n_falha_M}/{n_tot} RT FALSO = {100*n_falha_M/n_tot:.1f}%")
    print(f"       só a CHAVE muda ......... {len(so_chave):>2}  {so_chave[:8]}")
    print(f"       chave E VALORES corrompem {len(chave_e_vals):>2}  {chave_e_vals[:8]}")
    print(f"       escaparam ............... {len(ok_M):>2}  {ok_M}")
    print(f"  .8H: {falhas_H}/{n_tot} RT FALSO = {100*falhas_H/n_tot:.1f}%   "
          f"<- o `.8H` NÃO é controle: falha pelo MESMO mecanismo")
    print(f"  WARNINGS emitidos em todo o sweep: {len(capt)}   <- perda 100% silenciosa")
    reg["bloco2_sweep"] = {
        "n_casos": n_tot, "M_falso": n_falha_M, "M_so_chave": so_chave,
        "M_chave_e_valores": chave_e_vals, "M_ok": ok_M,
        "H_falso": falhas_H, "warnings": len(capt),
        "CONSTANTE_na_comparacao": "os MESMOS 26 valores; varia só o(s) último(s) char do NOME",
    }

    # ── BLOCO 3 — o par de contra-prova: 2 colunas NÃO quebram ──────────────
    print("\nBLOCO 3 — CONTRA-PROVA: a MESMA coluna, mas com uma SEGUNDA ao lado")
    ok2 = 0
    for p in string.punctuation:
        for nome in (f"ab{p}", f"ab{p}{p}"):
            d = {nome: list(VALS), "zz": list(VALS)}
            try:
                if decode(encode(d)) == d:
                    ok2 += 1
            except Exception:
                pass
    print(f"  2 colunas: {ok2}/{n_tot} RT OK = {100*ok2/n_tot:.1f}%")
    print(f"  => ISOLA a causa: com 2+ colunas o meta ganha `,`/`=` e o nome deixa de ser o")
    print(f"     fim da linha 1, então a polaridade não o alcança. O defeito é da coluna ÚNICA.")
    reg["bloco3_contraprova"] = {"duas_colunas_ok": ok2, "de": n_tot,
                                 "CONSTANTE_na_comparacao": "o MESMO nome e os MESMOS valores; muda só haver uma 2a coluna"}

    # evidência gravada: os wires do caso concreto
    for nome in ("obs.", "obs.."):
        d = {nome: list(VALS)}
        _esc(OUT / f"quebra-{'ponto' if nome=='obs.' else 'ponto-duplo'}.tcf", encode(d))
        _js(OUT / f"quebra-{'ponto' if nome=='obs.' else 'ponto-duplo'}.roundtrip.json", decode(encode(d)))
        _js(INP / f"quebra-{'ponto' if nome=='obs.' else 'ponto-duplo'}.entrada.json", d)
    _js(INP / "sweep.fonte.json", {
        "gerador": "run.py — string.punctuation x {1,2} repeticoes, nome 'ab'+p",
        "valores": "26 sinteticos v0..v25 (o dado nao importa; o NOME e' a variavel)",
        "pin": "sem Z:, inteiramente sintetico e deterministico"})
    _js(RAIZ / "resultado.json", reg)

    reproduziu = n_falha_M > 0 and falhas_H > 0 and len(capt) == 0
    print(f"\n{'DEFEITO REPRODUZIDO' if reproduziu else 'NAO reproduziu — investigar'}: "
          f"RT falso em {n_falha_M}/{n_tot} (.8M) e {falhas_H}/{n_tot} (.8H), {len(capt)} warnings")
    return 0 if reproduziu else 1


if __name__ == "__main__":
    raise SystemExit(main())
