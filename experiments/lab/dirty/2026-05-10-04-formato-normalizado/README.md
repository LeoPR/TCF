# 04 — formato normalizado + ordenações + fórmula

## Princípio / motivação

Continuação direta dos exps 02 e 03. Duas motivações:

1. A medição de bytes do exp 03 ficou contaminada por escolhas de
   formato (linha de comentário extra, `1x` explícito em count=1) que
   não pertenciam à diferença intrínseca entre as serializações
   separada e inline. Aqui ambas usam **a mesma régua** (sem
   comentários, omitir `1x` em count=1). A comparação isola a camada 2
   (marcadores de referência).
2. Os exps 02/03 só rodaram em 2 cenários. Não dava para ver como a
   diferença entre as serializações se comporta sob variações de
   estrutura (cardinalidade, ordenação). Aqui rodamos **16 cenários**
   = 4 datasets × 4 ordenações.

A ferramenta principal deste experimento é a **fórmula de previsão**
em `formula.py`: prevê o tamanho de cada serialização por camada
(macro / ref / dados) e compara com a medição direta no texto
encodado. Match exato em todos os 16 valida que o modelo de camadas é
consistente com o encoder.

## Propósito

Responde a três perguntas:

1. **Comparação justa** entre separado e inline com mesma régua de
   formato — qual a economia real (em camada 2) da serialização
   inline?
2. **Comportamento sob ordenação** — a diferença entre as duas
   serializações depende da ordem do input?
3. **Fórmula de grandeza** — é possível prever a economia em função
   de `(N_unique, N_pat_int)` ou variáveis estruturais semelhantes?

## Comparação

- **Compara com**: [02-patricia-nomes](../2026-05-10-02-patricia-nomes/)
  e [03-patricia-inline](../2026-05-10-03-patricia-inline/).
- **É comparável?** Sim. Mesma árvore Patricia (`patricia.py` byte
  idêntico), mesmas duas serializações, agora sob régua única. Os 2
  cenários do exp 02/03 estão aproximadamente reproduzidos como D1
  (≈ cenário A) e D3 (≈ cenário B), com ordenação adicional.
- O que se compara: bytes de cada camada (macro / ref / dados) e
  delta entre as duas serializações por cenário.

## Cenários e valores possíveis

**4 datasets** (variando cardinalidade e presença de Patricia):

| Dataset | N_total | N_unique | Patricia | N_pat_int |
|---|---:|---:|---|---:|
| D1 — baixa-card-sem-patricia | 50 | 5 | inativo | 0 |
| D2 — alta-card-sem-patricia | 100 | 40 | inativo | 1 |
| D3 — baixa-card-com-patricia | 50 | 5 | ativo | 1 |
| D4 — alta-card-com-patricia | 100 | 25 | ativo | 4 |

**4 ordenações** por dataset:
- `original` — embaralhamento moderado (1 shuffle)
- `sorted` — lex sortado (runs RLE máximos)
- `random` — embaralhamento profundo (3 shuffles)
- `agrupado` — todos iguais juntos (1 run por valor)

`gerar_dados.py` é determinista por seed (42). Cada CSV em
`data/<DN>-<...>/<ord>.csv` tem `N_total` linhas com cada valor
único aparecendo `N_total / N_unique` vezes.

Encoders **normalizados** (mesma régua):
- sem comentários no arquivo
- omitir `1x` em count=1, em decls e refs

Marcadores macro mantidos (`<patricia>`, `<body>`) — contagem
registrada mas tratada como "escala pequena" (camada 3) por convenção.

## Resultado observado

### Roundtrip e validação da fórmula

- **16 / 16 cenários roundtrip OK** em ambas as serializações.
- **Previsão simbólica = medição real em todos os 16 cenários**
  (separado e inline). Ver Tabela 2 no output do `run.py`. Confirma
  que o modelo de camadas em `formula.py` reproduz o encoder.

### Decomposição por camada (Tabela 3 do run.py)

- **Camada 1 (dados efetivos)** — idêntica entre separado e inline em
  todos os 16 cenários. A árvore Patricia produz os mesmos
  fragmentos.
- **Camada 3 (macros)** — separado: 38 bytes constantes; inline:
  15 bytes constantes. Diferença fixa de 23 bytes em todo cenário.
  Por convenção: registrada, não pesada na comparação.
- **Camada 2 (marcadores de ref)** — onde está a variação relevante.

### Camada 2 — economia inline vs separado (Tabela 4)

Os deltas (negativos = inline economiza):

| Dataset | original | sorted | random | agrupado |
|---|---:|---:|---:|---:|
| D1 (5 únicos, sem Patricia) | -55 | -55 | -55 | -55 |
| D2 (40 únicos, sem Patricia) | -468 | -467 | -467 | -467 |
| D3 (5 únicos, com 1 Patricia interno) | -51 | -51 | -51 | -51 |
| D4 (25 únicos, com 4 Patricia internos) | -288 | -289 | -288 | -294 |

**Observação central**: o delta em camada 2 é praticamente constante
ao longo das 4 ordenações de cada dataset. Pequenas flutuações em D4
(±6) vêm de counts diferentes na 1ª ocorrência (decl-com-ocorrência
inline pega o count, e o número de chars do count varia).

### Fórmula aproximada

A economia inline → separado em camada 2 pode ser aproximada por:

```
delta ≈ -(K_ref + 1) * N_unique  +  K_tardia * N_pat_int
```

onde:
- `K_ref` ≈ 9 + comprimento médio de eid em chars — overhead de uma
  ref no body (`  ref:noN\n` = 10 chars com eid de 1 char).
- `+1` é a economia de `: ` vs ` = ` na decl-com-ocorrência inline.
- `K_tardia` ≈ 5 chars — overhead extra de uma decl tardia (palavra
  `decl `).

Validação aproximada (com `K_ref ≈ 10`, `K_tardia ≈ 5`):

| Dataset | previsto ≈ | medido (média) |
|---|---:|---:|
| D1 | -55 | -55 |
| D2 | -440 + correções de eid | -467 |
| D3 | -55 + 5 = -50 | -51 |
| D4 | -275 + 20 = -255 | -290 |

Termos não capturados na forma simplificada: variação de
`len(str(eid))` entre nós (eids vão de 1 a `N_unique + N_pat_int`),
contribuição dos counts em decls com count > 1, etc. A fórmula exata
está em `formula.py` e bate 100%.

### Efeito da ordenação

A ordenação afeta o **número absoluto** de bytes em camada 2 (porque
muda o número de RLE entries no body), mas **não afeta o delta**
entre as serializações:

| | sep_ref (D2) | inl_ref (D2) | delta |
|---|---:|---:|---:|
| original | 1820 | 1352 | -468 |
| sorted | 1302 | 835 | -467 |
| random | 1819 | 1352 | -467 |
| agrupado | 1302 | 835 | -467 |

Sortado/agrupado têm refs comprimidas por RLE (quase 1 ref por valor
único). Original/random têm muitas refs individuais. Mas a
**diferença** entre as duas serializações vem da estrutura da árvore,
não da ordem do body — porque o que muda no inline é apenas a fusão
de `N_unique` decls + 1ªs refs e a adição de `N_pat_int` decls
tardias. Esses dois números não dependem da ordem.

## Limitações

- 16 cenários, todos com `N_total` ≤ 100 e cardinalidades discretas
  (5, 25, 40). Comportamento em N >> 100 ou em cardinalidades
  intermediárias (10, 50, 100) não foi medido.
- A fórmula simplificada é aproximação por valores médios. A fórmula
  exata é a implementação em `formula.py`, que reproduz o encoder
  caractere a caractere.
- "Mesma régua" significa: sem comentários e sem `1x` explícito.
  Outras escolhas de marcador (separadores, indentação, base do id)
  não foram testadas.
- Roundtrip valida apenas decode bem-formado. Robustez contra inputs
  corrompidos não foi testada.
- Geração dos datasets usa seed fixa (42). Alterações no padrão de
  shuffle do `random.Random` em outras versões de Python poderiam
  produzir CSVs ligeiramente diferentes.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-04-formato-normalizado
python gerar_dados.py     # gera os 16 CSVs em data/
python run.py             # roda + imprime 4 tabelas
```

`run.py` também salva os 32 arquivos `.tcf` em `encoded/` (1 por
cenário-serialização) para inspeção visual.
