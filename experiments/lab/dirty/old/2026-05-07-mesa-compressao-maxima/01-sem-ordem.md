# Compressão SEM REORDENAR (ordem original)

Aplicando as estratégias da mesa anterior (C1, C2, C3, C8, C11-bare, C11-híbrido)
ao dataset de 30 linhas na ordem em que aparece em `00-dataset.md`.

---

## C1 — CSV literal

≈ **762 B** (baseline)

---

## C2 — Column-major literal (sem compressão)

```
nome:               (8 valores únicos × ~4 ocorrências, média 7B/linha → ~199B)
produto:            (8 únicos × frequência variável → ~233B)
quantidade:         (12 únicos, mistura de 1-2 dígitos → ~72B)
valor_unitario:     (10 únicos, 4-5B cada → ~157B)
```

≈ **704 B** (-7% vs C1)

Headers (`nome:\n` etc.) = 43B; corpo = 661B.

---

## C3 — Column-major + RLE local (sem reordenar)

Na ordem original NÃO há quase nenhum adjacente igual:
- nome: zero pares adjacentes → 0B economizados
- produto: zero pares → 0B
- quantidade: 2 pares de `5,5` curtos → savings desprezível
- valor: 1 par de `2.00, 2.00` → save 3B

≈ **701 B** (RLE local não rende em dados embaralhados — confirma o esperado)

---

## C11-bare (dict implícito por coluna, sem reordenar)

### nome (8 únicos, todos não-numéricos → bare integer funciona)

Primeiras aparições + referências bare:
```
Helena       ← idx 1 (declaração)
Beto         ← idx 2
Diana        ← idx 3
Ana          ← idx 4
Carlos       ← idx 5
Eduardo      ← idx 6
2            ← ref Beto
Fernanda     ← idx 7
Gabriel      ← idx 8
1            ← ref Helena
4            ← ref Ana
3            ← ref Diana
... (22 referências bare no total, todas 1 dígito)
```

≈ **98 B** (vs 199B literal, -51%)

### produto (8 únicos, todos não-numéricos → bare funciona)

Mesma estrutura: 8 declarações de string + 22 refs de 1 dígito.

≈ **109 B** (vs 233B literal, -53%)

### quantidade (12 únicos, todos inteiros puros → COLIDE com índices)

Aqui dict não compensa: precisa marcador (`:N` ou `=valor`) que adiciona 1B
por ref. Para 18 refs de cardinalidade média, custo extra (~18B) supera
economia (~10B). **Encoder escolhe LITERAL**.

≈ **72 B** (igual a C2)

### valor_unitario (10 únicos, todos com decimal → bare funciona)

`1`, `2`, etc. nunca colidem com valores tipo `0.50`, `1.50`. Bare OK.

≈ **93 B** (vs 157B literal, -41%)

### Total C11-híbrido (sem reordenar)

| Coluna | Estratégia escolhida | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto | dict-bare | 109 |
| quantidade | literal (dict perdeu) | 72 |
| valor_unitario | dict-bare | 93 |
| headers | — | 43 |
| **total** | | **≈ 415 B** |

**-45% vs C1, -41% vs C2.** Dict implícito sozinho (sem sort) já retira quase
metade dos bytes — porque captura repetição ESPALHADA, não apenas contígua.

---

## C8 (dict explícito) e C9 (sort+RLE+dict explícito) — para referência

C8 puro: ≈ 720B (anti-compressivo aqui também — overhead de blocos `# dict ...`)

C9 não se aplica diretamente sem reordenar (depende de sort).

---

## Conclusão deste arquivo

Sem reordenar:
- **C11-híbrido domina sozinho** (415 B). Funciona porque o dict implícito
  pega repetição independente de posição.
- RLE local é praticamente inútil na ordem embaralhada.
- Quantidade é a coluna chata: dict colide com valores, RLE não tem com que
  trabalhar — ela fica em literal mesmo.
