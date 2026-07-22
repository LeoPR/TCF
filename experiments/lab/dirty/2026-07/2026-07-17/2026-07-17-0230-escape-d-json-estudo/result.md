# Resultado — escape D_json (3 lacunas fechadas)

**[probatório]** Ver [README.md](README.md) (mecanismo + veredito), `outputs/00-estudo.txt`
(pré-weld) e `outputs/00-resultado.txt` (wire real pós-weld). 9 `.tcf` inspecionáveis, roundtrip
byte-idêntico ao canônico (assert).

## Confirmado

1. **As 3 lacunas de dataset de D_json fecharam** com UM mecanismo: chave vazia (`\z`), LF em
   valor (`\n`), LF em nome (`\n`). O critério `J-RT-TX ⟹ T-RT` deixou de ter exceções de
   dataset — resta só o eixo raiz (P4b).
2. **O L1 ficou INTOCADO** — a premissa "toca o L1" era falsa; o `.8H` escapa na própria camada.
   Gate flat byte-canônico: 31 passed, zero re-pin.
3. **Injetivo**: exaustivo (85 strings, 0 colisões) + 20k fuzz + composição com P1/P2/P3a/P3b/P4a.
4. **Sentinela de corrupção preservado**: o parse checa o TOKEN CRU; `\z` é inemitível por dado.
5. **Erro tipado**: chave não-str era `TypeError` cru → agora `HierarchicalError` que ensina
   (E1 parcial, mesmo ato).

## O que este lab NÃO fecha

Raiz generalizada (P4b). Fora de D_json (NaN/Inf/tuple/chave-não-str/surrogate) — por decisão,
não por lacuna. A leniência `\X`→`X` do L1 é pré-existente e fora deste escopo (registrada em
T-FMT-META-STRICT, junto do KeyError cru).

`confianca: Alta` (injetividade exaustiva + fuzz + auditoria adversarial + gates verdes).
Sintético declarado.
