# Historia do dirty lab — TCF v0.6

**Data desta sintese**: 2026-05-17

> **Reorganizacao 2026-05-16**: pastas M0-M14 referenciadas neste
> arquivo foram movidas pra `experiments/lab/dirty/old/`. Paths
> historicos no texto podem nao incluir o prefixo `old/`; arquivos
> moram fisicamente em `dirty/old/<path>`.


**Ciclo**: dirty v0.6 (reset 2026-05-10)
**Narrativa escrita ate'**: M9 (2026-05-17) — M10-M14 welded mas nao narrados aqui; ver ADR-0008/0010/0011 + checkpoints/ para o rastro completo.

> Esta nota e' a **narrativa canonica** do que foi construido no
> dirty lab. Para detalhes tecnicos, ver READMEs dos macros e
> `conclusoes_*.md` proprios. Para hipoteses futuras, ver
> [`roadmap-hipoteses.md`](roadmap-hipoteses.md).

---

## Contexto

**TCF (Textual Compact Format)** e' um **algoritmo de compressao
de strings** com sintaxe composicional para producao textual.

> Nota historica: o nome TCF originalmente significava "Textual
> Columnar Format" no ciclo v0.5 (foco em LLMs lerem tabelas).
> No ciclo v0.6 (dirty lab atual), o foco eh o **algoritmo de
> compressao** (TCF-CORE / alg16 + Compactacao composicional). O
> uso por LLMs e' aplicacao **acessoria** — Phase 1 catalogou
> resultados; Phase 2 vira depois do algoritmo estabilizar.

O DIRTY LAB e' o espaco onde algoritmos e sintaxes sao iterados
sem compromisso com estabilidade — apenas validacao de
comportamento. Cada macro (M0..M9) explora uma faceta do design.
Esta historia consolida o que cada um estabeleceu.

### Componentes (atual)

- **OBAT** (Online Bidirectional Affix Tokenizer) — codnome `alg16`:
  camada 1 (tokenizacao). Tokeniza strings via LCP + LCS contra
  anteriores. Ver `docs/algorithms/OBAT.md`.
- **HCC** (Hierarchical Compositional Coding) — codnome `M8.A`:
  camada 2 (compactacao). Detector unificado + emit composicional
  (`~` cria ref, `,` concat efemero). Ver `docs/algorithms/HCC.md`.
- **TCF** (Tabular Compact Format): formato final (texto, sem
  brackets, LF only). Ver `docs/algorithms/TCF-format.md`.
- **LLM benchmark** (acessorio): Phase 1 fechado; pode virar
  projeto a parte.
- **Schema / Shaper** (ferramentas): uteis para criar datasets
  experimentais; podem virar projetos a parte.

---

## Linha do tempo

### M0 — Algoritmo raiz (OBAT — codnome `alg16`)

**16 experimentos preliminares**. Estabelece o algoritmo
`online.py` (exp 16): tokenizacao incremental via LCP/LCS de
strings unicas.

Saida do algoritmo: lista de tokens por string:
- `TokLit(text)`: literal puro
- `TokRefPref(string_id, length)`: prefixo de string ja' vista
- `TokRefSuf(string_id, length)`: sufixo

**Nome oficial (decidido 2026-05-17)**: **OBAT** — Online Bidirectional
Affix Tokenizer. Codnome de origem: `alg16`. Permanece intocado.
Localizacao canonica:
`experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`.

Ver `docs/algorithms/OBAT.md` para documentacao tecnica (estrutura,
sub-linguagem matematica, diferencial vs literatura).

### M0.5 — Vocabulario pre-M1

12 experimentos de variantes de sintaxe. Estabelece interface
`Syntax` (encode + decode) e vocabulario de tokens da saida
textual (chars `*`, `,`, `\`, `~`, etc.).

### M1 — Marcacao de ambiguidade local

6 micros (A, A', B, C, D, E) + F2. Investiga como serializar
refs+lits sem ambiguidade no texto resultante.

**Canonico**: **M1.E** (range + escape escopo). Outras micros
dominadas por bytes ou nicho.

Sintaxe M1.E:
- Refs como `a..b` (range) ou `a,b,c` (lista) — refs separadas por `,`.
- Lits com escape escopo: `\X` para chars reservados (`*`, `\`, digits).
- Separator `*` entre lit-lit ou lit-ref boundary.

### M2 — Redundancia entre linhas (preambulo)

**M2.A**: alias de tupla via preambulo `$N=tupla` no topo do body.

Posteriormente em M6: vista como **regressao** (preambulo paga
custo desnecessario). M2.A inline economiza 2+len(N) bytes/alias.
M2.A original mantido em disco mas demovido.

### M3 — Encadeamento de declaracoes

M3.A, M3.B: agrupar nos inteiros compartilhados entre eids.
**Dominado por M1.E** estruturalmente. Net 0. Mantido em disco como
referencia.

### M4 — Desfragmentacao da arvore → embriao do HCC

3 micros:
- **M4.A** instrumentacao (mede oportunidades teoricas)
- **M4.C1** batch greedy runs inteiras
- **M4.C1'** batch greedy subsequencias

Origem do conceito de **aliases compactos** via marker pair `~tupla~`
para definir + `&N` para reusar. M4.C1' captura subsequencias
contiguas (K>=2) que aparecem >= 2 vezes.

**Resultado historico**: M4.C1' = 636 bytes D1-D4 (-5.9% vs M1.E 676).

Esta etapa, originalmente chamada "desfragmentacao da arvore" e
depois "Compactacao composicional", recebeu nome oficial em
2026-05-17: **HCC** (Hierarchical Compositional Coding). Codnome
M4.C1' → M8.A → **HCC**. Ver
[`naming-compactacao-composicional.md`](naming-compactacao-composicional.md)
e `docs/algorithms/HCC.md`.

### M5 — Pilha M2.A + M4.C1'

Teste de ortogonalidade. Concluiu (incorretamente em primeira
analise) que M4.C1' subsume M2.A.

**Em M6 revisado**: M2.A com preambulo era regressao. M2.A inline
ainda perde por len(N) byte/alias mas e' mais proxima.

### M6 — Sintaxe composicional

Insight do user: markers entre refs sao **OPERADORES**:
- `,` entre refs: concat efemero (sem criar ref)
- `~` entre refs: concat + cria novo ref auto-nomeado (pairwise)
- Range `a..b` e' caso particular de composicao por sequencia
- Reuso: bare ref id (sem prefixo `&`)

**M6.C** = 619 bytes D1-D4 (-8.4% vs M1.E). Captura a hierarquia
natural do TCF-CORE.

### M7 — Refactor + nova estrutura debug

Reorganizacao do codigo em 3 fases limpas:
1. **Tokenize**: alg16 tokens → pieces (lit + refs com prov atom IDs)
2. **Detect**: greedy iterativo, modifica pieces in place
3. **Emit**: single pass, atribui IDs decoder-style interleaved

**M7.A == M6.C** em bytes (619). Codigo mais legivel.

Novo layout debug:
- `resultados/tokens/<dataset>.txt` (alg16 raw compartilhado)
- `<micro>/output|decoded|debug|detector_trace|redes/`

### M8 — Detector unificado + convencao output

Insight do user: alias_markers e refs atomicos vivem no MESMO
ESPACO. `'refs'` pieces contem refs mixtos (positivos = atom prov,
negativos = virtual alias).

Detector itera uniformemente. Captura pairs (atom, alias),
(alias, alias), etc.

**Restricao refinada via body-order check**: virtual em pos > 0
OK se a alias correspondente tem standalone occurrence em body
order ANTES do sub's first match. Garante pairwise correctness em
inline expansion.

**Convencao output adopted**:
- Sem brackets `[`/`]` (scaffolding desnecessario)
- LF only (`\n`); evitar CRLF do Windows

**M8.A** = **574 bytes D1-D4** (-15.1% vs M1.E baseline 676 com
brackets). Core canonico do protótipo.

### M9 — Stress adversarial

5 datasets novos (D5-D9) testam limites:
- D5 padroes multiplos coexistentes
- D6 poucos padroes em ruido (timestamps unicos)
- D7 aninhamento (sub-padrao em multiplas positions)
- D8 cabeca-cauda (prefix/suffix estaveis)
- D9 frequencia alta (R=20 wrapper com middle variavel)

RT 9/9 OK. Total **1615 bytes em 2973 raw = 54.3% ratio medio**.

**Limites identificados**:
- D6 timestamps: precisa **pre-tx delta**.
- D9 wrapper: precisa **primitivo de slot variavel** (`7{}5`).
- D4 caos: teto inerente quando variabilidade alta.

---

## Conceitos canonicos (nomes oficiais 2026-05-17)

### OBAT — Online Bidirectional Affix Tokenizer

Codnome: `alg16`. Camada 1 do TCF (tokenizacao). Online, processa
strings em ordem, matching bidirecional (LCP + LCS). Tokens raiz:
TokLit / TokRefPref / TokRefSuf. **Intocado desde M0 (exp 16).**

Documentacao: `docs/algorithms/OBAT.md`.

### HCC — Hierarchical Compositional Coding

Codnome: `M8.A`. Camada 2 do TCF (compactacao composicional). Recebe
tokens raiz de OBAT e produz body textual com:
- atoms ref's positivos (M1.E style)
- composicoes via `~` (cria refs auto-nomeados)
- range `a..b` (composicao por sequencia)
- reuso via bare ref id

Implementacao canonica em `src/tcf/composicional/syntax.py` (welded
de M8.A, byte-identico em logica). Documentacao:
`docs/algorithms/HCC.md`.

### TCF — Tabular Compact Format

Formato final. Texto, sem brackets, LF only. Pipeline:
`values → OBAT → HCC → TCF text`. Documentacao:
`docs/algorithms/TCF-format.md`.

### Convencao output (M8+)

- Sem brackets `[`/`]`
- LF only (`\n`)
- Decoder mantem skip de brackets pra back-compat

Ver [`convencao-output-tcf.md`](convencao-output-tcf.md).

---

## Estado canonico (apos M9)

| Componente | Nome oficial | Codnome | Localizacao welded |
|---|---|---|---|
| Tokenizador | **OBAT** | `alg16` | `src/tcf/core/online.py` (origem: M0) |
| Sintaxe ambiguidade local | M1.E (interna ao HCC) | M1.E | embutido em HCC |
| Compactacao composicional | **HCC** | `M8.A` | `src/tcf/composicional/syntax.py` (origem: M8.A) |
| Formato | **TCF** | (projeto) | `src/tcf/` (API: encode/decode) |
| Convencao output | sem brackets + LF | — | `notas/convencao-output-tcf.md` |
| Stress validation | D1-D9 | — | `datasets/synthetic/` (oficializado em M10) |

## Compressao medida (atual)

D1-D4 (canonicos pequenos): **574 bytes / 660 raw (clean) = 87% ratio** (= 13% reducao).

D1-D9 (com adversariais): **1615 / 2973 = 54.3% ratio medio** (varia
26% [D8 melhor] a 72% [D4 caos]).

## Roadmap

Ver [`roadmap-hipoteses.md`](roadmap-hipoteses.md) para hipoteses
futuras (pre-tx delta, decomposicao pos-detector, etc.).

## Notas transversais (vivas)

- [convencao-output-tcf.md](convencao-output-tcf.md)
- [vetores-de-comparacao-alem-de-bytes.md](vetores-de-comparacao-alem-de-bytes.md)
- [marcadores-multiplo-proposito.md](marcadores-multiplo-proposito.md)
- [comparacao-modular-camadas.md](comparacao-modular-camadas.md)
- [quebra-de-linha-como-marcador.md](quebra-de-linha-como-marcador.md)

## Macros (referencias)

| ID | Data | Estado | Resultado |
|---|---|---|---|
| M0 | 2026-05-11 | foi | alg16 cristalizado |
| M0.5 | 2026-05-11 | foi | vocabulario Syntax |
| M1 | 2026-05-12 | foi | M1.E base canonica |
| M2 | 2026-05-13 | foi | M2.A demovido em M5/M6 |
| M3 | 2026-05-13 | foi | dominado |
| M4 | 2026-05-13 | foi | M4.C1' base composicional |
| M5 | 2026-05-14 | foi | conclusao revisada em M6 |
| M6 | 2026-05-14 | foi | composicional natural |
| M7 | 2026-05-15 | foi | refactor + debug layout |
| M8 | 2026-05-16 | foi | **detector unificado canonico** |
| M9 | 2026-05-17 | foi | stress 9 datasets |
