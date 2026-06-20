# Família RLE no TCF — estudo consolidado (intra-valor + stream) [estudo]

**Data**: 2026-06-19 · estudo (consolida medições já feitas + perguntas abertas; **não decide nada**).
Origem: owner pediu pra "voltar com as ideias de RLE intra-valor e o RLE-STREAM pra estudar".
**Entrar por aqui** quando o assunto for "comprimir repetição". Tudo cross-linkado (diretiva
[[feedback-sempre-cross-reference]]).

## 1. Escopo

Três mecanismos no TCF "comprimem repetição", mas em **dimensões diferentes** e se **confundem**.
Este doc separa os três, mostra onde **competem**, e lista o que já foi **medido** e o que é
**pergunta aberta** — pra decidir a ordem de ataque sem retrabalho.

As duas ideias que o owner quer estudar:
- **(B) V2-RLE-STREAM** — RLE no stream de índices do V2-B. **Já caracterizado** (2026-06-19).
- **(C) RLE intra-valor** (H-INTRA / O-FMT-17) — repetição DENTRO de um valor. **Adiado**, ainda não medido.

E o terceiro, que já existe e **compete** com (B):
- **(A) RLE de linha** — `*N|` / seq-RLE `*N+delta|`. **Welded** no `src/tcf`.

## 2. A família em 3 níveis

| # | mecanismo | dimensão (o que repete) | status | onde vive / doc |
|---|---|---|---|---|
| **A** | RLE de linha `*N|` + seq-RLE `*N+delta|` (e `^N` = valor inteiro repetido) | **interlinha**: linha/valor inteiro adjacente | **WELDED** (dispositivo) | `src/tcf` (OBAT `core/online.py` + HCC `composicional/`); [ADR-0016](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md), [HCC](../../../../docs/algorithms/HCC.md), [OBAT](../../../../docs/algorithms/OBAT.md) |
| **B** | V2-RLE-STREAM — RLE no stream de índices do V2-B (`@dict`) | **intra-stream**: índice inteiro adjacente | **caracterizado** → CLOSED-geral / nicho aberto (probatório) | lab [result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md); registry [Pacote 11-bis](roadmap-hipoteses.md); depende de [ADR-0025 V2-B](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md) |
| **C** | RLE intra-valor (H-INTRA-01/02/03 / O-FMT-17) | **intra-valor**: substring dentro de uma célula | **ADIADO** (aberta, alvo 0.8) | registry [Pacote 11](roadmap-hipoteses.md#pacote-11); [O-FMT-17](futuras-otimizacoes-formato.md) |

## 3. Fatos medidos — V2-RLE-STREAM (B), uso geral

> **Para a intuição visual** (se os dados fossem assim → o que B tentava → por que não deu), ver o
> [exemplo trabalhado no lab](../2026-06-19-v2rle-stream-caracterizacao/result.md#exemplo-visual--o-que-a-hipótese-queria-resolver-e-por-que-não-deu).

Fonte: [lab result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md) (7 datasets reais, o teste
mede — não copiar números soltos). Resumo:
- **+1,19% weighted**, **0/7 datasets ≥15%** (melhor caso real: adult 7,34%). Upper bound `sort_by`
  ~13% (relationship).
- **−1,39% sob brotli** (agregado): a economia textual **some e inverte** — o brotli já captura os
  runs; os marcadores RLE viram overhead.
- → **CLOSED-INSUFFICIENT-GAIN** pro uso geral (tabelas largas / com compressor a jusante).

## 4. Fatos medidos — V2-RLE-STREAM (B), nicho "texto curto / formulário"

Fonte: [result_forms.txt](../2026-06-19-v2rle-stream-caracterizacao/result_forms.txt) (coluna isolada =
payload narrow). Em **ordem natural**, payload dominado por uma coluna low-card de texto:
- situacao (K=5, **skewed**) **+54,9%**; workclass (K=9) **+21,6%**; mesorregiao +5,5%; marital +5,3%;
  education (uniforme) +1,4%. **Todos morrem sob brotli** (−2,7% a −11,0%).
- **Nicho real**: payload minúsculo + low-card texto curto + **skewed** + ordem natural + **textual-puro**
  (sem compressor a jusante). 2 reais ≥15% *nesse nicho*. Alinha com a diretriz "transmissão minúscula".

## 5. Achado-chave — o overlap A↔B (por que B é quase um resíduo de A)

No lab, os casos **clusterizados / `sort_by`** **FLIPARAM a coluna pro modo `tcf`**: o `*N|` (A)
captura os runs longos e **vence o fallback** `min(tcf, raw, @dict, %split)` → o dict (e portanto o
stream) **nem é escolhido**. Consequência:
- **A e B competem pelo mesmo fenômeno** (repetição adjacente de valor inteiro). A já ganha onde os
  runs são **longos**.
- **B só tem espaço no regime de runs CURTOS** (ordem natural) **+ coluna skewed** — onde o dict vence
  o fallback e deixa o stream cru. Aí B captura algo que A não pega (porque A perdeu o fallback).
- Por isso B, na prática, é um **resíduo** de A: vale só na faixa estreita (curto+skewed+textual-puro).

## 6. Overlap B↔C (intra-valor) e a regra de layout

C (intra-valor) é **ortogonal em dimensão** (dentro do valor, não entre linhas/índices), mas
tematicamente "ataca repetição". O fio que liga os três:

> **A repetição capturada depende do LAYOUT**: runs longos → **A** (`*N|`); runs curtos+skewed →
> **B** (dict-stream); substring dentro do valor → **C** (intra-valor).

[H-INTRA-03](roadmap-hipoteses.md#pacote-11) já exige medir o **INCREMENTO** de C sobre
nature + split + dedup `^N` (anti-incidente 2026-05-21). O lab de B reforça: **B e C podem se
subsumir** — convém **caracterizar C antes de reabrir B** (evita retrabalho).

## 7. Custo de weld (comum a B e C)

Qualquer um dos dois, se avançar, é **format change** (grupo `#TCF.8`, ciclo 0.8 por
[ADR-0024](../../../../docs/adr/0024-pre-1.0-versioning-git-as-compat.md)) + **GATE real-world**
obrigatório + **re-pin** de baselines + complexidade permanente no decoder/lazy. Anti-incidente
2026-05-21 aplicável: ganho em sintético / coluna isolada **não generaliza** pra tabela/real-world.

## 8. Perguntas abertas (pro owner estudar)

1. O nicho **"transmissão minúscula textual-pura"** (low-card skewed, ordem natural, sem compressor a
   jusante) é prioritário o bastante pra justificar `#TCF.8` por B? (situacao +55% é real, mas estreito.)
2. **Caracterizar C (intra-valor) primeiro?** O overlap sugere que C pode subsumir B (ou vice-versa).
3. Ambos **morrem sob brotli** — o caso de uso textual-puro-sem-compressor existe de fato no roadmap,
   ou o alvo real é sempre TCF+compressor (onde A já basta)?
4. Se algum avançar: qual **engine** (OBAT vs HCC) e como medir o **INCREMENTO net** sobre A + nature +
   split + dedup `^N`?

## 9. Referências

- Lab B: [result.md](../2026-06-19-v2rle-stream-caracterizacao/result.md) +
  [result_forms.txt](../2026-06-19-v2rle-stream-caracterizacao/result_forms.txt) +
  scripts `analyze.py` / `analyze_forms.py`.
- Registry: [roadmap-hipoteses.md](roadmap-hipoteses.md) — Pacote 11-bis (B = H-V2RLE-01/02),
  [Pacote 11](roadmap-hipoteses.md#pacote-11) (C = H-INTRA-01/02/03).
- Formato futuro: [futuras-otimizacoes-formato.md](futuras-otimizacoes-formato.md) (O-FMT-17).
- ADRs: [0016 seq-RLE](../../../../docs/adr/0016-hcc-multi-delta-seq-rle.md) (A),
  [0025 V2-B](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md) (base de B),
  [0026 split](../../../../docs/adr/0026-structural-split-weld.md) (vizinho).
- Specs: [HCC](../../../../docs/algorithms/HCC.md), [OBAT](../../../../docs/algorithms/OBAT.md),
  [TCF-format](../../../../docs/algorithms/TCF-format.md). Tier: [ROADMAP](../../../../ROADMAP.md).
