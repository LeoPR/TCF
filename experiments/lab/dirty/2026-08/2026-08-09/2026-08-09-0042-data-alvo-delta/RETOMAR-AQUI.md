# RETOMAR AQUI — estado em 2026-08-09 02:25

Sessão interrompida a pedido do owner (desligar a máquina). **Nada pendente na árvore:
tudo commitado, `src/tcf` intocado.**

## Onde paramos

O `~` foi **decidido** pelo owner como sintaxe do seq-RLE periódico (reversível antes do
1.0). O [ADR-0040](../../../../../docs/adr/0040-seq-rle-periodico.md) está **proposto** e o
código do weld está pronto pra revisão em [`weld_proposto.py`](weld_proposto.py).

**O weld NÃO foi feito** — falta o "pode soldar" explícito do owner.

## O que já está provado (não precisa refazer)

| | |
|---|---|
| suíte inteira com a camada LIGADA | **1199 passed** |
| D1-D9 · real-world | **1545** · **89430** — byte-idênticos |
| ganho | úteis 1590→40 B · n=6000→41 (O(1)) · ids não-data 1959→32 |
| colocação (teto de memória) | dentro do `expand_seq_marker`: 0,0000 s vs 2,473 s |
| custo de CPU | v1 O(n²) 13,8 s → **v4 +35%** ([`detector_v4.py`](detector_v4.py)) |

## 2ª CAÇADA — concluída (2026-08-09)

Rodou contra a **v5**: 5 lentes, 10 achados brutos, **3 confirmados / 2 refutados**, e
**44 hipóteses que NÃO quebraram**. Os 2 defeitos distintos foram introduzidos pelos
próprios consertos anteriores, e estão fechados na v6 (`detector_v5.py`):

| # | defeito | fechado |
|---|---|---|
| 6 | o guard de canonicidade virou amplificador (48,8 KB → **126,87 s**; 22 B → 85 MB) | 3,75 ms · 0 MB |
| 7 | `_drena` sem piso ressuscitava marcador recusado; polaridade cobrava (corpo −9 B, wire +19 B) | 0 regressões em 1202 casos |

`v5_verificacao.py` = **10/10**. Suíte **1199 passed** com a camada ligada. Gates intactos.
Ticket novo registrado: `T-FLOOR-POS-POLARIDADE` (vale pro core de hoje, não só pro periódico).

## O que ficou PENDENTE (histórico da 1ª caçada — tudo fechado)

**A caçada adversarial foi interrompida.** 3 das 5 lentes terminaram; a fase de
verificação (refutação independente) **não rodou**. Os 12 achados brutos estão salvos em
[`outputs/cacada-achados-brutos.json`](outputs/cacada-achados-brutos.json) com repro de
cada um.

> **Nada disso está verificado.** A régua deste projeto: a auditoria do `nB` produziu 9
> "confirmados" que eram 6 distintos e **zero** alcançáveis via `encode→decode`. Tratar
> como pista, não como fato.

Os 12 colapsam em **5 distintos**:

| # | achado | escala | situação |
|---|---|---|---|
| 1 | `max_length` não cobre o marcador novo (bomba de descompressão) | E3 | **já resolvido** — é a decisão de colocação do ADR-0040 |
| 2 | detector `O(n²)` no dado que o mecanismo não deve tocar | E3 | **já resolvido** — v4 |
| 3 | FLOOR inverte o desempate (`min()` pega o CRU; o core prefere o COMPACTADO) — **807 B mudando** em coluna sem periodicidade | E4 | corrigido em `detector_v3/v4` e no `weld_proposto.py` (ordem `min(hoje, body_text, cand)`); **`design_probe.py` ainda tem a ordem antiga** |
| 4 | `_seq_info` nunca populado → `seq_rle_runs` zera **mesmo em wire byte-idêntico** ao de hoje | E3 | **PENDENTE** — é regressão de telemetria, pior do que o `weld_proposto.py §notas` registrava. Telemetria é requisito do owner |
| 5 | pad com sufixo morto: grafias diferentes decodificam pro mesmo dado | E4 | **PENDENTE, novo** — canonicidade do marcador |

## Próximos passos, em ordem

1. **Verificar adversarialmente os 5** (a fase que não rodou) — em especial #4 e #5, que
   são os únicos que não são achados meus reciclados.
2. Levar #4 e #5 pro ADR-0040 (§consequências / §guardas) se sobreviverem.
3. **Pedir o "pode soldar"** ao owner. Com o OK: transcrever `weld_proposto.py` para
   `src/tcf/composicional/hcc_seqrle.py`, com os testes já definidos (8 controles +
   adversariais de grafia + bomba de memória + os dois gates).
4. Depois: lab clean em massa da família data (molde EXP-016).

## Decisões do owner registradas nesta sessão

- Sintaxe `~` fica; se colidir, troca antes do 1.0.
- **Marcadores são abstratos por dentro; o caractere é só a saída** — poderiam ser
  contextuais e móveis, mas congelar em conhecidos é mais barato. Memorizado em
  `project_marcadores_abstratos_congelados`.
