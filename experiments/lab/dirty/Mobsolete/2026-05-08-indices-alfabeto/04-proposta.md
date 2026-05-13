# Proposta — alfabeto na hierarquia Lxxx

Como integrar a escolha de alfabeto à proposta da mesa de síntese
(`../2026-05-08-sintese-formato/`).

---

## Nova flag

Adicionar à hierarquia de flags Lxxx:

```
A = alfabeto adaptativo do índice
```

Como as outras flags (`R`, `D`, `M`, `δ`, `P`, `L'`, `K`), `A` é
**opt-in**. Default: ausente → encoder usa decimal (compatibilidade).

Quando ativada, encoder escolhe per-coluna:
- coluna alfabética → decimal (sem ganho real, mas consistente com domínio)
- coluna numérica → letras a-z (elimina marcador `:`)
- coluna mista → fallback para decimal+marcador

Sub-modos possíveis (se quisermos refinar):
- `A`         — auto (encoder decide per-coluna)
- `A=letters` — força letras em todas as colunas onde cabem
- `A=hex`     — força hex
- `A=mixed`   — letras em numéricas, decimal em alfabéticas (= `A` auto)

Provavelmente: manter só `A` (auto) para v0.5, deixar variantes para
versões futuras.

---

## Hierarquia Lxxx atualizada

| Lxxx | Flags | Significado |
|---|---|---|
| L0 | ∅ | literal apenas (ablação) |
| L1 | R | + RLE (ablação) |
| L2 | D | + dict (ablação) |
| **L3** | **RDM** | **regra unificada (produção default)** |
| L3+S | SRDM | + sort |
| **L3+SA** | **SRDMA** | **+ sort + alfabeto adaptativo (produção otimizada)** |
| L4δ | SRDMA δ | + delta |
| L4P | SRDMA P | + prefix |
| L5 | SRDMA δP | + ambas extensões |
| L6 | L'RDMA | line-RLE |
| L7 | SRDMAK | streaming |

Adição da flag `A` é não-disruptiva. Pode ser ligada/desligada
independentemente.

---

## Header com alfabeto declarado

```
# TCF v0.5 SRDMA sort=valor,produto,qty
```

Encoder pode opcionalmente declarar **qual alfabeto** por coluna:

```
# TCF v0.5 SRDMA sort=valor,produto,qty
# alpha: nome=dec, produto=dec, qty=letters, valor=dec
```

(Ou ausência → decoder infere pelo conteúdo, como faz com discriminação
bare/marcado.)

### Regra de inferência (sem header)

Decoder vê os caracteres usados em refs:
- Só dígitos → decimal
- Letras a-z (apenas) → letras
- Mistura ou ASCII estendido → marcador presente, é decimal+marcador

Heurística simples, robusta.

---

## Exemplo prático

Coluna `quantidade` com flag `A=auto`:

### Encoded (sort valor, produto, qty)

```
quantidade:
15
2*20
25
30
3*4
2*8
4*10
b               ← idx 2 (letra) = 20, em vez de :2 (3B → 2B)
2*12
4*5
2*3
2*5
3
2
3*1
```

Bytes: 54 (vs 55 com decimal+marcador). 1B economizado nesta coluna.

### Mapa idx → valor (implícito, decoder constrói)

| idx | valor |
|---|---|
| a | 15 |
| b | 20 |
| c | 25 |
| d | 30 |
| e | 4 |
| f | 8 |
| g | 10 |
| h | 12 |
| i | 5 |
| j | 3 |
| k | 2 |
| l | 1 |

Decoder vê `b` na pos 8 → consulta mapa → resolve como `20`.

---

## Tabela cruzada — quando ligar `A`

| Cenário | Ligar `A`? |
|---|---|
| Coluna numérica + cardinalidade ≥ 10 | **sim**, ganho real |
| Coluna numérica + cardinalidade ≤ 9 | tanto faz, default decimal já é ótimo |
| Coluna alfabética com qualquer cardinalidade | tanto faz |
| Pipeline com gzip downstream | possivelmente NÃO (gzip recupera parte) |
| Pipeline para LLM direto | **sim**, ganho integral |
| Cardinalidade muito alta (≥ 100) | considerar base64 (extensão futura) |

---

## Pontos de domínio matemático

Aplicando a mesma análise de domínio que fizemos antes:

### Alfabeto domina vs decimal quando

- Coluna numérica: letras dominam (elimina `:`)
- Cardinalidade no "trecho útil": letras dominam para 10-26, base64 para
  10-64 etc.

### Alfabeto NÃO domina (empata) quando

- Cardinalidade ≤ 9 e domínio alfabético: decimal já é 1 char/idx
- Coluna primária do sort (zero refs)

### Alfabeto perde quando

- Apenas se forçar ALFABETO ERRADO (tipo letras numa coluna que tem
  valores começando com letra). Auto-detect evita.

→ A flag `A` tem ganho ≥ 0 sempre. **Pode ser sempre ligada em
produção** sem risco (com auto-detect adequado).

---

## Recomendação final

### v0.5 default

```
flags = SRDMA  (sort + RLE + dict + auto-discrim + auto-alphabet)
```

Todas as flags ortogonais "ligadas por default" são:
- S (sort, com chaves auto-decididas pelo encoder)
- R (RLE)
- D (dict implícito)
- M (auto-discrim bare/marcado)
- A (auto-alfabeto)

Extensões (δ, P, L', K) ficam **opt-in** porque dependem do tipo de
dado. Não há risco de regressão se ausentes.

### Compatibilidade v0.4

TCF v0.4 não tinha alfabeto adaptativo. Decoder v0.5 lê v0.4 com decimal
forçado. Encoder v0.5 escreve com `A` ligado por default; arquivos v0.5
não são lidos por v0.4 se houver letras em refs (flag `A` declara isso).

---

## Próximas mesas pendentes (atualizado)

1. **Validar empiricamente** o ganho de `A` em datasets reais (TPC-H,
   logs com cardinalidades ≥ 50).
2. **Discutir extensões** δ, P, L' em mesas dedicadas.
3. **Voltar à mesa de transporte** — chunks, prioridade, paralelismo —
   agora que o formato base (`SRDMA`) está estável.
4. **Protótipo Python** do encoder com flags `SRDMA`.
