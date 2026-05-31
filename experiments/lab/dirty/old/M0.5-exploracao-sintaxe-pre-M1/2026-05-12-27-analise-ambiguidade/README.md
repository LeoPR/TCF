# 27 — analisador puro de ambiguidade (Etapa 1 do flow semântico)

## Princípio / motivação

Pulei a abordagem "implementar mais sintaxes". Em vez disso,
construo um **analisador** que classifica cada char de cada
literal em 3 categorias, **sem emitir TCF**.

A ideia é mapear o espaço de decisões antes de inventar
mecanismos. Este é o **passo 1** do flow semântico proposto:

```
1. Analisar       ← este experimento
2. Sumida         ← próximo (Etapa 2)
3. Órfã           ← Etapa 3
4. Agrupamento    ← Etapa 4
5. Integração     ← Etapa 5
```

## Raiz dos tokens

Tudo neste exp parte de **`online.py` do exp 16** — copiado
intocado. Os fragmentos literais analisados são exatamente o
que o algoritmo emite. Toda a investigação de sintaxe
(exps 21-26) usa essa mesma raiz. **Não estamos mexendo no
algoritmo — só na representação.**

## Definição das categorias

Sintaxe-base de análise: **v3** (a mais minimalista, sem aspas,
sem escape).

| Cat | Significado | Exemplos |
|---|---|---|
| **A** | char livre — nunca é marcador em v3 | letras, `.`, `@`, `'`, `"`, `+`, `-`, ` ` |
| **B** | char é marcador em alguma posição, mas no contexto não aciona o parser | `,` cercado de não-dígitos, `^` fora do início, `\|` fora de RLE, `[`/`]` no meio |
| **C** | char aciona o parser → precisa marcação | dígitos (refs), `*` (separador) |

## Resultado em `emails-quote-id` (12 strings)

### Visão geral

| Categoria | Total | % |
|---|---:|---:|
| A (livre) | 58 | **80.6%** |
| B (contexto resolve) | 0 | 0% |
| C (conflito real) | 14 | 19.4% |

**80% dos chars em literais não precisam de marcador algum.** Os
20% restantes são todos dígitos.

### Distribuição de C por fragmento

| K = chars C | Fragmentos |
|---:|---:|
| 0 (raw) | 11 |
| 1 | 2 |
| 2 | 3 |
| 3 | 2 |

11 dos 18 fragmentos são emitidos sem qualquer marcação. Os 7
restantes precisam tratar 1-3 dígitos cada.

### Custo de marcação — empate teórico, custo de separador refina

| Estratégia | Bytes extras |
|---|---:|
| Escape (`\X` por char C) | +14 |
| Aspas (`'X'` por fragmento) | +14 (7 × 2) |
| **Mista ótima** (escape K=1, aspas K≥2) | +12 (teórico) |

Em emails-quote-id o cálculo direto dá **empate** entre escape e
aspas. A "mista ótima" pareceria vencer por 2, mas em prática
empata também (devido ao custo de separador `*` entre literais —
confirmado no exp 26).

### Chars C distintos no dataset

```
'0': 2 ocorrências   '4': 2 ocorrências
'1': 3 ocorrências   '5': 1 ocorrência
'2': 3 ocorrências   '6': 1 ocorrência
'3': 2 ocorrências
```

Todos dígitos. Nenhum `*`, `,`, `^`, `|`, `[`, `]` em literais.
**Categoria B está vazia neste dataset.**

## Insights para próximas etapas

### 1. Categoria B é vazia em emails-quote-id

Isso significa que o flow semântico de "char é marcador mas
contexto resolve" não tem onde brilhar aqui. Só há A (sem
marcador) e C (precisa marcador).

**Para a Etapa 4 (agrupamento)** ter algo a explorar, o dataset
precisa de chars B reais — datasets com `,`, `^`, `|`, etc. no
literal.

### 2. Sumida (Etapa 2) tem terreno aqui

Os dígitos em literais formam sequências que **podem não
corresponder a idx existentes**:

- char `0` no literal: idx 0 nunca existe (idx começa em 1) →
  **sumida sempre possível para `0` isolado**
- dígito `5` no literal (eid=12): idx 5 existe (em emails-quote-id
  vai até idx 30+), confl ito real
- sequência `256` no literal: idx 256 não existe nesse dataset
  (max ~30) → **sumida possível para `256` como bloco**
- sequência `103` no literal: idx 103 não existe → **sumida
  possível**

**Estimativa**: dos 14 chars C, talvez 5-10 podem ser sumidos
via parser stateful. Próximo exp (Etapa 2) vai medir.

### 3. Aspas vs escape — empate confirmado

A análise teórica confirma o achado empírico do exp 24/26:
escape e aspas têm custo equivalente em datasets dominados por
dígitos. A escolha vira **questão de simplicidade**, não de
bytes.

### 4. Distribuição K mostra que o algoritmo fatora bem

K=0 em 11/18 fragmentos significa que **a maior parte dos
literais não tem ambiguidade**. O algoritmo do online.py
concentra ambiguidade em poucos fragmentos (os IDs).

## Limitações desta análise

- **Classificação por char isolado** — não considera ainda
  contexto de vizinhança (próximo passo: refinar B com base em
  vizinhos diretos)
- **Não considera estado de idx** — refinamento para "sumida"
  fica na Etapa 2
- **Só 1 dataset** — categoria B vazia aqui, mas pode aparecer
  em datasets com `,` ou outros chars

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-27-analise-ambiguidade
python analise.py
```

Imprime relatório char por char + sumário + estimativas de custo.

## Próximo passo natural — Etapa 2 (sumida)

Implementar parser stateful que reconhece dígitos no literal
**quando idx não existe**. Esperado: economizar 5-10 bytes em
emails-quote-id sem mudar o encoder além de **omitir o marcador**
nesses casos.

Dataset alvo: emails-quote-id mesmo (já temos os números).

Estrutura proposta:
- Encoder: para cada fragmento, verificar se cada char/sequência
  pode ser sumida (idx correspondente não existe)
- Decoder: stateful, mantém dict de idx existentes; quando vê
  dígitos, tenta como ref, se idx não existe trata como literal
