# Checkpoint 2026-07-15 — P1 weldado; PW3 real-world revelou crash do L1 (a diagnosticar)

**[pausa explícita — retomar em ~8h, de dia]** Owner precisou desligar. O diagnóstico do crash é
LENTO (encode de 200k), tem que rodar quando houver tempo de dia.

## Onde paramos (estado exato)

- **P1 (chave opcional / ragged) WELDADO** no core — commit `bcb6405`, **NÃO PUSHADO** (segurando
  o push até fechar o diagnóstico abaixo; owner autorizou push, mas a corrida revelou um crash).
  - Gramática `nome?:msize` (máscara 3-estados `.`/`-`/`0`-reservado), corpo denso. ADITIVO:
    uniforme fica byte-idêntico. ADR-0033 §Update P1.
  - Endureceu junto (auditoria adversarial `wf_e548aeaa-055`): tipo estrutural misto / null /
    array-de-objetos-vazios / size-None-no-meio / size<0 / máscara inválida / raiz-não-lista =
    **fail-loud tipado** (fecha corrupções silenciosas PRÉ-EXISTENTES do weld).
  - Gate: **suíte 684 passed, 2 skipped**; pins flat byte-canônicos verdes; 9 probes red→green.

## O CRASH aberto (PW3 real-world) — NÃO é do P1

Probe `probe_realworld.py` (receita-cnpj matriz→filiais, `nome_fantasia` omitido quando null =
ragged real) crashou no **DECODE do L1** (compressor de coluna, ABAIXO do P1):
```
src/tcf/composicional/syntax.py:734
    refs.extend(range(int(a), int(b) + 1))   ValueError: int('') — B vazio no range 'A..B' do seq-RLE
```

**Já provado (isolate.py/pinpoint.py)**:
- Ambos P1(ragged) E não-P1(coerido) crasham **idêntico** → **NÃO é bug do P1**.
- Colunas isoladas pelo L1 fazem RT: cnpj ordenado (200k) ✅ · raiz-prefixo8 (51536) ✅ ·
  fantasia não-null (104148) ✅.
- Suíte + fuzz seedado passam. **P1 está correto.**
- **ABERTO**: qual coluna EM CONTEXTO (mf/uf/sit/est.count — não testadas isoladas) OU se é
  interação/exaustão no rebuild (regressão que EU introduzi nas validações do decode?).

## PRÓXIMO PASSO (rodar de dia — 1º da retomada)

1. `python experiments/lab/dirty/2026-07-15-0125-p1-presenca-ragged-estudo/diagnostico_l1_seqrle_crash.py`
   — bisseca até o menor prefixo que crasha + decodifica coluna-a-coluna → nomeia a culpada.
2. **Se COLUNA** (bug L1 seq-RLE pré-existente, R0-class): abrir `tickets/BUG-SEQRLE-RANGE-EMPTY-B`
   com o repro mínimo; fix separado no core (aprovação + gate byte-canônico); ajustar PW3 pra não
   disparar (ordem/colunas); **então PUSH do P1**.
3. **Se FRAMING/exaustão** (regressão do PW1 no decode_hierarchical): consertar ANTES do push.
4. Depois: **re-listar o mapa de paridade JSON** (T-CODE-TCF8H-JSON-PARITY) pra planejar cada tipo
   negligenciado — owner quer **null primeiro** ("me parece fácil de resolver"; `0` já reservado na
   máscara P1) → depois P2 tipos, P4 rep-level. Objetivo: compatibilidade SEM quebra.

## Ritual de reentrada

STATUS → este checkpoint → `tickets/T-CODE-TCF8H-JSON-PARITY.md` (P1 ✅, próximos) +
`T-CODE-TCF8H-WELD.md` → diário `2026-07-15.md`. Repros/isolação: scratchpad da sessão foi
temporário; o essencial está em `diagnostico_l1_seqrle_crash.py` (durável) + este checkpoint.
