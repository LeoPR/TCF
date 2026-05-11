# H2 — Cabeçalho explícito de seleção por coluna

A proposta: o arquivo declara, por coluna, qual técnica de compressão foi
usada. Decoder lê o header e sabe direto o que esperar — sem inferir.

---

## Espaço de codes (3 bits = 8 modos)

Mantendo a proposta original e abrindo espaço para extensões futuras:

| Code | Símbolo | Significado | Quando faz sentido |
|---|---|---|---|
| `000` | L | literal | coluna sem repetição útil |
| `001` | R | RLE puro (`N*valor`) | runs longos contíguos |
| `010` | D | dict implícito bare | repetição espalhada, valores não-numéricos |
| `011` | B | dict + RLE em refs | repetição espalhada com runs de mesmo idx |
| `100` | M | dict marcado (`:N` ou `=val`) | coluna numérica com colisão |
| `101` | δ | delta encoding | reservado (sequenciais, timestamps) |
| `110` | P | prefix elision | reservado (strings com prefixo comum) |
| `111` | X | extensão / flag | escape para futuras |

São 4 modos efetivos hoje (L, R, D, B/M); os outros 4 reservados. 3 bits
prevê crescimento.

---

## Notações testadas

### A. Verbose (uma linha por coluna)
```
# col nome encoding=D
# col produto encoding=R
# col quantidade encoding=L
# col valor encoding=R
```
Bytes: ~80 B. Legível mas verboso.

### B. Lista compacta com código
```
# enc: D, R, L, R
```
Bytes: ~20 B. Boa relação clareza/tamanho.

### C. String contínua (1 char por coluna)
```
# enc: DRLR
```
Bytes: ~12 B. Mais compacto, menos legível.

### D. Bitmask binário
```
# enc: 010, 001, 000, 001
```
Bytes: ~28 B. Mais espaço para extensão; redundante para humanos.

### E. Run-length no header (proposta do usuário)
Vírgulas vazias = "mesmo da anterior":
```
# enc: D,, L, R
```
significa `D, D, D, L, R` (3 D, 1 L, 1 R). Útil em datasets com muitas colunas
de mesmo encoding.

Para 4 colunas: `# enc: D,, L, R` = ~16 B.
Para 100 colunas onde 95 são D e 5 são L: `# enc: D,,,,,...,L,L,L,L,L` ainda
fica grande. Melhor versão run-length explícita: `# enc: 95D 5L` = ~12 B.

### F. Bitmask como inteiro empacotado

Se cada coluna tem 3 bits, 4 colunas = 12 bits = 1.5 bytes binários (não-textual).
Em hex: 12 bits = 3 chars hex = `# enc: A48` (010 001 000 001 → A48 padded).
Mais compacto mas ilegível para humano e impossível para LLM ler. **Rejeitado**
para o objetivo do TCF (legível).

---

## Comparação prática

Para o vencedor de H1 (sort valor,produto,qty + C11-híbrido = 348 B):

| Notação | Header bytes | Total | Overhead |
|---|---|---|---|
| Sem header (auto-detect) | 0 | 348 | 0% |
| A. Verbose | ~80 | 428 | 23% |
| B. Lista compacta | ~20 | 368 | 5.7% |
| C. String contínua | ~12 | 360 | 3.4% |
| D. Bitmask 3-bit | ~28 | 376 | 8% |
| E. Run-length virgula | ~16 | 364 | 4.6% |

Para 30 linhas, qualquer header é ≥3% de overhead. Para 1000 linhas, mesmo
header verbose vira <1%.

---

## Vale a pena ter o header?

### Sim, em 4 cenários

1. **Decoder simples** — sem inferir, sem ambiguidade. Útil para libs minimalistas
   ou para servidor "burro" que só transmite (H7 da mesa de transporte).
2. **Datasets com colunas ambíguas** — se um valor literal coincide com sintaxe
   de RLE (`3*5` é literal "3 vezes 5" ou valor literal `3*5`?), o header
   resolve sem ambiguidade.
3. **Validação semântica** — encoder declara `R`, decoder verifica que vê
   só padrão `N*valor`. Detecção de bug/corrupção precoce.
4. **Quebra/streaming futura** — quando chunks viajam separados, cada chunk
   pode ter seu próprio header local declarando a estratégia daquele pedaço.

### Não, em 3 cenários

1. **Auto-detecção é trivial** — basta ler primeira linha de cada coluna
   para decidir o modo. Custo zero de inferência.
2. **Datasets curtos** — overhead relativo grande.
3. **Quando a estratégia é uniforme** — se todas as colunas usam D,
   `# enc: D,,,, ` agrega pouco vs convenção implícita "default = D".

---

## Combinatória header + multi-sort

Header pode declarar tanto a estratégia de codificação quanto o sort key
usado no encoding:

```
# sort: valor, produto, quantidade
# enc:  D, R, R, R       ← nome=D, produto=R, qty=R, valor=R
```

Decoder lê o header → sabe que dados foram sortidos por (valor, produto, qty);
o cliente, se quiser, pode re-sortar por outro critério após decode (ou só
manter a ordem de chegada se for satisfatório para a query).

Total com sort + enc declarados:
- header expandido: ~50 B
- corpo: 348 B
- total: ≈ 398 B

Overhead 14% para 30 linhas. Em 10000 linhas viraria <0.5%.

---

## Conclusão de H2

### Resposta às perguntas iniciais

1. **Header economiza bytes?** Não. Adiciona overhead (3-15%).
2. **Quando vale a pena?** Quando o ganho não é em bytes mas em:
   - simplicidade do decoder
   - ausência de ambiguidade
   - validação semântica
   - amortização em streaming/chunked
3. **Auto-detecção é suficiente?** Suficiente para casos comuns. Falha em
   ambíguos (raros) e em decoders simples (deliberadamente burros).
4. **Header expande L0/L1/L2/L3?** Sim — em vez de 1 nível por arquivo, dá
   1 código por coluna. O "nível" do TCF vira **vetor**, não escalar.

### Recomendação

Adotar **notação B (lista compacta)** como default opcional:
```
# enc: D, R, L, R
```

- Curta (~20 B), legível
- Permite extensão para múltiplos formatos
- Interoperável (parser simples, robusto a colunas extras)
- Compatível com auto-detect: se o header não estiver presente, decoder
  infere; se estiver, decoder usa

A notação E (vírgulas-repetição) é boa adição para datasets com muitas
colunas iguais — `# enc: D,,,, R` para "4 dicts e 1 RLE" — mas só vira
necessária com >10 colunas.

### Risco da extensão futura

Códigos `100`-`111` reservados são tentadores ("podemos colocar tudo"). Mas
cada código novo precisa de regra clara de parsing. A boa prática:
- adicionar code só após validar empiricamente que ele ganha em algum cenário
- nunca usar code sem documentação no header (ex: `# enc-version=2` se
  modos novos quebrarem compatibilidade)

Isso evita o "feature creep" do formato.
