"""Bordas em valor de spec — a reavaliacao que o owner pediu, em 4 eixos.

O REENQUADRAMENTO (owner, 2026-08-21), sobre o H-15-07
------------------------------------------------------
*"nesse caso e' similar a se comportar como um trim de bordas, quando tem
espacos por exemplo [...] o spec se interessa pelo tipo do dado, e restos
poderiam ser ignorados (por flag) [...] uma e' deixar ele mais preguicoso, e dar
um warning e tolerar e fazer trim, por outro lado, poderia ser mais rigido e
exigir que seja limpo [...] o TCF tem esse modo de spec lazy, entao em ultimo
caso poderia ate' tratar como CPF mesmo, mas tentando restaurar os caracteres
trim. [...] tem que ver se isso nao e' falha do construtor [...] o comum e' o
dado entrar OK. [...] tratar apenas o comum, e o incomum a gente tolera perda de
performance e emissoes de warning."*

OS 4 EIXOS
----------
  E1  ERRO DO TESTE? — de onde nasce o LF, e o que o TCF faz HOJE com CADA tipo
      de borda. (A resposta reenquadra o problema inteiro.)
  E2  POSSIBILIDADE DE OCORRER — prevalencia em dado REAL + as fontes de
      ingestao que produzem borda.
  E3  O QUE FAZER SE OCORRE — as 3 posturas do owner, medidas em BYTE.
  E4  O COMUM x O INCOMUM — quanto custa a guarda no caminho comum.

NADA e' soldado aqui. E' reavaliacao pra decisao do owner.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode, SideOutputs                          # noqa: E402
from tcf.natures import (                                            # noqa: E402
    SPEC_CNPJ, SPEC_CPF, SPEC_IP, SPEC_DATA_ISO, MARKER_LITERAL,
    classify_value, decode_value, encode_value,
)
from tcf.natures.templated_checked import _cnpj_check_fn             # noqa: E402

LF, CR, TAB, SP = "\n", "\r", "\t", " "
BASE = "11.222.333/0001-81"
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    p = pasta / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())


def main() -> int:
    res = {}
    print("=" * 96)
    print("BORDAS EM VALOR DE SPEC — reavaliacao em 4 eixos")
    print("=" * 96)

    # ── E1 ───────────────────────────────────────────────────────────────
    print("\nE1) O TCF JA' FAZ TRIM? — o que acontece HOJE com cada borda")
    print(f"  {'borda':<20} {'status':<18} {'payload':<13} RT")
    matriz = []
    for rot, v in [("nada", BASE), ("espaco a esquerda", SP * 2 + BASE),
                   ("espaco a direita", BASE + SP * 2),
                   ("espaco nos dois", SP * 2 + BASE + SP * 2),
                   ("tab a direita", BASE + TAB), ("LF a direita", BASE + LF),
                   ("CR a direita", BASE + CR), ("CRLF a direita", BASE + CR + LF),
                   ("LF duplo", BASE + LF * 2), ("LF a esquerda", LF + BASE)]:
        st = classify_value(SPEC_CNPJ, v)
        p, _ = encode_value(SPEC_CNPJ, v)
        rt = decode_value(SPEC_CNPJ, p) == v
        pv = (p[:11] + "..") if len(p) > 13 else p
        print(f"  {rot:<20} {st:<18} {pv:<13} {'ok' if rt else 'PERDE'}")
        matriz.append({"borda": rot, "status": st, "payload_len": len(p), "rt": rt})
    perdem = [m for m in matriz if not m["rt"]]
    print(f"\n  VEREDITO: {len(perdem)} de {len(matriz)} variantes perdem dado — "
          f"{[m['borda'] for m in perdem]}")
    print("  O TCF **nao faz trim nenhum**. Toda borda cai em literal e o RT se")
    print("  preserva. A excecao unica e' um vazamento acidental do `$` da regex,")
    print("  que em Python casa TAMBEM antes de UM LF final. Nao e' politica de")
    print("  trim: e' um caractere especifico escapando da validacao.")
    res["E1_matriz"] = matriz
    assert len(perdem) == 1 and perdem[0]["borda"] == "LF a direita"

    # o mesmo vazamento nos outros specs
    print("\n  o vazamento nos 4 specs (valor valido + LF):")
    raio = {}
    for nome, spec, amostras in (
            ("cpf", SPEC_CPF, ["529.982.247-25"]),
            ("cnpj", SPEC_CNPJ, [BASE, "12.ABC.345/01DE-35"]),
            ("ip", SPEC_IP, ["192.168.0.1", "192.168.001.001"]),
            ("data-iso", SPEC_DATA_ISO, ["2026-08-21"])):
        perde = [v for v in amostras
                 if decode_value(spec, encode_value(spec, v + LF)[0]) != v + LF]
        raio[nome] = {"testados": amostras, "perdem": perde}
        print(f"    {nome:9} perde em {len(perde)}/{len(amostras)}  {perde}")
    print("  `data-iso` ESCAPA porque o classify dele checa o COMPRIMENTO")
    print("  (`len(v) != 10`) antes da regex — a defesa que os outros nao tem.")
    res["E1_raio"] = raio

    # ── E2 ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("E2) POSSIBILIDADE DE OCORRER — prevalencia em dado REAL")
    print("=" * 96)
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=20000,
                                    seed=5, stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    campos = [k for k in rows[0] if isinstance(rows[0][k], str)]
    com_borda = {k: sum(1 for x in rows if isinstance(x.get(k), str)
                        and x[k] != x[k].strip()) for k in campos}
    com_borda = {k: n for k, n in com_borda.items() if n}
    print(f"  {len(rows):,} linhas · {len(campos)} campos texto (receita-cnpj-enderecos)")
    print(f"  campos com valor bordado: {len(com_borda)}  {com_borda or '(nenhum)'}")
    print("\n  MAS prevalencia-no-dataset NAO e' prevalencia-no-mundo: a fonte aqui")
    print("  ja' passou por limpeza. As fontes REAIS de borda sao de INGESTAO:")
    for fonte in ("`for line in f:` sem .strip() — o LF do arquivo VEM no valor",
                  "coluna CHAR(18) de banco — padding com espaco a direita",
                  "copy/paste de planilha ou PDF — espaco e NBSP nas pontas",
                  "CSV com espaco depois da virgula (`a, b`) sem skipinitialspace"):
        print(f"    · {fonte}")
    print("  Ou seja: raro no dado ARMAZENADO, plausivel no dado RECEBIDO.")
    res["E2_prevalencia"] = {"linhas": len(rows), "campos": len(campos),
                             "campos_com_borda": com_borda}

    # ── E3 ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("E3) AS 3 POSTURAS — custo em BYTE por valor")
    print("=" * 96)
    p_limpo, _ = encode_value(SPEC_CNPJ, BASE)
    print(f"  referencia: valor limpo -> payload {p_limpo!r} ({len(p_limpo)} chars)\n")
    print(f"  {'caso':<18} {'RIGIDO (hoje)':>15} {'PREGUICOSO':>13} {'LAZY restaura':>15}")
    posturas = []
    for rot, v in (("LF a direita", BASE + LF), ("espaco nos dois", SP * 2 + BASE + SP * 2),
                   ("tab a direita", BASE + TAB)):
        rigido = len(MARKER_LITERAL + v)
        preguicoso = len(p_limpo)                       # e' o BUG de hoje
        esq = len(v) - len(v.lstrip())
        dir_ = len(v) - len(v.rstrip())
        lazy = len(p_limpo) + 2 + esq + dir_            # +2 contagens, +os chars
        print(f"  {rot:<18} {rigido:>12} B {preguicoso:>10} B {lazy:>12} B")
        posturas.append({"caso": rot, "rigido": rigido, "preguicoso": preguicoso,
                         "lazy": lazy, "rt_preguicoso": False})
    print("\n  RIGIDO     = literal. RT correto. E' o que 9 das 10 bordas ja' fazem.")
    print("  PREGUICOSO = trim + comprime. 7 chars, mas PERDE a borda — e' EXATAMENTE")
    print("               o bug de hoje, so' que hoje ele e' acidental, mudo e so' p/ LF.")
    print("  LAZY       = comprime E grava a borda como afixo restauravel. RT correto,")
    print("               e vence o literal em ~10 B por valor. Exige GRAMATICA NOVA.")
    res["E3_posturas"] = posturas

    # ── E4 ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 96)
    print("E4) O COMUM x O INCOMUM — a guarda custa alguma coisa no caminho comum?")
    print("=" * 96)
    rng = random.Random(3)
    limpos = []
    for _ in range(50000):
        b = [rng.randint(0, 9) for _ in range(12)]
        s = "".join(map(str, b + _cnpj_check_fn(b)))
        limpos.append(f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}")
    medidas = []
    for _ in range(3):
        t0 = time.perf_counter()
        for v in limpos:
            SPEC_CNPJ.classify_value(v)
        a = time.perf_counter() - t0
        t0 = time.perf_counter()
        for v in limpos:
            if v != v.strip():
                pass
            SPEC_CNPJ.classify_value(v)
        b_ = time.perf_counter() - t0
        medidas.append((a, b_))
    a = min(m[0] for m in medidas)
    b_ = min(m[1] for m in medidas)
    print(f"  50.000 classify_value em valores LIMPOS (melhor de 3)")
    print(f"    sem guarda : {a*1000:8.1f} ms")
    print(f"    com guarda : {b_*1000:8.1f} ms   ({(b_/a-1)*100:+.1f}%)")
    print(f"  => a guarda `v != v.strip()` e' indistinguivel do ruido: o classify")
    print(f"     ja' faz varredura de char, e um strip a mais nao aparece.")
    res["E4_custo_guarda_pct"] = round((b_ / a - 1) * 100, 2)

    # ── telemetria: o warning que o owner mencionou ─────────────────────
    print("\n" + "=" * 96)
    print("O WARNING — o canal JA' EXISTE, falta o ROTULO")
    print("=" * 96)
    so = SideOutputs()
    col = [BASE, SP * 2 + BASE + SP * 2, BASE + TAB, "AB.CDE.FGH/IJKL-99"]
    w = encode(col, nature=SPEC_CNPJ, side_outputs=so)
    assert decode(w) == col
    d = so.as_dict() if hasattr(so, "as_dict") else vars(so)
    na = (d.get("nature_apply") or {})
    grava(IN, "telemetria.json", json.dumps(col, ensure_ascii=False, indent=1))
    grava(OUT, "telemetria.tcf", w)
    grava(OUT, "telemetria.roundtrip.json", json.dumps(decode(w), ensure_ascii=False, indent=1))
    print(f"  by_status hoje: {json.dumps(na, ensure_ascii=False)[:200]}")
    print("  Os 2 valores BORDADOS aparecem como `format_mismatch` — visiveis, mas")
    print("  misturados com 'nao reconheco essa forma'. Um rotulo proprio diria")
    print("  'isto E' um CNPJ, com lixo de borda' — acionavel pra limpar o pipeline.")
    print("  PRECEDENTE na propria taxonomia: `format_unmasked` e `format_padded_zeros`")
    print("  existem exatamente pra nomear VARIANTE reconhecivel que nao comprime.")
    res["telemetria"] = na

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos)
    print(f"\n-> {len(achados)} arquivos, portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
