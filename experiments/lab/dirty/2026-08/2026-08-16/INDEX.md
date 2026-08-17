# 2026-08-16 — índice do dia

> **Síntese acima deste índice**: [`../README.md`](../README.md) — o estado de cada TIPO
> (date, bool, int, float, hora, datetime, nativos) e de cada ROTA (single, multi, hier),
> os modos, o compartilhamento entre colunas, o header e o paralelismo.

Onde conferir cada coisa afirmada neste dia. **Todo lab roda com `python run.py`** e sai `0`
só se as suas próprias provas fecharem.

## Comece por aqui, se quiser conferir os welds

**[`2020-verificacao-dos-welds-C1-C2-C3/`](2026-08-16-2020-verificacao-dos-welds-C1-C2-C3/)**
— materializa o código **pré-weld direto do git** e roda o mesmo repro contra as duas versões,
em subprocesso. É a prova vermelho→verde dos três welds, sem depender da minha palavra.
Resultado: **3/3 confirmados**.

## Os labs do dia

| lab | pergunta | veredito |
|---|---|---|
| [`1330-polaridade-come-nome-de-coluna`](2026-08-16-1330-polaridade-come-nome-de-coluna/) | a polaridade come o fim do nome da coluna? | **sim** — 48/64 (.8M) e 38/64 (.8H), 0 warnings. **Consertado**: 0/64 e 0/64, wire byte-idêntico |
| [`1400-cadastro-popular-header-do-M`](2026-08-16-1400-cadastro-popular-header-do-M/) | como o header do `.8M` fica com specs variados? | 5 modos em 7 colunas; `:cpf` vence o FLOOR (−17,5%), `:dt` aplica e **perde** pro split |
| [`1450-ordem-de-colunas-no-M`](2026-08-16-1450-ordem-de-colunas-no-M/) | a ordem das colunas prende alguma coisa? | corpos byte-idênticos em qualquer permutação; variação total **3 B**. Achou o defeito do C2 |
| [`1530-piso-do-header-e-fronteira-paralela`](2026-08-16-1530-piso-do-header-e-fronteira-paralela/) | dá pra tirar mais explicitude do header? e o paralelismo? | header **já está no piso**; **6 invariantes** provam o decode paralelo (7 threads == serial) |
| [`1610-agrupar-tipos-comuns-no-M`](2026-08-16-1610-agrupar-tipos-comuns-no-M/) | agrupar tipos comuns compartilha o header? | rende **0,13%**; o que decide é o **tamanho do domínio** (k=2 → 0,5%; k=500 → 21,2%) |
| [`2020-verificacao-dos-welds-C1-C2-C3`](2026-08-16-2020-verificacao-dos-welds-C1-C2-C3/) | os três welds fazem o que eu disse? | **3/3 confirmados** contra o código real do git |
| [`2110-comportamento-normal-e-verificacao-logica`](2026-08-16-2110-comportamento-normal-e-verificacao-logica/) | o código normal resiste? e a lógica fecha? | 7 operações normais + determinismo (5 seeds → 1 hash) + **enumeração exaustiva** dos 3 espaços de decisão |
| [`2130-auditoria-do-M-no-corpus`](2026-08-16-2130-auditoria-do-M-no-corpus/) | o  está OK em dado REAL? | **23 tabelas / 186 colunas, 0 falhas**. Invariantes 23/23, guards 0 disparos, os 4 candidatos com domínio real. **CORRIGE** minha extrapolação: o  VENCE por 5,1% no corpus, e o teto da união é **2,3%**, não 27% |

## As notas do dia

| nota | o que é |
|---|---|
| [`1510-estagios-e-soldas-do-M`](../../notas/2026-08/2026-08-16-1510-estagios-e-soldas-do-M.md) | o `.8M` em estágios (encode E1–E5, decode D0–D6) e as 4 soldas nomeadas |
| [`1545-o-que-falta-pro-M`](../../notas/2026-08/2026-08-16-1545-o-que-falta-pro-M.md) | o inventário em 4 grupos, e o gargalo (`T-META-NAO-DECLARA-MODO`) |
| [`1630-revisao-strata-L0`](../../notas/2026-08/2026-08-16-1630-revisao-strata-L0.md) | a revisão de aderência ao núcleo L0, matriz dos 10 princípios |

## Os welds no `src/tcf` (Grupo C fechado)

| commit | ticket | arquivos |
|---|---|---|
| `0dec1a06` | `T-META-COLISAO-NOME-POSICIONAL` | `multi/core.py`, `view.py` |
| `ec08634c` | `T-NATURE-IGNORADA-CALADA` §1 e §2 | `encoder.py` |
| `2464f561` | `T-POLARIDADE-COME-NOME` | `decoder.py` |

Pinos na suíte: `TestMetaColisaoNomePosicional`, `TestNatureIgnoradaCalada`,
`TestPolaridadeComeNome` — todos em `tests/test_f0_boundary_fixes.py`.
Suíte do dia: **1260 → 1285 passed**.

## O que este índice existe para corrigir

O owner não achou os labs e concluiu, corretamente, que sem evidência conferível é o mesmo
que não ter feito. Os labs existiam, mas a evidência estava espalhada e **três furos eram
reais**: `1450` e `1530` gravavam `.tcf` sem roundtrip, e os welds C2/C3 não tinham lab
próprio — a prova vermelho→verde deles era transiente. Os três foram fechados, e este índice
existe para que a próxima conferência comece por um lugar só.
