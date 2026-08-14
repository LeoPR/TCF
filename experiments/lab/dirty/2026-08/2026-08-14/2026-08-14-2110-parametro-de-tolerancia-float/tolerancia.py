# -*- coding: utf-8 -*-
r"""O PARÂMETRO de tolerância para float — protótipo.

Engenhoca de dirty lab: para JOGAR FORA. Sobrevive a IDEIA, não o código.
**Nada aqui toca `src/tcf`.** É pré-transformação externa, na forma que o `nature=` já usa.

## De onde vem

`docs/workbench/_archive/tickets/frozen/H-smart-rounding.md` (2026-04-10, status OPEN,
**as 4 tarefas desmarcadas**) desenhou isto e nunca implementou:

    config = EncodeConfig(max_error_pct=0.001, aggregate_columns=["total"])

e listou 4 alternativas, a 3ª marcada como *"precisão derivada de tolerância (inovação)"*.
Este protótipo implementa a 3ª — e as outras como casos particulares.

## O que mudou desde aquele desenho

O ticket tinha **um eixo** (`max_error_pct`) e presumia que erro é um número. A medição de
hoje mostrou que **a mesma perda significa coisas diferentes por operação** — 66,67% por valor
vira 0,00029% na soma e 825,9% numa diferença. Então o parâmetro tem **4 eixos + 1
qualificador**, derivados por redução mútua contra 5 áreas normativas:

| eixo | promete | compõe sob |
|---|---|---|
| `quantum` | `x̂` é múltiplo exato de `q` | — (é grade, não bound) |
| `abs` | `\|x̂−x\| ≤ ε` | **soma** |
| `rel` | `\|x̂−x\|/\|x\| ≤ ε` | **produto** |
| `agg` | `Σ x̂ = Σ x` exata no eixo declarado | — (é restrição de conjunto) |
| `mode` | direção do desempate — decide o **viés** | — |

## As duas regras que o protótipo obedece

1. **DERIVAR, depois VERIFICAR.** A fórmula propõe a precisão; a medição decide se aceita.
   Fórmula que não é verificada é a mesma classe de erro do epsilon na escala (lab 1745).
2. **FALHAR ALTO.** Se a tolerância pedida não pode ser cumprida, recusa — nunca entrega um
   dado que viola o contrato que ele mesmo declara.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

MODOS = ("half-even", "half-up", "down", "stochastic")
AGREGADOS = ("soma", None)


@dataclass(frozen=True)
class Tolerancia:
    """O parâmetro complementar. Todos os eixos são opcionais e COMPÕEM (AND)."""

    quantum: float | None = None      # grade: x̂ ∈ {k·q}
    abs: float | None = None          # |x̂−x| ≤ abs
    rel: float | None = None          # |x̂−x|/|x| ≤ rel
    agg: str | None = None            # "soma" -> Σ x̂ = Σ x exata
    mode: str = "half-even"           # desempate; decide o VIÉS
    casas_max: int = 12               # teto de busca

    def __post_init__(self):
        if self.mode not in MODOS:
            raise ValueError(f"mode deve ser um de {MODOS}; got {self.mode!r}")
        if self.agg not in AGREGADOS:
            raise ValueError(f"agg deve ser um de {AGREGADOS}; got {self.agg!r}")
        for nome in ("quantum", "abs", "rel"):
            v = getattr(self, nome)
            if v is not None and (not isinstance(v, (int, float)) or v <= 0):
                raise ValueError(f"{nome} deve ser > 0; got {v!r}")
        if not any((self.quantum, self.abs, self.rel, self.agg)):
            raise ValueError("Tolerancia vazia: declare ao menos um eixo "
                             "(quantum/abs/rel/agg) — senão use encode() sem tolerância")


# ── ESTÁGIO A — DERIVAR a precisão a partir do que foi prometido ─────────────
def passo_de_erro(modo: str) -> float:
    """Quantos passos de `10^-d` o modo pode errar.

    **ACHADO DESTE LAB (1ª rodada)**: eu tratava `mode` só como VIÉS — foi o que a literatura
    destacou (a distinção do HMRC). Mas ele também muda a MAGNITUDE do erro, e portanto a
    fórmula da derivação:

    - `half-*` e `stochastic` erram até **meio** passo (o desempate cai para o lado mais perto);
    - `down` (truncar) erra até **um passo inteiro** — nunca sobe.

    Com a fórmula de meio passo, `mode="down"` prometia 1% e entregava ~1,01% em
    `wine.density`. **A verificação pegou e recusou** — que é o desenho funcionando. Aqui a
    derivação passa a ser correta desde o início, e a verificação continua sendo o juiz.
    """
    return 1.0 if modo == "down" else 0.5


def deriva_casas(vals, tol: Tolerancia) -> tuple[int | None, dict]:
    """A precisão MÍNIMA que satisfaz todos os eixos. `None` = impossível.

    Arredondar a `d` casas erra no máximo `p·10^-d`, com `p = passo_de_erro(mode)`. Então:
      - `abs=ε`  ->  p·10^-d <= ε        ->  d >= -log10(ε/p)
      - `rel=ε`  ->  p·10^-d <= ε·|v|    ->  d >= -log10(ε·|v|/p), pior no MENOR |v|
      - `quantum=q` -> d = casas de q (só potências de 10 viram casas decimais)

    O `rel` é o eixo perigoso: ele é amarrado pelo menor valor não-nulo da coluna, então UM
    centavo perdido na cauda inferior obriga a coluna inteira a mais precisão.
    """
    diario = {}
    uteis = [abs(v) for v in vals if v is not None and v != 0]
    exigidas = []
    p = passo_de_erro(tol.mode)
    diario["passo_de_erro_do_modo"] = {"mode": tol.mode, "passos": p,
                                       "nota": "`down` erra 1 passo inteiro; os demais, meio"}

    if tol.abs is not None:
        d = math.ceil(-math.log10(tol.abs / p))
        exigidas.append(d)
        diario["abs"] = {"pedido": tol.abs, "casas_exigidas": d}

    if tol.rel is not None:
        if not uteis:
            diario["rel"] = {"pedido": tol.rel, "casas_exigidas": 0,
                             "nota": "coluna sem valor não-nulo"}
        else:
            menor = min(uteis)
            d = math.ceil(-math.log10(tol.rel * menor / p))
            exigidas.append(d)
            diario["rel"] = {"pedido": tol.rel, "menor_valor_nao_nulo": menor,
                             "casas_exigidas": d,
                             "nota": "amarrado pelo MENOR valor — a cauda inferior manda"}

    if tol.quantum is not None:
        lg = -math.log10(tol.quantum)
        if abs(lg - round(lg)) > 1e-9:
            diario["quantum"] = {"pedido": tol.quantum,
                                 "recusa": "grade não-decimal (não é potência de 10); "
                                           "este protótipo só faz grade decimal"}
            return None, diario
        d = int(round(lg))
        exigidas.append(d)
        diario["quantum"] = {"pedido": tol.quantum, "casas_exigidas": d,
                            "nota": "grade é mais forte que bound: o valor tem de ser "
                                    "EXPRESSÁVEL nela, não apenas perto"}

    if not exigidas:                       # só `agg` — não restringe a precisão
        casas = max((_casas(v) for v in vals if v is not None), default=0)
        diario["derivado"] = {"casas": casas, "nota": "só `agg` pedido: mantém a precisão "
                                                      "da origem e só realoca o resíduo"}
        return casas, diario

    d = max(exigidas)
    if d > tol.casas_max:
        diario["derivado"] = {"recusa": f"exige {d} casas, acima do teto {tol.casas_max}"}
        return None, diario
    d = max(d, 0)
    diario["derivado"] = {"casas": d, "eixo_dominante": max(diario, key=lambda k: (
        diario[k].get("casas_exigidas", -1) if isinstance(diario[k], dict) else -1))}
    return d, diario


def _casas(v) -> int:
    s = repr(float(v))
    return len(s.split(".")[1]) if "." in s and "e" not in s else 0


# ── ESTÁGIO B — APLICAR ──────────────────────────────────────────────────────
def _round_modo(v, d, modo):
    esc = 10 ** d
    x = v * esc
    if modo == "half-even":
        r = round(x)                       # o round() do Python JÁ é half-even
    elif modo == "half-up":
        r = math.floor(x + 0.5)
    elif modo == "down":
        r = math.floor(x)
    else:                                  # stochastic: determinístico p/ ser reprodutível
        frac = x - math.floor(x)
        r = math.floor(x) + (1 if frac > 0.5 else 0)
    return r / esc


def _maior_resto(vals, d):
    """Hamilton: preserva a SOMA exata na escala de `d`. Erra até 1 passo por linha."""
    esc = 10 ** d
    idx = [i for i, v in enumerate(vals) if v is not None]
    pisos = {i: math.floor(vals[i] * esc) for i in idx}
    falta = round(sum(vals[i] for i in idx) * esc) - sum(pisos.values())
    ordem = sorted(idx, key=lambda i: -(vals[i] * esc - pisos[i]))
    incr = set(ordem[:max(0, falta)])
    fora = list(vals)
    for i in idx:
        fora[i] = round((pisos[i] + (1 if i in incr else 0)) / esc, d)
    return fora


def aplica(vals, tol: Tolerancia):
    """Devolve `(ajustados, laudo)`. `ajustados=None` se a tolerância for impossível.

    O laudo é o produto principal: ele mede o erro por TODAS as lentes, não só a prometida —
    porque o achado desta sessão é que a mesma perda significa coisas diferentes.
    """
    casas, diario = deriva_casas(vals, tol)
    laudo = {"tolerancia": {"quantum": tol.quantum, "abs": tol.abs, "rel": tol.rel,
                            "agg": tol.agg, "mode": tol.mode},
             "estagio_A_derivar": diario}
    if casas is None:
        laudo["veredito"] = "RECUSA — tolerância não realizável"
        return None, laudo

    if tol.agg == "soma":
        aj = _maior_resto(vals, casas)
        laudo["estagio_B_aplicar"] = {"casas": casas, "metodo": "maior-resto (Hamilton)",
                                      "nota": "o `mode` não se aplica: a alocação decide o "
                                              "desempate, não a direção de arredondamento"}
    else:
        aj = [None if v is None else _round_modo(v, casas, tol.mode) for v in vals]
        laudo["estagio_B_aplicar"] = {"casas": casas, "metodo": f"round {tol.mode}"}

    laudo["estagio_C_verificar"] = verifica(vals, aj, tol, casas)
    laudo["veredito"] = ("CUMPRE" if laudo["estagio_C_verificar"]["cumpre_tudo"]
                         else "RECUSA — a derivação prometeu e a medição desmentiu")
    return (aj if laudo["estagio_C_verificar"]["cumpre_tudo"] else None), laudo


# ── ESTÁGIO C — VERIFICAR (a fórmula propõe; a medição decide) ───────────────
def verifica(orig, aj, tol: Tolerancia, casas: int) -> dict:
    par = [(a, b) for a, b in zip(orig, aj) if a is not None]
    if not par:
        return {"cumpre_tudo": True, "nota": "coluna vazia"}
    erros_abs = [abs(b - a) for a, b in par]
    erros_rel = [abs(b - a) / abs(a) for a, b in par if a != 0]
    soma_o, soma_a = sum(a for a, _ in par), sum(b for _, b in par)
    esc = 10 ** casas

    v = {"casas_aplicadas": casas,
         "erro_abs_max": max(erros_abs),
         "erro_rel_max": max(erros_rel) if erros_rel else 0.0,
         "erro_soma_rel": abs(soma_a - soma_o) / abs(soma_o) if soma_o else 0.0,
         "soma_exata_na_escala": round(soma_a * esc) == round(soma_o * esc),
         "viés_medio_por_valor": sum(b - a for a, b in par) / len(par)}

    checks = {}
    if tol.abs is not None:
        checks["abs"] = v["erro_abs_max"] <= tol.abs * (1 + 1e-12)
    if tol.rel is not None:
        checks["rel"] = v["erro_rel_max"] <= tol.rel * (1 + 1e-12)
    if tol.quantum is not None:
        q = tol.quantum
        checks["quantum"] = all(abs(b / q - round(b / q)) < 1e-9 for _, b in par)
    if tol.agg == "soma":
        checks["agg"] = v["soma_exata_na_escala"]
    v["checks"] = checks
    v["cumpre_tudo"] = all(checks.values())
    return v
