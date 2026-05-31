# Regra mínima — o que sobra como base do formato

Depois de eliminar tudo que é dominado, sobra um formato compacto e
modular. Este arquivo define a especificação mínima.

---

## Sintaxe da regra unificada

### Linha de coluna

Cada linha do corpo de uma coluna é uma das 4 formas:

```
<v>            ← 1 ocorrência literal
N*<v>          ← N ocorrências contíguas literais
<r>            ← 1 referência (idx já declarado)
N*<r>          ← N referências contíguas
```

Onde:
- `<v>` é um valor textual (string ou número)
- `<r>` é um inteiro (referência a idx já declarado nesta coluna)
- A 1ª aparição de cada `<v>` na coluna recebe automaticamente o próximo
  idx disponível (1, 2, 3, ...)
- `N` é um inteiro ≥ 2 (a forma `1*x` é proibida; usar `x` direto)

### Discriminação literal vs ref

O encoder detecta automaticamente o domínio da coluna na 1ª varredura:

| Domínio | Modo | `<r>` aparece como |
|---|---|---|
| Strings ou numéricos com decimal (não colidem com inteiros) | bare | `1`, `2`, ... |
| Inteiros puros (colidem com indices) | marcado | `:1`, `:2`, ... |

Header opcional pode declarar o modo explicitamente; ausência → auto.

### Layout do arquivo

```
<col_1>:
<linhas codificadas da coluna 1>
<col_2>:
<linhas codificadas da coluna 2>
...
```

Cada bloco de coluna começa com `<nome>:` e termina implicitamente quando
começa o próximo `<nome>:` (ou no fim do arquivo).

---

## Parâmetros declarados em header (opcionais)

```
# TCF v0.5
# sort: <chaves separadas por vírgula>
# discrim: <modo por coluna, opcional>
# ext: <extensões por coluna, opcional>
```

### Sort

Declara ordem em que as linhas foram organizadas. Útil para o cliente
saber se precisa re-sortar. Sem `# sort:`, dados estão na ordem original
da fonte.

```
# sort: valor, produto, qty
```

### Discrim

Declara o modo de discriminação por coluna quando auto-detecção pode
falhar. Sem header, decoder infere.

```
# discrim: nome=bare, qty=marked
```

(Colunas omitidas usam auto-detect.)

### Ext

Declara extensões aplicadas por coluna. Sem header, nenhuma extensão.

```
# ext: timestamp=delta, invoice_id=prefix
```

---

## Extensões ortogonais (opt-in)

Cada extensão é uma **transformação aplicada antes da regra unificada** ou
um **modo de layout** alternativo.

### δ (delta) — sequências aritméticas

Antes da regra unificada, transformar a coluna em deltas:

```
Original:    2026-01-01, 2026-01-02, 2026-01-03, 2026-01-05
Delta:       2026-01-01, +1d, +1d, +2d
Após RLE:    2026-01-01, 2*+1d, +2d
```

Decoder reverte: lê 1º valor + acumula deltas.

Escopo: aplicado por coluna. Header declara `# ext: <col>=delta`.

### P (prefix elision) — prefixo comum

Antes da regra unificada, extrair prefixo comum da coluna:

```
Original:    INV-001, INV-002, INV-003, INV-004
Prefix:      INV-
Tail:        001, 002, 003, 004
Após δ+RLE:  001, 3*+1
```

Decoder concatena prefix + tail por linha.

Escopo: aplicado por coluna. Header declara `# ext: <col>=prefix:INV-`
(prefixo declarado explicitamente).

### L' (line-RLE) — linhas duplicadas inteiras

Modo de layout alternativo. Aplicado quando o dataset tem linhas
inteiras repetidas. Em vez de column-major, escreve:

```
@row 3* | Ana | Caneta | 10 | 1.50
```

Significa "essa linha aparece 3 vezes contiguamente".

Escopo: arquivo todo (não por coluna). Header declara
`# layout: line-rle` no topo.

### Count-recycling (C12) — streaming de longa duração

Já documentado em mesa anterior. Para streaming, declarações trazem count
e índices podem ser reciclados quando esgotam.

Escopo: opcional, ativado em chunks de stream. Header declara
`# ext: <col>=counted`.

---

## Flags de ablação (não-produção)

Apenas para experimentação científica:

```
# ablate: force=literal     ← desliga RLE e refs (encoder emite tudo literal)
# ablate: force=rle-only    ← desliga refs (encoder emite só literais e RLE)
# ablate: force=dict-only   ← desliga RLE em literais (encoder emite refs sem N*)
```

Em produção, sem `# ablate:`. Encoder usa a regra unificada plena.

A presença de `# ablate:` torna o arquivo **não-canônico**: explicitamente
sub-ótimo para fins de comparação. Decoder lê normalmente.

---

## O que o decoder precisa fazer

### Mínimo (sem header)

1. Ler `<col>:` linha
2. Para cada linha do corpo:
   - Se começa com `N*`: parse run length, restante é valor ou ref
   - Se é inteiro puro (e coluna tem modo bare): é ref
   - Senão: é literal, declarar idx se 1ª aparição
3. Manter mapa idx→valor enquanto lê a coluna
4. Resolver refs ao mapa
5. Emitir para o cliente as linhas decodificadas

### Com header (opt-in)

Decoder pode usar `# discrim:` para definir modo bare/marcado sem inferir.
Decoder pode usar `# ext:` para aplicar transformações inversas (delta,
prefix) antes de devolver ao cliente. Decoder pode aplicar `# sort:` como
informação para o cliente (não muda o decode em si).

---

## Hierarquia mínima

```
TCF v0.5 = {
  layout: column-major | line-rle           # default: column-major
  encoding: regra-unificada                 # único
  sort: lista de chaves (opcional)          # default: ordem da fonte
  discrim: por coluna (opcional)            # default: auto
  ext: por coluna (opcional)                # default: nenhuma
  ablate: flags experimentais (opcional)    # default: nenhuma (produção)
}
```

Esses são os 6 eixos do formato. **Nenhum modo discreto** (L0/L1/L2/L3
desaparece). O encoder aplica a regra unificada e os parâmetros decidem
variações.

A próxima etapa (`03-lxxx-proposta.md`) define como descrever isso no
header de forma compacta, e como nomear "níveis" se ainda for desejável
(p.ex. para benchmarking).
