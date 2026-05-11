# Inventário completo de tipos de dado — status de cobertura

Para fechar v0.5, precisa-se garantir que a Etapa 1 (algoritmo lógico
em ASCII) cobre os tipos de dado **comuns em datasets reais**.

Lista organizada por categoria, com status: ✓ coberto, ◐ parcial,
❌ não tratado, ⊘ fora de escopo v0.5.

---

## Categoria 1 — Atômicos (1 valor por célula)

### 1.1 Strings curtas (nomes, códigos textuais)

**Status**: ✓ Coberto pela regra unificada (RLE+dict) com alfabeto A.

### 1.2 Strings longas (descrições, comentários, freeform)

**Status**: ◐ Parcial.

A regra unificada cobre o caso geral, mas em strings longas únicas:
- Cardinalidade ≈ N
- Dict não ajuda
- Cada linha vira literal

Solução: aceitar literal puro. Compressão do conteúdo interno (gzip
substring) fica para Etapa 2 ou para compressão downstream.

**Ação para v0.5**: documentar que strings longas únicas não são
otimizadas pelo TCF; recomendar pipeline com gzip. Sem flag nova.

### 1.3 Booleans (true/false, 0/1, sim/não)

**Status**: ❌ Não tratado especificamente.

Cardinalidade 2. Dict perfeito (idx 1, idx 2). Mas overhead de dict
para cardinalidade 2 é alto:
- 2 declarações + (N-2) refs vs N literais
- Para `true/false`: literal = 5/6 chars; ref = 1 char. Dict ganha
  facilmente.
- Para `0/1`: literal = 1 char; ref = 1 char. Empate, dict pode até
  perder se não otimizado.

**Ação para v0.5**: a regra unificada já cobre matematicamente;
encoder pode ter atalho — para cardinalidade 2 com valores curtos,
não declarar dict. Decisão por linha.

Alternativa: representação canonical compacta (`t`/`f` ou `1`/`0`).
Encoder adota o que já estiver no dado — não normaliza.

### 1.4 Inteiros pequenos (até ~1000)

**Status**: ✓ Coberto.

### 1.5 Inteiros grandes (IDs, contagens grandes)

**Status**: ◐ Parcial.

Para cardinalidade alta (cada valor único — IDs sequenciais), δ vence.
Para iid com poucos valores, dict.

**Ação para v0.5**: heurística do encoder cobre; sem flag nova. Mas
documentar com exemplo.

### 1.6 Decimais com precisão fixa (preço, valores monetários)

**Status**: ✓ Coberto.

### 1.7 Floats com precisão variável

**Status**: ❌ Pendente — mesa numérica abriu tickets:
- T-N-IoT-baseline (oscilação)
- T-N-financial-sum-preserving

**Ação para v0.5**: incluir flag `Q` (quantização) como pendente.
Casos não-quantizáveis ficam como literal.

### 1.8 Datas (sem hora)

**Status**: ✓ Coberto via δ.

### 1.9 Timestamps (com hora, opcional ms)

**Status**: ✓ Coberto via δ multi-escala.

### 1.10 Times sem data (apenas HH:MM ou HH:MM:SS)

**Status**: ❌ Não testado mas teoricamente coberto.

ISO 8601 permite hora isolada (`14:30:00`). Decoder reconhece pelo
shape. δ aplicaria com unidades h/m/s.

**Ação para v0.5**: declarar coberto por extensão da gramática de
timestamps; testar com dataset.

### 1.11 Durations / intervals ("1h30m", "P1Y2M")

**Status**: ❌ Não tratado.

ISO 8601 tem `P1Y2M3DT4H5M6S` (Period). Alternativa "natural":
`1h30m`.

Para TCF: tratar como string (literal); δ não aplica diretamente
(durations não são pontos no tempo).

**Ação para v0.5**: documentar como literal. Compressão por dict se
houver repetição. Sem flag nova.

---

## Categoria 2 — Compostos (1 valor com estrutura interna)

### 2.1 Currency (number + unit, "R$ 10,50" ou "10.50 USD")

**Status**: ❌ Não tratado.

Combinação de número + código de moeda. Se a moeda é única na coluna
inteira (sempre USD), pode ser elidida (tratar como flag P sobre o
sufixo).

**Ação para v0.5**: documentar como caso de uso da flag P futura.
Por enquanto, literal.

### 2.2 Percentage ("12.5%")

**Status**: ◐ Parcial.

Pode ser tratado como decimal (Q quantização) com `%` como sufixo
literal. Se sufixo único na coluna, P-elision.

**Ação para v0.5**: cobertura indireta via Q + P.

### 2.3 Coordenadas geográficas (lat/lon)

**Status**: ❌ Não tratado.

Pares correlacionados. Em datasets de mapeamento, lat e lon vizinhos
são similares.

Opções:
- 2 colunas separadas, cada uma com δ-baseline (centro do mapa) + Q
  (precisão de ~10m)
- 1 coluna composta `-23.5505,-46.6333` — depois aplica decoder de par

**Ação para v0.5**: tratar como **2 colunas separadas**. Não criar
tipo composto novo.

### 2.4 Versions semânticas ("1.2.3")

**Status**: ❌ Não tratado.

3 partes inteiras separadas por `.`. Cada parte tem cardinalidade
baixa e correlação (após sort por versão, partes evoluem).

**Ação para v0.5**: tratar como string literal por padrão. Encoder
não decompõe. Compressão via dict se houver repetição.

### 2.5 Endereços / códigos postais

**Status**: ❌ Não tratado.

CEP `01310-100`: estrutura semi-rígida, dict pode ajudar para cidades
mesmas. P-elision para prefixos.

**Ação para v0.5**: literal. Compressão via dict + P (quando P
existir).

---

## Categoria 3 — Casos especiais

### 3.1 NULL / valores ausentes

**Status**: ❌ NÃO tratado — **CRÍTICO para v0.5**.

Datasets reais têm valores ausentes. TCF precisa representar.

Opções:
- Linha vazia: `\n` sem conteúdo. Funciona em line-mode mas confunde
  parser (ambíguo com fim de bloco).
- Marcador especial: `~` ou `\N` (PostgreSQL) ou `?`
- Símbolo dedicado: `null` literal

Proposta: **`~` como marcador NULL universal**. Ocupa 1 char, raro de
colidir, fácil de ler.

```
nome:
Ana
~          ← NULL
Beto
~
```

Com RLE: `3*~` para 3 NULLs contíguos. Com dict: NULL pode receber idx
0 reservado, ou ser tratado como literal especial.

**Decisão sugerida**: NULL é um literal especial. Encoder/decoder
reconhece `~` em qualquer linha como NULL.

**Ação para v0.5**: criar mesa rápida específica para NULL. Validar
escolha de marcador, comportamento com RLE/dict.

### 3.2 Sparse columns (maioria NULL ou zero)

**Status**: ❌ Não tratado.

Quando >70% das linhas são NULL/zero, RLE no NULL captura muito.

Opção alternativa: armazenar **só os não-NULL com posição**.

```
sparse: positions=[3, 7, 12], values=[42, 99, 17]
```

Mas isso é layout muito diferente.

**Ação para v0.5**: aceitar que RLE+dict no NULL marker (`~`) cobre
parcialmente. Layout sparse específico fica para v0.6.

### 3.3 Arrays / listas multi-valor por célula

**Status**: ⊘ Fora de escopo v0.5.

Bancos relacionais têm tags = `["azul", "grande", "promocao"]`. TCF
column-major assume escalares.

**Ação**: deferido para mesa de **arrays/listas** futuras (v0.6+).

### 3.4 Estruturas aninhadas (JSON dentro de célula)

**Status**: ⊘ Fora de escopo v0.5.

Tratar como string literal. Ou exigir flatten antes de TCF.

### 3.5 UUIDs

**Status**: ◐ Parcial.

Cardinalidade ≈ N (todos únicos). Dict não ajuda. Literal apenas. P
pode atuar se há prefixo em comum (raro).

**Ação para v0.5**: documentar como caso degenerado. Literal aceitável.

### 3.6 Hashes / blobs binários (base64, hex)

**Status**: ⊘ Fora de escopo.

Aleatórios. Sem padrão. Literal.

### 3.7 URLs

**Status**: ◐ Parcial.

Prefixos comuns (`https://example.com/`). P-elision quando vier.

**Ação para v0.5**: ticket P para o futuro.

### 3.8 Email addresses

**Status**: ◐ Parcial.

Sufixo de domínio comum (`@gmail.com`, `@empresa.com`). Pode ter dict
nas partes. P-elision para sufixo.

**Ação para v0.5**: P futuro. Por agora, literal.

---

## Categoria 4 — Relações entre colunas

### 4.1 Foreign keys (correlação dura)

**Status**: ◐ Parcial.

Quando 2 colunas correlacionam fortemente (e.g., produto ↔ valor),
sort por uma puxa a outra. Já investigado em mesas de multi-sort.

**Ação para v0.5**: nada novo. A heurística de sort já aproveita.

### 4.2 Computed columns (uma derivada de outras)

**Status**: ⊘ Fora de escopo do formato.

Se col `total = preco * qty`, TCF poderia armazenar 2 colunas e
calcular a 3ª. Mas isso é responsabilidade da aplicação, não do
formato.

### 4.3 Cross-column dict (mesma representação em colunas distintas)

**Status**: ❌ Insight curioso anotado em mesa C8, não explorado.

Quando 2 colunas têm exatamente os mesmos valores únicos (e.g.,
"cidade_origem" e "cidade_destino"), poderiam compartilhar dict.

**Ação para v0.5**: ticket de pesquisa. Não bloqueia v0.5.

---

## Resumo do inventário

| Tipo | Status | Bloqueia v0.5? |
|---|---|---|
| Strings curtas | ✓ | não |
| Strings longas | ◐ documentar | não |
| Booleans | ❌ ajuste menor | **sim** (validar comportamento) |
| Inteiros pequenos | ✓ | não |
| Inteiros grandes | ◐ documentar | não |
| Decimais fixos | ✓ | não |
| Floats variáveis | ❌ Q proposta | parcial — Q opcional |
| Datas | ✓ | não |
| Timestamps | ✓ | não |
| Times isolados | ❌ extensão simples | testar |
| Durations | ❌ literal | não |
| Currency com unidade | ❌ P futuro | não |
| Percentages | ◐ Q + P | não |
| Coordenadas | ❌ 2 colunas | não |
| Versions | ❌ literal | não |
| **NULL / missing** | **❌ CRÍTICO** | **sim** |
| Sparse columns | ❌ futuro | não |
| Arrays | ⊘ v0.6 | não |
| Nested | ⊘ v0.6 | não |
| UUIDs | ◐ literal | não |
| Hashes | ⊘ literal | não |
| URLs | ◐ P futuro | não |
| Emails | ◐ P futuro | não |

### Gargalos críticos para v0.5

1. **NULL / valores ausentes** — não pode ser ignorado, dataset real
   sempre tem
2. **Booleans** — caso comum, validar que regra unificada funciona bem
3. **Times isolados** — extensão pequena de timestamps
4. **Floats com Q** — quantização explícita

Próximo arquivo (`02-fechamento-v05.md`) detalha como resolver cada um
e o que fica para v0.6+.
