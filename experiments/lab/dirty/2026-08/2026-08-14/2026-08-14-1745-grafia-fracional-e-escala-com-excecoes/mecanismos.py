# -*- coding: utf-8 -*-
"""Os quatro mecanismos, NAIVE e por estagios visiveis (A-identify / B-normalize / C-verify).

Engenhoca de dirty lab: hardcoded, sintaxe ilustrativa, para JOGAR FORA. O que sobrevive
daqui e' a IDEIA, nunca o codigo.

## A fronteira que organiza tudo

| mecanismo | contrato | o que muda | gate |
|---|---|---|---|
| M1 grafia fracional | **exato** | so' a GRAFIA (`0.333333333333` -> `1/3~12`) | nenhum — e' lossless |
| M2 escala pura | **exato** | so' a GRAFIA (`0.25` -> `25`, k=2) | nenhum — e' o de hoje |
| M3 escala com excecoes | **exato** | so' a GRAFIA, com patching por-valor | nenhum — e' lossless |
| M4 round soma-preservada | **exato-no-agregado** | o VALOR | **GATEADO** (Pacote 10, v2.0) |

M1-M3 sao lossless: passam pelo RT estrito (tipo + valor + sinal do zero). M4 muda o dado —
aqui e' SO' MEDICAO, nunca proposta de weld. A decisao de escopo do owner (2026-06-15)
mantem o formato lossless-puro.

## Por que "verify" e' um estagio, e nao um detalhe

M1 e M3 sao seguros por CONSTRUCAO porque re-emitem e comparam a grafia antes de aceitar.
Um valor que nao reproduz byte-a-byte e' RECUSADO — a auto-protecao e' o mecanismo, nao um
teste sobre ele. Medido na sonda: `2.718281828`, `0.30000000000000004` e `12.3456789` sao
recusados sozinhos.
"""
from __future__ import annotations

import math
from decimal import Decimal as _D
from fractions import Fraction

# ── contabilidade honesta ─────────────────────────────────────────────────────
# `encode([str, ...])` emite header `#TCF.8`; um spec sobre float emitiria
# `#TCF.8n :xx` (a tag `n` + o id). A diferenca e' exatamente `n :xx` = 5 B.
# Marcadores sao abstratos e congelados por economia — o caractere e' so' a saida.
CUSTO_SPEC_ID = 5           # `n :xx`
LIMITE_DENOM = 10_000       # teto do denominador procurado
MIN_CASAS_FRAC = 6          # abaixo disso a decimal ja' e' curta; nao ha' o que ganhar
KMAX = 12                   # teto do expoente da escala


def _e_finito_decimal(v) -> bool:
    """Serve para transformacao de grafia? Exclui as bordas do fechamento do float."""
    if v is None or not isinstance(v, float):
        return False
    if math.isnan(v) or math.isinf(v):
        return False                      # fora do JSON (RFC 8259)
    s = repr(v)
    if "e" in s or "E" in s:
        return False                      # cientifica: a grafia nao tem "casas"
    if v == 0.0 and math.copysign(1.0, v) < 0:
        return False                      # -0.0: `==` nao distingue; nao arriscar
    return "." in s


def _casas(v) -> int:
    return len(repr(v).split(".")[1])


# ── M1 — GRAFIA FRACIONAL (lossless) ──────────────────────────────────────────
def m1_fracao(v):
    """`0.333333333333` -> `1/3~12`. Devolve (grafia, diario) ou (None, diario)."""
    d = {"estagio_A_identify": None, "estagio_B_normalize": None, "estagio_C_verify": None}
    if not _e_finito_decimal(v):
        d["estagio_A_identify"] = "recusa: nao e' decimal finito (nulo/NaN/Inf/cientifica/-0.0)"
        return None, d
    casas = _casas(v)
    if casas < MIN_CASAS_FRAC:
        d["estagio_A_identify"] = f"recusa: {casas} casas < {MIN_CASAS_FRAC} (decimal ja' curta)"
        return None, d
    d["estagio_A_identify"] = f"candidato: {casas} casas"

    fr = Fraction(v).limit_denominator(LIMITE_DENOM)
    if fr.numerator == 0 or fr.denominator == 1:
        d["estagio_B_normalize"] = f"recusa: fracao degenerada ({fr})"
        return None, d
    d["estagio_B_normalize"] = f"achou {fr.numerator}/{fr.denominator}"

    volta = round(fr.numerator / fr.denominator, casas)
    if repr(volta) != repr(v):
        d["estagio_C_verify"] = f"RECUSA: re-emite {volta!r} != {v!r}"
        return None, d
    d["estagio_C_verify"] = "re-emite identico"
    g = f"{fr.numerator}/{fr.denominator}~{casas}"
    if len(g) >= len(repr(v)):
        d["estagio_C_verify"] += f"; mas nao encurta ({len(g)} >= {len(repr(v))})"
        return None, d
    return g, d


def m1_de_volta(g: str) -> float:
    """O decodificador de M1. `1/3~12` -> 0.333333333333"""
    frac, _, casas = g.partition("~")
    p, _, q = frac.partition("/")
    return round(int(p) / int(q), int(casas))


def m1_coluna(vals):
    """Aplica M1 valor a valor. Devolve (corpo, diario_por_valor, n_convertidos)."""
    corpo, diarios, n = [], [], 0
    for v in vals:
        g, d = (None, {"estagio_A_identify": "slot nulo"}) if v is None else m1_fracao(v)
        if g is None:
            corpo.append(repr(v) if v is not None else None)
        else:
            corpo.append(g)
            n += 1
        diarios.append(d)
    return corpo, diarios, n


def m1_reverso(corpo, originais):
    """Reconstroi a coluna a partir do corpo de M1, preservando o TIPO da origem."""
    fora = []
    for c, orig in zip(corpo, originais):
        if c is None:
            fora.append(None)
        elif "~" in c and "/" in c:
            fora.append(m1_de_volta(c))
        else:
            fora.append(type(orig)(c) if not isinstance(orig, str) else c)
    return fora


# ── M2 — ESCALA PURA (lossless, tudo-ou-nada; e' o candidato de hoje) ─────────
#
# DEFEITO ACHADO POR ESTE LAB (1a rodada): a versao ingenua testava a escala com
# tolerancia (`abs(esc - round(esc)) < 1e-9`). Com isso `0.30000000000000004` "fecha" em
# k=1 e volta `0.3` — um LOSSLESS QUE PERDE, calado. O epsilon e' o bug.
#
# A correcao e' a MESMA disciplina do M1: **verificar por re-emissao**. So' aceita a escala
# se o inteiro volta ao mesmo float E a' mesma grafia. `Decimal(repr(v))` da' a grafia
# decimal exata; a multiplicacao binaria nunca entra na decisao.
def escala_exata(v, k):
    """O inteiro escalado, se a escala for exata e verificada. Senao None."""
    if not _e_finito_decimal(v):
        return None
    d = _D(repr(v)).scaleb(k)
    if d != d.to_integral_value():
        return None
    n = int(d)
    if abs(n) >= 2 ** 53:                 # fora do inteiro exato do IEEE-754
        return None
    volta = float(_D(n).scaleb(-k))
    if volta != v or repr(volta) != repr(v):
        return None                       # nao re-emite identico -> RECUSA
    return n


def _so_float(vals) -> bool:
    """A escala exige coluna de float PURO.

    PECULIARIDADE #1 do float (fechamento 2026-08-14): a tag `n` e' a UNIAO `int|float`, e o
    tipo concreto vem da GRAFIA. Escalar apaga essa distincao — um `1` escalado em k=12 vira
    `1000000000000`, e na volta `/10^12` da' `1.0` (float), nao `1` (int). Pior: se o int for
    tratado como EXCECAO, a grafia literal dele (`1`) fica identica a' de um valor escalado, e
    o decoder nao consegue distinguir. Este lab quebrou o RT das duas maneiras antes da regra.
    """
    return all(isinstance(v, float) for v in vals if v is not None)


def m2_escala_pura(vals, kmax=KMAX):
    """menor k que serve a TODOS. Devolve (k, corpo) ou (None, None)."""
    uteis = [v for v in vals if v is not None]
    if not uteis or not _so_float(vals) or not all(_e_finito_decimal(v) for v in uteis):
        return None, None
    for k in range(kmax + 1):
        escalados = [None if v is None else escala_exata(v, k) for v in vals]
        if all(e is not None for e, v in zip(escalados, vals) if v is not None):
            return k, [None if e is None else str(e) for e in escalados]
    return None, None


# ── M3 — ESCALA COM EXCECOES (lossless; a ideia do ALP/SIGMOD-2024) ───────────
#
# O ponto do ALP: decimal-como-inteiro nao e' tudo-ou-nada. Escala o vetor com o k que
# serve a MAIORIA e guarda os poucos que nao fecham em grafia plena (patching).
#
# GUARDA DA MAIORIA (achada na 2a rodada deste lab): sem ela, `k=0` vence em `wine.alcohol`
# marcando 1716 de 2000 valores como "excecao". Mas em k=0 **nao ha' escala nenhuma** — o
# mecanismo estaria so' relabelando a coluna, e quem decide os bytes ali e' o bN de dominio
# (`#TCF.8B77d0`, 111 distintos), nao a escala. Um mecanismo que "ganha" por nao fazer o que
# promete esta' medindo outra coisa. Regra: excecoes tem de ser MINORIA.
#
# A excecao NAO precisa de lista de posicoes — **desde que a coluna seja float puro**: o
# `repr` de um float SEMPRE traz `.` ou `e`, e um valor escalado e' sempre inteiro puro
# (`-?\d+`). O decoder distingue pela GRAFIA, como faz com o slot nulo. Numa coluna da
# tag-UNIAO (com int junto) a regra COLIDE — ver `_so_float`, e o RT quebrado que motivou.
def m3_escala_com_excecoes(vals, kmax=KMAX):
    """Devolve os (k, corpo, posicoes_excecao) viaveis, ou None."""
    uteis = [v for v in vals if v is not None]
    if not uteis or not _so_float(vals):
        return None
    saida = []
    for k in range(kmax + 1):
        escalados = [None if v is None else escala_exata(v, k) for v in vals]
        exc = [i for i, (e, v) in enumerate(zip(escalados, vals))
               if v is not None and e is None]
        if len(exc) * 2 >= len(uteis):
            continue                       # GUARDA DA MAIORIA — ver nota abaixo
        corpo = [None if v is None else
                 (repr(v) if e is None else str(e))
                 for e, v in zip(escalados, vals)]
        saida.append((k, corpo, exc))
    return saida or None


def m3_reverso(corpo, k, originais=None):
    """Reconstroi: inteiro puro -> /10^k (por Decimal, exato); resto -> literal.

    Nao consulta os originais — e' o que um decoder de verdade teria.
    """
    fora = []
    for c in corpo:
        if c is None:
            fora.append(None)
        elif c.lstrip("-").isdigit():
            fora.append(float(_D(int(c)).scaleb(-k)))
        else:
            fora.append(float(c))
    return fora


# ── M3b — ESCALA COM EXCECOES, USANDO O MARCADOR QUE O NUCLEO JA' TEM ────────
#
# ACHADO DO LEVANTAMENTO: eu inventei o "distingue pela grafia" sem precisar. O core ja'
# tem excecao por-valor welded — `MARKER_LITERAL = '_'` (`templated_checked.py:38`), usado
# identico pelas 4 natures, e desambiguado por EXCLUSAO DE ALFABETO (o `_` sai do BASE94 e
# os payloads sao digit-only), nao por escape. E `int_pad.py:73-74` (`length_wrong`) e'
# literalmente o caso ALP: o valor que nao cabe na largura da coluna vira literal SOZINHO,
# sem alargar nem recusar a coluna.
#
# Custo: +1 B por excecao. Ganho: resolve a colisao que derrubou o M3 na tag-UNIAO — com o
# `_`, um int pode ir literal sem se confundir com um escalado, e o tipo volta pela grafia.
MARCADOR_LITERAL = "_"          # o mesmo do core (`tcf.natures.MARKER_LITERAL`)


def m3b_com_marcador(vals, kmax=KMAX):
    """Escala + excecao marcada com `_`. Aceita coluna de tipo MISTO."""
    uteis = [v for v in vals if v is not None]
    if not uteis:
        return None
    saida = []
    for k in range(kmax + 1):
        escalados = [None if v is None else
                     (escala_exata(v, k) if isinstance(v, float) else None)
                     for v in vals]
        exc = [i for i, (e, v) in enumerate(zip(escalados, vals))
               if v is not None and e is None]
        if len(exc) * 2 >= len(uteis):
            continue                       # GUARDA DA MAIORIA (mesma do M3)
        corpo = [None if v is None else
                 (MARCADOR_LITERAL + repr(v) if e is None else str(e))
                 for e, v in zip(escalados, vals)]
        saida.append((k, corpo, exc))
    return saida or None


def m3b_reverso(corpo, k):
    """`_x` -> literal (tipo pela grafia, como a tag-UNIAO `n` faz); resto -> /10^k."""
    fora = []
    for c in corpo:
        if c is None:
            fora.append(None)
        elif c.startswith(MARCADOR_LITERAL):
            lit = c[1:]
            fora.append(int(lit) if lit.lstrip("-").isdigit() else float(lit))
        else:
            fora.append(float(_D(int(c)).scaleb(-k)))
    return fora


# ── M4 — ROUND COM SOMA PRESERVADA (LOSS — GATEADO, so' medicao) ─────────────
#
# Metodo do maior resto (Hamilton / greatest-mantissa), o canonico do "controlled
# rounding" da estatistica oficial. Ja' validado no PoC de 2026-06-14; aqui so' se mede
# o efeito sobre a GRAFIA em casos particulares, para comparar com M1-M3 no mesmo eixo.
#
# NADA disto e' proposta de weld: o formato e' lossless-puro por decisao do owner
# (2026-06-15) e qualquer perda exige gate real-world N>=5 + decisao explicita.
def m4_round_soma_preservada(vals, casas):
    """Arredonda para `casas` preservando a SOMA exata. Devolve (ingenuo, maior_resto)."""
    uteis = [(i, v) for i, v in enumerate(vals) if v is not None]
    if not uteis:
        return None, None
    esc = 10 ** casas
    ingenuo = [None] * len(vals)
    for i, v in uteis:
        ingenuo[i] = round(round(v * esc) / esc, casas)

    alvo = round(sum(v for _, v in uteis) * esc)      # a soma exata, na escala
    pisos = [(i, math.floor(v * esc), v * esc - math.floor(v * esc)) for i, v in uteis]
    falta = alvo - sum(p for _, p, _ in pisos)
    ordem = sorted(pisos, key=lambda t: (-t[2], t[0]))  # maiores restos primeiro
    incr = {i for i, _, _ in ordem[:max(0, falta)]}
    maior_resto = [None] * len(vals)
    for i, piso, _ in pisos:
        maior_resto[i] = round((piso + (1 if i in incr else 0)) / esc, casas)
    return ingenuo, maior_resto
