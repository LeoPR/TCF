# Custo de marcadores, refs e índices — nota conceitual

Data: 2026-05-11
Contexto: discussão durante exp 14 → 15.

Esta nota registra **ideias teóricas** sobre como contabilizar o custo
de marcadores (refs, índices, separadores) numa estrutura de
compressão. Não é especificação fechada; é base conceitual para
avaliar experimentos futuros sem perder o fio.

---

## A separação central

A estrutura comprimida tem **3 tipos de coisa** que ocupam espaço:

| Tipo | Custo | Comportamento |
|---|---|---|
| **Dados efetivos** | proporcional ao conteúdo, em bytes/chars | fixo — Ana ocupa 3 chars sempre |
| **Marcadores de divisão** (`*`, `[`, `:`, etc.) | sintáticos, custam algo para "marcar" que dado está segmentado | dependem da gramática do formato |
| **Refs/índices/nós** (`no1`, `R1`, posição lógica) | **elásticos** — variam de quase-zero a alguns bytes | depende de como são representados |

A regra: **dados efetivos** entram na conta sempre (são o "payload").
**Marcadores** e **refs** entram na conta **só depois que a estrutura
está fechada e prestes a ser emitida** (no momento do "soltar o body").

---

## Por que refs são elásticos

Diferentes representações de uma ref custam diferente:

- `no1` (notação atual) — 3 chars
- `1` (índice nu) — 1 char (se contexto deixa claro)
- byte binário — 1 byte para 256 refs, 2 bytes para 65k
- **posição lógica** — 0 bytes (deduzido pela ordem)

Na fase atual (dirty, sintaxe verbosa) refs custam 3-9 chars. Na
fase prototype (compacto) custariam 1-2 bytes. No limite ideal, podem
custar zero — apenas pela posição que ocupam.

---

## Onde marcadores aparecem

Dois tipos principais:

1. **Marcador de declaração** — diz que um dado vai ser segmentado e
   ganhar identidade reutilizável. Custa algo (ex: `*` antes do
   fragmento que recebe id implícito). Vale a pena se o que segue
   vai ser referenciado N vezes onde `N * ganho_por_ref > custo_marcador`.

2. **Marcador de uso** — referencia algo já declarado. Idem: vale
   se o que economiza ao não duplicar texto compensa o overhead.

---

## A conta heurística

Para decidir se vale criar uma ref para fragmento `f` que aparece `N`
vezes:

```
ganho_por_uso  = len(f) − custo_ref
ganho_total    = N * ganho_por_uso  −  custo_marcador_decl
vale_se        = ganho_total > 0
```

Hoje (sintaxe verbosa): `custo_ref ≈ 3-9 chars`, `custo_marcador ≈
10-20 chars`. Limiar relativamente alto — só vale para fragmentos
longos com muitas ocorrências.

Futuro (sintaxe compacta): `custo_ref ≈ 1-2 bytes`, `custo_marcador
≈ 1-3 bytes`. Limiar baixo — vale para fragmentos curtos com poucas
ocorrências.

---

## Casos de dedução implícita

Em alguns esquemas, refs podem ser **deduzidas pelo contexto** sem
custar marcador:

- **Numeração por ordem de aparição**: `no1`, `no2`, `no3` deduzidos
  pela posição na sequência → o `no` em si não precisa ser escrito.
- **RLE como ref de linha natural**: cada linha já tem um "número de
  linha" implícito; sequências de linhas iguais podem ser
  compactadas sem ref explícita.
- **Inferência por gramática**: se o decoder sabe que após um
  separador X só vem do tipo Y, a ref de tipo é dedutível.

Esses esquemas **trocam complexidade do decoder por bytes
economizados** no encode.

---

## Implicação para experimentação

Ao comparar 2 algoritmos de compressão:

1. **Bytes literais hoje** (sintaxe verbosa) não é métrica fiel — a
   sintaxe polui a comparação.
2. **Unidades de informação** (1 ref = 1 unidade; 1 char dado =
   1 unidade) aproxima melhor o que o formato compacto custaria.
3. **Curva de elasticidade**: alguns esquemas perdem hoje (custo
   alto de ref) mas vencem com refs compactas. Outros já vencem
   hoje. A análise precisa considerar ambos os regimes.

---

## Sobre a proporção entre trocas

Em alguns casos a comparação entre 2 esquemas depende menos do valor
exato do custo_ref e mais da **proporção** entre o que muda:

- Se algoritmo A produz 10 refs e B produz 8 refs (sob mesma sintaxe),
  A perde por 2 refs — independente de cada ref custar 2 ou 5 bytes.
- A proporção 8/10 = 0.8 é a métrica relevante; o byte exato é
  segunda ordem.

Quando o ganho é grande, valor exato do custo_ref pode ser ignorado
para tomada de decisão.

---

## Pontos abertos para investigação futura

1. **Limiar de marcador**: para cada formato/sintaxe, qual o `N`
   mínimo (ocorrências) para valer criar ref?
2. **Esquemas de dedução**: quais esquemas de ref implícita
   (numeração por ordem, posição lógica) são viáveis sem perder
   roundtrip?
3. **Curva de elasticidade**: como tabela o "byte de ref"
   afeta a escolha de melhor algoritmo entre Re-Pair (exp 13),
   online sem revisão (exp 14), online com fix (exp 15), etc.?
4. **Inferência inteligente**: compressor que detecta quando
   marcador vale a pena por dataset, calibrando dinamicamente.

---

## Como aplicar agora (até o prototype)

Em experimentos do dirty:

- Reportar **bytes literais** (medição direta) — útil para inspeção
- Reportar **unidades de informação** (1 ref = 1 unidade) — útil
  para comparação intrínseca
- Convenção das 4 camadas continua válida; esta nota refina **como
  contar a camada 2 (marcadores de ref)** quando comparando entre
  algoritmos diferentes.

Quando experimentos futuros aplicarem sintaxe compacta (fase
prototype), reportar bytes nas duas formas (verbosa e compacta) para
ver de fato o ganho.
