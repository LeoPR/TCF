# TCF — Tabular Compact Format

## Visão geral

TCF é um formato textual para representar **dados tabulares** de
forma **compacta**, mantendo:

- **Output em texto** (sem binário) — inspeção visual e
  processamento por LLMs/pipelines line-oriented
- **Roundtrip lossless** — `decode(encode(values)) == values` sempre
- **Compressão estrutural** — explora padrões em colunas (afixos
  compartilhados, sub-padrões recorrentes)

Formato projetado para:
- Colunas de dados tabulares onde valores compartilham estrutura
  (URLs, emails, IDs, datas, paths, identificadores estruturados)
- Volumes médios (não substitui gzip pra logs massivos; substitui
  CSV/JSON quando legibilidade importa)

## Pipeline

```
Lista de strings (uma coluna)
       ↓
   OBAT (camada 1: tokenização)
       ↓ tokens raiz (TokLit, TokRefPref, TokRefSuf)
   HCC (camada 2: compactação composicional)
       ↓ texto TCF (operadores `~`/`,`, refs numéricos, escapes)
   Arquivo TCF (LF only, sem brackets)
```

Camadas detalhadas:
- [OBAT](OBAT.md) — Online Bidirectional Affix Tokenizer
- [HCC](HCC.md) — Hierarchical Compositional Coding

## API mínima

```python
from tcf import encode, decode

text = encode(["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"])
values = decode(text)
assert values == ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]
```

## Posicionamento na literatura de compressão

TCF se localiza no cruzamento de três famílias clássicas:

### 1. Compressão estrutural de string dictionaries

**Famíla**: front-coding e variantes (Witten et al., HTFC e RPDac de
Brisaboa et al. 2011, etc.)

**Comparação**:
- TCF, via OBAT, generaliza front-coding com **bidirecionalidade**
  (LCP + LCS), captura padrões "tipo email" onde sufixo
  (`@gmail.com`) é estável e prefixo varia.
- TCF, via HCC, adiciona **composições hierárquicas** — não há
  análogo direto em front-coding clássico.

### 2. Grammar-based compression

**Família**: Re-Pair (Larsson & Moffat 1999), Sequitur
(Nevill-Manning & Witten 1997).

**Comparação**:
- HCC é greedy iterative, espírito Re-Pair mas em tokens de OBAT
  (não bytes).
- HCC tem **operadores semânticos distintos** (`~` vs `,`) — não há
  análogo em Re-Pair (toda substituição cria regra).
- HCC é **offline** (analisa body completo) mas mais simples que
  Sequitur (que mantém invariantes online complexos).

### 3. Compactação para LLM consumption (acessório no v0.6)

**Família**: TabLLM (2023), TOON, JSON-tabular, formatos compactos
para LLMs lerem tabelas (Sui 2024 review).

**Comparação**:
- Phase 1 (ciclo v0.5) catalogou Q01-Q38 sobre LLM-readability do
  TCF antigo (columnar/RLE). Esse trabalho é **acessório** ao foco
  v0.6 (algoritmo de compressão).
- LLM-readability volta a ser relevante quando Phase 2 for revivida
  OU virar projeto a parte.

## Diferenciais agregados

| Característica | TCF | LZ77/gzip | Re-Pair | Front-coding |
|---|---|---|---|---|
| Output | textual | binário | binário | binário/textual |
| Inspecionável visualmente | sim | não | não | parcial |
| Online (streaming-friendly) | parcial | sim | não (offline) | sim |
| Bidirecional (prefixo + sufixo) | sim | n/a | n/a | só prefixo |
| Hierarquia de composições | sim | implícita | sim (grammar) | não |
| Auto-naming sem dict explícito | sim | n/a | não (precisa dict) | sim |
| Adequado a colunar | sim (desenhado pra) | genérico | genérico | sim |

## Quando usar TCF

**Bom uso**:
- Colunas de strings com padrões textuais (URLs, emails, IDs, datas,
  paths)
- Volume médio (centenas a milhares de linhas)
- Output em texto é requisito (inspeção, pipelines line-oriented,
  consumo por LLMs)

**Quando preferir alternativas**:
- **CSV/JSON** — formato muito simples, sem necessidade de
  compressão (mas TCF mantém legibilidade)
- **gzip/brotli/zstd** — datasets MUITO grandes, compressão crítica,
  binário OK
- **Re-Pair/Sequitur/HTFC** — dicionários gigantes, output binário OK,
  busca aleatória importante

## Estado v0.6

- **Implementação canônica**: `src/tcf/` (`from tcf import encode, decode`)
- **Escopo**: single-column. Multi-column / multi-dataset
  (encoder/organizador) é fase posterior.
- **Validação**: 9 datasets sintéticos (D1-D9) cobrindo cenários
  variados (emails simples/com apóstrofe, URLs com paths comuns,
  timestamps com ruído, padrões aninhados, caos misto, etc.).
- **Compressão medida**: D1-D9 total **1615 bytes em 2981 raw =
  54.2% ratio médio**. Varia 26% (D8 cabeça-cauda, padrão estável)
  a 72% (D4 caos-mix, alta variabilidade).
- **Roundtrip**: 9/9 OK em todos os datasets, validado byte-a-byte
  contra cadeia de checkpoints M9 → M10 → M11 → M12 → M13 → M14.

## Estado v0.5 (acessório)

Há código v0.5 em `old/tcf/` (formato columnar com RLE/dict/stats
para LLM benchmark). **Não é canônico no v0.6**. Mantido para
referência histórica e enquanto Phase 1 LLM findings (em
`docs/findings/`) tiverem relevância de pesquisa.

## Conexões

- [OBAT](OBAT.md) — camada 1 (tokenização)
- [HCC](HCC.md) — camada 2 (compactação composicional)
- `../../experiments/lab/dirty/notas/historia-dirty-lab.md` — narrativa
  M0-M14 do desenvolvimento
- `../../experiments/lab/dirty/notas/roadmap-hipoteses.md` — direções
  futuras (pre-tx delta, decomposição pós-detector, escala, etc.)
- `../../README.md` — visão de projeto
