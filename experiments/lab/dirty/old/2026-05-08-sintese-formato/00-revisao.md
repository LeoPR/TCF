# Revisão completa — o que sobreviveu, o que cai

Tabela de auditoria de tudo que foi testado nas mesas anteriores, marcando
cada variante como **mantida**, **dominada** (substituível por outra melhor
em qualquer cenário) ou **ortogonal** (cobre algo que outras não cobrem).

---

## Estratégias de codificação testadas

| ID | Nome | Status | Quem domina |
|---|---|---|---|
| C1 | Row-major literal (CSV) | dominada | C2 (col literal) |
| C2 | Column-major literal | dominada | regra unificada (= C2 quando degenera) |
| C3 | Col + RLE local (sem sort) | dominada | regra unificada |
| C4 | Sort por nome + RLE | dominada | regra unificada com mesmo sort |
| C5 | Sort por produto + RLE | dominada | regra unificada com mesmo sort |
| C6 | Group por produto + RLE | dominada | regra unificada (group = sort estável) |
| C7 | Sort por valor + RLE | dominada | regra unificada com mesmo sort |
| C8 | Dict explícito por coluna | **estritamente dominada** | C11 (dict implícito, sem bloco header) |
| C9 | Sort + RLE + dict explícito | **estritamente dominada** | regra unificada (sem bloco dict) |
| C10 | Dict implícito sempre marcado (`:`) | dominada | C11 (auto-discrimina por coluna) |
| C11 | Dict implícito com auto-discriminação | dominada | regra unificada (per-line vs per-column) |
| C11-híbrido | Per-coluna escolhe RLE/dict/literal | dominada | regra unificada (per-line é ≥ per-column) |
| C12 | Dict com prognóstico de count + reciclagem | **ortogonal** | aplicável a streaming (C12 ≥ C11 quando há reciclagem) |
| **Regra unificada** | RLE+dict por linha, auto-discrim | **mantida** | — |

### Síntese

- **9 variantes (C1-C7, C10, C11) são dominadas pela regra unificada.**
  Não há cenário onde elas vençam a unificada. São casos particulares dela.
- **C8 e C9 são estritamente dominadas**: o dict explícito em bloco custa
  bytes que a forma implícita evita.
- **C11-híbrido é dominado**: a escolha per-coluna é um caso particular da
  escolha per-linha; a unificada captura ganhos extras quando uma coluna
  mistura modos.
- **C12 é ortogonal**: ataca um problema diferente (streaming + cardinalidade
  alta com reciclagem), não comprime mais em batch puro. Manter como
  extensão opt-in para casos de stream.

---

## Estratégias de ordem (sort) testadas

| Sort | Status | Por quê |
|---|---|---|
| Sem sort | dominado | qualquer sort com chave correlacionada melhora |
| Sort solo (1 chave) | parcialmente dominado | multi-sort 2-3 chaves vence sempre |
| Sort 2 chaves | dominado por 3 chaves | gain marginal positivo |
| Sort 3 chaves | dominado por sort completo (em alguns casos) | depende do dataset |
| Sort 4+ chaves | retorno marginal ≈ 0 | só ajuda se há linhas duplicadas exatas |
| Sort com chave não-correlacionada | placebo | confirmado: zero ganho |

### Conclusão sobre sort

Sort não é dominado: é uma **dimensão ortogonal** ao encoding. Manter como
parâmetro do formato com 0 a N chaves.

**Heurística estável:** primeira chave de sort = aquela com maior produto
de (cardinalidade alta) × (correlação com outras colunas). Heurística
vence escolha aleatória em todos os datasets testados.

---

## Notações de cabeçalho testadas

| Notação | Status | Razão |
|---|---|---|
| A. Verbose (1 linha por col) | dominada | B é mais curta com mesma clareza |
| **B. Lista compacta** (`# enc: D, R, L, R`) | **mantida** | melhor relação clareza/tamanho |
| C. String contínua (`# enc: DRLR`) | dominada | ilegível com >5 colunas |
| D. Bitmask 3-bit (`# enc: 010, 001`) | dominada | redundante para humanos; reservado bits sub-utilizados |
| E. Run-length vírgula (`# enc: D,, R`) | mantida (extensão de B) | útil para >10 colunas com repetição |
| F. Hex packed | rejeitada | ilegível, anti-objetivo do TCF |

### Conclusão sobre header

Manter **B** (com **E** como extensão opcional para colunas-repetição).
Header é **opcional** — decoder consegue inferir tudo da estrutura na
maioria dos casos.

Com a regra unificada, o header passa a declarar bem menos:
- Não precisa declarar modo (literal/RLE/dict) — emerge da regra
- Pode declarar **discriminador por coluna** (bare vs marcado) — opcional,
  decoder também detecta sozinho
- Pode declarar **ordem do sort** — útil para o cliente saber se precisa
  re-sortar para sua query
- Pode declarar **flags de extensão** (δ, P, L') — opt-in por coluna

---

## O que sobra

### Núcleo (sempre presente)
- **Regra unificada**: RLE+dict por linha, com auto-discriminação
- **Layout column-major**: cada coluna em bloco separado, marcado por
  `nome:\n`

### Parâmetros (opcionais, default = sem)
- **Sort**: 0 a N chaves; se ausente, dados ficam na ordem original
- **Discriminador por coluna**: auto se ausente, declarado se presente

### Extensões ortogonais (opt-in, opcionais)
- **δ (delta)**: para colunas com sequência aritmética
- **P (prefix elision)**: para colunas com prefixo comum
- **L' (line-RLE)**: para datasets com linhas duplicadas inteiras
- **C12 (count + reciclagem)**: para streaming de longa duração

### Header (opcional, default = ausente)
- Notação B/E para declarar discriminador, sort e extensões quando o
  decoder precisa ser simples ou quando há ambiguidade

---

## O que pode ser descartado

Para fins de **especificação do formato TCF v0.5**, podem sair:
- L0/L1/L2/L3 como modos discretos
- Bloco `# dict <col>: ...` (dict implícito é sempre ≤)
- Notações C, D, F do header
- Diferenciação C1/C2/C3/.../C12 — todas são casos particulares da regra
  unificada

Para **fins de pesquisa/ablação**, manter as variantes como flags forçados
(`force=literal`, `force=rle-only`, `force=dict-only`) **só durante
experimentos**. Em produção, sempre rodar a regra unificada.
