# Mesa ampla — escalando + reflexao hipotetica

## Objetivo

1. Ver onde tudo COLIDE (tecnicas se reforcam ou interferem)
2. Identificar em qual escala cada tecnica COMECA a fazer sentido
3. Refletir hipoteticamente sobre camadas ainda nao tocadas
   (schema, LLM, paralelismo, prioridade)
4. Preparar "bancada limpa" para fase de implementacao

## Resultado de escala

| Nivel | Rows totais | naive | TCFv04 | Ganho |
|-------|-------------|-------|--------|-------|
| N1 (1t, 5 rows, 2 cols) | 5 | 74 | 109 | **+47.3% (perde)** |
| N2 (1t, 50 rows, 5 cols) | 50 | 1617 | 1027 | **-36.5%** |
| N3 (3t, mini-banco com FKs) | 110 | 1895 | 1232 | **-35.0%** |
| N4 (5t, banco completo) | 1100 | 20077 | 11672 | **-41.9%** |

### Achados induzidos

**A1 — Em N=5 o overhead domina; TCF perde 47%.**
Markers `pk_eliminated=`, `dict=`, header de tabela custam bytes
que so se pagam em payload maior.

**A2 — A partir de N=50 ganho consistente -35% a -42%.**
TCF v0.4 com auto-tudo bate naive de forma robusta a partir de
escala media.

**A3 — Mais tabelas + mais relacoes = mais ganho relativo.**
N4 (5 tabelas com FKs cruzando) ganha mais que N3 (3 tabelas).
Cross-DICT, key elimination e affix se reforcam mutuamente.

**A4 — Ponto de equilibrio: ~N=20-30 rows.**
Abaixo disso, TCF nao paga overhead. Ja eh um "sinal" para
auto-bypass do FORMATO inteiro: dataset minusculo deveria emitir
TCF mais simples ou voltar para CSV-like.

## Onde tudo colide (interacao das tecnicas)

### Reforco mutuo

| Combo | Efeito |
|-------|--------|
| Cross-DICT + Key elimination | FK substituida por indice cuja vocab ja eh global → economia DUPLA |
| Affix + DICT inline | nome de produto `Prod-NNN`: affix extrai prefixo, sufixo numerico fica curto |
| Auto-bypass + Cross-DICT | colunas com cardinality alta NAO entram em cross — preserva o sentido do cross |
| PK eliminada + ordem do DICT | indice DICT vira PK canonica natural |

### Conflito potencial (a investigar futuramente)

| Combo | Tensao |
|-------|--------|
| Affix + Cross-DICT | se afixo pode entrar em multiplas colunas, qual prevalece? |
| Stratified STATS + Eliminacao | STATS estratificada por categorical eliminada precisa do DICT |
| Sort_by + chunks | sort altera ordem; em chunks, "primeira coluna" decide grupos |
| Auto-detect grau chave + UUID | UUIDs detectados como string podem virar elegiveis a affix indevidamente |

## Reflexao hipotetica — camadas nao tocadas

### Schema como fonte de informacao

Ate aqui o encoder usa **heuristicas** para inferir:
- Tipo (int/float/str via Python `type()`)
- Cardinality (set len)
- Affix (LCP)
- PK auto-increment (sorted == 1..N)
- Vocabulario compartilhado (set intersection)

Com schema explicito ganhamos:

| Info do schema | O que habilita |
|----------------|----------------|
| Tipos declarados | Proposta B (type-preserving) sem heuristica |
| PKs/FKs explicitos | Proposta I (key elimination) confiavel |
| Constraints (NOT NULL, UNIQUE) | STATS exatas; auto-bypass mais agressivo |
| Ranges (min/max declarados) | escolher Delta vs RLE em time-series |
| Indices declarados | sugere `sort_by` ideal (Proposta F) |
| Categoricos enumerados | DICT preconstruido; cross-DICT obvio |
| Formato de chave (UUID vs INT) | classifica grau (Proposta I) sem heuristica |

**Hipotese forte**: schema simplificado (mesmo opcional) pode
**reduzir overhead de deteccao** e **aumentar ganho** em ate 5-10%
adicionais. Vale exigir schema em casos relacionais.

API hipotetica:
```python
encode_database(tables, schema={
    "pessoas": {"pk": "id", "type:id": "int_grau2",
                 "type:nome": "str", "categories:cat_pref": ["A","B","C","D"]},
    "pedidos": {"pk": "pedido_id",
                 "fks": {"pessoa_id": "pessoas"}, ...},
})
```

### Paralelismo (hipotetico, v0.5+)

O modelo de chunks autocontidos (D1-D5) ja prepara terreno:

- Cada chunk encoda independentemente em CPU separada
- Coordinator (EncodeManager) recebe chunks fora de ordem
- Compressor generico (camada 3) aplica sobre cada batch

**Conflito potencial**: se cross-DICT atravessa tabelas (como em N4
GLOBAL_2 cobrindo 3 tabelas), encoder paralelo precisa coordenar
DICT antes de paralelizar. Ou aceita pequena perda por nao
compartilhar DICT entre chunks.

**Hipotese**: paralelismo ganha proporcional ao numero de chunks
(N CPUs ↔ N chunks autocontidos). Cross-DICT cross-tabela vira
custo serial pequeno antes de paralelizar.

### Prioridade de emissao (hipotetico)

Dado plano explicito (`Plan(group_by=..., order=...)`):

- "Top 5 grupos por frequencia" pode ser emitido PRIMEIRO
- Cliente comeca a renderizar enquanto resto vem
- Em multi-tabela: emitir "dimensoes pequenas" primeiro
  (categorias, status), depois "fatos" (pedidos)

**Conflito potencial**: prioridade depende do `Plan` do cliente,
nao do encoder. Encoder so respeita ordem; quem decide eh cliente.
Limite: fora desta fase v0.4.

### LLM como camada (escopo separado ⚫)

Nao testar agora. Mas refletir:

- DICT inline (D16) **ajuda LLM**: ele le coluna → dict → valores
  em sequencia
- Affix-DICT **ajuda LLM**: prefixo virou regra explicita
- Key elimination **pode confundir LLM**: ele perde refer encia
  cruzada entre tabelas se nao entender `pk_eliminated`
- Cross-DICT GLOBAL_N **pode ajudar LLM**: tabela mental de "categoria"
  unificada

**Reflexao**: TCF v0.4 caminho-feliz **otimiza bytes**. Para LLM,
talvez precisemos uma flag `verbose_llm=True` que:
- Mantem PKs/FKs (legibilidade)
- Repete DICT em cada coluna (se for muito longe na leitura)
- Adiciona @llm-hint blocks

Isso fica em [M-llm-integration-future](../../../../docs/workbench/tickets/open/M-llm-integration-future.md).

### Cardinalidade dedutivel sem schema

Heuristicas atuais funcionam mas com falsos positivos:

| Heuristica | Falha em |
|-----------|---------|
| `sorted == 1..N` para PK | numericos sequenciais que NAO sao PK (ex: ano 2020,2021,...) |
| `cardinality < N/2` para DICT | datasets muito pequenos onde threshold eh pouco discriminante |
| `LCP >= 5` para affix | identificadores curtos (`X1`, `X2`) onde affix poderia ajudar com >= 2 |
| `int auto-increment` para grau 2 | ids sequenciais usados externamente (lemme tabela com timestamp como int) |

**Conclusao**: heuristicas suficientes para "caminho feliz" automatico,
mas schema explicito eh sempre melhor para producao critica.

## Obsolescencias revisitadas (visao ampla)

User comentou: algumas obsolescencias eh "sempre vence" mas
**ablacao cientifica** ainda precisa testar formas antigas.
Reclassificar:

| Tipo | Tratamento |
|------|-----------|
| **Default removido** | forma vencedora eh padrao; antiga sai do auto |
| **Disponivel para ablacao** | flag `legacy_mode="dict_in_header"` para experimentos |
| **Banido** | nunca emitir, nem em ablacao |

Sugestao de classificacao:

| Comparacao | Status |
|-----------|--------|
| L3 preserva PK grau 2 | DEFAULT REMOVIDO; disponivel ablacao |
| DICT no header | DEFAULT REMOVIDO; disponivel ablacao (chunks puderam mostrar valor) |
| L3 cardinality alta | DEFAULT REMOVIDO; ablacao |
| L3 per-column quando cross vence | DEFAULT REMOVIDO; ablacao |
| Sort lex em ints | BANIDO (eh bug, nao otimizacao) |
| `sorted_by=` quando eh grouped | BANIDO (eh mentira semantica) |
| RLE atravessa chunk | BANIDO (quebra autocontencao) |
| Header verboso | DEFAULT REMOVIDO; ablacao |

## Como "limpar a bancada" — proxima fase

Apos esta mesa suja, a bancada tem:
- 7 labs dirty rodados
- 3 propostas validadas (E, H, I)
- 3 propostas selecionadas mas sem lab (A, B, F)
- 16 decisoes congeladas (D1-D16)
- 8 obsolescencias categorizadas

**Sugestao de "lab clean" inaugural** (proxima fase):

Pasta: `experiments/lab/clean/EXP-003-caminho-feliz-formal/`
Estrutura:
- README.md com hipotese clara
- run.py com framework `pipeline.py` (ja existe em lab/framework/)
- 3+ datasets reais escolhidos (TPC-H, Adult, e mais 1)
- Tabela formal: caminho feliz vs naive vs L3 vs gzip externo
- Conclusao reproduzivel

Antes de criar EXP-003, validar:
- Implementar Plan + chunks no core (M-chunks-v04 Bloco 1)
- Implementar Propostas E, H, I no core (opt-in)
- Validar Propostas A, B, F com labs dirty

## Conclusao da mesa ampla

Resultado: TCF v0.4 caminho feliz **ganha consistentemente em escala**
(N >= 50 rows) com -35% a -42% vs naive. Em escala minuscula (N=5)
**perde 47% por overhead** — ponto de auto-bypass do formato inteiro
quando justificado.

Schema explicito eh **alavanca importante** para reduzir incerteza
e aumentar ganho. Sem schema, heuristicas funcionam bem em casos
comuns mas tem zonas de falha conhecidas.

Camadas nao tocadas (LLM, paralelismo, prioridade, schema avancado)
**convergem com tudo que decidimos** — cada uma eh extensao natural
do que ja temos. Nenhuma exige re-design do formato.

Proxima fase: limpar bancada → implementar core seletivamente.
