# META-NAMING — Naming oficial v0.6

**Status**: CLOSED (2026-05-17)
**Criado**: 2026-05-17
**Fechado**: 2026-05-17 (mesmo dia)
**Escopo**: fixar nomenclatura oficial do projeto e dos componentes
canonicos (alg16, M8.A). Pre-requisito para reorganizacao docs.

## Resultado

Decisoes oficializadas:
- **D1**: TCF = **Tabular Compact Format** ✓
- **D2**: alg16 → **OBAT** (Online Bidirectional Affix Tokenizer) ✓
- **D3**: M8.A → **HCC** (Hierarchical Compositional Coding) ✓

Codnomes preservados em historia + dirty lab. Nomes oficiais
adotados em src/, docs, README, CHANGELOG, pyproject, MEMORY.md.

## Sub-decisoes

### D1 — Nome do projeto (acronimo TCF)

**Decisao tentativa**: `TCF — Tabular Compact Format` ✓ (user confirmou)

- **Tabular**: dados tabulares (single-column v0.6, multi-column futuro)
- **Compact**: reducao de bytes e' objetivo
- **Format**: especificacao de arquivo

Substitui:
- "Textual Columnar Format" (v0.5, LLM-focused)
- "Tabular Compact Format" (v0.4 design — agora oficializado pra v0.6)

### D2 — Nome do tokenizador (codnome alg16 / OAS)

**Inspiracao**: LZ77 + front-coding + suffix-tree (Witten et al.,
Brisaboa et al. 2011 RPDac, HTFC)

**Inovacoes**:
1. Bidirecional (LCP + LCS)
2. Online incremental (vs Re-Pair offline)
3. Token-output (TokLit / TokRefPref / TokRefSuf — ortogonal a sintaxe)
4. Min-len threshold para cost-benefit
5. Adequado a colunar (afixos comuns entre valores de mesma coluna)

**Opcoes (escolher 1)**:

- [ ] **OAS** — Online Affix Search (codnome atual, curto)
- [ ] **BAT** — Bidirectional Affix Tokenizer (foca inovacao)
- [x] **OBAT** — Online Bidirectional Affix Tokenizer (descritivo completo) ✓ ESCOLHIDO
- [ ] **BiFC** — Bidirectional Front Coding (conecta direto a literatura classica)
- [ ] outro: ___

**Codnome a preservar**: `alg16` (experimento de origem em M0).

### D3 — Nome da camada composicional (codnome M8.A)

**Inspiracao**: Re-Pair (Larsson & Moffat 1999) + Sequitur
(Nevill-Manning & Witten 1997) + LZW (Lempel-Ziv-Welch 1984)

**Inovacoes**:
1. Marker semantico (`~` cria ref, `,` concat efemero) — nao ha em Re-Pair classico
2. Auto-naming implicito (IDs sequenciais pela ordem de aparicao)
3. Espaco unificado de refs (atomicos + virtuais)
4. Body-order constraint pra inline expansion correto
5. Range `a..b` como caso particular de composicao por sequencia
6. Streaming-compatible em principio (sem preambulo)

**Opcoes (escolher 1)**:

- [ ] **CTE** — Compositional Token Encoder
- [ ] **MTG** — Marked Token Grammar (foca innovacao semantica markers)
- [ ] **iTRP** — iterative Token Re-Pair (conecta a literatura)
- [x] **HCC** — Hierarchical Compositional Coding ✓ ESCOLHIDO
- [ ] outro: ___

**Codnome a preservar**: `M8.A` (experimento de origem em M8).

## Criterio de aceite

1. User escolhe opcoes em D1, D2, D3
2. Atualizar todas as referencias em:
   - `src/tcf/__init__.py`
   - `src/tcf/encoder.py`, `src/tcf/decoder.py`
   - `src/tcf/core/__init__.py`
   - `src/tcf/composicional/__init__.py`
   - `experiments/lab/dirty/notas/historia-dirty-lab.md`
   - `experiments/lab/dirty/notas/naming-compactacao-composicional.md`
   - `README.md` (raiz)
   - `CHANGELOG.md`
   - `pyproject.toml` (description + keywords)
3. Codnomes preservados em comentario/historia para rastreabilidade
4. Push commit "Naming oficial v0.6: TCF + <alg16-name> + <M8.A-name>"

## Notas

- Codnomes `alg16` e `M8.A` permanecem em historia + dirty lab como
  identificadores de origem experimental.
- Nomes oficiais sao usados em codigo, docs publicas, paper.
- Mudancas de codigo sao apenas docstrings / nomes de classe podem
  manter (`M8AVirtualRefsSyntax`) — nome de classe e' implementacao,
  nome publico e' API/doc.

## Commits relacionados

Sequencia de execucao (2026-05-17):
1. Fase 1: `docs/algorithms/` com OBAT.md + HCC.md + TCF-format.md + index
   — commit `3f8215d`
2. Fase 2: docstrings src/tcf/ atualizados (encoder, decoder, __init__.py,
   core/__init__.py, core/syntax_base.py, composicional/__init__.py)
   — commit `6616a93`
3. Fase 3: dirty/notas/historia-dirty-lab.md +
   naming-compactacao-composicional.md atualizados
   — commit `3bde767`
4. Fase 4: README.md + CHANGELOG.md + pyproject.toml atualizados
   — commit `d897888`
5. Fase 5: MEMORY.md (memoria auto) + fechar este ticket
   — commit pendente (este)
