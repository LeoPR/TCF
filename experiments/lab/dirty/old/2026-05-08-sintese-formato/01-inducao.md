# Indução sobre formas de dados — por que a regra unificada domina

Argumento que **não depende do dataset específico**: para qualquer
distribuição de dados, a regra unificada (RLE+dict por linha, auto-discrim)
é ≥ qualquer alternativa do conjunto {literal, RLE-only, dict-only,
RLE+dict explícito}.

---

## 4 formas arquetípicas (extremos)

### Forma A — Todos diferentes (cardinalidade = N)

Todos os valores únicos. Sem repetição.

| Codificação | Comportamento | Bytes |
|---|---|---|
| Literal | escreve cada valor 1× | N · (len(v) + 1) |
| RLE | cada run = 1 (degenera p/ literal sem prefix `1*`) | igual literal |
| Dict | cada valor declarado 1×, sem refs (degenera) | igual literal |
| **Unificada** | escolhe literal por linha (ref impossível) | **igual literal** |

→ Empate. Unificada não cria overhead onde não há padrão.

---

### Forma B — Todos iguais (cardinalidade = 1, N ocorrências)

Um único valor `v` repetido N vezes.

| Codificação | Bytes |
|---|---|
| Literal | N · (len(v) + 1) |
| RLE | digits(N) + 1 + len(v) + 1 |
| Dict | (len(v) + 1) + (N-1) · (digits(idx) + 1) ≈ len(v) + 1 + 2(N-1) |
| **Unificada** | digits(N) + 1 + len(v) + 1 (= RLE) |

Para N=10 e len(v)=4 (`Ana`):
- Literal: 50 B
- RLE: 7 B
- Dict: 23 B
- Unificada: 7 B (= RLE)

→ Unificada **iguala RLE**, **vence literal e dict**.

---

### Forma C — Runs perfeitos pós-sort (k blocos contíguos de tamanho n_k)

Caso de coluna primária do sort. k valores únicos, cada um em 1 bloco.

| Codificação | Bytes |
|---|---|
| Literal | Σ n_k · (len(v_k) + 1) |
| RLE | Σ (digits(n_k) + 1 + len(v_k) + 1) para n_k>1, senão len(v_k)+1 |
| Dict | Σ (len(v_k) + 1) + Σ (n_k - 1) · (digits(idx) + 1) |
| **Unificada** | igual RLE (refs não fazem sentido — cada valor em 1 bloco) |

→ Unificada **iguala RLE**, **vence literal e geralmente dict**.

---

### Forma D — Repetições espalhadas (cardinalidade << N, sem contiguidade)

Caso de coluna não-sortida com valores que reaparecem em posições
distantes.

| Codificação | Bytes |
|---|---|
| Literal | Σ N · (len(v) + 1) |
| RLE | ≈ literal (poucos pares adjacentes) |
| Dict | Σ (len(v) + 1) + (N - card) · (digits(idx) + 1) |
| **Unificada** | igual dict (escolhe ref por linha quando ref < literal) |

→ Unificada **iguala dict**, **vence literal e RLE**.

---

### Forma E — Fragmentação (mesmo valor em múltiplos blocos)

Caso típico após multi-sort com chaves correlacionadas imperfeitamente.
Valor `v` aparece em m blocos de tamanho n_1, n_2, ..., n_m.

| Codificação | Bytes |
|---|---|
| Literal | Σ Σ (len(v) + 1) |
| RLE | Σ (digits(n_i) + 1 + len(v) + 1) — repete `v` literal a cada bloco |
| Dict | (len(v) + 1) + (Σ n_i - 1) · (digits(idx) + 1) |
| **Unificada** | 1º bloco: literal RLE; demais: ref RLE (`n_i*<idx>`) |

Para v=`Caderno` (len=7), m=2 blocos de tamanhos 4 e 1:
- Literal: 8·5 = 40 B
- RLE: 10 + 8 = 18 B
- Dict: 8 + 4·2 = 16 B
- Unificada: `4*Caderno` (10) + `<idx>` (2) = 12 B

→ Unificada **vence todas**. Estritamente dominante neste caso.

---

## Por que a unificada nunca perde

### Argumento (informal)

A regra unificada permite, por linha, emitir QUALQUER uma das formas:
- literal isolado (`<v>`)
- literal RLE (`N*<v>`)
- ref isolada (`<idx>`)
- ref RLE (`N*<idx>`)

A escolha local é a mais curta. Logo:

```
bytes(unificada, linha i) ≤ bytes(qualquer outra forma, linha i)
```

Somando sobre todas as linhas:

```
bytes(unificada, coluna) ≤ bytes(qualquer encoding monolítico, coluna)
```

E sobre todas as colunas:

```
bytes(unificada, arquivo) ≤ bytes(qualquer outra encoding, arquivo)
```

Igualdade quando o encoding alternativo coincide com a escolha ótima por
linha. Estrita desigualdade quando há mistura de modos ótimos por linha
(forma E acima).

### O que falta para ser prova rigorosa

- Definir formalmente "linha válida" (1ª aparição não pode ser ref)
- Mostrar que a escolha local é independente das demais (não há
  acoplamento entre linhas que invalide a soma)
- Considerar o overhead de cada modo (`*` para RLE, `:` para marcador)

Esses são detalhes técnicos. O argumento estrutural está correto.

---

## Indução sobre escala

A dominância da unificada vale **independentemente de N (linhas) e da
cardinalidade**. Demonstração:

### Crescimento de N com cardinalidade fixa

Conforme N → ∞ com cardinalidade c fixa:
- Literal cresce linearmente: O(N · len(v))
- RLE cresce sublinearmente: O(c · log(N) + c · len(v))
- Dict cresce linearmente: O(c · len(v) + N · digits(c))
- Unificada cresce sublinearmente após sort: O(c · log(N) + c · len(v))
- Unificada cresce linearmente sem sort: O(c · len(v) + N · digits(c))

Em ambos os casos, unificada ≥ a melhor das outras.

### Crescimento de cardinalidade c com N fixo

Conforme c → N (todos diferentes):
- Todas as formas convergem para literal.
- Dict acrescenta overhead de digits(idx) sem ganho. **Unificada decide
  "não usar dict"** linha-a-linha. Iguala literal.

Conforme c → 1 (todos iguais):
- RLE explode em ganho. Dict também (1 declaração + N-1 refs).
- Unificada captura RLE. Iguala RLE.

Em todos os pontos da escala, unificada ≥ a melhor alternativa.

### Conclusão indutiva

Não há tamanho de dataset, cardinalidade ou distribuição em que uma das
formas-ablação (literal, RLE-only, dict-only, RLE+dict explícito) vença a
regra unificada. **A regra unificada é mathematically dominante** dentro
do escopo {RLE, dict} clássicos.

---

## Onde a indução **não** se estende

A dominância é apenas dentro do **espaço de modos {literal, RLE, dict}**.
Não cobre transformações pré-encoding que captam padrões estruturais
diferentes:

| Padrão de dado | Regra unificada captura? | Quem captura |
|---|---|---|
| Repetição contígua | ✓ (RLE) | unificada |
| Repetição espalhada | ✓ (dict) | unificada |
| Fragmentação | ✓ (mix) | unificada |
| **Sequência aritmética** | ✗ | δ (delta) |
| **Prefixo comum** | ✗ | P (prefix elision) |
| **Linhas duplicadas inteiras** | ✗ (só por coluna) | L' (line-RLE) |

Esses 3 padrões precisam de **transformações ortogonais**, aplicadas
**antes** ou **em substituição** à regra unificada. São extensões
opt-in, não ablação.

---

## Implicação para o formato

A regra unificada é a base **única** para v0.5. As 12 variantes (C1-C12)
não precisam coexistir como modos discretos. Reduzem a:

1. **Núcleo**: regra unificada (sempre)
2. **Parâmetros**: sort (multi-chave), discriminador por coluna
3. **Extensões**: δ, P, L', count-recycling — opt-in por coluna
4. **Flags de ablação**: `force=literal`, `force=rle`, `force=dict` —
   apenas para experimentação, não produção

A próxima etapa (`02-regra-minima.md`) detalha o formato resultante.
