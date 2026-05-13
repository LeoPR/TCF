# Conclusões — H1 + H2 combinadas

---

## Tabela mestre cruzada

| Estratégia | Bytes | vs C1 (762) | Notas |
|---|---|---|---|
| C1 CSV | 762 | — | baseline |
| C2 col literal | 704 | -8% | só transposição |
| Unordered + C11-híbrido | 415 | -45% | sem sort |
| Sort-nome | 387 | -49% | RLE só em nome |
| Sort-produto | 379 | -50% | RLE em produto + qty parcial |
| Sort-valor | 369 | -52% | RLE em 3 colunas |
| (produto, valor) | 353 | -54% | multi-sort 2 chaves |
| (valor, produto) | 352 | -54% | + fusão Caneta×7 |
| (produto, valor, qty) | 349 | -54% | 3 chaves |
| **(valor, produto, qty)** | **348** | **-54%** | **vencedor de bytes puros** |
| + header notação B | 368 | -52% | trade bytes por explicitude |
| Cota teórica | ~100 | -87% | entropy + dict |

---

## A pergunta central: existe regra estável de quando RLE+DICT vale?

**Resposta empírica:** sim, e é decidível por característica local da coluna,
**após** ter escolhido a ordem.

### Fluxograma para o encoder (1 passada por coluna após sort)

```
Para cada coluna C, após o sort decidido:
  contar runs ≥ 2 e seus tamanhos
  contar valores únicos
  
  se cardinalidade == n_linhas:
      → L0 (literal)
  
  senão se max_run >= 3 OU >50% das linhas estão em runs ≥ 2:
      → R (RLE)
  
  senão se valores são strings ou numéricos com decimal (não colidem com idx):
      → D (dict-bare implícito)
  
  senão se valores são inteiros puros (colidem com idx):
      se cardinalidade < 30% das linhas:
          → M (dict marcado, ex: ":N")
      senão:
          → L0 (overhead supera ganho)
```

Este fluxograma reproduz **todas** as escolhas C11-híbridas que vimos nos
testes desta mesa e da anterior. É a "regra estável" da hipótese.

### Onde o fluxograma falha (cenários a estudar depois)

1. **Datasets com timestamps sequenciais ou IDs com prefixo comum** — nem
   RLE nem dict atacam isso bem. Precisaria de modos δ (delta) ou P (prefix).
2. **Linhas duplicadas inteiras** — RLE no nível da linha inteira (não da
   coluna) seria mais eficiente. Não testado.
3. **Cardinalidade mista por bloco** — uma coluna que é L0 numa parte e D
   noutra. Hoje o encoder escolhe um único modo por coluna; futuro: modo
   por bloco/chunk.

---

## Sort: a regra prática

Multi-sort de 2-3 chaves vence sort solo, MAS:

- Ganho marginal cai rápido (16B → 4B → <2B).
- Sub-sort em coluna não-correlacionada é placebo.
- Ordem das chaves importa pouco (1-2 B), mas há heurística:
  **primeira chave deve ser a que maximize a soma de runs em todas as
  colunas correlacionadas.**

→ Para nosso dataset: valor é a melhor primeira chave porque correlaciona
com produto E quantidade. Para datasets onde uma coluna domina correlação
com todas as outras (ex: `customer_id` em sistema de vendas), essa é a
escolha óbvia.

### Limite teórico de sort completo

Sort por todas as 4 colunas é determinístico mas só ajuda quando há linhas
duplicadas exatas. No nosso dataset (sem duplicadas), 4ª chave é redundante.
Em logs ou eventos com repetições exatas, multi-sort completo + RLE de linha
inteira vira poderoso. Reservar para outra mesa.

---

## Cabeçalho: quando declarar?

### Tabela de decisão

| Situação | Header recomendado |
|---|---|
| Dataset pequeno, sem ambiguidade, decoder esperto | **omitir** (auto-detect) |
| Dataset grande (>1000 linhas), decoder simples | **B (compacto)** |
| Streaming/chunked com chunks que mudam estratégia | **B + por-chunk** |
| Dados podem conter sintaxe ambígua (`3*5` literal) | **B obrigatório** |
| Validação/auditoria (gateways, pipelines) | **A (verbose) ou B+sort** |

### Default proposto

Header opcional. Se ausente, decoder usa heurística por coluna (a 1ª linha
de cada coluna decide o modo). Se presente, decoder confia no declarado.
Erro silencioso vira erro explícito.

---

## Implicação para o formato TCF v0.4+

A combinação H1+H2 permite redefinir o que "nível L0/L1/L2/L3" significa:

### Antes (escalar)
```
# TCF v0.4 lv=2     ← um nível para o arquivo todo
```

### Depois (vetor)
```
# TCF v0.5
# sort: valor, produto, quantidade
# enc:  D, R, R, R
```

`enc` é o "nível por coluna", `sort` declara a ordem aplicada, e ambos são
**opcionais** (defaults inferidos se ausentes).

### Compatibilidade

- TCF v0.4 sem header de enc/sort = decoder infere.
- TCF v0.5 com header = decoder lê e usa.
- Migração suave — versão velha continua funcionando, versão nova adiciona
  precisão.

---

## Próximos passos

1. **Validar regra do fluxograma** num dataset de cardinalidade radicalmente
   diferente (ex: 1000 nomes únicos vs 5 — extremos).
2. **Testar modos reservados** (δ, P) num dataset com timestamps ou IDs
   estruturados.
3. **Linha-RLE** num dataset com duplicadas exatas (logs, telemetria).
4. **Implementar a heurística do encoder** num pequeno protótipo Python
   antes de mexer no encoder real.
5. **Discutir adoção da notação `enc:`** como decisão de v0.5 — abrir ticket.

A mesa cumpriu seu propósito: agora há uma **regra decidível** para
RLE/DICT/literal por coluna, e um espaço de design claro para o header.
Antes de partir para Fase 2 (motores) da pasta de transporte, vale fechar
esses pontos como decisões de formato (ou abrir ticket por cada).
