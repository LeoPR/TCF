# Conclusões da mesa δ (delta) — integração com Lxxx

---

## O que ficou claro

### Delta é uma transformação pré-encoding, não um modo competitivo

Delta NÃO substitui RLE/dict. Ele é um pré-passo que **transforma valores
únicos sequenciais em valores repetitivos derivados**. Depois do delta, a
regra unificada (RLE+dict) aplica-se normalmente sobre os deltas.

```
Coluna original (datas únicas)
    ↓ transformação δ
Coluna delta (valores derivados, mais repetitivos)
    ↓ regra unificada (RLE + dict refs)
Coluna codificada (compacta)
```

Composição limpa. Modular. Ortogonal.

### Delta tem dois ganhos distintos

1. **Representação curta**: `+1` (3B) vs `2026-01-06` (10B). Ganho
   **independente** de RLE/dict.
2. **Padrões repetitivos induzidos**: deltas iguais (`+1, +1, +1` ou
   `0, 0, 0`) viram RLE eficiente. Ganho **dependente** da ordem.

Em ordem cronológica, ambos atuam. Em ordem errada, só o primeiro.

### Delta não cobre tudo

Falha em:
- Datas aleatórias sem ordem temporal (deltas grandes e imprevisíveis,
  representação curta ainda ajuda mas RLE/dict não)
- Coluna não-numérica em sentido temporal (precisa de outras transformações)

---

## Posição do δ na hierarquia Lxxx

A flag `δ` foi reservada na mesa de síntese. Confirma-se útil:

```
L4δ = SRDMAδ
    = sort + RLE + dict + auto-discrim + auto-alphabet + delta
```

Ativação: per-coluna, declarada no header.

```
# TCF v0.5 SRDMAδ sort=data,produto,qty
# ext: data=delta
```

`# ext:` lista as colunas que recebem transformação delta antes da
regra unificada. Outras colunas seguem normalmente.

---

## Quando o encoder ativa `δ`

Heurística sugerida:
1. Coluna tem tipo data/timestamp/numérico crescente?
2. Cardinalidade alta (>30% das linhas) — repetição de literais é baixa?
3. Maioria das transições (>70%) é monotônica (ascendente ou descendente)?

Se sim → ativa delta. Caso contrário, mantém absolutos.

Métrica de decisão:
```
score(coluna) = bytes(absolutos com unified) - bytes(deltas com unified)
ativa δ se score > 0
```

Encoder pode rodar AMBAS em uma passada e escolher a menor.

---

## Sintaxe consolidada para v0.5 com δ

### Header

```
# TCF v0.5 SRDMAδ
# sort: <chaves>
# ext: <coluna>=delta[, <coluna>=prefix, ...]
```

Múltiplas extensões por header, uma flag global `δ` (ou `P`, `L'`, `K`)
para sinalizar presença.

### Linha de coluna delta

```
<absoluto>          ← declaração inicial (1ª linha) ou reset
+<n>                ← delta positivo
-<n>                ← delta negativo
0                   ← delta zero (mesma data anterior)
N*<delta>           ← RLE de delta literal
<ref>               ← ref bare ao dict implícito de deltas
N*<ref>             ← RLE de refs
```

### Decoder rules

Linha:
- Tem hífens em posições típicas de data (5ª e 8ª) → absoluto
- Começa com `+` ou `-` → delta literal
- É só `0` → delta zero
- Tem só dígitos → ref bare ao dict de deltas
- Começa com `N*` → run length, restante é literal/delta/ref conforme acima

---

## Demais extensões (status)

### P (prefix elision)

Análoga a δ mas para strings com prefixo comum (`INV-001`, `INV-002`...).
Mesmo padrão de transformação pré-encoding. Próxima mesa quando dataset
trouxer esse caso.

### L' (line-RLE)

Mais radical: muda o LAYOUT (column-major → line-RLE quando linhas
inteiras se repetem). Não é "transformação por coluna" — afeta toda a
estrutura. Ticket separado.

### K (count + reciclagem)

Ortogonal. Para streaming. Já desenhada na mesa de dict implícito (C12).

---

## Comparação cumulativa do dataset (todas mesas)

| Mesa / variante | Bytes (4 ou 5 colunas) | Notas |
|---|---|---|
| C1 (CSV) — 4 colunas | 762 | baseline original |
| C11-híbrido sort-(valor, produto, qty) — 4 colunas | 348 | mesa de multisort |
| Regra unificada — 4 colunas | 342 | mesa de síntese |
| Regra unificada + flag A — 4 colunas | 341 | mesa de alfabeto |
| **Regra unificada + δ data — 5 colunas** | **409** | **adiciona coluna inteira por +67 B** |
| Sem delta, 5 colunas | 598 | absoluto seria 67% maior |

Coluna `data` adiciona muito ao dataset, mas com δ o custo é proporcional
ao **conteúdo informacional** dela, não ao número de bytes literais.

---

## Hipóteses ainda em aberto

| ID | Hipótese | Como testar |
|---|---|---|
| H-δ5 | δ não ajuda em datas aleatórias | dataset com datas shuffled completamente |
| H-δ6 | δ funciona com timestamps (segundo de precisão) | adicionar coluna timestamp ao dataset |
| H-δ7 | δ + sort por delta é ainda melhor que sort por data | testar — sort=δ ordena pela diferença, não pelo absoluto |
| H-δ8 | encoder pode escolher AUTOMÁTICA pela métrica score | implementar protótipo |

---

## Direção futura (priorizada)

1. **Mesa P (prefix elision)** — análoga, para colunas tipo `INV-001`
2. **Mesa L' (line-RLE)** — quando há linhas inteiras duplicadas
3. **Voltar à mesa de transporte** (`2026-05-07-hipoteses-transporte`) —
   chunks, prioridade, paralelismo, agora que o formato base está estável
4. **Protótipo Python** — implementar L3+SA com δ ativável por coluna

A regra unificada com flags ortogonais (S, R, D, M, A, δ, e mais quando
testarmos) está se consolidando como **base estável e composicional** do
TCF v0.5.

---

## Lições da mesa para o framework geral

1. **Transformações pré-encoding** (δ, P) são modulares e não conflitam
   com a regra unificada. Boa decisão arquitetural.
2. **Per-coluna sempre vence per-arquivo** — δ se ativa onde ajuda,
   permanece desligado onde não.
3. **Ordem de operações importa**: sort → transformação → encoding. Cada
   estágio reduz a entropia para o seguinte.
4. **Padrões "esquisitos" da realidade** (mesmo-dia + sequencial + gap)
   são bem cobertos pela combinação. Mistura de padrões é o caso comum,
   não o exceção.
